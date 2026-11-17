DO $$
DECLARE table_name text;
BEGIN
 FOREACH table_name IN ARRAY ARRAY['inbox','operation_facts']
 LOOP
  EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
  EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
  EXECUTE format('CREATE POLICY tenant_isolation ON %I USING
   (organization_id = NULLIF(current_setting(''nexus.organization_id'', true), '''')::uuid)
   WITH CHECK (organization_id = NULLIF(current_setting(''nexus.organization_id'', true), '''')::uuid)', table_name);
 END LOOP;
END $$;
