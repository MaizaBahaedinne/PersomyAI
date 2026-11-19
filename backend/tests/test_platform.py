from tests.conftest import PASSWORD


def test_health_endpoints(client):
    assert client.get("/health").json() == {"status": "ok"}
    r = client.get("/health/ready")
    assert r.status_code == 200 and r.json()["database"] == "ok"


def test_unknown_route_returns_structured_error(client):
    r = client.get("/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "http_error"


def test_audit_requires_permission(make_user, login):
    make_user("o@example.com", "OPERATOR")
    make_user("a@example.com", "ADMIN")
    assert login("o@example.com").get("/api/v1/audit").status_code == 403
    assert login("a@example.com").get("/api/v1/audit").status_code == 200


def test_audit_listing_and_filters(make_user, login, client):
    make_user("a@example.com", "ADMIN")
    client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "bad-password-1"})
    c = login("a@example.com")
    data = c.get("/api/v1/audit").json()
    assert data["total"] >= 2
    failures = c.get("/api/v1/audit", params={"status": "failure"}).json()
    assert failures["total"] == 1 and failures["items"][0]["action"] == "auth.login.failed"
    assert c.get("/api/v1/audit", params={"action": "auth.login"}).json()["total"] == 2
    assert c.get("/api/v1/audit", params={"status": "weird"}).status_code == 422


def test_audit_is_append_only(make_user, login):
    make_user("s@example.com", "SUPER_ADMIN")
    c = login("s@example.com")
    assert c.delete("/api/v1/audit").status_code == 405
    assert c.put("/api/v1/audit", json={}).status_code == 405


def test_dashboard_reflects_real_data(make_user, login, client):
    make_user("s1@example.com", "SUPER_ADMIN")
    make_user("v@example.com", "VIEWER", active=False)
    client.post("/api/v1/auth/login", json={"email": "s1@example.com", "password": "bad-password-1"})
    c = login("s1@example.com")
    d = c.get("/api/v1/dashboard/summary").json()
    assert d["users"] == {"total": 2, "active": 1, "disabled": 1, "super_admins": 1}
    assert d["sessions"]["active"] == 1
    assert d["security"]["logins_failed_24h"] == 1
    assert d["security"]["logins_success_24h"] == 1
    assert d["pending_modules"] == ["automations"]
    assert d["agents"]["total"] == 0
    assert d["tasks"]["total"] == 0 and d["missions"]["total"] == 0
    assert {s["name"]: s["status"] for s in d["services"]} == {"api": "ok", "database": "ok"}
    assert any(a["code"] == "single_super_admin" for a in d["alerts"])


def test_dashboard_requires_auth(client):
    assert client.get("/api/v1/dashboard/summary").status_code == 401


def test_settings_read_write_permissions(make_user, login):
    make_user("a@example.com", "ADMIN")
    make_user("s@example.com", "SUPER_ADMIN")
    admin, sa = login("a@example.com"), login("s@example.com")
    assert admin.get("/api/v1/settings").json() == {"company_name": "Persomy AI", "default_language": "fr"}
    assert admin.put("/api/v1/settings", json={"company_name": "X"}).status_code == 403
    r = sa.put("/api/v1/settings", json={"company_name": "  Persomy Labs ", "default_language": "en"})
    assert r.status_code == 200 and r.json() == {"company_name": "Persomy Labs", "default_language": "en"}
    assert admin.get("/api/v1/settings").json()["company_name"] == "Persomy Labs"
    assert sa.put("/api/v1/settings", json={"default_language": "de"}).status_code == 422
    assert sa.put("/api/v1/settings", json={"company_name": ""}).status_code == 422


def test_passwords_never_in_responses(make_user, login):
    make_user("s@example.com", "SUPER_ADMIN")
    c = login("s@example.com")
    for path in ("/api/v1/users", "/api/v1/auth/me", "/api/v1/dashboard/summary", "/api/v1/audit"):
        text = c.get(path).text.lower()
        assert "password_hash" not in text and "argon2" not in text and PASSWORD.lower() not in text
