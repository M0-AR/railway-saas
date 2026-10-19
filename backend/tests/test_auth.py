from sqlalchemy import text

from tests.conftest import API, auth, login, register_tenant


async def test_register_returns_tokens_and_tenant(client):
    body = await register_tenant(client)
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["role"] == "owner"
    assert body["tenant"]["slug"] == "acme"
    assert body["tenant"]["plan_code"] == "starter"


async def test_me_reports_entitlements(client):
    body = await register_tenant(client)
    response = await client.get(f"{API}/me", headers=auth(body["access_token"]))
    assert response.status_code == 200
    me = response.json()
    assert me["user"]["email"] == "owner@acme.example"
    assert me["entitlements"]["plan_code"] == "starter"
    assert me["entitlements"]["features"]["custom_domain"] is False
    assert me["entitlements"]["quotas"]["max_trains"] == 10


async def test_slug_is_normalized(client):
    body = await register_tenant(client, slug="Acme-Rail", email="a@acme.example")
    assert body["tenant"]["slug"] == "acme-rail"


async def test_duplicate_slug_conflicts(client):
    await register_tenant(client)
    response = await client.post(
        f"{API}/auth/register",
        json={
            "org_name": "Other Rail",
            "slug": "acme",
            "full_name": "Other Owner",
            "email": "other@acme.example",
            "password": "Passw0rd!234",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_duplicate_email_in_tenant_conflicts(client):
    await register_tenant(client)
    response = await client.post(
        f"{API}/auth/register",
        json={
            "org_name": "Acme Again",
            "slug": "acme",
            "full_name": "Twin Owner",
            "email": "owner@acme.example",
            "password": "Passw0rd!234",
        },
    )
    assert response.status_code == 409


async def test_reserved_and_invalid_slugs_rejected(client):
    for bad_slug in ("www", "api", "ab", "has_underscore", "-leading"):
        response = await client.post(
            f"{API}/auth/register",
            json={
                "org_name": "Bad Slug Rail",
                "slug": bad_slug,
                "full_name": "Bad Owner",
                "email": f"bad-{bad_slug}@example.com",
                "password": "Passw0rd!234",
            },
        )
        assert response.status_code == 422, bad_slug


async def test_weak_password_rejected(client):
    response = await client.post(
        f"{API}/auth/register",
        json={
            "org_name": "Weak Rail",
            "slug": "weakrail",
            "full_name": "Weak Owner",
            "email": "weak@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422


async def test_login_logout_cycle(client):
    await register_tenant(client)

    ok = await client.post(
        f"{API}/auth/login",
        json={"email": "owner@acme.example", "password": "Passw0rd!234", "tenant_slug": "acme"},
    )
    assert ok.status_code == 200

    wrong_password = await client.post(
        f"{API}/auth/login",
        json={"email": "owner@acme.example", "password": "WrongPassword!", "tenant_slug": "acme"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["error"]["code"] == "unauthorized"

    unknown_tenant = await client.post(
        f"{API}/auth/login",
        json={"email": "owner@acme.example", "password": "Passw0rd!234", "tenant_slug": "ghost"},
    )
    assert unknown_tenant.status_code == 401


async def test_refresh_rotates_session(client):
    registered = await register_tenant(client)

    refreshed = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": registered["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_access = refreshed.json()["access_token"]

    me = await client.get(f"{API}/me", headers=auth(new_access))
    assert me.status_code == 200

    bogus = await client.post(f"{API}/auth/refresh", json={"refresh_token": "not-a-token"})
    assert bogus.status_code == 401


async def test_access_token_is_not_a_refresh_token(client):
    registered = await register_tenant(client)
    response = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": registered["access_token"]}
    )
    assert response.status_code == 401


async def test_unauthenticated_access_is_rejected(client):
    response = await client.get(f"{API}/me")
    assert response.status_code == 401


async def test_refresh_requires_active_tenant_and_member(client, owner_engine):
    owner = await register_tenant(
        client, slug="refresh-guard", email="owner@refresh-guard.example"
    )
    created = await client.post(
        f"{API}/team/users",
        headers=auth(owner["access_token"]),
        json={
            "email": "agent@refresh-guard.example",
            "full_name": "Refresh Agent",
            "role": "agent",
            "password": "Passw0rd!234",
        },
    )
    assert created.status_code == 201
    agent = await login(
        client, slug="refresh-guard", email="agent@refresh-guard.example"
    )

    deactivated = await client.patch(
        f"{API}/team/users/{created.json()['member']['id']}",
        headers=auth(owner["access_token"]),
        json={"is_active": False},
    )
    assert deactivated.status_code == 200
    stale = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": agent["refresh_token"]}
    )
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "unauthorized"

    async with owner_engine.begin() as conn:
        await conn.execute(
            text("UPDATE tenant SET status = 'suspended' WHERE slug = 'refresh-guard'")
        )
    suspended = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": owner["refresh_token"]}
    )
    assert suspended.status_code == 401
