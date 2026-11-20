from app.modules.agents.models import Agent


def make_agent(db, name: str, department: str, status: str):
    db.add(
        Agent(
            identity_key=f"agt_{name.lower()}",
            name=name,
            description="",
            department=department,
            role="Assistant",
            mission="Mission",
            skills=[],
            status=status,
            autonomy_level=1,
            config={},
            max_actions_per_day=50,
            monthly_budget_cents=0,
        )
    )


def test_departments_summary_counts(make_user, login, db):
    make_user("v@example.com", "VIEWER")
    viewer = login("v@example.com")

    make_agent(db, "A1", "sales", "ACTIVE")
    make_agent(db, "A2", "sales", "PAUSED")
    make_agent(db, "A3", "finance", "DRAFT")
    db.commit()

    r = viewer.get("/api/v1/departments/summary")
    assert r.status_code == 200, r.text
    items = {i["code"]: i for i in r.json()["items"]}
    assert items["sales"]["agents_total"] == 2
    assert items["sales"]["agents_active"] == 1
    assert items["sales"]["agents_paused"] == 1
    assert items["finance"]["agents_total"] == 1
    assert items["finance"]["agents_active"] == 0
