"""CSV import: entitlement gate, role gate, create/update semantics, per-line
errors, malformed input, size limit, and quota interaction."""

from sqlalchemy import text

from tests.conftest import API, auth, create_train, login, register_tenant, set_tenant_plan

HEADER = (
    "number,name,train_type,source,destination,departure_time,arrival_time,"
    "days_of_week,total_seats,fare\n"
)


def _csv(*rows: str) -> bytes:
    return (HEADER + "\n".join(rows) + "\n").encode()


def _upload(client, token: str, content: bytes, filename: str = "trains.csv"):
    return client.post(
        f"{API}/trains/import",
        files={"file": (filename, content, "text/csv")},
        headers=auth(token),
    )


async def test_import_requires_feature_and_manager_role(client, owner_engine):
    registered = await register_tenant(client, slug="imp-gate", email="owner@imp-gate.example")
    token = registered["access_token"]
    row = "I-1,Interceptor,express,North,South,08:00,12:00,1,50,20.00"

    gated = await _upload(client, token, _csv(row))
    assert gated.status_code == 402
    assert gated.json()["error"]["code"] == "entitlement_required"

    await set_tenant_plan(owner_engine, "imp-gate", "growth")
    created = await client.post(
        f"{API}/team/users",
        json={
            "email": "viewer@imp-gate.example",
            "full_name": "Viewer Person",
            "role": "viewer",
            "password": "Passw0rd!234",
        },
        headers=auth(token),
    )
    assert created.status_code == 201
    viewer = await login(client, slug="imp-gate", email="viewer@imp-gate.example")

    forbidden = await _upload(client, viewer["access_token"], _csv(row))
    assert forbidden.status_code == 403


async def test_import_creates_updates_and_reports_line_errors(client, owner_engine):
    registered = await register_tenant(client, slug="imp-flow", email="owner@imp-flow.example")
    await set_tenant_plan(owner_engine, "imp-flow", "growth")
    token = registered["access_token"]
    await create_train(client, token, number="I-10", name="Original")

    content = _csv(
        "I-10,Updated Name,express,North,South,08:00,12:00,1,60,25.50",
        "I-11,Brand New,intercity,East,West,,,1,80,10.00",
        "I-12,Bad Type,spaceship,Earth,Mars,,,1,10,5.00",
    )
    imported = await _upload(client, token, content)
    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["created"] == 1
    assert body["updated"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["line"] == 4
    assert "train_type" in body["errors"][0]["error"]

    refreshed = await client.get(
        f"{API}/trains", params={"q": "I-10"}, headers=auth(token)
    )
    row = refreshed.json()["items"][0]
    assert row["name"] == "Updated Name"
    assert row["total_seats"] == 60
    assert row["fare_cents"] == 2550

    added = await client.get(f"{API}/trains", params={"q": "I-11"}, headers=auth(token))
    assert added.json()["total"] == 1
    assert added.json()["items"][0]["train_type"] == "intercity"

    # Re-importing the same file is idempotent: updates, no duplicates.
    again = await _upload(client, token, content)
    assert again.json()["created"] == 0
    assert again.json()["updated"] == 2
    assert len(again.json()["errors"]) == 1
    listing = await client.get(f"{API}/trains", headers=auth(token))
    assert listing.json()["total"] == 2


async def test_import_rejects_malformed_input(client, owner_engine):
    registered = await register_tenant(client, slug="imp-bad", email="owner@imp-bad.example")
    await set_tenant_plan(owner_engine, "imp-bad", "growth")
    token = registered["access_token"]

    empty = await _upload(client, token, b"")
    assert empty.status_code == 400
    assert "header" in empty.json()["error"]["message"].lower()

    missing = await _upload(client, token, b"number,name\nI-1,Incomplete\n")
    assert missing.status_code == 400
    assert "missing required columns" in missing.json()["error"]["message"]

    binary = await _upload(client, token, b"\xff\xfe\x00\x01")
    assert binary.status_code == 400

    oversized = await _upload(client, token, b"number" + b"x" * (5 * 1024 * 1024))
    assert oversized.status_code == 400
    assert "too large" in oversized.json()["error"]["message"].lower()


async def test_import_respects_train_quota(client, owner_engine):
    registered = await register_tenant(client, slug="imp-quota", email="owner@imp-quota.example")
    token = registered["access_token"]

    # Starter plan lacks csv.import, so enable only that feature via override;
    # the max_trains quota (10) stays at the starter level.
    async with owner_engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE tenant SET features_override = "
                "'{\"features\": {\"csv.import\": true}}'::jsonb WHERE slug = 'imp-quota'"
            )
        )

    for index in range(10):
        await create_train(client, token, number=f"IQ-{index:02d}")

    overflow = await _upload(
        client, token, _csv("IQ-NEW,One Too Many,express,A,B,,,1,10,5.00")
    )
    assert overflow.status_code == 402
    assert overflow.json()["error"]["code"] == "quota_exceeded"
