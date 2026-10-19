"""Public (anonymous) surface: tenant resolution and the plan catalog.

These endpoints are hit by every visitor before sign-in, so they must stay
authenticated-free, minimal, and never leak internal columns.
"""

from tests.conftest import API, auth, register_tenant, set_tenant_plan


async def test_public_tenant_lookup_is_minimal(client):
    await register_tenant(client, slug="acme-public", email="owner@acme-public.example")

    response = await client.get(f"{API}/public/tenant", params={"slug": "Acme-Public"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["slug"] == "acme-public"
    assert body["name"] == "Acme Rail"
    assert body["plan_code"] == "starter"
    assert body["features"]["reports.basic"] is True
    assert body["features"]["reports.advanced"] is False
    for leaked in ("id", "custom_domain", "billing_customer_id", "features_override"):
        assert leaked not in body, f"public payload leaks {leaked}"


async def test_custom_domain_resolution_prefers_domain(client, owner_engine):
    registered = await register_tenant(
        client, slug="acme-domain", email="owner@acme-domain.example"
    )
    await set_tenant_plan(owner_engine, "acme-domain", "growth")

    patched = await client.patch(
        f"{API}/settings",
        json={"custom_domain": "trains.acme-domain.example"},
        headers=auth(registered["access_token"]),
    )
    assert patched.status_code == 200, patched.text

    by_domain = await client.get(
        f"{API}/public/tenant",
        params={"slug": "unrelated", "domain": "TRAINS.ACME-DOMAIN.EXAMPLE:8443"},
    )
    assert by_domain.status_code == 200
    assert by_domain.json()["slug"] == "acme-domain"


async def test_public_lookup_errors(client):
    missing = await client.get(f"{API}/public/tenant")
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "bad_request"

    unknown = await client.get(f"{API}/public/tenant", params={"slug": "no-such-workspace"})
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"


async def test_public_plan_catalog(client):
    response = await client.get(f"{API}/public/plans")
    assert response.status_code == 200
    plans = response.json()
    assert [p["code"] for p in plans] == ["starter", "growth", "enterprise"]

    starter, growth, enterprise = plans
    assert starter["price_cents"] == 0
    assert growth["features"]["csv.import"] is True
    assert growth["quotas"]["max_trains"] == 100
    assert enterprise["quotas"]["max_trains"] == -1
