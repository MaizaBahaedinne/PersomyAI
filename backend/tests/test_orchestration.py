from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.db import utcnow
from app.modules.audit.models import AuditEvent
from app.modules.orchestration import providers
from app.modules.orchestration.models import Task, TaskRun
from app.modules.orchestration.providers import Completion, ProviderError

AGENTS = "/api/v1/agents"
MISSIONS = "/api/v1/missions"
TASKS = "/api/v1/tasks"


class FakeProvider:
    """Fournisseur de test uniquement : aucun fournisseur réel n'existe dans l'application."""

    name = "fake"

    def __init__(self, paid=False, cost=0, fail=None):
        self.paid, self.cost, self.fail = paid, cost, fail
        self.calls = []

    def complete(self, *, system, prompt, timeout_seconds):
        self.calls.append({"system": system, "prompt": prompt, "timeout": timeout_seconds})
        if self.fail:
            raise self.fail
        return Completion(text=f"result for: {prompt}", cost_cents=self.cost, tokens_in=10, tokens_out=20)


@pytest.fixture()
def install(monkeypatch):
    def _install(**kwargs):
        provider = FakeProvider(**kwargs)
        monkeypatch.setattr(providers, "get_provider", lambda: provider)
        return provider

    return _install


@pytest.fixture()
def admin(make_user, login):
    make_user("a@example.com", "ADMIN")
    return login("a@example.com")


@pytest.fixture()
def admin2(make_user, login):
    make_user("b@example.com", "ADMIN")
    return login("b@example.com")


@pytest.fixture()
def sa(make_user, login):
    make_user("s@example.com", "SUPER_ADMIN")
    return login("s@example.com")


def make_agent(sa, name="Writer", autonomy=3, scopes=("crm:read",), activate=True, **extra):
    body = {"name": name, "department": "sales", "role": "Rédacteur", "mission": "Rédiger", **extra}
    r = sa.post(AGENTS, json=body)
    assert r.status_code == 201, r.text
    agent = r.json()
    url = f"{AGENTS}/{agent['id']}"
    if autonomy != 1:
        assert sa.patch(url, json={"autonomy_level": autonomy}).status_code == 200
    if scopes:
        assert sa.put(f"{url}/permissions", json={"permissions": list(scopes)}).status_code == 200
    if activate:
        assert sa.post(f"{url}/status", json={"status": "ACTIVE"}).status_code == 200
    return sa.get(url).json()


def make_task(client, agent=None, **over):
    body = {"title": "Écrire un résumé", "description": "Sur le trimestre"}
    if agent:
        body["agent_id"] = agent["id"]
    r = client.post(TASKS, json={**body, **over})
    assert r.status_code == 201, r.text
    return r.json()


def act(client, task, action, **kwargs):
    return client.post(f"{TASKS}/{task['id']}/{action}", **kwargs)


def code(response):
    return response.json()["error"]["code"]


def audit_events(db, action):
    return db.scalars(select(AuditEvent).where(AuditEvent.action == action)).all()


# --- Accès ---------------------------------------------------------------------


def test_permissions_by_role(make_user, login, admin):
    make_user("v@example.com", "VIEWER")
    make_user("o@example.com", "OPERATOR")
    task = make_task(admin)
    viewer, operator = login("v@example.com"), login("o@example.com")
    for url in (MISSIONS, TASKS, f"{TASKS}/provider", f"{TASKS}/{task['id']}"):
        assert viewer.get(url).status_code == 403
        assert operator.get(url).status_code == 200
    assert operator.post(MISSIONS, json={"title": "x"}).status_code == 403
    assert operator.post(TASKS, json={"title": "x"}).status_code == 403
    assert act(operator, task, "run").status_code == 403
    assert act(operator, task, "approve").status_code == 403
    assert act(operator, task, "reject", json={"reason": "no"}).status_code == 403
    assert act(operator, task, "cancel").status_code == 403


