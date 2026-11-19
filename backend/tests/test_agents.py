import pytest
from sqlalchemy import select

from app.modules.agents import catalog
from app.modules.agents.models import Agent, AgentPermission, AgentTool
from app.modules.audit.models import AuditEvent
from app.modules.permissions.policy import Permission
from app.modules.users.models import User

AGENTS = "/api/v1/agents"
NEW = {
    "name": "Sales Assistant",
    "description": "Qualifie les prospects",
    "department": "sales",
    "role": "Assistant commercial",
    "mission": "Qualifier les leads entrants",
    "skills": ["prospection", "Prospection", " relance "],
}


@pytest.fixture()
def admin(make_user, login):
    make_user("a@example.com", "ADMIN")
    return login("a@example.com")


@pytest.fixture()
def sa(make_user, login):
    make_user("s@example.com", "SUPER_ADMIN")
    return login("s@example.com")


def create(client, **over):
    r = client.post(AGENTS, json={**NEW, **over})
    assert r.status_code == 201, r.text
    return r.json()


# --- Accès et création ---------------------------------------------------------


def test_permissions_by_role(make_user, login):
    make_user("v@example.com", "VIEWER")
    make_user("o@example.com", "OPERATOR")
    assert login("v@example.com").get(AGENTS).status_code == 403
    op = login("o@example.com")
    assert op.get(AGENTS).status_code == 200
    assert op.get(f"{AGENTS}/catalog").status_code == 200
    assert op.post(AGENTS, json=NEW).status_code == 403


def test_agents_require_authentication(client):
    assert client.get(AGENTS).status_code == 401


def test_create_agent_defaults_and_technical_identity(admin, db):
    users_before = db.scalars(select(User)).all()
    a = create(admin)
    assert a["status"] == "DRAFT" and a["autonomy_level"] == 1
    assert a["monthly_budget_cents"] == 0 and a["max_actions_per_day"] == 50
    assert a["identity_key"].startswith("agt_") and len(a["identity_key"]) == 20
    assert a["permissions"] == [] and a["tools"] == []
    assert a["skills"] == ["prospection", "relance"]  # nettoyées, dédupliquées
    # Aucune identité humaine n'est créée : pas de ligne users, pas de mot de passe.
    assert len(db.scalars(select(User)).all()) == len(users_before)
    assert "password" not in str(a).lower()


def test_identity_keys_are_unique(admin):
    keys = {create(admin, name=f"Agent {i}")["identity_key"] for i in range(5)}
    assert len(keys) == 5


