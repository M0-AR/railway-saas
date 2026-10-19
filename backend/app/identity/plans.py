"""Plan catalog definitions. Seeded idempotently at startup and by app.seed.

Entitlement model (verified: Stripe guidance — separate billing from entitlements):
- features: boolean gates checked server-side per request;
- quotas: numeric limits (-1 means unlimited), enforced server-side per request.
Tenant-level `features_override` (JSONB) can override either per tenant.
"""

from typing import Any

PLAN_DEFINITIONS: list[dict[str, Any]] = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "For single-station operators getting online.",
        "price_cents": 0,
        "currency": "USD",
        "interval": "month",
        "sort_order": 0,
        "features": {
            "reports.basic": True,
            "reports.advanced": False,
            "csv.import": False,
            "custom_domain": False,
            "audit.view": False,
            "team.roles": False,
        },
        "quotas": {"max_trains": 10, "max_users": 3, "max_bookings_per_month": 500},
    },
    {
        "code": "growth",
        "name": "Growth",
        "description": "For multi-route operators with a booking desk.",
        "price_cents": 4900,
        "currency": "USD",
        "interval": "month",
        "sort_order": 1,
        "features": {
            "reports.basic": True,
            "reports.advanced": True,
            "csv.import": True,
            "custom_domain": True,
            "audit.view": True,
            "team.roles": True,
        },
        "quotas": {"max_trains": 100, "max_users": 15, "max_bookings_per_month": 10000},
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "Unlimited scale, audit, and white-labeling.",
        "price_cents": 24900,
        "currency": "USD",
        "interval": "month",
        "sort_order": 2,
        "features": {
            "reports.basic": True,
            "reports.advanced": True,
            "csv.import": True,
            "custom_domain": True,
            "audit.view": True,
            "team.roles": True,
        },
        "quotas": {"max_trains": -1, "max_users": -1, "max_bookings_per_month": -1},
    },
]

DEFAULT_PLAN_CODE = "starter"