def test_requires_authentication(client):
    assert client.get(MISSIONS).status_code == 401
    assert client.get(TASKS).status_code == 401


# --- Missions ------------------------------------------------------------------


def test_mission_lifecycle_and_counts(admin):
    m = admin.post(MISSIONS, json={"title": "  Lancement  ", "description": "Q1"}).json()
    assert m["title"] == "Lancement" and m["status"] == "OPEN" and m["task_counts"]["total"] == 0
    make_task(admin, mission_id=m["id"])
    make_task(admin, mission_id=m["id"])
    got = admin.get(f"{MISSIONS}/{m['id']}").json()
    assert got["task_counts"]["open"] == 2 and got["task_counts"]["total"] == 2
    assert admin.get(MISSIONS, params={"search": "lance"}).json()["total"] == 1
    assert admin.get(MISSIONS, params={"status": "DONE"}).json()["total"] == 0
    r = admin.patch(f"{MISSIONS}/{m['id']}", json={"status": "DONE", "description": "Q1 bis"})
    assert r.status_code == 200 and r.json()["status"] == "DONE"
    assert admin.get(f"{TASKS}", params={"mission_id": m["id"]}).json()["total"] == 2


def test_mission_validation_and_not_found(admin):
    assert admin.post(MISSIONS, json={"title": "  "}).status_code == 422
    assert admin.post(MISSIONS, json={"title": "x" * 201}).status_code == 422
    assert admin.patch(f"{MISSIONS}/{'0' * 8}-0000-0000-0000-{'0' * 12}", json={"title": "x"}).status_code == 404
    r = admin.get(f"{MISSIONS}/{'0' * 8}-0000-0000-0000-{'0' * 12}")
    assert r.status_code == 404 and code(r) == "mission_not_found"
    assert admin.get(MISSIONS, params={"status": "WEIRD"}).status_code == 422


def test_closed_mission_rejects_new_tasks_and_runs(admin, sa, install):
    install()
    agent = make_agent(sa)
    m = admin.post(MISSIONS, json={"title": "M"}).json()
    task = make_task(admin, agent, mission_id=m["id"])
    admin.patch(f"{MISSIONS}/{m['id']}", json={"status": "CANCELLED"})
    r = admin.post(TASKS, json={"title": "t", "mission_id": m["id"]})
    assert r.status_code == 409 and code(r) == "mission_not_open"
    r = act(admin, task, "run")
    assert r.status_code == 409 and code(r) == "mission_not_open"
    assert admin.get(f"{TASKS}/{task['id']}").json()["status"] == "OPEN"
    assert admin.post(TASKS, json={"title": "t", "mission_id": "0" * 8 + "-0000-0000-0000-" + "0" * 12}).status_code == 404


# --- Création et modification de tâches ----------------------------------------


def test_create_task_defaults_and_names(admin, sa):
    agent = make_agent(sa)
    m = admin.post(MISSIONS, json={"title": "Mission A"}).json()
    t = make_task(admin, agent, mission_id=m["id"], required_scope="crm:read", priority="HIGH")
    assert t["status"] == "OPEN" and t["priority"] == "HIGH"
    assert t["agent_name"] == "Writer" and t["mission_title"] == "Mission A"
    assert t["requires_approval"] is False  # autonomie 3 + permission non critique
    unassigned = make_task(admin)
    assert unassigned["agent_id"] is None and unassigned["requires_approval"] is None


@pytest.mark.parametrize(
    "payload",
    [{"title": ""}, {"title": "t", "priority": "URGENT"}, {"title": "t", "required_scope": "users:write"},
     {"title": "t", "description": "x" * 8001}],
)
def test_create_task_validation(admin, payload):
    assert admin.post(TASKS, json=payload).status_code == 422


