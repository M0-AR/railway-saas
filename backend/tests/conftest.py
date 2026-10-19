"""Test harness.

Boots a disposable `railway_test` database (owned by railway_owner, migrated
with the real Alembic chain) and drives the real ASGI app — lifespan included —
against it as `railway_app`, the same un-privileged runtime role production
uses. Every RLS claim in the suite is therefore exercised for real, not mocked.
"""

import asyncio
import os
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_DB = "railway_test"
PG_HOST = os.environ.get("TEST_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("TEST_PG_PORT", "5432"))
OWNER_USER, OWNER_PW = "railway_owner", "railway_owner_pw"
APP_USER, APP_PW = "railway_app", "railway_app_pw"

OWNER_DB_URL = f"postgresql+asyncpg://{OWNER_USER}:{OWNER_PW}@{PG_HOST}:{PG_PORT}/{TEST_DB}"
APP_DB_URL = f"postgresql+asyncpg://{APP_USER}:{APP_PW}@{PG_HOST}:{PG_PORT}/{TEST_DB}"

# Must be in place before app.core.config is imported anywhere.
os.environ.update(
    {
        "DATABASE_URL": APP_DB_URL,
        "MIGRATION_DATABASE_URL": OWNER_DB_URL,
        "SECRET_KEY": "test-secret-key-0123456789abcdef0123456789abcdef",
        "ENVIRONMENT": "local",
        "RATE_LIMIT_PER_MINUTE": "1000000",
        "AUTH_RATE_LIMIT_PER_MINUTE": "1000000",
        "SEED_DEMO": "false",
        "REDIS_URL": "",
        "STRIPE_WEBHOOK_SECRET": "",
    }
)

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from alembic import command as alembic_command  # noqa: E402
from app.main import app  # noqa: E402

API = "/api/v1"


def _recreate_database() -> None:
    async def _run() -> None:
        conn = await asyncpg.connect(
            host=PG_HOST, port=PG_PORT, user=OWNER_USER, password=OWNER_PW, database="postgres"
        )
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
            await conn.execute(f'CREATE DATABASE "{TEST_DB}" OWNER "{OWNER_USER}"')
        finally:
            await conn.close()

    asyncio.run(_run())


def _run_migrations() -> None:
    config = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    alembic_command.upgrade(config, "head")


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    _recreate_database()
    _run_migrations()


@pytest.fixture(scope="session")
async def owner_engine(database):
    engine = create_async_engine(OWNER_DB_URL)
    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_db(owner_engine, database):
    async with owner_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE tenant CASCADE"))
    yield


@pytest.fixture(scope="session")
async def client(database):
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as http:
            yield http


# ---------------------------------------------------------------- helpers


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register_tenant(
    client: AsyncClient,
    *,
    slug: str = "acme",
    email: str = "owner@acme.example",
    password: str = "Passw0rd!234",
    org_name: str = "Acme Rail",
    full_name: str = "Ada Owner",
) -> dict[str, Any]:
    response = await client.post(
        f"{API}/auth/register",
        json={
            "org_name": org_name,
            "slug": slug,
            "full_name": full_name,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(
    client: AsyncClient,
    *,
    slug: str,
    email: str,
    password: str = "Passw0rd!234",
) -> dict[str, Any]:
    response = await client.post(
        f"{API}/auth/login",
        json={"email": email, "password": password, "tenant_slug": slug},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def create_train(client: AsyncClient, token: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "number": "TX-100",
        "name": "Test Express",
        "train_type": "express",
        "source": "Central",
        "destination": "North",
        "total_seats": 50,
        "fare_cents": 1000,
        "days_of_week": [1, 2, 3, 4, 5, 6, 7],
    }
    payload.update(overrides)
    response = await client.post(f"{API}/trains", json=payload, headers=auth(token))
    assert response.status_code == 201, response.text
    return response.json()


async def set_tenant_plan(owner_engine, slug: str, plan_code: str) -> None:
    """Test setup only: move a workspace to another plan without billing."""
    async with owner_engine.begin() as conn:
        await conn.execute(
            text("UPDATE tenant SET plan_code = :plan WHERE slug = :slug"),
            {"plan": plan_code, "slug": slug},
        )
