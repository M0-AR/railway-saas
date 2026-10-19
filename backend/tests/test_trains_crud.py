"""Trains CRUD, role gates, archival semantics, availability, export.

Plan quotas are covered in test_entitlements.py and test_trains_import.py.
"""

from datetime import date, timedelta

from tests.conftest import API, auth, create_train, login, register_tenant, set_tenant_plan


def _tomorrow() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


async def _member(client, owner_token, *, email: str, role: str):
    response = await client.post(
        f"{API}/team/users",
        json={
            "email": email,
            "full_name": f"{role.title()} Person",
            "role": role,
            "password": "Passw0rd!234",
        },
        headers=auth(owner_token),
    )
    assert response.status_code == 201, response.text
    return response.json()["member"]


async def test_train_crud_lifecycle(client):
    registered = await register_tenant(client, slug="rail-crud", email="owner@rail-crud.example")
    token = registered["access_token"]

    created = await create_train(
        client,
        token,
        number="TR-1",
        name="Trunk Line",
        source="Northgate",
        destination="Southport",
        fare_cents=1250,
        days_of_week=[5, 1, 3, 1],
    )
    assert created["currency"] == "USD"
    assert created["is_active"] is True
    assert created["days_of_week"] == [1, 3, 5]

    listing = await client.get(f"{API}/trains", headers=auth(token))
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    assert (
        await client.get(f"{API}/trains", params={"q": "tr-1"}, headers=auth(token))
    ).json()["total"] == 1
    assert (
        await client.get(f"{API}/trains", params={"q": "southport"}, headers=auth(token))
    ).json()["total"] == 1
    assert (
        await client.get(f"{API}/trains", params={"train_type": "sleeper"}, headers=auth(token))
    ).json()["total"] == 0

    fetched = await client.get(f"{API}/trains/{created['id']}", headers=auth(token))
    assert fetched.status_code == 200

    patched = await client.patch(
        f"{API}/trains/{created['id']}",
        json={"name": "Trunk Line Express", "fare_cents": 1500},
        headers=auth(token),
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Trunk Line Express"
    assert patched.json()["fare_cents"] == 1500

    deleted = await client.delete(f"{API}/trains/{created['id']}", headers=auth(token))
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True, "archived": False, "bookings": 0}

    gone = await client.get(f"{API}/trains/{created['id']}", headers=auth(token))
    assert gone.status_code == 404
    assert (await client.get(f"{API}/trains", headers=auth(token))).json()["total"] == 0


async def test_train_number_must_be_unique_per_tenant(client):
    first = await register_tenant(client, slug="rail-uniq", email="owner@rail-uniq.example")
    await create_train(client, first["access_token"], number="U-1")

    payload = {
        "number": "U-1",
        "name": "Copycat",
        "train_type": "express",
        "source": "Aville",
        "destination": "Bville",
        "total_seats": 10,
        "fare_cents": 500,
        "days_of_week": [1],
    }
    clash = await client.post(f"{API}/trains", json=payload, headers=auth(first["access_token"]))
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "conflict"

    second = await register_tenant(client, slug="rail-uniq2", email="owner@rail-uniq2.example")
    same_number_elsewhere = await create_train(client, second["access_token"], number="U-1")
    assert same_number_elsewhere["number"] == "U-1"


async def test_train_validation_rejections(client):
    registered = await register_tenant(client, slug="rail-valid", email="owner@rail-valid.example")
    token = registered["access_token"]
    base = {
        "number": "V-1",
        "name": "Valid Name",
        "train_type": "express",
        "source": "Here",
        "destination": "There",
        "total_seats": 20,
        "fare_cents": 900,
        "days_of_week": [1],
    }

    for mutate in (
        {"train_type": "hyperloop"},
        {"days_of_week": []},
        {"days_of_week": [0, 8]},
        {"total_seats": 0},
        {"fare_cents": -1},
        {"name": "X"},
        {"number": ""},
    ):
        response = await client.post(f"{API}/trains", json={**base, **mutate}, headers=auth(token))
        assert response.status_code == 422, (mutate, response.text)
        assert response.json()["error"]["code"] == "validation_error"


