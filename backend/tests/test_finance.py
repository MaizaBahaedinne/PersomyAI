FINANCE = "/api/v1/finance"


def test_permissions(make_user, login):
    make_user("a@example.com", "ADMIN")
    make_user("o@example.com", "OPERATOR")
    make_user("v@example.com", "VIEWER")
    admin = login("a@example.com")
    operator = login("o@example.com")
    viewer = login("v@example.com")

    assert admin.get(f"{FINANCE}/summary").status_code == 200
    assert operator.get(f"{FINANCE}/summary").status_code == 200
    assert viewer.get(f"{FINANCE}/summary").status_code == 403

    payload = {
        "monthly_revenue_cents": 1000000,
        "gross_margin_percent": 40,
        "ai_cost_cents_monthly": 50000,
        "growth_percent": 10,
    }
    assert operator.post(f"{FINANCE}/simulate", json=payload).status_code == 200
    assert viewer.post(f"{FINANCE}/simulate", json=payload).status_code == 403


def test_simulation_math(make_user, login):
    make_user("a@example.com", "ADMIN")
    admin = login("a@example.com")
    payload = {
        "monthly_revenue_cents": 2000000,
        "gross_margin_percent": 50,
        "ai_cost_cents_monthly": 120000,
        "growth_percent": 5,
    }
    r = admin.post(f"{FINANCE}/simulate", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["projected_revenue_cents"] == 2100000
    assert data["projected_margin_cents"] == 1050000
    assert data["margin_after_ai_cents"] == 930000
