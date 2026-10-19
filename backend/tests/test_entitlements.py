"""Plan gates on the starter plan: feature gates (402) and quota gates (402)."""

from datetime import date, timedelta

from tests.conftest import API, auth, create_train, register_tenant


def _tomorrow() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


async def test_starter_feature_gates(client):
    registered = await register_tenant(client)
    token = registered["access_token"]
    headers = auth(token)

    custom_domain = await client.patch(
        f"{API}/settings", json={"custom_domain": "rail.acme.example"}, headers=headers
    )
    assert custom_domain.status_code == 402
    assert custom_domain.json()["error"]["code"] == "entitlement_required"

    csv_import = await client.post(
        f"{API}/trains/import",
        files={"file": ("trains.csv", b"number,name\nT1,Test\n", "text/csv")},
        headers=headers,
    )
    assert csv_import.status_code == 402

    audit = await client.get(f"{API}/audit", headers=headers)
    assert audit.status_code == 402

    advanced = await client.get(f"{API}/reports/revenue", headers=headers)
    assert advanced.status_code == 402

    basic = await client.get(f"{API}/reports/overview", headers=headers)
    assert basic.status_code == 200

    plain_settings = await client.patch(
        f"{API}/settings", json={"name": "Acme Rail HQ"}, headers=headers
    )
    assert plain_settings.status_code == 200
    assert plain_settings.json()["name"] == "Acme Rail HQ"


async def test_starter_user_quota(client):
    registered = await register_tenant(client)
    token = registered["access_token"]
    headers = auth(token)

    for index in range(2):
        response = await client.post(
            f"{API}/team/users",
            json={
                "email": f"member{index}@acme.example",
                "full_name": f"Member {index}",
                "role": "agent",
                "password": "Passw0rd!234",
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text

    blocked = await client.post(
        f"{API}/team/users",
        json={
            "email": "overflow@acme.example",
            "full_name": "Overflow Member",
            "role": "agent",
            "password": "Passw0rd!234",
        },
        headers=headers,
    )
    assert blocked.status_code == 402
    assert blocked.json()["error"]["code"] == "quota_exceeded"

    team = await client.get(f"{API}/team/users", headers=headers)
    assert team.json()["total"] == 3


async def test_starter_train_quota(client):
    registered = await register_tenant(client)
    token = registered["access_token"]

    for index in range(10):
        await create_train(
            client, token, number=f"Q-{index:02d}", name=f"Quota Train {index}"
        )

    blocked = await client.post(
        f"{API}/trains",
        json={
            "number": "Q-99",
            "name": "One Too Many",
            "source": "Alpha",
            "destination": "Beta",
            "total_seats": 10,
            "fare_cents": 100,
        },
        headers=auth(token),
    )
    assert blocked.status_code == 402
    assert blocked.json()["error"]["code"] == "quota_exceeded"

    trains = await client.get(f"{API}/trains", headers=auth(token))
    assert trains.json()["total"] == 10


async def test_me_exposes_locked_entitlements(client):
    registered = await register_tenant(client)
    me = await client.get(f"{API}/me", headers=auth(registered["access_token"]))
    entitlements = me.json()["entitlements"]

    assert entitlements["plan_code"] == "starter"
    assert entitlements["features"] == {
        "reports.basic": True,
        "reports.advanced": False,
        "csv.import": False,
        "custom_domain": False,
        "audit.view": False,
        "team.roles": False,
    }
    assert entitlements["quotas"] == {
        "max_trains": 10,
        "max_users": 3,
        "max_bookings_per_month": 500,
    }
