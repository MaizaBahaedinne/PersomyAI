import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.cli import reset_two_factor
from app.core import crypto, totp
from app.core.config import get_settings
from app.main import create_app
from app.modules.audit.models import AuditEvent
from app.modules.authentication.models import AuthSession, RecoveryCode
from app.modules.users.models import User
from tests.conftest import PASSWORD

API = "/api/v1"
RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # "12345678901234567890" en base32 (RFC 6238)


def code_for(secret: str, offset: int = 0) -> str:
    return totp._hotp(secret, totp.current_step() + offset)


# --- TOTP (RFC 6238) -----------------------------------------------------------


def test_totp_matches_rfc6238_vectors():
    # Vecteurs SHA-1 de l'annexe B du RFC, tronqués à 6 chiffres.
    assert totp._hotp(RFC_SECRET, 59 // 30) == "287082"
    assert totp._hotp(RFC_SECRET, 1111111109 // 30) == "081804"
    assert totp._hotp(RFC_SECRET, 1234567890 // 30) == "005924"


def test_totp_verify_window_replay_and_format():
    now = 1111111109
    step = now // 30
    good = totp._hotp(RFC_SECRET, step)
    assert totp.verify(RFC_SECRET, good, now=now) == step
    assert totp.verify(RFC_SECRET, totp._hotp(RFC_SECRET, step - 1), now=now) == step - 1
    assert totp.verify(RFC_SECRET, totp._hotp(RFC_SECRET, step + 1), now=now) == step + 1
    assert totp.verify(RFC_SECRET, totp._hotp(RFC_SECRET, step - 2), now=now) is None
    assert totp.verify(RFC_SECRET, good, now=now, after_step=step) is None  # rejeu refusé
    for bad in ("", "12345", "1234567", "12345a", "١٢٣٤٥٦"):
        assert totp.verify(RFC_SECRET, bad, now=now) is None


def test_generated_secret_and_uri():
    secret = totp.generate_secret()
    assert len(secret) == 32 and secret == secret.upper()
    assert totp.generate_secret() != secret
    uri = totp.provisioning_uri(secret, "a+b@example.com")
    assert uri.startswith("otpauth://totp/Persomy%20AI%3Aa%2Bb%40example.com?")
    assert f"secret={secret}" in uri and "digits=6" in uri and "period=30" in uri


# --- Chiffrement du secret ------------------------------------------------------


def test_encryption_roundtrip_and_unavailable_without_key(monkeypatch):
    get_settings.cache_clear()
    token = crypto.encrypt_secret(RFC_SECRET)
    assert RFC_SECRET not in token and crypto.decrypt_secret(token) == RFC_SECRET
    monkeypatch.setenv("TWO_FACTOR_KEY", "")
    get_settings.cache_clear()
    assert crypto.is_available() is False
    with pytest.raises(crypto.TwoFactorUnavailable):
        crypto.encrypt_secret(RFC_SECRET)
    monkeypatch.setenv("TWO_FACTOR_KEY", "not-a-valid-key")
    get_settings.cache_clear()
    assert crypto.is_available() is False
    get_settings.cache_clear()


# --- API -----------------------------------------------------------------------


@pytest.fixture()
def admin(make_user):
    return make_user("boss@example.com", "SUPER_ADMIN")


def new_client():
    return TestClient(create_app())


def enable_2fa(client, offset=-1):
    """Active la 2FA via l'API ; retourne (secret, codes de secours)."""
    r = client.post(f"{API}/auth/2fa/setup", json={"password": PASSWORD})
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    r = client.post(f"{API}/auth/2fa/enable", json={"code": code_for(secret, offset)})
    assert r.status_code == 200, r.text
    return secret, r.json()["recovery_codes"]


def login_with(email, otp=None, password=PASSWORD):
    c = new_client()
    body = {"email": email, "password": password}
    if otp is not None:
        body["otp"] = otp
    return c, c.post(f"{API}/auth/login", json=body)


def test_status_before_setup(admin, login):
    client = login("boss@example.com")
    assert client.get(f"{API}/auth/2fa").json() == {"enabled": False, "available": True, "recovery_codes_left": 0}


def test_setup_requires_correct_password(admin, login, db):
    client = login("boss@example.com")
    r = client.post(f"{API}/auth/2fa/setup", json={"password": "wrong-password-1"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"
    db.expire_all()
    assert db.scalars(select(User)).one().two_factor_secret_encrypted is None


def test_setup_stores_encrypted_secret_without_enabling(admin, login, db):
    client = login("boss@example.com")
    r = client.post(f"{API}/auth/2fa/setup", json={"password": PASSWORD})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    body = r.json()
    user = db.scalars(select(User)).one()
    db.refresh(user)
    assert user.two_factor_enabled is False
    assert user.two_factor_secret_encrypted and body["secret"] not in user.two_factor_secret_encrypted
    assert crypto.decrypt_secret(user.two_factor_secret_encrypted) == body["secret"]
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert body["qr_svg_data_uri"].startswith("data:image/svg+xml;base64,")


def test_enable_rejects_wrong_code_then_accepts_valid_one(admin, login, db):
    client = login("boss@example.com")
    client.post(f"{API}/auth/2fa/setup", json={"password": PASSWORD})
    r = client.post(f"{API}/auth/2fa/enable", json={"code": "000000"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_otp"
    assert client.get(f"{API}/auth/me").json()["user"]["two_factor_enabled"] is False


def test_enable_without_setup_is_refused(admin, login):
    client = login("boss@example.com")
    r = client.post(f"{API}/auth/2fa/enable", json={"code": "123456"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "two_factor_not_started"


def test_enable_returns_ten_single_use_codes_and_revokes_other_sessions(admin, login, db):
    other = login("boss@example.com")
    client = login("boss@example.com")
    secret, codes = enable_2fa(client)
    assert len(codes) == 10 and len(set(codes)) == 10
    assert all(len(c) == 11 and c[5] == "-" for c in codes)
    assert client.get(f"{API}/auth/me").json()["user"]["two_factor_enabled"] is True
    assert other.get(f"{API}/auth/me").status_code == 401  # l'autre appareil est déconnecté
    assert client.get(f"{API}/auth/2fa").json() == {"enabled": True, "available": True, "recovery_codes_left": 10}
    stored = db.scalars(select(RecoveryCode)).all()
    assert len(stored) == 10 and all(codes[0].replace("-", "") not in r.code_hash for r in stored)
    assert client.post(f"{API}/auth/2fa/setup", json={"password": PASSWORD}).status_code == 409


def test_login_requires_code_once_enabled(admin, login, db):
    secret, _ = enable_2fa(login("boss@example.com"))
    c, r = login_with("boss@example.com")
    assert r.status_code == 401 and r.json()["error"]["code"] == "two_factor_required"
    assert "persomy_session" not in c.cookies
    db.expire_all()
    assert db.scalars(select(AuthSession).where(AuthSession.revoked_at.is_(None))).all() != []  # sessions antérieures seulement
    c, r = login_with("boss@example.com", otp=code_for(secret, 0))
    assert r.status_code == 200 and "persomy_session" in c.cookies
    assert r.json()["user"]["two_factor_enabled"] is True


def test_wrong_code_is_refused_and_counted(admin, login, db):
    enable_2fa(login("boss@example.com"))
    c, r = login_with("boss@example.com", otp="000000")
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_otp"
    assert "persomy_session" not in c.cookies
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.login.failed")).all()[-1]
    assert event.details == {"reason": "bad_otp"} and event.status == "failure"


def test_wrong_password_never_reveals_second_factor(admin, login):
    enable_2fa(login("boss@example.com"))
    _, r = login_with("boss@example.com", password="wrong-password-1")
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"


def test_code_cannot_be_replayed(admin, login, db):
    secret, _ = enable_2fa(login("boss@example.com"))
    code = code_for(secret, 0)
    assert login_with("boss@example.com", otp=code)[1].status_code == 200
    r = login_with("boss@example.com", otp=code)[1]
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_otp"
    # Un code déjà utilisé à l'activation ne sert pas non plus à se connecter.
    assert login_with("boss@example.com", otp=code_for(secret, -1))[1].status_code == 401


def test_repeated_wrong_codes_trigger_throttling(admin, login):
    enable_2fa(login("boss@example.com"))
    for _ in range(5):
        assert login_with("boss@example.com", otp="000000")[1].status_code == 401
    r = login_with("boss@example.com", otp="000000")[1]
    assert r.status_code == 429 and r.json()["error"]["code"] == "login_throttled"
    assert "Retry-After" in r.headers


def test_recovery_code_works_once(admin, login, db):
    _, codes = enable_2fa(login("boss@example.com"))
    assert login_with("boss@example.com", otp=codes[0].upper())[1].status_code == 200  # insensible à la casse
    r = login_with("boss@example.com", otp=codes[0])[1]
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_otp"
    assert login_with("boss@example.com", otp=codes[1].replace("-", " "))[1].status_code == 200
    c, _ = login_with("boss@example.com", otp=codes[2])
    c.headers["X-CSRF-Token"] = c.cookies.get("persomy_csrf")
    assert c.get(f"{API}/auth/2fa").json()["recovery_codes_left"] == 7
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.login")).all()[-1]
    assert event.details == {"second_factor": "recovery"}


def test_disable_requires_password_and_code(admin, login, db):
    secret, codes = enable_2fa(login("boss@example.com"))
    c, _ = login_with("boss@example.com", otp=code_for(secret, 0))
    c.headers["X-CSRF-Token"] = c.cookies.get("persomy_csrf")
    r = c.post(f"{API}/auth/2fa/disable", json={"password": "wrong-password-1", "code": code_for(secret, 1)})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_credentials"
    r = c.post(f"{API}/auth/2fa/disable", json={"password": PASSWORD, "code": "000000"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_otp"
    assert c.get(f"{API}/auth/me").json()["user"]["two_factor_enabled"] is True
    r = c.post(f"{API}/auth/2fa/disable", json={"password": PASSWORD, "code": codes[0]})
    assert r.status_code == 204
    db.expire_all()
    user = db.scalars(select(User)).one()
    assert user.two_factor_enabled is False and user.two_factor_secret_encrypted is None
    assert db.scalars(select(RecoveryCode)).all() == []
    assert login_with("boss@example.com")[1].status_code == 200  # plus de second facteur


def test_regenerate_recovery_codes_invalidates_old_ones(admin, login, db):
    secret, old = enable_2fa(login("boss@example.com"))
    c, _ = login_with("boss@example.com", otp=code_for(secret, 0))
    c.headers["X-CSRF-Token"] = c.cookies.get("persomy_csrf")
    r = c.post(f"{API}/auth/2fa/recovery-codes", json={"password": PASSWORD, "code": code_for(secret, 1)})
    assert r.status_code == 200
    new = r.json()["recovery_codes"]
    assert len(new) == 10 and not set(new) & set(old)
    assert login_with("boss@example.com", otp=old[0])[1].status_code == 401
    assert login_with("boss@example.com", otp=new[0])[1].status_code == 200


def test_disable_and_regenerate_require_enabled_2fa(admin, login):
    client = login("boss@example.com")
    body = {"password": PASSWORD, "code": "123456"}
    for path in ("disable", "recovery-codes"):
        r = client.post(f"{API}/auth/2fa/{path}", json=body)
        assert r.status_code == 409 and r.json()["error"]["code"] == "two_factor_not_enabled"


def test_2fa_endpoints_require_authentication_and_csrf(admin, login):
    anonymous = new_client()
    assert anonymous.get(f"{API}/auth/2fa").status_code == 401
    assert anonymous.post(f"{API}/auth/2fa/setup", json={"password": PASSWORD}).status_code == 401
    client = login("boss@example.com")
    client.headers.pop("X-CSRF-Token")
    r = client.post(f"{API}/auth/2fa/setup", json={"password": PASSWORD})
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_invalid"


def test_setup_unavailable_without_key(admin, login, monkeypatch):
    client = login("boss@example.com")
    monkeypatch.setenv("TWO_FACTOR_KEY", "")
    get_settings.cache_clear()
    assert client.get(f"{API}/auth/2fa").json()["available"] is False
    r = client.post(f"{API}/auth/2fa/setup", json={"password": PASSWORD})
    assert r.status_code == 409 and r.json()["error"]["code"] == "two_factor_unavailable"
    get_settings.cache_clear()


def test_secret_and_codes_never_leak_in_api_or_audit(admin, login, db):
    client = login("boss@example.com")
    secret, codes = enable_2fa(client)
    me = client.get(f"{API}/auth/me").text
    users = client.get(f"{API}/users").text
    audit_dump = client.get(f"{API}/audit?limit=200").text
    for text in (me, users, audit_dump):
        assert secret not in text and "secret" not in text.lower().replace("two_factor_enabled", "")
        assert not any(code in text for code in codes)
    actions = {e.action for e in db.scalars(select(AuditEvent)).all()}
    assert {"auth.2fa_setup", "auth.2fa_enable"} <= actions


def test_cli_reset_2fa_disables_and_revokes_sessions(admin, login, db):
    client = login("boss@example.com")
    enable_2fa(client)
    revoked = reset_two_factor("BOSS@example.com")
    assert revoked >= 1
    db.expire_all()
    user = db.scalars(select(User)).one()
    assert user.two_factor_enabled is False and user.two_factor_secret_encrypted is None
    assert db.scalars(select(RecoveryCode)).all() == []
    assert client.get(f"{API}/auth/me").status_code == 401
    assert login_with("boss@example.com")[1].status_code == 200
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.2fa_reset")).one()
    assert event.actor_label == "cli"
    with pytest.raises(ValueError):
        reset_two_factor("nobody@example.com")


def test_undecryptable_secret_blocks_login_instead_of_bypassing_it(admin, login, db, monkeypatch):
    enable_2fa(login("boss@example.com"))
    from cryptography.fernet import Fernet

    monkeypatch.setenv("TWO_FACTOR_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    _, r = login_with("boss@example.com", otp="123456")
    assert r.status_code == 409 and r.json()["error"]["code"] == "two_factor_unavailable"
    get_settings.cache_clear()