def test_assignment_rules(admin, sa):
    r = admin.post(TASKS, json={"title": "t", "agent_id": "0" * 8 + "-0000-0000-0000-" + "0" * 12})
    assert r.status_code == 404 and code(r) == "agent_not_found"
    agent = make_agent(sa, activate=False)
    sa.post(f"{AGENTS}/{agent['id']}/status", json={"status": "DISABLED"})
    r = admin.post(TASKS, json={"title": "t", "agent_id": agent["id"]})
    assert r.status_code == 409 and code(r) == "agent_not_assignable"
    revoked = make_agent(sa, name="Revoked")
    sa.post(f"{AGENTS}/{revoked['id']}/revoke-access")
    assert code(admin.post(TASKS, json={"title": "t", "agent_id": revoked["id"]})) == "agent_not_assignable"


def test_update_assign_unassign_and_priority(admin, sa):
    a1, a2 = make_agent(sa, "A1"), make_agent(sa, "A2")
    t = make_task(admin, a1)
    url = f"{TASKS}/{t['id']}"
    r = admin.patch(url, json={"agent_id": a2["id"], "title": "Nouveau"})
    assert r.json()["agent_name"] == "A2" and r.json()["title"] == "Nouveau"
    assert admin.patch(url, json={"agent_id": None}).json()["agent_id"] is None
    assert admin.patch(url, json={"required_scope": "crm:read"}).json()["required_scope"] == "crm:read"
    assert admin.patch(url, json={"required_scope": None}).json()["required_scope"] is None
    assert admin.patch(url, json={"priority": "LOW"}).json()["priority"] == "LOW"
    assert admin.patch(url, json={"required_scope": "agents:grant"}).status_code == 422
    assert admin.patch(url, json={}).status_code == 200


def test_content_change_resets_approval_but_priority_does_not(admin, admin2, sa, install):
    install()
    agent = make_agent(sa, autonomy=1)
    t = make_task(admin, agent)
    url = f"{TASKS}/{t['id']}"
    act(admin, t, "request-approval")
    assert admin.patch(url, json={"priority": "HIGH"}).json()["status"] == "AWAITING_APPROVAL"
    assert admin.patch(url, json={"description": "Autre chose"}).json()["status"] == "OPEN"
    act(admin, t, "request-approval")
    assert act(admin2, t, "approve").json()["status"] == "APPROVED"
    # Modifier une tâche déjà approuvée annule l'approbation : l'humain a validé un autre contenu.
    r = admin.patch(url, json={"title": "Détourné"})
    body = r.json()
    assert body["status"] == "OPEN" and body["decided_at"] is None and body["decided_by_label"] is None
    r = act(admin, t, "run")
    assert r.status_code == 409 and code(r) == "approval_required"


# --- Exécution : cas nominal ---------------------------------------------------


def test_run_success_records_run_and_audit(admin, sa, install, db):
    provider = install(cost=0)
    agent = make_agent(sa, scopes=("crm:read",))
    t = make_task(admin, agent, required_scope="crm:read")
    r = act(admin, t, "run")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["task"]["status"] == "DONE"
    assert body["run"]["status"] == "SUCCESS" and body["run"]["provider"] == "fake"
    assert body["run"]["output"] == "result for: Écrire un résumé\n\nSur le trimestre"
    assert body["run"]["tokens_in"] == 10 and body["run"]["error_code"] is None
    call = provider.calls[0]
    assert "Writer" in call["system"] and "Rédiger" in call["system"] and call["timeout"] == 60
    runs = admin.get(f"{TASKS}/{t['id']}/runs").json()
    assert len(runs) == 1 and runs[0]["id"] == body["run"]["id"]
    event = audit_events(db, "task.run")[0]
    assert event.status == "success" and event.details["provider"] == "fake"
    assert "output" not in event.details and "prompt" not in str(event.details)  # pas de contenu dans l'audit
    # Une tâche terminée ne se relance pas.
    again = act(admin, t, "run")
    assert again.status_code == 409 and code(again) == "invalid_task_state"


# --- Exécution : refus ---------------------------------------------------------


