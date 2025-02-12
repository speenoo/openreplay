-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS events_common;
CREATE SCHEMA IF NOT EXISTS events;
CREATE SCHEMA IF NOT EXISTS events_ios;
CREATE SCHEMA IF NOT EXISTS or_cache;
CREATE SCHEMA IF NOT EXISTS spots;

-- Version function
CREATE OR REPLACE FUNCTION openreplay_version()
    RETURNS text AS
$$
SELECT 'v1.21.0'
$$ LANGUAGE sql IMMUTABLE;

-- Import base schema
\ir ../scripts/schema/db/init_dbs/postgresql/init_schema.sql

-- Grant necessary permissions to service role
GRANT USAGE ON SCHEMA public TO service_role;
GRANT USAGE ON SCHEMA events_common TO service_role;
GRANT USAGE ON SCHEMA events TO service_role;
GRANT USAGE ON SCHEMA events_ios TO service_role;
GRANT USAGE ON SCHEMA or_cache TO service_role;
GRANT USAGE ON SCHEMA spots TO service_role;

-- Grant table permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA events_common TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA events TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA events_ios TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA or_cache TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA spots TO service_role;

-- Grant sequence permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA events_common TO service_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA events TO service_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA events_ios TO service_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA or_cache TO service_role;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA spots TO service_role; 