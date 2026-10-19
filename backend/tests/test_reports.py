"""Reports: zero-state, real activity math, tenant scoping, and query bounds."""

from datetime import date

from tests.conftest import API, auth, create_train, register_tenant, set_tenant_plan


def _today() -> str:
    return date.today().isoformat()


async def _book(client, token: str, train_id: str, seats: int, name: str):
    response = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train_id,
            "travel_date": _today(),
            "seats": seats,
            "contact_name": name,
        },
        headers=auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_overview_zero_state_on_starter_plan(client):
    registered = await register_tenant(client, slug="rep-zero", email="owner@rep-zero.example")
    response = await client.get(
        f"{API}/reports/overview", headers=auth(registered["access_token"])
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "currency": "USD",
        "revenue": {"today_cents": 0, "last_30d_cents": 0},
        "bookings": {"today": 0, "last_30d": 0},
        "trains": {"active": 0, "total": 0},
        "occupancy_today": {"booked": 0, "capacity": 0, "rate": 0.0},
        "cancellation_rate_30d": 0.0,
    }


async def test_overview_and_advanced_numbers_match_real_activity(client, owner_engine):
    registered = await register_tenant(client, slug="rep-live", email="owner@rep-live.example")
    await set_tenant_plan(owner_engine, "rep-live", "growth")
    token = registered["access_token"]
    train = await create_train(client, token, number="RP-1", total_seats=40, fare_cents=1500)

    confirmed = await _book(client, token, train["id"], 3, "Confirmed Party")
    doomed = await _book(client, token, train["id"], 2, "Cancelled Party")
    cancelled = await client.post(
        f"{API}/bookings/{doomed['id']}/cancel", headers=auth(token)
    )
    assert cancelled.status_code == 200

    overview = (
        await client.get(f"{API}/reports/overview", headers=auth(token))
    ).json()
    assert overview["currency"] == "USD"
    assert overview["revenue"]["today_cents"] == 4500  # confirmed seats only
    assert overview["bookings"]["today"] == 2  # cancelled booking still counted
    assert overview["trains"] == {"active": 1, "total": 1}
    assert overview["occupancy_today"] == {"booked": 3, "capacity": 40, "rate": 0.075}
    assert overview["cancellation_rate_30d"] == 0.5

    revenue = (
        await client.get(f"{API}/reports/revenue", params={"days": 7}, headers=auth(token))
    ).json()
    assert revenue["currency"] == "USD"
    assert len(revenue["days"]) == 7
    assert revenue["days"][-1]["day"] == _today()
    assert revenue["days"][-1]["revenue_cents"] == 4500
    assert revenue["days"][-1]["bookings"] == 1
    assert all(point["revenue_cents"] == 0 for point in revenue["days"][:-1])

    top = (
        await client.get(f"{API}/reports/top-trains", params={"days": 7}, headers=auth(token))
    ).json()
    assert top["days"] == 7
    assert len(top["trains"]) == 1
    row = top["trains"][0]
    assert row["train_id"] == confirmed["train"]["id"]
    assert row["number"] == "RP-1"
    assert row["bookings"] == 1
    assert row["seats"] == 3
    assert row["revenue_cents"] == 4500

    occupancy = (
        await client.get(
            f"{API}/reports/occupancy", params={"on": _today()}, headers=auth(token)
        )
    ).json()
    assert occupancy["date"] == _today()
    assert len(occupancy["trains"]) == 1
    assert occupancy["trains"][0]["booked"] == 3
    assert occupancy["trains"][0]["capacity"] == 40
    assert occupancy["trains"][0]["rate"] == 0.075


async def test_reports_are_tenant_scoped(client, owner_engine):
    booked = await register_tenant(client, slug="rep-a", email="owner@rep-a.example")
    await set_tenant_plan(owner_engine, "rep-a", "growth")
    train = await create_train(client, booked["access_token"], number="RA-1")
    await _book(client, booked["access_token"], train["id"], 1, "Isolation Party")

    other = await register_tenant(client, slug="rep-b", email="owner@rep-b.example")
    await set_tenant_plan(owner_engine, "rep-b", "growth")
    headers = auth(other["access_token"])

    overview = (await client.get(f"{API}/reports/overview", headers=headers)).json()
    assert overview["bookings"]["today"] == 0
    assert overview["revenue"]["today_cents"] == 0

    top = (
        await client.get(f"{API}/reports/top-trains", params={"days": 7}, headers=headers)
    ).json()
    assert top["trains"] == []
    occupancy = (await client.get(f"{API}/reports/occupancy", headers=headers)).json()
    assert occupancy["trains"] == []


async def test_revenue_days_bounds_are_validated(client, owner_engine):
    registered = await register_tenant(client, slug="rep-bound", email="owner@rep-bound.example")
    await set_tenant_plan(owner_engine, "rep-bound", "growth")
    headers = auth(registered["access_token"])

    too_short = await client.get(f"{API}/reports/revenue", params={"days": 6}, headers=headers)
    assert too_short.status_code == 422
    too_long = await client.get(f"{API}/reports/revenue", params={"days": 181}, headers=headers)
    assert too_long.status_code == 422