def test_run_without_provider_is_honestly_refused(admin, sa, db):
    agent = make_agent(sa)
    t = make_task(admin, agent)
    r = act(admin, t, "run")
    assert r.status_code == 409 and code(r) == "provider_not_configured"
    assert admin.get(f"{TASKS}/{t['id']}").json()["status"] == "OPEN"
    assert db.scalars(select(TaskRun)).all() == []  # aucune exécution simulée
    event = audit_events(db, "task.run_blocked")[0]
    assert event.status == "failure" and event.details == {"reason": "provider_not_configured"}
    assert admin.get(f"{TASKS}/provider").json() == {"name": "none", "configured": False, "paid": False}


def test_provider_info_when_configured(admin, install):
    install(paid=True)
    assert admin.get(f"{TASKS}/provider").json() == {"name": "fake", "configured": True, "paid": True}


def test_run_requires_an_agent(admin, install):
    install()
    t = make_task(admin)
    r = act(admin, t, "run")
    assert r.status_code == 409 and code(r) == "agent_required"
    assert code(act(admin, t, "request-approval")) == "agent_required"


@pytest.mark.parametrize("target", ["PAUSED", "DISABLED"])
def test_run_requires_active_agent(admin, sa, install, target):
    install()
    agent = make_agent(sa)
    t = make_task(admin, agent)
    sa.post(f"{AGENTS}/{agent['id']}/status", json={"status": target})
    assert code(act(admin, t, "run")) == "agent_not_active"


def test_run_requires_granted_scope(admin, sa, install):
    install()
    agent = make_agent(sa, scopes=("crm:read",))
    t = make_task(admin, agent, required_scope="documents:write")
    r = act(admin, t, "run")
    assert r.status_code == 409 and code(r) == "scope_not_granted"
    sa.put(f"{AGENTS}/{agent['id']}/permissions", json={"permissions": ["documents:write"]})
    assert act(admin, t, "run").status_code == 200


def test_permission_revoked_after_approval_blocks_run(admin, admin2, sa, install):
    install()
    agent = make_agent(sa, autonomy=1, scopes=("crm:read",))
    t = make_task(admin, agent, required_scope="crm:read")
    act(admin, t, "request-approval")
    act(admin2, t, "approve")
    sa.post(f"{AGENTS}/{agent['id']}/revoke-access")
    assert code(act(admin, t, "run")) == "agent_not_active"


def test_emergency_stop_blocks_runs(admin, sa, install):
    install()
    agent = make_agent(sa)
    t = make_task(admin, agent)
    admin.post(f"{AGENTS}/emergency-stop")
    r = act(admin, t, "run")
    assert r.status_code == 409 and code(r) == "emergency_stop_active"
    sa.delete(f"{AGENTS}/emergency-stop")
    sa.post(f"{AGENTS}/{agent['id']}/status", json={"status": "ACTIVE"})
    assert act(admin, t, "run").status_code == 200


def test_daily_quota_counts_every_attempt(admin, sa, install):
    install(fail=ProviderError("upstream_timeout"))
    agent = make_agent(sa, max_actions_per_day=2)
    tasks = [make_task(admin, agent, title=f"T{i}") for i in range(3)]
    assert act(admin, tasks[0], "run").json()["run"]["status"] == "FAILED"  # un échec consomme le quota
    assert act(admin, tasks[1], "run").status_code == 200
    r = act(admin, tasks[2], "run")
    assert r.status_code == 409 and code(r) == "daily_quota_exceeded"
    # Les exécutions d'hier ne comptent pas.
    zero = make_agent(sa, "Zero", max_actions_per_day=0)
    assert code(act(admin, make_task(admin, zero), "run")) == "daily_quota_exceeded"


