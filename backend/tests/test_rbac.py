from datetime import date, timedelta

from tests.conftest import API, auth, create_train, register_tenant, set_tenant_plan

DEFAULT_PW = "Passw0rd!234"


def _tomorrow() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


async def _seed_team(client, owner_engine):
    owner = await register_tenant(client)
    token = owner["access_token"]
    await set_tenant_plan(owner_engine, "acme", "growth")

    members = {}
    for role in ("manager", "agent", "viewer", "admin"):
        response = await client.post(
            f"{API}/team/users",
            json={
                "email": f"{role}@acme.example",
                "full_name": f"Acme {role.title()}",
                "role": role,
                "password": DEFAULT_PW,
            },
            headers=auth(token),
        )
        assert response.status_code == 201, response.text
        members[role] = response.json()["member"]

    train = await create_train(client, token, number="RB-1", name="RBAC Express")
    return owner, members, train


async def _token_for(client, role):
    session = await client.post(
        f"{API}/auth/login",
        json={"email": f"{role}@acme.example", "password": DEFAULT_PW, "tenant_slug": "acme"},
    )
    assert session.status_code == 200, session.text
    return session.json()["access_token"]


async def test_staff_roles_can_book_but_not_manage_catalog(client, owner_engine):
    _, _, train = await _seed_team(client, owner_engine)
    agent_token = await _token_for(client, "agent")
    viewer_token = await _token_for(client, "viewer")

    agent_booking = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": _tomorrow(),
            "seats": 1,
            "contact_name": "Agent Sale",
        },
        headers=auth(agent_token),
    )
    assert agent_booking.status_code == 201, agent_booking.text

    agent_create_train = await client.post(
        f"{API}/trains",
        json={
            "number": "AG-1",
            "name": "Agent Attempt",
            "source": "Alpha",
            "destination": "Beta",
            "total_seats": 10,
            "fare_cents": 100,
        },
        headers=auth(agent_token),
    )
    assert agent_create_train.status_code == 403

    viewer_list = await client.get(f"{API}/trains", headers=auth(viewer_token))
    assert viewer_list.status_code == 200

    viewer_booking = await client.post(
        f"{API}/bookings",
        json={
            "train_id": train["id"],
            "travel_date": _tomorrow(),
            "seats": 1,
            "contact_name": "Viewer Attempt",
        },
        headers=auth(viewer_token),
    )
    assert viewer_booking.status_code == 403


async def test_team_management_is_restricted(client, owner_engine):
    _, _, _ = await _seed_team(client, owner_engine)
    agent_token = await _token_for(client, "agent")

    agent_list = await client.get(f"{API}/team/users", headers=auth(agent_token))
    assert agent_list.status_code == 403


async def test_admins_cannot_manage_owners_or_admins(client, owner_engine):
    owner, members, _ = await _seed_team(client, owner_engine)
    admin_token = await _token_for(client, "admin")

    demote_owner = await client.patch(
        f"{API}/team/users/{owner['user']['id']}",
        json={"role": "viewer"},
        headers=auth(admin_token),
    )
    assert demote_owner.status_code == 403

    promote_to_admin = await client.post(
        f"{API}/team/users",
        json={
            "email": "admin2@acme.example",
            "full_name": "Second Admin",
            "role": "admin",
            "password": DEFAULT_PW,
        },
        headers=auth(admin_token),
    )
    assert promote_to_admin.status_code == 403

    manager_ok = await client.post(
        f"{API}/team/users",
        json={
            "email": "manager2@acme.example",
            "full_name": "Second Manager",
            "role": "manager",
            "password": DEFAULT_PW,
        },
        headers=auth(admin_token),
    )
    assert manager_ok.status_code == 201

    owner_can_demote_admin = await client.patch(
        f"{API}/team/users/{members['admin']['id']}",
        json={"role": "manager"},
        headers=auth(owner["access_token"]),
    )
    assert owner_can_demote_admin.status_code == 200
    assert owner_can_demote_admin.json()["role"] == "manager"


async def test_last_owner_cannot_be_removed(client):
    owner = await register_tenant(client)

    self_demote = await client.patch(
        f"{API}/team/users/{owner['user']['id']}",
        json={"role": "admin"},
        headers=auth(owner["access_token"]),
    )
    assert self_demote.status_code == 403

    self_deactivate = await client.patch(
        f"{API}/team/users/{owner['user']['id']}",
        json={"is_active": False},
        headers=auth(owner["access_token"]),
    )
    assert self_deactivate.status_code == 403


async def test_deactivated_member_cannot_use_their_token(client, owner_engine):
    await _seed_team(client, owner_engine)
    owner_session = await register_tenant(
        client, slug="frozen", email="frozen-owner@example.com", org_name="Frozen Rail"
    )
    frozen_token = owner_session["access_token"]

    created = await client.post(
        f"{API}/team/users",
        json={
            "email": "soon-gone@frozen.example",
            "full_name": "Soon Gone",
            "role": "agent",
            "password": DEFAULT_PW,
        },
        headers=auth(frozen_token),
    )
    assert created.status_code == 201

    gone_session = await client.post(
        f"{API}/auth/login",
        json={"email": "soon-gone@frozen.example", "password": DEFAULT_PW, "tenant_slug": "frozen"},
    )
    assert gone_session.status_code == 200
    gone_token = gone_session.json()["access_token"]

    assert (await client.get(f"{API}/me", headers=auth(gone_token))).status_code == 200

    deactivated = await client.patch(
        f"{API}/team/users/{created.json()['member']['id']}",
        json={"is_active": False},
        headers=auth(frozen_token),
    )
    assert deactivated.status_code == 200

    assert (await client.get(f"{API}/me", headers=auth(gone_token))).status_code == 403
