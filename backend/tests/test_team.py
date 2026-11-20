TEAM = "/api/v1/team"


def test_permissions(make_user, login):
    make_user("a@example.com", "ADMIN")
    make_user("o@example.com", "OPERATOR")
    make_user("v@example.com", "VIEWER")
    admin = login("a@example.com")
    operator = login("o@example.com")
    viewer = login("v@example.com")

    assert admin.get(TEAM).status_code == 200
    assert operator.get(TEAM).status_code == 200
    assert viewer.get(TEAM).status_code == 403


def test_team_summary_and_filters(make_user, login):
    make_user("a@example.com", "ADMIN", name="Alice")
    make_user("b@example.com", "OPERATOR", active=False, name="Bob")
    admin = login("a@example.com")

    all_data = admin.get(TEAM).json()
    assert all_data["summary"]["total"] >= 2

    only_active = admin.get(TEAM, params={"active": True}).json()
    assert all(m["is_active"] for m in only_active["items"])

    by_name = admin.get(TEAM, params={"search": "alice"}).json()
    assert by_name["items"]
    assert by_name["items"][0]["display_name"].lower() == "alice"
