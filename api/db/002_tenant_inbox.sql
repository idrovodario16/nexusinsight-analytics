-- Event identifiers are unique within a producer organization, not globally.
ALTER TABLE inbox DROP CONSTRAINT inbox_pkey;
ALTER TABLE inbox ADD PRIMARY KEY (organization_id, event_id);
