CREATE TABLE IF NOT EXISTS inbox (
 event_id uuid PRIMARY KEY,organization_id uuid NOT NULL,payload jsonb NOT NULL,received_at timestamptz NOT NULL DEFAULT clock_timestamp());
CREATE INDEX IF NOT EXISTS inbox_org ON inbox(organization_id);
CREATE TABLE IF NOT EXISTS operation_facts (
 id uuid NOT NULL,organization_id uuid NOT NULL,title varchar(120) NOT NULL CHECK(length(trim(title))>=3),
 sector text NOT NULL CHECK(sector IN ('logistics','retail','services')),
 status text NOT NULL CHECK(status IN ('pending','in_progress','completed','cancelled')),
 amount_cents integer NOT NULL CHECK(amount_cents BETWEEN 0 AND 1000000000),revision integer NOT NULL CHECK(revision>0),
 created_at timestamptz NOT NULL,updated_at timestamptz NOT NULL,PRIMARY KEY(organization_id,id));
CREATE INDEX IF NOT EXISTS facts_org_sector_status ON operation_facts(organization_id,sector,status);
