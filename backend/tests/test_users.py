import pytest
from sqlalchemy import select

from app.core.errors import Conflict
from app.modules.audit.models import AuditEvent
from app.modules.users import service as users_service
from app.modules.users.schemas import UserUpdate
from tests.conftest import PASSWORD

USERS = "/api/v1/users"
NEW = {"email": "new@example.com", "display_name": "New", "password": "Brand-New-Pass-9", "role": "VIEWER"}


def test_viewer_cannot_list_users(make_user, login):
    make_user("v@example.com", "VIEWER")
    assert login("v@example.com").get(USERS).status_code == 403


def test_operator_can_read_but_not_write(make_user, login):
    make_user("o@example.com", "OPERATOR")
    c = login("o@example.com")
    assert c.get(USERS).status_code == 200
    assert c.post(USERS, json=NEW).status_code == 403


def test_admin_creates_low_privilege_user_but_not_admin(make_user, login):
    make_user("a@example.com", "ADMIN")
    c = login("a@example.com")
    assert c.post(USERS, json=NEW).status_code == 201
    r = c.post(USERS, json={**NEW, "email": "n2@example.com", "role": "ADMIN"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "super_admin_required"
    r = c.post(USERS, json={**NEW, "email": "n3@example.com", "role": "SUPER_ADMIN"})
    assert r.status_code == 403


def test_super_admin_creates_admin_and_user_can_login(make_user, login, client):
    make_user("s@example.com", "SUPER_ADMIN")
    c = login("s@example.com")
    r = c.post(USERS, json={**NEW, "role": "ADMIN"})
    assert r.status_code == 201
    assert "password" not in r.json() and "password_hash" not in r.json()
    ok = client.post("/api/v1/auth/login", json={"email": NEW["email"], "password": NEW["password"]})
    assert ok.status_code == 200


def test_duplicate_email_and_weak_password(make_user, login):
    make_user("s@example.com", "SUPER_ADMIN")
    c = login("s@example.com")
    assert c.post(USERS, json={**NEW, "email": "Dup@example.com"}).status_code == 201
    assert c.post(USERS, json={**NEW, "email": "dup@EXAMPLE.com"}).status_code == 409
    assert c.post(USERS, json={**NEW, "email": "w@example.com", "password": "short"}).status_code == 422
    assert c.post(USERS, json={**NEW, "email": "bad-email", "password": "Brand-New-Pass-9"}).status_code == 422


def test_admin_cannot_modify_admin_accounts(make_user, login):
    make_user("a1@example.com", "ADMIN")
    target = make_user("a2@example.com", "ADMIN")
    c = login("a1@example.com")
    r = c.patch(f"{USERS}/{target.id}", json={"is_active": False})
    assert r.status_code == 403


def test_cannot_change_own_role_or_status(make_user, login):
    s = make_user("s@example.com", "SUPER_ADMIN")
    c = login("s@example.com")
    r = c.patch(f"{USERS}/{s.id}", json={"role": "VIEWER"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "self_change_forbidden"
    assert c.patch(f"{USERS}/{s.id}", json={"is_active": False}).status_code == 403


def test_disable_revokes_sessions_and_blocks_login(make_user, login, client):
    make_user("s@example.com", "SUPER_ADMIN")
    target = make_user("t@example.com", "OPERATOR")
    admin = login("s@example.com")
    victim = login("t@example.com")
    assert admin.patch(f"{USERS}/{target.id}", json={"is_active": False}).status_code == 200
    assert victim.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "t@example.com", "password": PASSWORD}).status_code == 401
    assert admin.patch(f"{USERS}/{target.id}", json={"is_active": True}).status_code == 200


def test_role_change_revokes_sessions(make_user, login):
    make_user("s@example.com", "SUPER_ADMIN")
    target = make_user("t@example.com", "OPERATOR")
    admin = login("s@example.com")
    victim = login("t@example.com")
    assert admin.patch(f"{USERS}/{target.id}", json={"role": "VIEWER"}).status_code == 200
    assert victim.get("/api/v1/auth/me").status_code == 401


def test_last_active_super_admin_is_protected(make_user, db):
    inactive_actor = make_user("actor@example.com", "SUPER_ADMIN", active=False)
    last = make_user("last@example.com", "SUPER_ADMIN")

    class Req:
        client = None
        headers = {}

    with pytest.raises(Conflict) as exc:
        users_service.update_user(db, inactive_actor, last, UserUpdate(is_active=False), Req())
    assert exc.value.code == "last_super_admin"
    with pytest.raises(Conflict):
        users_service.update_user(db, inactive_actor, last, UserUpdate(role="ADMIN"), Req())


def test_password_reset_only_super_admin(make_user, login, client):
    make_user("s@example.com", "SUPER_ADMIN")
    make_user("a@example.com", "ADMIN")
    target = make_user("t@example.com", "VIEWER")
    admin = login("a@example.com")
    assert admin.put(f"{USERS}/{target.id}/password", json={"new_password": "Reset-Pass-12345"}).status_code == 403
    sa = login("s@example.com")
    victim = login("t@example.com")
    assert sa.put(f"{USERS}/{target.id}/password", json={"new_password": "Reset-Pass-12345"}).status_code == 204
    assert victim.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "t@example.com", "password": "Reset-Pass-12345"}).status_code == 200


def test_admin_revokes_user_sessions(make_user, login):
    make_user("a@example.com", "ADMIN")
    target = make_user("t@example.com", "VIEWER")
    a = login("a@example.com")
    v = login("t@example.com")
    assert a.delete(f"{USERS}/{target.id}/sessions").status_code == 204
    assert v.get("/api/v1/auth/me").status_code == 401


def test_user_management_is_audited(make_user, login, db):
    make_user("s@example.com", "SUPER_ADMIN")
    c = login("s@example.com")
    c.post(USERS, json=NEW)
    events = db.scalars(select(AuditEvent).where(AuditEvent.action == "user.create")).all()
    assert len(events) == 1 and events[0].actor_label == "s@example.com"
    assert "password" not in (events[0].details or {})


def test_list_users_filters(make_user, login):
    make_user("s@example.com", "SUPER_ADMIN", name="Sam")
    make_user("v@example.com", "VIEWER", name="Vera", active=False)
    c = login("s@example.com")
    assert c.get(USERS).json()["total"] == 2
    assert c.get(USERS, params={"search": "vera"}).json()["total"] == 1
    assert c.get(USERS, params={"active": "false"}).json()["total"] == 1
    assert c.get(USERS, params={"role": "BAD"}).status_code == 422