def test_paid_provider_respects_monthly_budget(admin, sa, install):
    install(paid=True, cost=60)
    free = make_agent(sa, "NoBudget")
    assert code(act(admin, make_task(admin, free), "run")) == "budget_exceeded"  # budget 0 = aucun appel payant
    funded = make_agent(sa, "Funded")
    sa.patch(f"{AGENTS}/{funded['id']}", json={"monthly_budget_cents": 100})
    first = act(admin, make_task(admin, funded, title="1"), "run")
    assert first.status_code == 200 and first.json()["run"]["cost_cents"] == 60
    assert act(admin, make_task(admin, funded, title="2"), "run").status_code == 200  # 60 < 100 avant l'appel
    r = act(admin, make_task(admin, funded, title="3"), "run")
    assert r.status_code == 409 and code(r) == "budget_exceeded"  # 120 >= 100


def test_free_provider_ignores_budget(admin, sa, install):
    install(paid=False)
    agent = make_agent(sa)
    assert act(admin, make_task(admin, agent), "run").status_code == 200


# --- Validation humaine --------------------------------------------------------


def test_low_autonomy_requires_approval_flow(admin, admin2, sa, install, db):
    install()
    agent = make_agent(sa, autonomy=2)
    t = make_task(admin, agent)
    assert t["requires_approval"] is True
    r = act(admin, t, "run")
    assert r.status_code == 409 and code(r) == "approval_required"
    r = act(admin, t, "request-approval")
    assert r.json()["status"] == "AWAITING_APPROVAL"
    assert code(act(admin, t, "run")) == "invalid_task_state"  # en attente : pas lançable avant la décision
    assert code(act(admin, t, "request-approval")) == "invalid_task_state"
    r = act(admin2, t, "approve", json={"comment": "OK pour moi"})
    body = r.json()
    assert body["status"] == "APPROVED" and body["decided_by_label"] == "b@example.com"
    assert body["decision_reason"] == "OK pour moi" and body["decided_at"]
    assert act(admin, t, "run").json()["task"]["status"] == "DONE"
    # L'approbation est à usage unique.
    assert code(act(admin, t, "run")) == "invalid_task_state"
    assert audit_events(db, "task.approval_request") and audit_events(db, "task.approve")


def test_approve_without_body_and_non_critical_self_approval(admin, sa):
    agent = make_agent(sa, autonomy=1)
    t = make_task(admin, agent)
    act(admin, t, "request-approval")
    assert act(admin, t, "approve").json()["status"] == "APPROVED"  # non critique : permis


def test_reject_requires_reason_then_reopen(admin, admin2, sa, install):
    install()
    agent = make_agent(sa, autonomy=1)
    t = make_task(admin, agent)
    act(admin, t, "request-approval")
    assert act(admin2, t, "reject", json={}).status_code == 422
    assert act(admin2, t, "reject", json={"reason": "   "}).status_code == 422
    r = act(admin2, t, "reject", json={"reason": "Hors périmètre"})
    assert r.json()["status"] == "REJECTED" and r.json()["decision_reason"] == "Hors périmètre"
    assert code(act(admin, t, "run")) == "invalid_task_state"
    r = act(admin, t, "reopen")
    assert r.json()["status"] == "OPEN" and r.json()["decision_reason"] is None
    assert act(admin, t, "request-approval").json()["status"] == "AWAITING_APPROVAL"


def test_approval_not_required_for_autonomous_agent(admin, sa):
    agent = make_agent(sa, autonomy=3)
    t = make_task(admin, agent, required_scope="crm:read")
    r = act(admin, t, "request-approval")
    assert r.status_code == 409 and code(r) == "approval_not_required"


def test_critical_scope_requires_approval_even_for_autonomous_agent(admin, admin2, sa, install):
    install()
    agent = make_agent(sa, autonomy=3, scopes=("email:send",))
    t = make_task(admin, agent, required_scope="email:send")
    assert t["requires_approval"] is True
    assert code(act(admin, t, "run")) == "approval_required"
    act(admin, t, "request-approval")
    assert act(admin2, t, "approve").status_code == 200
    assert act(admin, t, "run").status_code == 200