async def test_train_role_permissions(client, owner_engine):
    registered = await register_tenant(client, slug="rail-roles", email="owner@rail-roles.example")
    await set_tenant_plan(owner_engine, "rail-roles", "enterprise")
    owner_token = registered["access_token"]

    for email, role in (
        ("viewer@rail-roles.example", "viewer"),
        ("agent@rail-roles.example", "agent"),
        ("manager@rail-roles.example", "manager"),
    ):
        await _member(client, owner_token, email=email, role=role)

    viewer = await login(client, slug="rail-roles", email="viewer@rail-roles.example")
    agent = await login(client, slug="rail-roles", email="agent@rail-roles.example")
    manager = await login(client, slug="rail-roles", email="manager@rail-roles.example")

    payload = {
        "number": "RO-1",
        "name": "Role Test",
        "train_type": "express",
        "source": "Here",
        "destination": "There",
        "total_seats": 20,
        "fare_cents": 900,
        "days_of_week": [1],
    }
    for token in (viewer["access_token"], agent["access_token"]):
        denied = await client.post(f"{API}/trains", json=payload, headers=auth(token))
        assert denied.status_code == 403

    allowed = await client.post(
        f"{API}/trains", json=payload, headers=auth(manager["access_token"])
    )
    assert allowed.status_code == 201, allowed.text

    readable = await client.get(f"{API}/trains", headers=auth(viewer["access_token"]))
    assert readable.status_code == 200
    assert readable.json()["total"] == 1


async def test_train_with_bookings_is_archived_not_deleted(client):
    registered = await register_tenant(client, slug="rail-arch", email="owner@rail-arch.example")
    token = registered["access_token"]
    train = await create_train(client, token, number="AR-1", total_seats=10)

    booking = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": _tomorrow(),
            "seats": 1,
            "contact_name": "Archive Party",
        },
        headers=auth(token),
    )
    assert booking.status_code == 201, booking.text

    deleted = await client.delete(f"{API}/trains/{train['id']}", headers=auth(token))
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": False, "archived": True, "bookings": 1}

    fetched = await client.get(f"{API}/trains/{train['id']}", headers=auth(token))
    assert fetched.json()["is_active"] is False

    active = await client.get(f"{API}/trains", params={"is_active": "true"}, headers=auth(token))
    assert active.json()["total"] == 0
    archived = await client.get(
        f"{API}/trains", params={"is_active": "false"}, headers=auth(token)
    )
    assert archived.json()["total"] == 1


async def test_availability_follows_schedule_and_bookings(client):
    registered = await register_tenant(client, slug="rail-avail", email="owner@rail-avail.example")
    token = registered["access_token"]
    train = await create_train(client, token, number="AV-1", total_seats=6, days_of_week=[1])

    target = date.today() + timedelta(days=1)
    while target.isoweekday() != 1:
        target += timedelta(days=1)

    before = await client.get(
        f"{API}/trains/{train['id']}/availability",
        params={"date_from": target.isoformat(), "days": 7},
        headers=auth(token),
    )
    assert before.status_code == 200
    days = before.json()["days"]
    assert len(days) == 7
    running = [day for day in days if day["runs"]]
    assert len(running) == 1
    assert running[0]["date"] == target.isoformat()
    assert running[0]["seats_left"] == 6
    assert all(day["seats_left"] == 0 for day in days if not day["runs"])

    booked = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": target.isoformat(),
            "seats": 2,
            "contact_name": "Availability Party",
        },
        headers=auth(token),
    )
    assert booked.status_code == 201, booked.text

    after = await client.get(
        f"{API}/trains/{train['id']}/availability",
        params={"date_from": target.isoformat(), "days": 7},
        headers=auth(token),
    )
    booked_day = [day for day in after.json()["days"] if day["runs"]][0]
    assert booked_day["seats_left"] == 4


async def test_train_export_csv_roles_and_formula_guard(client, owner_engine):
    anonymous = await client.get(f"{API}/trains/export.csv")
    assert anonymous.status_code == 401

    registered = await register_tenant(
        client, slug="rail-export", email="owner@rail-export.example"
    )
    await set_tenant_plan(owner_engine, "rail-export", "enterprise")
    token = registered["access_token"]
    await create_train(client, token, number="EX-1", name="=SUM(A1:A2)")

    for email, role in (
        ("viewer@rail-export.example", "viewer"),
        ("agent@rail-export.example", "agent"),
    ):
        await _member(client, token, email=email, role=role)
        member = await login(client, slug="rail-export", email=email)
        denied = await client.get(f"{API}/trains/export.csv", headers=auth(member["access_token"]))
        assert denied.status_code == 403, email

    exported = await client.get(f"{API}/trains/export.csv", headers=auth(token))
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    body = exported.text
    assert body.splitlines()[0].startswith("number,name,train_type")
    assert "'=SUM(A1:A2)" in body
