-- Postgres init script: runs once on first volume creation.
-- This is NOT the Alembic schema. It only enables extensions and creates
-- supporting roles. Alembic migrations create the actual tables.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Read-only role for analytics / admin queries
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kyros_readonly') THEN
    CREATE ROLE kyros_readonly NOLOGIN;
  END IF;
END
$$;

GRANT CONNECT ON DATABASE kyros TO kyros_readonly;
GRANT USAGE ON SCHEMA public TO kyros_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO kyros_readonly;
