CRM = "/api/v1/crm"


def test_permissions_by_role(make_user, login):
    make_user("a@example.com", "ADMIN")
    make_user("o@example.com", "OPERATOR")
    make_user("v@example.com", "VIEWER")
    admin = login("a@example.com")
    operator = login("o@example.com")
    viewer = login("v@example.com")

    assert admin.get(f"{CRM}/companies").status_code == 200
    assert operator.get(f"{CRM}/companies").status_code == 200
    assert viewer.get(f"{CRM}/companies").status_code == 403

    assert operator.post(f"{CRM}/companies", json={"name": "Acme"}).status_code == 403


def test_companies_and_contacts_crud(make_user, login):
    make_user("a@example.com", "ADMIN")
    admin = login("a@example.com")

    c = admin.post(f"{CRM}/companies", json={"name": "Acme", "website": "https://acme.test"})
    assert c.status_code == 201, c.text
    company = c.json()

    dup = admin.post(f"{CRM}/companies", json={"name": "Acme"})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "company_name_taken"

    updated = admin.patch(f"{CRM}/companies/{company['id']}", json={"status": "ARCHIVED"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "ARCHIVED"

    contact = admin.post(
        f"{CRM}/contacts",
        json={
            "first_name": "Nora",
            "last_name": "Baha",
            "email": "nora@example.com",
            "company_id": company["id"],
            "status": "LEAD",
        },
    )
    assert contact.status_code == 201, contact.text

    lst = admin.get(f"{CRM}/contacts", params={"search": "nora"})
    assert lst.status_code == 200
    assert lst.json()["total"] == 1
    assert lst.json()["items"][0]["company_name"] == "Acme"


def test_not_found_codes(make_user, login):
    make_user("a@example.com", "ADMIN")
    admin = login("a@example.com")
    missing = "00000000-0000-0000-0000-000000000000"

    assert admin.get(f"{CRM}/companies/{missing}").status_code == 404
    assert admin.get(f"{CRM}/companies/{missing}").json()["error"]["code"] == "company_not_found"

    assert admin.get(f"{CRM}/contacts/{missing}").status_code == 404
    assert admin.get(f"{CRM}/contacts/{missing}").json()["error"]["code"] == "contact_not_found"