def test_four_eyes_on_critical_tasks(admin, admin2, sa):
    agent = make_agent(sa, autonomy=3, scopes=("social:publish",))
    t = make_task(admin, agent, required_scope="social:publish")  # créée par admin
    act(admin2, t, "request-approval")  # demandée par admin2
    for forbidden in (admin, admin2):  # ni le créateur ni le demandeur
        r = act(forbidden, t, "approve")
        assert r.status_code == 403 and code(r) == "self_approval_forbidden"
    assert admin.get(f"{TASKS}/{t['id']}").json()["status"] == "AWAITING_APPROVAL"
    assert act(sa, t, "approve").json()["status"] == "APPROVED"


def test_unrelated_user_can_reject_critical_task(admin, admin2, sa):
    agent = make_agent(sa, autonomy=3, scopes=("email:send",))
    t = make_task(admin, agent, required_scope="email:send")
    act(admin, t, "request-approval")
    assert act(admin, t, "reject", json={"reason": "ma propre demande"}).json()["status"] == "REJECTED"


def test_approve_wrong_state(admin, sa):
    agent = make_agent(sa, autonomy=1)
    t = make_task(admin, agent)
    assert code(act(admin, t, "approve")) == "invalid_task_state"
    assert code(act(admin, t, "reject", json={"reason": "x"})) == "invalid_task_state"


# --- Échecs du fournisseur, reprise, annulation --------------------------------


def test_provider_error_marks_task_failed_without_leaking_message(admin, sa, install, db):
    install(fail=ProviderError("upstream_timeout", "key sk-secret rejected"))
    agent = make_agent(sa)
    t = make_task(admin, agent)
    r = act(admin, t, "run")
    assert r.status_code == 200
    assert r.json()["task"]["status"] == "FAILED"
    assert r.json()["run"]["status"] == "FAILED" and r.json()["run"]["error_code"] == "upstream_timeout"
    assert "sk-secret" not in r.text
    event = audit_events(db, "task.run")[0]
    assert event.status == "failure" and "sk-secret" not in str(event.details)


def test_unexpected_provider_crash_never_leaves_task_running(admin, sa, install):
    install(fail=RuntimeError("boom"))
    agent = make_agent(sa)
    t = make_task(admin, agent)
    body = act(admin, t, "run").json()
    assert body["task"]["status"] == "FAILED" and body["run"]["error_code"] == "provider_error"


def test_reopen_failed_task_and_retry(admin, sa, monkeypatch):
    agent = make_agent(sa)
    t = make_task(admin, agent)
    monkeypatch.setattr(providers, "get_provider", lambda: FakeProvider(fail=ProviderError("upstream_error")))
    assert act(admin, t, "run").json()["task"]["status"] == "FAILED"
    assert code(act(admin, t, "run")) == "invalid_task_state"
    assert act(admin, t, "reopen").json()["status"] == "OPEN"
    monkeypatch.setattr(providers, "get_provider", lambda: FakeProvider())
    assert act(admin, t, "run").json()["task"]["status"] == "DONE"
    assert len(admin.get(f"{TASKS}/{t['id']}/runs").json()) == 2


def test_cancel_rules(admin, sa, install):
    install()
    agent = make_agent(sa)
    open_task = make_task(admin, agent)
    assert act(admin, open_task, "cancel").json()["status"] == "CANCELLED"
    assert code(act(admin, open_task, "run")) == "invalid_task_state"
    assert code(act(admin, open_task, "cancel")) == "invalid_task_state"
    assert admin.patch(f"{TASKS}/{open_task['id']}", json={"title": "x"}).status_code == 409
    done = make_task(admin, agent, title="done")
    act(admin, done, "run")
    assert code(act(admin, done, "cancel")) == "invalid_task_state"
    assert code(act(admin, done, "reopen")) == "invalid_task_state"


