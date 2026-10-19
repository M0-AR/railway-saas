"""Audit log: plan + role gates, recorded actions, filters, tenant scoping."""

from datetime import date, timedelta

from tests.conftest import (
    API,
    auth,
    create_train,
    login,
    register_tenant,
    set_tenant_plan,
)

DEFAULT_PW = "Passw0rd!234"


def _yesterday() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


async def _entries(client, token: str, **params) -> dict:
    response = await client.get(f"{API}/audit", params=params, headers=auth(token))
    assert response.status_code == 200, response.text
    return response.json()


async def test_audit_requires_plan_and_staff_role(client, owner_engine):
    registered = await register_tenant(client, slug="aud-roles", email="owner@aud-roles.example")
    token = registered["access_token"]

    gated = await client.get(f"{API}/audit", headers=auth(token))
    assert gated.status_code == 402
    assert gated.json()["error"]["code"] == "entitlement_required"

    await set_tenant_plan(owner_engine, "aud-roles", "growth")
    allowed = await client.get(f"{API}/audit", headers=auth(token))
    assert allowed.status_code == 200

    created = await client.post(
        f"{API}/team/users",
        json={
            "email": "manager@aud-roles.example",
            "full_name": "Audit Manager",
            "role": "manager",
            "password": DEFAULT_PW,
        },
        headers=auth(token),
    )
    assert created.status_code == 201, created.text
    manager = await login(client, slug="aud-roles", email="manager@aud-roles.example")

    denied = await client.get(f"{API}/audit", headers=auth(manager["access_token"]))
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"


async def test_audit_records_actions_with_filters(client, owner_engine):
    registered = await register_tenant(client, slug="aud-flow", email="owner@aud-flow.example")
    await set_tenant_plan(owner_engine, "aud-flow", "growth")
    token = registered["access_token"]
    train = await create_train(client, token, number="AU-1")

    booked = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": date.today().isoformat(),
            "seats": 1,
            "contact_name": "Audit Party",
        },
        headers=auth(token),
    )
    assert booked.status_code == 201, booked.text
    cancelled = await client.post(
        f"{API}/bookings/{booked.json()['id']}/cancel", headers=auth(token)
    )
    assert cancelled.status_code == 200
    patched = await client.patch(
        f"{API}/settings", json={"name": "Audited Rail"}, headers=auth(token)
    )
    assert patched.status_code == 200
    await login(client, slug="aud-flow", email="owner@aud-flow.example")

    full = await _entries(client, token, page_size=100)
    actions = {item["action"] for item in full["items"]}
    assert {
        "tenant.provisioned",
        "auth.login",
        "train.created",
        "booking.created",
        "booking.cancelled",
        "settings.updated",
    } <= actions
    timestamps = [item["created_at"] for item in full["items"]]
    assert timestamps == sorted(timestamps, reverse=True)
    assert all(item["actor_email"] == "owner@aud-flow.example" for item in full["items"])

    by_action = await _entries(client, token, action="train.created")
    assert by_action["total"] == 1
    entry = by_action["items"][0]
    assert entry["entity_type"] == "train"
    assert entry["entity_id"] == train["id"]

    by_type = await _entries(client, token, entity_type="booking")
    assert by_type["total"] == 2

    by_q = await _entries(client, token, q="SETTINGS.UPDATED")
    assert by_q["total"] == 1

    recent = await _entries(client, token, date_from=date.today().isoformat())
    assert recent["total"] == len(full["items"])
    stale = await _entries(client, token, date_to=_yesterday())
    assert stale["total"] == 0

    paged = await _entries(client, token, page_size=2, page=2)
    assert paged["total"] == len(full["items"])
    assert len(paged["items"]) == 2


async def test_audit_is_tenant_scoped(client, owner_engine):
    first = await register_tenant(client, slug="aud-first", email="owner@aud-first.example")
    second = await register_tenant(client, slug="aud-second", email="owner@aud-second.example")
    await set_tenant_plan(owner_engine, "aud-first", "growth")
    await set_tenant_plan(owner_engine, "aud-second", "growth")

    other = await _entries(client, second["access_token"], page_size=100)
    assert other["total"] == 1
    assert other["items"][0]["action"] == "tenant.provisioned"

    mine = await _entries(client, first["access_token"], page_size=100)
    assert mine["total"] == 1
    assert all(item["entity_id"] != other["items"][0]["entity_id"] for item in mine["items"])
