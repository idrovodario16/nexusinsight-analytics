from sqlalchemy import text


def verify_database_isolation(engine):
    with engine.connect() as conn:
        role = conn.execute(text('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user')).mappings().one()
        tables = conn.execute(text("""SELECT c.relname,c.relrowsecurity,c.relforcerowsecurity,
            pg_has_role(current_user,c.relowner,'MEMBER') AS can_own
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname IN ('inbox','operation_facts')""")).mappings().all()
        if role['rolsuper'] or role['rolbypassrls'] or len(tables) != 2 or any(
                not r['relrowsecurity'] or not r['relforcerowsecurity'] or r['can_own'] for r in tables):
            raise RuntimeError('Database isolation requires migrated tables and a non-owner role without SUPERUSER/BYPASSRLS')