def test_running_task_is_protected_and_stale_run_can_be_reopened(admin, sa, install, db):
    install()
    agent = make_agent(sa)
    t = make_task(admin, agent)
    row = db.get(Task, __import__("uuid").UUID(t["id"]))
    row.status = "RUNNING"
    db.add(TaskRun(task_id=row.id, agent_id=row.agent_id, status="RUNNING", provider="fake"))
    db.commit()
    # Pas de double exécution, pas de modification, pas d'annulation pendant l'exécution.
    assert code(act(admin, t, "run")) == "invalid_task_state"
    assert admin.patch(f"{TASKS}/{t['id']}", json={"title": "x"}).status_code == 409
    assert code(act(admin, t, "cancel")) == "invalid_task_state"
    assert code(act(admin, t, "reopen")) == "invalid_task_state"  # trop récente
    row.updated_at = utcnow() - timedelta(minutes=30)
    db.commit()
    assert act(admin, t, "reopen").json()["status"] == "OPEN"
    run = admin.get(f"{TASKS}/{t['id']}/runs").json()[0]
    assert run["status"] == "FAILED" and run["error_code"] == "interrupted"
    assert act(admin, t, "run").json()["task"]["status"] == "DONE"


# --- Lecture : filtres, historique, tableau de bord ----------------------------


def test_list_filters(admin, sa):
    a1, a2 = make_agent(sa, "A1"), make_agent(sa, "A2")
    t1 = make_task(admin, a1, title="Alpha rapport")
    make_task(admin, a2, title="Beta")
    act(admin, t1, "cancel")
    assert admin.get(TASKS).json()["total"] == 2
    assert admin.get(TASKS, params={"agent_id": a2["id"]}).json()["items"][0]["title"] == "Beta"
    assert admin.get(TASKS, params={"status": "CANCELLED"}).json()["items"][0]["title"] == "Alpha rapport"
    assert admin.get(TASKS, params={"search": "RAPPORT"}).json()["total"] == 1
    assert admin.get(TASKS, params={"limit": 1}).json()["items"][0]["title"] == "Beta"  # plus récent d'abord
    assert admin.get(TASKS, params={"status": "WEIRD"}).status_code == 422
    assert "description" not in admin.get(TASKS).json()["items"][0]


def test_task_history(admin, admin2, sa):
    agent = make_agent(sa, autonomy=1)
    t = make_task(admin, agent)
    act(admin, t, "request-approval")
    act(admin2, t, "approve")
    other = make_task(admin)
    h = admin.get(f"{TASKS}/{t['id']}/history").json()
    assert [e["action"] for e in h["items"]] == ["task.approve", "task.approval_request", "task.create"]
    assert h["items"][0]["actor_label"] == "b@example.com"
    assert admin.get(f"{TASKS}/{other['id']}/history").json()["total"] == 1
    assert admin.get(f"{TASKS}/{'0' * 8}-0000-0000-0000-{'0' * 12}/history").status_code == 404


def test_task_not_found_everywhere(admin):
    missing = f"{TASKS}/{'0' * 8}-0000-0000-0000-{'0' * 12}"
    assert admin.get(missing).status_code == 404 and code(admin.get(missing)) == "task_not_found"
    for action in ("run", "approve", "cancel", "reopen", "request-approval"):
        assert admin.post(f"{missing}/{action}").status_code == 404
    assert admin.get(f"{missing}/runs").status_code == 404


def test_dashboard_counts_tasks_and_missions(admin, sa):
    agent = make_agent(sa, autonomy=1)
    admin.post(MISSIONS, json={"title": "M"})
    t = make_task(admin, agent)
    make_task(admin, agent, title="b")
    act(admin, t, "request-approval")
    d = sa.get("/api/v1/dashboard/summary").json()
    assert d["tasks"]["total"] == 2 and d["tasks"]["awaiting_approval"] == 1 and d["tasks"]["open"] == 1
    assert d["missions"]["open"] == 1 and d["missions"]["total"] == 1
    assert {"code": "tasks_awaiting_approval", "severity": "info", "count": 1} in d["alerts"]
