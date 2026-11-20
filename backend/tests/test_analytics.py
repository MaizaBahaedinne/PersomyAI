ANALYTICS = "/api/v1/analytics/summary"


def test_permissions(make_user, login):
    make_user("a@example.com", "ADMIN")
    make_user("o@example.com", "OPERATOR")
    make_user("v@example.com", "VIEWER")
    admin = login("a@example.com")
    operator = login("o@example.com")
    viewer = login("v@example.com")

    assert admin.get(ANALYTICS).status_code == 200
    assert operator.get(ANALYTICS).status_code == 200
    assert viewer.get(ANALYTICS).status_code == 403


def test_summary_shape(make_user, login):
    make_user("a@example.com", "ADMIN")
    admin = login("a@example.com")
    r = admin.get(ANALYTICS)
    assert r.status_code == 200, r.text
    body = r.json()
    for key in [
        "users_total",
        "users_active",
        "users_with_2fa",
        "agents_total",
        "automations_total",
        "automations_active",
        "companies_total",
        "contacts_total",
        "tasks_total",
        "tasks_open",
        "tasks_done",
        "task_runs_total",
        "task_runs_success_30d",
        "ai_cost_cents_30d",
    ]:
        assert key in body
