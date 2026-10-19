"""API contract: uniform error envelope and the blanket auth wall.

The authentication test walks the real router table, so any new private GET
endpoint that forgets an auth dependency fails here immediately.
"""

from app.core.config import settings
from app.main import app
from tests.conftest import API

UUID_SENTINEL = "00000000-0000-0000-0000-000000000000"
ANONYMOUS_PREFIXES = (f"{API}/auth/", f"{API}/public/")


def _private_get_paths() -> list[str]:
    paths: list[str] = []
    for path, operations in app.openapi()["paths"].items():
        if "get" not in operations or not path.startswith(API):
            continue
        if path.startswith(ANONYMOUS_PREFIXES):
            continue
        paths.append(path)
    return paths


async def test_every_private_get_route_requires_authentication(client):
    paths = _private_get_paths()
    assert len(paths) >= 10, "route inventory unexpectedly small"

    for path in paths:
        concrete = "/".join(
            UUID_SENTINEL if part.startswith("{") and part.endswith("}") else part
            for part in path.split("/")
        )
        response = await client.get(concrete)
        assert response.status_code == 401, f"{concrete} answered {response.status_code}"
        assert response.json()["error"]["code"] == "unauthorized", concrete


async def test_validation_errors_use_the_standard_envelope(client):
    response = await client.post(f"{API}/auth/register", json={})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert isinstance(error["details"], list) and error["details"]
    assert {"loc", "msg", "type"} <= set(error["details"][0])


async def test_unknown_resources_use_the_not_found_envelope(client):
    response = await client.get(f"{API}/public/tenant", params={"slug": "ghost-workspace"})
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["message"]


async def test_system_endpoints_and_openapi(client):
    health = await client.get("/healthz")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = await client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"

    if settings.docs_enabled:
        schema = await client.get("/openapi.json")
        assert schema.status_code == 200
        documented = set(schema.json()["paths"])
        for path in (f"{API}/trains", f"{API}/bookings", f"{API}/reports/overview"):
            assert path in documented, f"{path} missing from OpenAPI schema"
