"""Billing webhook: signature verification, idempotency, and the entitlement
switch (billing is the provider's job; entitlements are ours)."""

import hashlib
import hmac
import json
import time

from app.core.config import settings
from tests.conftest import API, auth, register_tenant

SECRET = "whsec_test_0123456789"


def _sign(body: bytes, secret: str = SECRET, timestamp: int | None = None) -> str:
    ts = str(timestamp if timestamp is not None else int(time.time()))
    digest = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _event(event_id: str, event_type: str, *, tenant_slug: str, plan_code: str = "growth") -> bytes:
    return json.dumps(
        {
            "id": event_id,
            "type": event_type,
            "data": {
                "object": {
                    "customer": "cus_test_123",
                    "metadata": {"tenant_slug": tenant_slug, "plan_code": plan_code},
                }
            },
        }
    ).encode()


async def _post_webhook(client, body: bytes, signature: str):
    return await client.post(
        f"{API}/billing/webhook/stripe",
        content=body,
        headers={"stripe-signature": signature, "content-type": "application/json"},
    )


async def test_webhook_requires_configuration(client):
    registered = await register_tenant(client)
    body = _event("evt_unconfigured", "customer.subscription.updated", tenant_slug="acme")
    response = await _post_webhook(client, body, _sign(body))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_configured"
    assert registered  # tenant exists; failure is purely deployment config


async def test_webhook_rejects_bad_signatures(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    await register_tenant(client)
    body = _event("evt_bad_sig", "customer.subscription.updated", tenant_slug="acme")

    assert (await _post_webhook(client, body, "garbage")).status_code == 401
    assert (await _post_webhook(client, body, _sign(body, secret="whsec_wrong"))).status_code == 401
    stale = _sign(body, timestamp=int(time.time()) - 3600)
    assert (await _post_webhook(client, body, stale)).status_code == 401


async def test_webhook_upgrades_plan_and_is_idempotent(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    registered = await register_tenant(client)
    token = registered["access_token"]

    before = await client.get(f"{API}/me", headers=auth(token))
    assert before.json()["entitlements"]["plan_code"] == "starter"

    body = _event("evt_upgrade_1", "customer.subscription.updated", tenant_slug="acme")
    first = await _post_webhook(client, body, _sign(body))
    assert first.status_code == 200, first.text
    assert first.json()["plan_code"] == "growth"

    after = await client.get(f"{API}/me", headers=auth(token))
    entitlements = after.json()["entitlements"]
    assert entitlements["plan_code"] == "growth"
    assert entitlements["features"]["csv.import"] is True
    assert entitlements["quotas"]["max_trains"] == 100

    unlocked = await client.patch(
        f"{API}/settings",
        json={"custom_domain": "rail.acme.example"},
        headers=auth(token),
    )
    assert unlocked.status_code == 200
    assert unlocked.json()["custom_domain"] == "rail.acme.example"

    replay = await _post_webhook(client, body, _sign(body))
    assert replay.status_code == 200
    assert replay.json().get("duplicate") is True


async def test_webhook_downgrade_and_ignored_events(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    registered = await register_tenant(client)
    token = registered["access_token"]

    upgrade = _event("evt_up_2", "customer.subscription.created", tenant_slug="acme")
    assert (await _post_webhook(client, upgrade, _sign(upgrade))).status_code == 200

    unrelated = _event("evt_other", "invoice.paid", tenant_slug="acme")
    ignored = await _post_webhook(client, unrelated, _sign(unrelated))
    assert ignored.status_code == 200
    assert ignored.json().get("ignored") is True

    deleted = _event("evt_down_1", "customer.subscription.deleted", tenant_slug="acme")
    downgraded = await _post_webhook(client, deleted, _sign(deleted))
    assert downgraded.status_code == 200
    assert downgraded.json()["plan_code"] == "starter"

    me = await client.get(f"{API}/me", headers=auth(token))
    assert me.json()["entitlements"]["plan_code"] == "starter"


async def test_webhook_for_unknown_tenant_is_ignored(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    body = _event("evt_ghost", "customer.subscription.updated", tenant_slug="ghost")
    response = await _post_webhook(client, body, _sign(body))
    assert response.status_code == 200
    assert response.json().get("ignored") is True


async def test_subscription_endpoint_reports_plan(client):
    registered = await register_tenant(client)
    response = await client.get(
        f"{API}/billing/subscription", headers=auth(registered["access_token"])
    )
    assert response.status_code == 200
    body = response.json()
    assert body["plan_code"] == "starter"
    assert body["plan_name"] == "Starter"
    assert body["quotas"]["max_users"] == 3


async def test_webhook_unknown_provider_is_404(client):
    await register_tenant(client)
    body = _event("evt_provider", "customer.subscription.updated", tenant_slug="acme")
    response = await client.post(
        f"{API}/billing/webhook/paypal",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_webhook_invalid_json_is_400(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)
    await register_tenant(client)
    for payload in (b"not-json", b"[1, 2, 3]"):
        response = await _post_webhook(client, payload, _sign(payload))
        assert response.status_code == 400, payload
        assert response.json()["error"]["code"] == "bad_request"
