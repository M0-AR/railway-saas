from datetime import date, timedelta

from app.bookings.service import PNR_ALPHABET, PNR_LENGTH
from tests.conftest import API, auth, create_train, register_tenant


async def _train_and_token(client, *, total_seats: int = 5):
    registered = await register_tenant(client)
    train = await create_train(
        client, registered["access_token"], total_seats=total_seats, fare_cents=1000
    )
    return registered, train


def _tomorrow() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


async def test_booking_lifecycle_keeps_inventory_consistent(client):
    registered, train = await _train_and_token(client)
    token = registered["access_token"]
    travel = _tomorrow()

    created = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": travel,
            "seats": 3,
            "contact_name": "Grace Lindqvist",
            "contact_email": "grace@example.com",
            "passengers": [
                {"full_name": "Grace Lindqvist", "age": 34},
                {"full_name": "Jon Doe", "age": 31},
                {"full_name": "Amy Doe", "age": 9},
            ],
        },
        headers=auth(token),
    )
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["status"] == "confirmed"
    assert booking["total_fare_cents"] == 3000
    assert booking["currency"] == "USD"
    assert len(booking["pnr"]) == PNR_LENGTH
    assert set(booking["pnr"]) <= set(PNR_ALPHABET)
    assert len(booking["passengers"]) == 3

    availability = await client.get(
        f"{API}/trains/{train['id']}/availability",
        params={"date_from": travel, "days": 1},
        headers=auth(token),
    )
    assert availability.status_code == 200
    assert availability.json()["days"][0]["seats_left"] == 2
    assert availability.json()["days"][0]["runs"] is True

    listings = await client.get(f"{API}/bookings", headers=auth(token))
    assert listings.json()["total"] == 1
    assert listings.json()["items"][0]["pnr"] == booking["pnr"]

    cancelled = await client.post(f"{API}/bookings/{booking['id']}/cancel", headers=auth(token))
    assert cancelled.status_code == 200
    cancelled_body = cancelled.json()
    assert cancelled_body["status"] == "cancelled"
    assert cancelled_body["refund_status"] == "pending"
    assert cancelled_body["cancelled_at"] is not None

    restored = await client.get(
        f"{API}/trains/{train['id']}/availability",
        params={"date_from": travel, "days": 1},
        headers=auth(token),
    )
    assert restored.json()["days"][0]["seats_left"] == 5

    again = await client.post(f"{API}/bookings/{booking['id']}/cancel", headers=auth(token))
    assert again.status_code == 409

    fetched = await client.get(f"{API}/bookings/{booking['id']}", headers=auth(token))
    assert fetched.status_code == 200
    assert fetched.json()["pnr"] == booking["pnr"]


async def test_overbooking_is_blocked_with_seat_details(client):
    registered, train = await _train_and_token(client, total_seats=4)
    token = registered["access_token"]
    travel = _tomorrow()

    first = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": travel,
            "seats": 3,
            "contact_name": "First Party",
        },
        headers=auth(token),
    )
    assert first.status_code == 201

    overbook = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": travel,
            "seats": 4,
            "contact_name": "Too Many",
        },
        headers=auth(token),
    )
    assert overbook.status_code == 409
    error = overbook.json()["error"]
    assert error["code"] == "conflict"
    assert error["details"]["seats_left"] == 1
    assert error["details"]["requested"] == 4

    listings = await client.get(f"{API}/bookings", headers=auth(token))
    assert listings.json()["total"] == 1


async def test_booking_validation_rules(client):
    registered, train = await _train_and_token(client)
    token = registered["access_token"]

    mismatch = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": _tomorrow(),
            "seats": 2,
            "contact_name": "Count Mismatch",
            "passengers": [{"full_name": "Only One", "age": 40}],
        },
        headers=auth(token),
    )
    assert mismatch.status_code == 409

    past = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": (date.today() - timedelta(days=1)).isoformat(),
            "seats": 1,
            "contact_name": "Time Traveler",
        },
        headers=auth(token),
    )
    assert past.status_code == 409

    unknown_train = await client.post(
        f"{API}/bookings",
        json={
            "train_id": "00000000-0000-0000-0000-000000000000",
            "travel_date": _tomorrow(),
            "seats": 1,
            "contact_name": "Ghost Train",
        },
        headers=auth(token),
    )
    assert unknown_train.status_code == 404

    bad_seats = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": _tomorrow(),
            "seats": 0,
            "contact_name": "Zero Seats",
        },
        headers=auth(token),
    )
    assert bad_seats.status_code == 422


async def test_booking_respects_operating_days(client):
    registered = await register_tenant(client, slug="weekday", email="owner@weekday.example")
    token = registered["access_token"]
    train = await create_train(
        client, token, number="WD-1", name="Weekday Only", days_of_week=[1]
    )

    target = date.today() + timedelta(days=1)
    while target.isoweekday() != 1:
        target += timedelta(days=1)

    on_day = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": target.isoformat(),
            "seats": 1,
            "contact_name": "Monday Rider",
        },
        headers=auth(token),
    )
    assert on_day.status_code == 201

    off_day = target + timedelta(days=1)
    refused = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": off_day.isoformat(),
            "seats": 1,
            "contact_name": "Tuesday Rider",
        },
        headers=auth(token),
    )
    assert refused.status_code == 409
