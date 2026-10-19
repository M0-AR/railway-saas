"""Team management: onboarding with temporary passwords, resets, conflicts,
deactivation, cross-tenant isolation, and listing filters.

Role permission matrix lives in test_rbac.py; this module covers the flows.
"""

from tests.conftest import API, auth, login, register_tenant, set_tenant_plan

DEFAULT_PW = "Passw0rd!234"


async def _create(client, token: str, email: str, role: str = "agent", **extra):
    return await client.post(
        f"{API}/team/users",
        json={
            "email": email,
            "full_name": f"{role.title()} Person",
            "role": role,
            **extra,
        },
        headers=auth(token),
    )


async def test_onboarding_temp_password_and_reset(client):
    registered = await register_tenant(client, slug="team-temp", email="owner@team-temp.example")
    token = registered["access_token"]

    created = await _create(client, token, "newbie@team-temp.example")
    assert created.status_code == 201, created.text
    body = created.json()
    temp_password = body["temporary_password"]
    assert temp_password
    member_id = body["member"]["id"]

    session = await client.post(
        f"{API}/auth/login",
        json={
            "email": "newbie@team-temp.example",
            "password": temp_password,
            "tenant_slug": "team-temp",
        },
    )
    assert session.status_code == 200, session.text

    reset = await client.patch(
        f"{API}/team/users/{member_id}",
        json={"password": "FreshPassw0rd!1"},
        headers=auth(token),
    )
    assert reset.status_code == 200

    stale = await client.post(
        f"{API}/auth/login",
        json={
            "email": "newbie@team-temp.example",
            "password": temp_password,
            "tenant_slug": "team-temp",
        },
    )
    assert stale.status_code == 401

    fresh = await client.post(
        f"{API}/auth/login",
        json={
            "email": "newbie@team-temp.example",
            "password": "FreshPassw0rd!1",
            "tenant_slug": "team-temp",
        },
    )
    assert fresh.status_code == 200


async def test_duplicate_email_reports_conflict(client):
    registered = await register_tenant(client, slug="team-dup", email="owner@team-dup.example")
    token = registered["access_token"]

    assert (await _create(client, token, "dup@team-dup.example")).status_code == 201
    clash = await _create(client, token, "dup@team-dup.example")
    assert clash.status_code == 409
    assert clash.json()["error"]["code"] == "conflict"


async def test_deactivated_member_cannot_sign_in_again(client):
    registered = await register_tenant(client, slug="team-gone", email="owner@team-gone.example")
    token = registered["access_token"]
    created = await _create(client, token, "gone@team-gone.example", password=DEFAULT_PW)
    assert created.status_code == 201

    deactivated = await client.patch(
        f"{API}/team/users/{created.json()['member']['id']}",
        json={"is_active": False},
        headers=auth(token),
    )
    assert deactivated.status_code == 200

    refused = await client.post(
        f"{API}/auth/login",
        json={
            "email": "gone@team-gone.example",
            "password": DEFAULT_PW,
            "tenant_slug": "team-gone",
        },
    )
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "forbidden"


async def test_cross_tenant_member_ids_are_invisible(client):
    first = await register_tenant(client, slug="team-a", email="owner@team-a.example")
    second = await register_tenant(client, slug="team-b", email="owner@team-b.example")

    probe = await client.patch(
        f"{API}/team/users/{second['user']['id']}",
        json={"full_name": "Hijacked Name"},
        headers=auth(first["access_token"]),
    )
    assert probe.status_code == 404
    assert probe.json()["error"]["code"] == "not_found"

    still_ok = await client.get(f"{API}/me", headers=auth(second["access_token"]))
    assert still_ok.status_code == 200
    assert still_ok.json()["user"]["full_name"] == "Ada Owner"


async def test_team_listing_filters_and_pagination(client, owner_engine):
    registered = await register_tenant(client, slug="team-list", email="owner@team-list.example")
    await set_tenant_plan(owner_engine, "team-list", "growth")
    token = registered["access_token"]

    for name in ("alice", "bob", "carol"):
        created = await client.post(
            f"{API}/team/users",
            json={
                "email": f"{name}@team-list.example",
                "full_name": f"{name.title()} Member",
                "role": "agent",
                "password": DEFAULT_PW,
            },
            headers=auth(token),
        )
        assert created.status_code == 201, created.text

    everyone = await client.get(f"{API}/team/users", headers=auth(token))
    assert everyone.json()["total"] == 4

    filtered = await client.get(
        f"{API}/team/users", params={"q": "ALI"}, headers=auth(token)
    )
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["email"] == "alice@team-list.example"

    page_one = await client.get(
        f"{API}/team/users", params={"page_size": 2, "page": 1}, headers=auth(token)
    )
    assert len(page_one.json()["items"]) == 2
    assert page_one.json()["total"] == 4
    page_two = await client.get(
        f"{API}/team/users", params={"page_size": 2, "page": 2}, headers=auth(token)
    )
    assert len(page_two.json()["items"]) == 2
    assert {m["email"] for m in page_one.json()["items"]} & {
        m["email"] for m in page_two.json()["items"]
    } == set()


async def test_only_owner_can_manage_admins(client, owner_engine):
    registered = await register_tenant(client, slug="team-adm", email="owner@team-adm.example")
    await set_tenant_plan(owner_engine, "team-adm", "growth")
    token = registered["access_token"]

    admin = await _create(
        client, token, "admin@team-adm.example", role="admin", password=DEFAULT_PW
    )
    assert admin.status_code == 201, admin.text

    admin_session = await login(client, slug="team-adm", email="admin@team-adm.example")

    escalated = await _create(client, token, "peer-admin@team-adm.example", role="admin")
    assert escalated.status_code == 201  # owner may appoint peers

    admin_to_admin = await _create(
        client,
        admin_session["access_token"],
        "second-admin@team-adm.example",
        role="admin",
    )
    assert admin_to_admin.status_code == 403

    owner_target = await client.patch(
        f"{API}/team/users/{registered['user']['id']}",
        json={"full_name": "Renamed Owner"},
        headers=auth(admin_session["access_token"]),
    )
    assert owner_target.status_code == 403
