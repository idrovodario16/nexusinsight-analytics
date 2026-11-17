-- Run once as a database administrator after migrations. No login/password is created.
DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nexus_insight_runtime') THEN
  CREATE ROLE nexus_insight_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
END $$;
GRANT USAGE ON SCHEMA public TO nexus_insight_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON inbox, operation_facts TO nexus_insight_runtime;
