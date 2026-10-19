"""Workspace settings PATCH: field normalization, role gate, domain lifecycle."""

from tests.conftest import API, auth, login, register_tenant, set_tenant_plan

DEFAULT_PW = "Passw0rd!234"


async def test_settings_patch_normalizes_fields(client):
    registered = await register_tenant(client, slug="set-fields", email="owner@set-fields.example")
    response = await client.patch(
        f"{API}/settings",
        json={
            "name": "Acme Rail Group",
            "default_currency": "eur",
            "locale": "fr-FR",
            "timezone": "Europe/Paris",
        },
        headers=auth(registered["access_token"]),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["name"] == "Acme Rail Group"
    assert body["default_currency"] == "EUR"
    assert body["locale"] == "fr-FR"
    assert body["timezone"] == "Europe/Paris"

    fetched = await client.get(
        f"{API}/settings", headers=auth(registered["access_token"])
    )
    assert fetched.json()["default_currency"] == "EUR"


async def test_branding_patch_merges_with_existing_values(client):
    registered = await register_tenant(client, slug="set-brand", email="owner@set-brand.example")
    response = await client.patch(
        f"{API}/settings",
        json={"branding": {"primary_color": "#123456"}},
        headers=auth(registered["access_token"]),
    )
    assert response.status_code == 200
    branding = response.json()["branding"]
    assert branding["primary_color"] == "#123456"
    assert branding["accent_color"] == "#22d3ee"  # untouched default
    assert branding["logo_text"] == "Acme Rail"  # set at registration


async def test_settings_patch_requires_owner_or_admin(client):
    registered = await register_tenant(client, slug="set-roles", email="owner@set-roles.example")
    token = registered["access_token"]
    created = await client.post(
        f"{API}/team/users",
        json={
            "email": "agent@set-roles.example",
            "full_name": "Settings Agent",
            "role": "agent",
            "password": DEFAULT_PW,
        },
        headers=auth(token),
    )
    assert created.status_code == 201, created.text
    agent = await login(client, slug="set-roles", email="agent@set-roles.example")

    denied = await client.patch(
        f"{API}/settings",
        json={"name": "Agent Renamed Us"},
        headers=auth(agent["access_token"]),
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"

    readable = await client.get(f"{API}/settings", headers=auth(agent["access_token"]))
    assert readable.status_code == 200


async def test_custom_domain_lifecycle_on_growth(client, owner_engine):
    first = await register_tenant(client, slug="set-dom-a", email="owner@set-dom-a.example")
    second = await register_tenant(client, slug="set-dom-b", email="owner@set-dom-b.example")
    await set_tenant_plan(owner_engine, "set-dom-a", "growth")
    await set_tenant_plan(owner_engine, "set-dom-b", "growth")

    attached = await client.patch(
        f"{API}/settings",
        json={"custom_domain": "Rail-Set-Dom.Example"},
        headers=auth(first["access_token"]),
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["custom_domain"] == "rail-set-dom.example"

    idempotent = await client.patch(
        f"{API}/settings",
        json={"custom_domain": "rail-set-dom.example"},
        headers=auth(first["access_token"]),
    )
    assert idempotent.status_code == 200

    clash = await client.patch(
        f"{API}/settings",
        json={"custom_domain": "rail-set-dom.example"},
        headers=auth(second["access_token"]),
    )
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "conflict"

    cleared = await client.patch(
        f"{API}/settings",
        json={"custom_domain": ""},
        headers=auth(first["access_token"]),
    )
    assert cleared.status_code == 200
    assert cleared.json()["custom_domain"] is None
