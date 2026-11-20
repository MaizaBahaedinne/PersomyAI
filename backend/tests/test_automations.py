import time

AUTOMATIONS = "/api/v1/automations"


def test_permissions_by_role(make_user, login):
    make_user("a@example.com", "ADMIN")
    make_user("o@example.com", "OPERATOR")
    make_user("v@example.com", "VIEWER")
    admin = login("a@example.com")
    operator = login("o@example.com")
    viewer = login("v@example.com")

    assert operator.get(AUTOMATIONS).status_code == 200
    assert viewer.get(AUTOMATIONS).status_code == 403
    assert operator.post(
        AUTOMATIONS,
        json={
            "name": "x",
            "trigger_type": "SCHEDULE",
            "actions": [{"type": "notify.audit"}],
        },
    ).status_code == 403

    assert admin.post(
        AUTOMATIONS,
        json={
            "name": "on-hour",
            "trigger_type": "SCHEDULE",
            "trigger_config": {"cron": "0 * * * *"},
            "conditions": [],
            "actions": [{"type": "notify.audit"}],
            "cooldown_seconds": 60,
        },
    ).status_code == 201


def test_create_validation_and_name_uniqueness(make_user, login):
    make_user("a@example.com", "ADMIN")
    admin = login("a@example.com")

    bad = admin.post(
        AUTOMATIONS,
        json={
            "name": "loop-risk",
            "trigger_type": "TASK_STATUS_CHANGED",
            "actions": [{"type": "task.set_status"}],
        },
    )
    assert bad.status_code == 409
    assert bad.json()["error"]["code"] == "automation_loop_risk"

    payload = {
        "name": "auto-1",
        "trigger_type": "TASK_STATUS_CHANGED",
        "trigger_config": {"from": "OPEN", "to": "DONE"},
        "conditions": [{"type": "task.required_scope", "equals": "crm:read"}],
        "actions": [{"type": "notify.audit"}],
    }
    assert admin.post(AUTOMATIONS, json=payload).status_code == 201
    dup = admin.post(AUTOMATIONS, json=payload)
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "automation_name_taken"


def test_status_and_anti_loop_guard(make_user, login):
    make_user("a@example.com", "ADMIN")
    admin = login("a@example.com")

    created = admin.post(
        AUTOMATIONS,
        json={
            "name": "guarded",
            "trigger_type": "SCHEDULE",
            "trigger_config": {"cron": "*/5 * * * *"},
            "actions": [{"type": "notify.audit"}],
            "anti_loop_key": "same-event",
            "cooldown_seconds": 2,
        },
    ).json()

    aid = created["id"]
    assert admin.post(f"{AUTOMATIONS}/{aid}/status", json={"status": "ACTIVE"}).status_code == 200

    first = admin.post(f"{AUTOMATIONS}/{aid}/simulate-trigger", json={"event_key": "same-event"})
    assert first.status_code == 200 and first.json()["accepted"] is True

    blocked = admin.post(f"{AUTOMATIONS}/{aid}/simulate-trigger", json={"event_key": "same-event"})
    assert blocked.status_code == 200
    assert blocked.json() == {"accepted": False, "reason": "automation_loop_blocked"}

    time.sleep(2)
    accepted = admin.post(f"{AUTOMATIONS}/{aid}/simulate-trigger", json={"event_key": "same-event"})
    assert accepted.status_code == 200 and accepted.json()["accepted"] is True
