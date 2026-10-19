#!/bin/sh
set -eu

# Runs once on first initdb of the postgres container (docker-entrypoint-initdb.d).
# Two roles per verified RLS practice:
#   railway_owner: schema owner, runs migrations (only this role may own tables)
#   railway_app:   request path. NOSUPERUSER NOBYPASSRLS so FORCE RLS always applies.
# The application refuses to boot if its runtime role can bypass RLS.
#
# Passwords come from RAILWAY_OWNER_PASSWORD / RAILWAY_APP_PASSWORD (see .env.example);
# keep them URL-safe and keep them in sync with DATABASE_URL / MIGRATION_DATABASE_URL.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE railway_owner LOGIN PASSWORD '${RAILWAY_OWNER_PASSWORD:-railway_owner_pw}' CREATEDB;
CREATE ROLE railway_app LOGIN PASSWORD '${RAILWAY_APP_PASSWORD:-railway_app_pw}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;

GRANT CREATE, USAGE ON SCHEMA public TO railway_owner;
GRANT USAGE ON SCHEMA public TO railway_app;

ALTER DATABASE "$POSTGRES_DB" OWNER TO railway_owner;
EOSQL