def test_duplicate_name_is_rejected_case_insensitive(admin):
    create(admin)
    r = admin.post(AGENTS, json={**NEW, "name": "sales ASSISTANT"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "agent_name_taken"


@pytest.mark.parametrize(
    "payload",
    [
        {"department": "astrology"},
        {"name": "   "},
        {"role": ""},
        {"skills": ["x" * 61]},
        {"skills": [f"s{i}" for i in range(31)]},
        {"config": {"api_key": "sk-123"}},
        {"config": {"nested": {"Password": "x"}}},
        {"config": {"auth": [{"token": "x"}]}},
        {"config": {"blob": "x" * 9000}},
        {"max_actions_per_day": -1},
        {"monthly_budget_cents": -5},
    ],
)
def test_create_validation(admin, payload):
    assert admin.post(AGENTS, json={**NEW, **payload}).status_code == 422


def test_budget_requires_super_admin(admin, sa):
    assert admin.post(AGENTS, json={**NEW, "monthly_budget_cents": 500}).status_code == 403
    assert sa.post(AGENTS, json={**NEW, "monthly_budget_cents": 500}).status_code == 201


def test_list_filters_and_pagination(admin):
    create(admin, name="Alpha", department="sales")
    b = create(admin, name="Beta", department="finance", mission="m")
    create(admin, name="Gamma", department="sales")
    admin.post(f"{AGENTS}/{b['id']}/status", json={"status": "ACTIVE"})
    assert admin.get(AGENTS).json()["total"] == 3
    assert admin.get(AGENTS, params={"department": "sales"}).json()["total"] == 2
    assert admin.get(AGENTS, params={"status": "ACTIVE"}).json()["items"][0]["name"] == "Beta"
    assert admin.get(AGENTS, params={"search": "gam"}).json()["total"] == 1
    assert admin.get(AGENTS, params={"limit": 2}).json()["items"][1]["name"] == "Beta"
    assert admin.get(AGENTS, params={"status": "WEIRD"}).status_code == 422
    assert "config" not in admin.get(AGENTS).json()["items"][0]


def test_get_unknown_agent(admin):
    r = admin.get(f"{AGENTS}/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404 and r.json()["error"]["code"] == "agent_not_found"


# --- Modification --------------------------------------------------------------


def test_update_agent_and_autonomy_rules(admin, sa):
    a = create(admin)
    r = admin.patch(f"{AGENTS}/{a['id']}", json={"role": "Responsable ventes", "config": {"tone": "formel"}})
    assert r.status_code == 200 and r.json()["role"] == "Responsable ventes"
    assert r.json()["config"] == {"tone": "formel"}
    # Un ADMIN ne peut pas augmenter l'autonomie ni le budget.
    assert admin.patch(f"{AGENTS}/{a['id']}", json={"autonomy_level": 2}).status_code == 403
    assert admin.patch(f"{AGENTS}/{a['id']}", json={"monthly_budget_cents": 1}).status_code == 403
    assert sa.patch(f"{AGENTS}/{a['id']}", json={"autonomy_level": 3, "monthly_budget_cents": 100}).status_code == 200
    # ... mais peut les réduire.
    r = admin.patch(f"{AGENTS}/{a['id']}", json={"autonomy_level": 1, "monthly_budget_cents": 0})
    assert r.status_code == 200 and r.json()["autonomy_level"] == 1
    assert admin.patch(f"{AGENTS}/{a['id']}", json={"autonomy_level": 4}).status_code == 422
    assert admin.patch(f"{AGENTS}/{a['id']}", json={"status": "ACTIVE"}).json()["status"] == "DRAFT"


def test_update_name_conflict(admin):
    create(admin, name="One")
    two = create(admin, name="Two")
    assert admin.patch(f"{AGENTS}/{two['id']}", json={"name": "ONE"}).status_code == 409
    assert admin.patch(f"{AGENTS}/{two['id']}", json={"name": "Two"}).status_code == 200


# --- Statuts -------------------------------------------------------------------


def test_status_lifecycle(admin):
    a = create(admin)
    url = f"{AGENTS}/{a['id']}/status"
    for target, expected in [("ACTIVE", 200), ("PAUSED", 200), ("ACTIVE", 200), ("DISABLED", 200), ("DRAFT", 200)]:
        r = admin.post(url, json={"status": target})
        assert r.status_code == expected, (target, r.text)
        assert r.json()["status"] == target


@pytest.mark.parametrize("current,target", [("DRAFT", "PAUSED"), ("DISABLED", "ACTIVE"), ("ACTIVE", "DRAFT"), ("PAUSED", "DRAFT")])
def test_invalid_transitions(admin, db, current, target):
    a = create(admin)
    agent = db.get(Agent, __import__("uuid").UUID(a["id"]))
    agent.status = current
    db.commit()
    r = admin.post(f"{AGENTS}/{a['id']}/status", json={"status": target})
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition"


def test_same_status_and_error_not_targetable(admin):
    a = create(admin)
    assert admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "DRAFT"}).json()["error"]["code"] == "status_unchanged"
    assert admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ERROR"}).status_code == 422


def test_error_state_recovery(admin, db):
    a = create(admin)
    agent = db.get(Agent, __import__("uuid").UUID(a["id"]))
    agent.status = "ERROR"
    db.commit()
    assert admin.get(AGENTS, params={"status": "ERROR"}).json()["total"] == 1
    assert admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"}).status_code == 200


def test_activation_requires_mission(admin):
    a = create(admin, mission="")
    r = admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "agent_incomplete"
    admin.patch(f"{AGENTS}/{a['id']}", json={"mission": "Une mission"})
    assert admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"}).status_code == 200


# --- Permissions et outils -----------------------------------------------------


def test_catalog_contains_no_admin_or_payment_permission():
    human = {p.value for p in Permission}
    assert not human & set(catalog.SCOPES)
    forbidden_prefixes = ("users", "settings", "audit", "sessions", "agents", "admin", "payment", "payments", "transfer")
    assert not any(code.split(":")[0] in forbidden_prefixes for code in catalog.SCOPES)
    assert catalog.SCOPES["email:send"] and catalog.SCOPES["social:publish"]  # critiques


def test_grant_permissions_is_super_admin_only(admin, sa):
    a = create(admin)
    url = f"{AGENTS}/{a['id']}/permissions"
    assert admin.put(url, json={"permissions": ["crm:read"]}).status_code == 403
    r = sa.put(url, json={"permissions": ["crm:write", "crm:read", "crm:read"]})
    assert r.status_code == 200 and r.json()["permissions"] == ["crm:read", "crm:write"]
    r = sa.put(url, json={"permissions": ["crm:read", "reports:read"]})
    assert r.json()["permissions"] == ["crm:read", "reports:read"]
    assert sa.put(url, json={"permissions": []}).json()["permissions"] == []


@pytest.mark.parametrize("bad", ["users:write", "settings:write", "audit:read", "agents:grant", "payments:send", "*", "SUPER_ADMIN"])
def test_agents_can_never_receive_admin_permissions(sa, bad):
    a = create(sa)
    r = sa.put(f"{AGENTS}/{a['id']}/permissions", json={"permissions": [bad]})
    assert r.status_code == 422
    assert sa.get(f"{AGENTS}/{a['id']}").json()["permissions"] == []


def test_tools(admin, sa):
    a = create(admin)
    url = f"{AGENTS}/{a['id']}/tools"
    assert admin.put(url, json={"tools": ["web_search"]}).status_code == 403
    assert sa.put(url, json={"tools": ["web_search", "crm"]}).json()["tools"] == ["crm", "web_search"]
    assert sa.put(url, json={"tools": ["rm_rf"]}).status_code == 422


def test_revoke_access(admin, sa, db):
    a = create(admin)
    sa.put(f"{AGENTS}/{a['id']}/permissions", json={"permissions": ["crm:read"]})
    sa.put(f"{AGENTS}/{a['id']}/tools", json={"tools": ["crm"]})
    admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"})
    assert admin.post(f"{AGENTS}/{a['id']}/revoke-access").status_code == 403
    r = sa.post(f"{AGENTS}/{a['id']}/revoke-access")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "DISABLED" and body["permissions"] == [] and body["tools"] == []
    assert body["access_revoked_at"] is not None
    assert db.scalars(select(AgentPermission)).all() == [] and db.scalars(select(AgentTool)).all() == []
    # Pas de ré-octroi tant que l'agent n'est pas repassé en brouillon.
    assert sa.put(f"{AGENTS}/{a['id']}/permissions", json={"permissions": ["crm:read"]}).json()["error"]["code"] == "access_revoked"
    assert sa.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"}).status_code == 409
    assert sa.post(f"{AGENTS}/{a['id']}/status", json={"status": "DRAFT"}).json()["access_revoked_at"] is None
    assert sa.put(f"{AGENTS}/{a['id']}/permissions", json={"permissions": ["crm:read"]}).status_code == 200


# --- Suppression ---------------------------------------------------------------


def test_delete_rules(admin, sa, db):
    a = create(admin)
    sa.put(f"{AGENTS}/{a['id']}/permissions", json={"permissions": ["crm:read"]})
    assert admin.delete(f"{AGENTS}/{a['id']}").status_code == 403  # ADMIN: pas de suppression
    admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"})
    r = sa.delete(f"{AGENTS}/{a['id']}")
    assert r.status_code == 409 and r.json()["error"]["code"] == "agent_not_deletable"
    admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "DISABLED"})
    assert sa.delete(f"{AGENTS}/{a['id']}").status_code == 204
    assert sa.get(f"{AGENTS}/{a['id']}").status_code == 404
    assert db.scalars(select(AgentPermission)).all() == []
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "agent.delete")).one()
    assert event.target_id == a["id"] and event.details["name"] == "Sales Assistant"


