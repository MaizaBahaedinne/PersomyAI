from datetime import timedelta

from sqlalchemy import select

from app.core.db import utcnow
from app.modules.audit.models import AuditEvent
from app.modules.authentication.models import AuthSession, LoginAttempt
from tests.conftest import PASSWORD

LOGIN = "/api/v1/auth/login"


def test_login_success_sets_secure_cookies_and_stores_only_hash(client, make_user, db):
    make_user("admin@example.com", "SUPER_ADMIN")
    r = client.post(LOGIN, json={"email": "Admin@Example.com", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "admin@example.com"
    assert "users:write" in body["permissions"]
    assert "password" not in str(body).lower()

    set_cookie = [v for k, v in r.headers.multi_items() if k == "set-cookie"]
    session_cookie = next(c for c in set_cookie if c.startswith("persomy_session="))
    csrf_cookie = next(c for c in set_cookie if c.startswith("persomy_csrf="))
    assert "HttpOnly" in session_cookie and "SameSite=lax" in session_cookie
    assert "HttpOnly" not in csrf_cookie

    token = client.cookies.get("persomy_session")
    stored = db.scalars(select(AuthSession)).all()
    assert len(stored) == 1
    assert stored[0].token_hash != token and token not in stored[0].token_hash
    assert len(stored[0].token_hash) == 64


def test_login_failure_is_generic_for_unknown_and_wrong_password(client, make_user):
    make_user("a@example.com")
    r1 = client.post(LOGIN, json={"email": "a@example.com", "password": "bad-password-1"})
    r2 = client.post(LOGIN, json={"email": "nobody@example.com", "password": "bad-password-1"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()


def test_disabled_account_cannot_login(client, make_user, db):
    make_user("off@example.com", active=False)
    r = client.post(LOGIN, json={"email": "off@example.com", "password": PASSWORD})
    assert r.status_code == 401
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "auth.login.failed")).one()
    assert event.details == {"reason": "account_disabled"}


def test_protected_route_requires_session(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_authenticated"


def test_me_and_logout_revokes_session(client, make_user, login):
    make_user("u@example.com", "ADMIN")
    c = login("u@example.com")
    assert c.get("/api/v1/auth/me").json()["user"]["email"] == "u@example.com"
    token = c.cookies.get("persomy_session")
    assert c.post("/api/v1/auth/logout").status_code == 204
    c.cookies.set("persomy_session", token)
    assert c.get("/api/v1/auth/me").status_code == 401


def test_csrf_required_on_unsafe_methods(client, make_user, login):
    make_user("u@example.com")
    c = login("u@example.com")
    good = c.headers.pop("X-CSRF-Token")
    assert c.post("/api/v1/auth/logout").status_code == 403
    c.headers["X-CSRF-Token"] = "wrong"
    assert c.post("/api/v1/auth/logout").status_code == 403
    c.headers["X-CSRF-Token"] = good
    assert c.post("/api/v1/auth/logout").status_code == 204


def test_untrusted_origin_is_rejected(client, make_user):
    make_user("u@example.com")
    r = client.post(
        LOGIN, json={"email": "u@example.com", "password": PASSWORD}, headers={"Origin": "https://evil.example"}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "origin_not_allowed"
    ok = client.post(
        LOGIN, json={"email": "u@example.com", "password": PASSWORD}, headers={"Origin": "http://localhost:3000"}
    )
    assert ok.status_code == 200


def test_bruteforce_is_throttled_even_with_correct_password(client, make_user):
    make_user("t@example.com")
    for _ in range(5):
        assert client.post(LOGIN, json={"email": "t@example.com", "password": "nope-nope-nope"}).status_code == 401
    r = client.post(LOGIN, json={"email": "t@example.com", "password": PASSWORD})
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    assert r.json()["error"]["code"] == "login_throttled"


def test_throttle_expires_after_window(client, make_user, db):
    make_user("t@example.com")
    for _ in range(5):
        client.post(LOGIN, json={"email": "t@example.com", "password": "nope-nope-nope"})
    for a in db.scalars(select(LoginAttempt)).all():
        a.created_at = utcnow() - timedelta(minutes=16)
    db.commit()
    assert client.post(LOGIN, json={"email": "t@example.com", "password": PASSWORD}).status_code == 200


def test_throttle_per_ip_independent_of_email(client, make_user):
    for i in range(20):
        client.post(LOGIN, json={"email": f"x{i}@example.com", "password": "nope-nope-nope"})
    make_user("fresh@example.com")
    assert client.post(LOGIN, json={"email": "fresh@example.com", "password": PASSWORD}).status_code == 429


def test_idle_and_absolute_expiry(client, make_user, db):
    make_user("u@example.com")
    client.post(LOGIN, json={"email": "u@example.com", "password": PASSWORD})
    session = db.scalars(select(AuthSession)).one()

    session.last_seen_at = utcnow() - timedelta(hours=3)
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401

    session.last_seen_at = utcnow()
    session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_deactivated_user_session_stops_working(client, make_user, login, db):
    user = make_user("u@example.com")
    c = login("u@example.com")
    user.is_active = False
    db.commit()
    assert c.get("/api/v1/auth/me").status_code == 401


def test_change_password_revokes_other_sessions(client, make_user, login):
    make_user("u@example.com")
    a = login("u@example.com")
    b = login("u@example.com")
    new_pw = "Another-Strong-Pass-7"
    bad = a.post("/api/v1/auth/change-password", json={"current_password": "wrong", "new_password": new_pw})
    assert bad.status_code == 401
    ok = a.post("/api/v1/auth/change-password", json={"current_password": PASSWORD, "new_password": new_pw})
    assert ok.status_code == 204
    assert a.get("/api/v1/auth/me").status_code == 200
    assert b.get("/api/v1/auth/me").status_code == 401
    assert client.post(LOGIN, json={"email": "u@example.com", "password": new_pw}).status_code == 200


def test_change_password_rejects_weak(client, make_user, login):
    make_user("u@example.com")
    c = login("u@example.com")
    r = c.post("/api/v1/auth/change-password", json={"current_password": PASSWORD, "new_password": "short"})
    assert r.status_code == 422
    r = c.post("/api/v1/auth/change-password", json={"current_password": PASSWORD, "new_password": "onlyletterspassword"})
    assert r.status_code == 422


def test_list_and_revoke_own_sessions(make_user, login):
    make_user("u@example.com")
    a = login("u@example.com")
    b = login("u@example.com")
    sessions = a.get("/api/v1/auth/sessions").json()
    assert len(sessions) == 2 and sum(s["current"] for s in sessions) == 1
    other = next(s for s in sessions if not s["current"])
    assert a.delete(f"/api/v1/auth/sessions/{other['id']}").status_code == 204
    assert b.get("/api/v1/auth/me").status_code == 401


def test_update_preferences(make_user, login):
    make_user("u@example.com")
    c = login("u@example.com")
    r = c.patch("/api/v1/auth/me", json={"preferred_language": "en"})
    assert r.status_code == 200 and r.json()["user"]["preferred_language"] == "en"
    assert c.patch("/api/v1/auth/me", json={"preferred_language": "de"}).status_code == 422


def test_audit_never_contains_passwords(client, make_user, db):
    make_user("u@example.com")
    client.post(LOGIN, json={"email": "u@example.com", "password": PASSWORD})
    client.post(LOGIN, json={"email": "u@example.com", "password": "bad-password-1"})
    blob = " ".join(str(e.details) for e in db.scalars(select(AuditEvent)).all())
    assert PASSWORD not in blob and "bad-password-1" not in blob
