"""initial schema with row-level security

Revision ID: 0001
Revises:
Create Date: 2026-10-18

Creates the full schema and, critically, the multi-tenant isolation layer:
ENABLE + FORCE ROW LEVEL SECURITY with fail-closed policies keyed on the
transaction-local setting app.current_tenant (OWASP Multi-Tenant Security
Cheat Sheet pattern). Grants the request role (railway_app) table access
WITHOUT ownership so RLS is always enforced.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "member",
    "train",
    "train_inventory",
    "booking",
    "booking_passenger",
    "audit_log",
)

TENANT_POLICY = """
    USING (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid)
"""


def upgrade() -> None:
    # ---------------------------------------------------------------- platform
    op.create_table(
        "plan",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("interval", sa.String(16), nullable=False, server_default="month"),
        sa.Column(
            "features", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "quotas", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )

    op.create_table(
        "tenant",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("custom_domain", sa.String(255), unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("plan_code", sa.String(32), nullable=False, server_default="starter"),
        sa.Column(
            "branding", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "features_override",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("default_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("locale", sa.String(16), nullable=False, server_default="en"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("region", sa.String(32), nullable=False, server_default="global"),
        sa.Column("billing_customer_id", sa.String(64)),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["plan_code"], ["plan.code"], name="tenant_plan_code_fkey", ondelete="RESTRICT"
        ),
    )

    # ---------------------------------------------------------------- identity
    op.create_table(
        "member",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE", name="member_tenant_id_fkey"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="agent"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("tenant_id", "email", name="member_tenant_email_key"),
    )
    op.create_index("member_tenant_id_idx", "member", ["tenant_id"])
    op.create_index("member_tenant_role_idx", "member", ["tenant_id", "role"])

    # ------------------------------------------------------------------ trains
    op.create_table(
        "train",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE", name="train_tenant_id_fkey"),
            nullable=False,
        ),
        sa.Column("number", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("train_type", sa.String(24), nullable=False, server_default="express"),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("destination", sa.String(120), nullable=False),
        sa.Column("departure_time", sa.Time()),
        sa.Column("arrival_time", sa.Time()),
        sa.Column(
            "days_of_week",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[1,2,3,4,5,6,7]'::jsonb"),
        ),
        sa.Column(
            "stops", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("total_seats", sa.Integer(), nullable=False),
        sa.Column("fare_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("tenant_id", "number", name="train_tenant_number_key"),
    )
    op.create_index("train_tenant_id_idx", "train", ["tenant_id"])
    op.create_index("train_tenant_name_idx", "train", ["tenant_id", "name"])
    op.create_index("train_tenant_route_idx", "train", ["tenant_id", "source", "destination"])

    op.create_table(
        "train_inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "tenant.id", ondelete="CASCADE", name="train_inventory_tenant_id_fkey"
            ),
            nullable=False,
        ),
        sa.Column(
            "train_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("train.id", ondelete="CASCADE", name="train_inventory_train_id_fkey"),
            nullable=False,
        ),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("seats_booked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "train_id",
            "travel_date",
            name="train_inventory_tenant_train_date_key",
        ),
    )
    op.create_index("train_inventory_tenant_id_idx", "train_inventory", ["tenant_id"])

    # ---------------------------------------------------------------- bookings
    op.create_table(
        "booking",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE", name="booking_tenant_id_fkey"),
            nullable=False,
        ),
        sa.Column("pnr", sa.String(10), nullable=False),
        sa.Column(
            "train_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("train.id", ondelete="RESTRICT", name="booking_train_id_fkey"),
            nullable=False,
        ),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("contact_name", sa.String(120), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("contact_phone", sa.String(40), nullable=False, server_default=""),
        sa.Column("seats", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="confirmed"),
        sa.Column("total_fare_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("refund_status", sa.String(16), nullable=False, server_default="none"),
        sa.Column("channel", sa.String(16), nullable=False, server_default="counter"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("tenant_id", "pnr", name="booking_tenant_pnr_key"),
    )
    op.create_index("booking_tenant_id_idx", "booking", ["tenant_id"])
    op.create_index("booking_tenant_travel_date_idx", "booking", ["tenant_id", "travel_date"])
    op.create_index("booking_tenant_status_idx", "booking", ["tenant_id", "status"])
    op.create_index("booking_tenant_contact_idx", "booking", ["tenant_id", "contact_email"])

    op.create_table(
        "booking_passenger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "tenant.id", ondelete="CASCADE", name="booking_passenger_tenant_id_fkey"
            ),
            nullable=False,
        ),
        sa.Column(
            "booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "booking.id", ondelete="CASCADE", name="booking_passenger_booking_id_fkey"
            ),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("age", sa.Integer()),
        sa.Column("gender", sa.String(16), nullable=False, server_default=""),
        sa.Column("seat_preference", sa.String(24), nullable=False, server_default=""),
        sa.Column("id_document", sa.String(64), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("booking_passenger_tenant_id_idx", "booking_passenger", ["tenant_id"])
    op.create_index(
        "booking_passenger_tenant_booking_idx", "booking_passenger", ["tenant_id", "booking_id"]
    )

    # ------------------------------------------------------------------- audit
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenant.id", ondelete="CASCADE", name="audit_log_tenant_id_fkey"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False, server_default=""),
        sa.Column("entity_id", sa.String(64), nullable=False, server_default=""),
        sa.Column(
            "payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("audit_log_tenant_id_idx", "audit_log", ["tenant_id"])
    op.create_index("audit_log_tenant_created_idx", "audit_log", ["tenant_id", "created_at"])
    op.create_index("audit_log_tenant_action_idx", "audit_log", ["tenant_id", "action"])

    # ------------------------------------------------------- row level security
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} {TENANT_POLICY}"
        )

    # ------------------------------------------------------------------ grants
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'railway_app') THEN
                GRANT USAGE ON SCHEMA public TO railway_app;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO railway_app;
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO railway_app;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    for table in (
        "audit_log",
        "booking_passenger",
        "booking",
        "train_inventory",
        "train",
        "member",
        "tenant",
        "plan",
    ):
        op.drop_table(table)