# --- Historique et audit -------------------------------------------------------


def test_history_records_actions_without_secrets(admin, sa):
    a = create(admin)
    admin.patch(f"{AGENTS}/{a['id']}", json={"role": "Nouveau rôle"})
    admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE", "reason": "go"})
    sa.put(f"{AGENTS}/{a['id']}/permissions", json={"permissions": ["crm:read"]})
    other = create(admin, name="Other")
    h = admin.get(f"{AGENTS}/{a['id']}/history").json()
    actions = [e["action"] for e in h["items"]]
    assert actions == ["agent.permissions_update", "agent.status", "agent.update", "agent.create"]
    status_event = h["items"][1]
    assert status_event["details"] == {"from": "DRAFT", "to": "ACTIVE", "reason": "go"}
    assert status_event["actor_label"] == "a@example.com"
    assert admin.get(f"{AGENTS}/{other['id']}/history").json()["total"] == 1
    assert admin.get(f"{AGENTS}/00000000-0000-0000-0000-000000000000/history").status_code == 404


# --- Arrêt d'urgence -----------------------------------------------------------


def test_emergency_stop_pauses_active_agents_and_blocks_activation(admin, sa):
    a1, a2, a3 = create(admin, name="A1"), create(admin, name="A2"), create(admin, name="A3")
    for a in (a1, a2):
        assert admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"}).status_code == 200
    assert admin.get(f"{AGENTS}/emergency-stop").json()["active"] is False

    r = admin.post(f"{AGENTS}/emergency-stop")
    assert r.status_code == 200 and r.json()["active"] is True and r.json()["paused_agents"] == 2
    assert admin.get(f"{AGENTS}/{a1['id']}").json()["status"] == "PAUSED"
    assert admin.get(f"{AGENTS}/{a3['id']}").json()["status"] == "DRAFT"

    r = admin.post(f"{AGENTS}/{a1['id']}/status", json={"status": "ACTIVE"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "emergency_stop_active"
    assert admin.post(f"{AGENTS}/{a3['id']}/status", json={"status": "ACTIVE"}).status_code == 409

    # Un ADMIN peut déclencher l'arrêt, seul un SUPER_ADMIN peut le lever.
    assert admin.delete(f"{AGENTS}/emergency-stop").status_code == 403
    assert sa.delete(f"{AGENTS}/emergency-stop").json()["active"] is False
    # Les agents restent en pause : reprise explicite requise.
    assert sa.get(f"{AGENTS}/{a1['id']}").json()["status"] == "PAUSED"
    assert sa.post(f"{AGENTS}/{a1['id']}/status", json={"status": "ACTIVE"}).status_code == 200


def test_emergency_stop_is_audited_and_idempotent(admin, db):
    a = create(admin)
    admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"})
    admin.post(f"{AGENTS}/emergency-stop")
    assert admin.post(f"{AGENTS}/emergency-stop").json()["paused_agents"] == 0
    stops = db.scalars(select(AuditEvent).where(AuditEvent.action == "agent.emergency_stop")).all()
    assert len(stops) == 2 and stops[0].actor_label == "a@example.com"


def test_emergency_route_not_captured_by_agent_id(sa):
    assert sa.get(f"{AGENTS}/emergency-stop").status_code == 200
    assert sa.get(f"{AGENTS}/catalog").status_code == 200


def test_catalog_endpoint(admin):
    c = admin.get(f"{AGENTS}/catalog").json()
    assert "sales" in c["departments"] and len(c["departments"]) == 10
    assert c["statuses"] == ["DRAFT", "ACTIVE", "PAUSED", "ERROR", "DISABLED"]
    assert "ERROR" not in c["settable_statuses"]
    assert {"code": "email:send", "critical": True} in c["scopes"]
    assert c["autonomy_levels"] == [1, 2, 3]


# --- Tableau de bord -----------------------------------------------------------


def test_dashboard_counts_agents_from_real_data(admin, sa):
    d = sa.get("/api/v1/dashboard/summary").json()
    assert d["agents"] == {"draft": 0, "active": 0, "paused": 0, "error": 0, "disabled": 0, "total": 0}
    a = create(admin)
    create(admin, name="B")
    admin.post(f"{AGENTS}/{a['id']}/status", json={"status": "ACTIVE"})
    d = sa.get("/api/v1/dashboard/summary").json()
    assert d["agents"]["total"] == 2 and d["agents"]["active"] == 1 and d["agents"]["draft"] == 1
    assert d["emergency_stop"] is False and d["pending_modules"] == ["automations"]
    admin.post(f"{AGENTS}/emergency-stop")
    d = sa.get("/api/v1/dashboard/summary").json()
    assert d["emergency_stop"] is True and d["agents"]["paused"] == 1
    assert any(x["code"] == "emergency_stop_active" for x in d["alerts"])
