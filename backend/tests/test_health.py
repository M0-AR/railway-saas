from tests.conftest import API, register_tenant


async def test_healthz(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_readyz(client):
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


async def test_public_plans(client):
    response = await client.get(f"{API}/public/plans")
    assert response.status_code == 200
    codes = [plan["code"] for plan in response.json()]
    assert codes == ["starter", "growth", "enterprise"]
    starter = response.json()[0]
    assert starter["price_cents"] == 0
    assert starter["features"]["csv.import"] is False


async def test_public_tenant_resolution(client):
    registered = await register_tenant(client)
    slug = registered["tenant"]["slug"]

    response = await client.get(f"{API}/public/tenant", params={"slug": slug})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Acme Rail"
    assert body["plan_code"] == "starter"
    assert body["features"]["reports.basic"] is True
    assert body["features"]["csv.import"] is False
    assert body["currency"] == "USD"

    missing = await client.get(f"{API}/public/tenant", params={"slug": "no-such-workspace"})
    assert missing.status_code == 404

    empty = await client.get(f"{API}/public/tenant")
    assert empty.status_code == 400
