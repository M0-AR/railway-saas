"""Booking listing filters, pagination, role gates, validation edges, and the
CSV export (including the spreadsheet-formula guard)."""

from datetime import date, timedelta

from tests.conftest import API, auth, create_train, login, register_tenant, set_tenant_plan


def _tomorrow() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


async def _book(client, token: str, train_id: str, *, seats: int = 1, name: str = "Passenger One"):
    return await client.post(
        f"{API}/bookings",
        json={
            "train_id": train_id,
            "travel_date": _tomorrow(),
            "seats": seats,
            "contact_name": name,
        },
        headers=auth(token),
    )


async def _add_member(client, owner_token: str, email: str, role: str):
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


async def test_booking_list_filters_and_pagination(client):
    registered = await register_tenant(
        client, slug="bk-filters", email="owner@bk-filters.example"
    )
    token = registered["access_token"]
    train_a = await create_train(client, token, number="FA-1")
    train_b = await create_train(client, token, number="FB-2")

    first = (await _book(client, token, train_a["id"], name="Filterme Person")).json()
    second = (await _book(client, token, train_a["id"], name="Second Person")).json()
    third = (await _book(client, token, train_b["id"], name="Train Bee")).json()
    assert len({first["pnr"], second["pnr"], third["pnr"]}) == 3

    cancelled = await client.post(f"{API}/bookings/{first['id']}/cancel", headers=auth(token))
    assert cancelled.status_code == 200

    by_q = await client.get(
        f"{API}/bookings", params={"q": first["pnr"].lower()}, headers=auth(token)
    )
    assert by_q.json()["total"] == 1
    assert by_q.json()["items"][0]["id"] == first["id"]

    by_status = await client.get(
        f"{API}/bookings", params={"status": "cancelled"}, headers=auth(token)
    )
    assert by_status.json()["total"] == 1

    by_train = await client.get(
        f"{API}/bookings", params={"train_id": train_b["id"]}, headers=auth(token)
    )
    assert by_train.json()["total"] == 1

    by_date = await client.get(
        f"{API}/bookings",
        params={"date_from": _tomorrow(), "date_to": _tomorrow()},
        headers=auth(token),
    )
    assert by_date.json()["total"] == 3

    page_one = await client.get(
        f"{API}/bookings", params={"page_size": 2, "page": 1}, headers=auth(token)
    )
    assert page_one.json()["total"] == 3
    assert len(page_one.json()["items"]) == 2
    page_two = await client.get(
        f"{API}/bookings", params={"page_size": 2, "page": 2}, headers=auth(token)
    )
    assert len(page_two.json()["items"]) == 1

    oversized = await client.get(f"{API}/bookings", params={"page_size": 500}, headers=auth(token))
    assert oversized.status_code == 422
    capped = await client.get(f"{API}/bookings", params={"page_size": 100}, headers=auth(token))
    assert capped.status_code == 200
    assert capped.json()["page_size"] == 100


async def test_booking_write_roles(client, owner_engine):
    registered = await register_tenant(client, slug="bk-roles", email="owner@bk-roles.example")
    await set_tenant_plan(owner_engine, "bk-roles", "growth")
    owner_token = registered["access_token"]
    train = await create_train(client, owner_token, number="BR-1")

    await _add_member(client, owner_token, "viewer@bk-roles.example", "viewer")
    await _add_member(client, owner_token, "agent@bk-roles.example", "agent")
    viewer = await login(client, slug="bk-roles", email="viewer@bk-roles.example")
    agent = await login(client, slug="bk-roles", email="agent@bk-roles.example")

    denied = await _book(client, viewer["access_token"], train["id"])
    assert denied.status_code == 403

    readable = await client.get(f"{API}/bookings", headers=auth(viewer["access_token"]))
    assert readable.status_code == 200

    allowed = await _book(client, agent["access_token"], train["id"])
    assert allowed.status_code == 201, allowed.text
    cancelled = await client.post(
        f"{API}/bookings/{allowed.json()['id']}/cancel", headers=auth(agent["access_token"])
    )
    assert cancelled.status_code == 200


async def test_booking_schema_validation(client):
    registered = await register_tenant(client, slug="bk-valid", email="owner@bk-valid.example")
    token = registered["access_token"]
    train = await create_train(client, token, number="BV-1")
    base = {
        "train_id": train["id"],
        "travel_date": _tomorrow(),
        "seats": 1,
        "contact_name": "Validation Person",
    }

    for mutate in (
        {"channel": "web"},
        {"seats": 11},
        {"seats": 0},
        {"contact_name": "X"},
        {"notes": "n" * 2001},
    ):
        response = await client.post(
            f"{API}/bookings", json={**base, **mutate}, headers=auth(token)
        )
        assert response.status_code == 422, (mutate, response.text)
        assert response.json()["error"]["code"] == "validation_error"


async def test_inactive_train_cannot_take_bookings(client):
    registered = await register_tenant(
        client, slug="bk-inactive", email="owner@bk-inactive.example"
    )
    token = registered["access_token"]
    train = await create_train(client, token, number="BI-1")

    patched = await client.patch(
        f"{API}/trains/{train['id']}", json={"is_active": False}, headers=auth(token)
    )
    assert patched.status_code == 200

    refused = await _book(client, token, train["id"])
    assert refused.status_code == 409
    assert "no longer in service" in refused.json()["error"]["message"]


async def test_booking_export_csv_roles_and_formula_guard(client, owner_engine):
    anonymous = await client.get(f"{API}/bookings/export.csv")
    assert anonymous.status_code == 401

    registered = await register_tenant(
        client, slug="bk-export", email="owner@bk-export.example"
    )
    await set_tenant_plan(owner_engine, "bk-export", "growth")
    token = registered["access_token"]
    train = await create_train(client, token, number="BE-1")
    booked = await _book(client, token, train["id"], name="=cmd|' /C calc'!A0")
    assert booked.status_code == 201

    await _add_member(client, token, "viewer@bk-export.example", "viewer")
    await _add_member(client, token, "agent@bk-export.example", "agent")
    viewer = await login(client, slug="bk-export", email="viewer@bk-export.example")
    agent = await login(client, slug="bk-export", email="agent@bk-export.example")

    for member in (viewer, agent):
        denied = await client.get(
            f"{API}/bookings/export.csv", headers=auth(member["access_token"])
        )
        assert denied.status_code == 403

    exported = await client.get(f"{API}/bookings/export.csv", headers=auth(token))
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    body = exported.text
    assert body.splitlines()[0].startswith("pnr,train_number")
    assert "'=cmd|" in body
    assert booked.json()["pnr"] in body
