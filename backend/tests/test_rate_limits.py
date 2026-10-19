"""Rate limiting: noisy-neighbor protection with clean 429 envelopes."""

import pytest

from app.core.config import settings
from app.core.rate_limit import InMemoryLimiter, limiter
from tests.conftest import API, auth, register_tenant


@pytest.fixture(autouse=True)
def clean_limiter():
    limiter._memory._hits.clear()
    yield
    limiter._memory._hits.clear()


def test_in_memory_window_slides(monkeypatch):
    clock = {"now": 100.0}
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: clock["now"])
    bucket = InMemoryLimiter()

    assert bucket.hit("tenant", 2) is None
    assert bucket.hit("tenant", 2) is None
    assert bucket.hit("tenant", 2) == pytest.approx(60.0)

    clock["now"] += 61
    assert bucket.hit("tenant", 2) is None


async def test_public_requests_are_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 2)

    for _ in range(2):
        assert (await client.get(f"{API}/public/plans")).status_code == 200

    limited = await client.get(f"{API}/public/plans")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) >= 1


async def test_authenticated_requests_are_limited_per_tenant(client, monkeypatch):
    registered = await register_tenant(
        client, slug="rate-tenant", email="owner@rate-tenant.example"
    )
    headers = auth(registered["access_token"])
    monkeypatch.setattr(settings, "rate_limit_per_minute", 2)

    for _ in range(2):
        response = await client.get(f"{API}/me", headers=headers)
        assert response.status_code == 200
        assert response.headers["x-ratelimit-limit"] == "2"

    limited = await client.get(f"{API}/me", headers=headers)
    assert limited.status_code == 429
    assert 1 <= int(limited.headers["retry-after"]) <= 60

    other = await register_tenant(
        client, slug="rate-other", email="owner@rate-other.example"
    )
    fresh = await client.get(f"{API}/me", headers=auth(other["access_token"]))
    assert fresh.status_code == 200


async def test_invalid_bearer_falls_back_to_ip_budget(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1)
    bogus = {"Authorization": "Bearer not-a-token"}

    assert (await client.get(f"{API}/me", headers=bogus)).status_code == 401
    limited = await client.get(f"{API}/me", headers=bogus)
    assert limited.status_code == 429


async def test_health_checks_are_exempt(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 1)
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 1)

    for _ in range(3):
        assert (await client.get("/healthz")).status_code == 200
        assert (await client.get("/readyz")).status_code == 200


async def test_zero_limit_disables_limiting():
    assert await limiter.hit("disabled", 0) is None
