"""Seal each summary independently; failed build transactions leave no rows."""
TABLES = ('fresh_mta_planningsummaryreceipt', 'fresh_mta_planningsummarycontribution')
FORWARD = r'''
CREATE FUNCTION mta.guard_planning_summary() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE owner uuid;
BEGIN
 IF TG_OP='TRUNCATE' OR TG_OP='DELETE' THEN
  RAISE EXCEPTION 'Planning summary generations are retained';
 END IF;
 IF TG_TABLE_NAME='fresh_mta_planningsummaryreceipt' THEN
  IF TG_OP='INSERT' AND NEW.status='BUILDING' THEN RETURN NEW; END IF;
  IF TG_OP='UPDATE' AND OLD.status='BUILDING'
     AND current_setting('fresh.planning_summary_build',true)=NEW.id::text
     AND NEW.status='READY' AND NEW.run_id=OLD.run_id
     AND NEW.source_digest=OLD.source_digest AND NEW.generation_digest=OLD.generation_digest
     AND NEW.recipe_digest=OLD.recipe_digest AND NEW.business_date=OLD.business_date THEN RETURN NEW; END IF;
 ELSE
  owner=NEW.receipt_id;
  IF TG_OP='INSERT' AND current_setting('fresh.planning_summary_build',true)=owner::text
     AND EXISTS(SELECT 1 FROM mta.fresh_mta_planningsummaryreceipt WHERE id=owner AND status='BUILDING') THEN RETURN NEW; END IF;
 END IF;
 RAISE EXCEPTION 'Planning summary generation is sealed';
END $$;
'''
for table in TABLES:
    FORWARD += f'''
CREATE TRIGGER planning_summary_row BEFORE INSERT OR UPDATE OR DELETE ON mta.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_planning_summary();
CREATE TRIGGER planning_summary_truncate BEFORE TRUNCATE ON mta.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_planning_summary();
'''
REVERSE = '\n'.join(f'DROP TRIGGER {name} ON mta.{table};' for table in TABLES
                    for name in ('planning_summary_row','planning_summary_truncate'))
REVERSE += '\nDROP FUNCTION mta.guard_planning_summary();'


def verify_guards(connection):
    import re
    from mta.presentation.context import PublicationUnavailable
    with connection.cursor() as c:
        c.execute("""SELECT c.relname,t.tgname,t.tgenabled,t.tgtype,p.proname
          FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
          JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_proc p ON p.oid=t.tgfoid
          WHERE n.nspname='mta' AND c.relname=ANY(%s) AND t.tgname LIKE 'planning_summary_%%'""",[list(TABLES)])
        expected={(table,name,'O',kind,'guard_planning_summary') for table in TABLES
                  for name,kind in (('planning_summary_row',31),('planning_summary_truncate',34))}
        if set(c.fetchall())!=expected:
            raise PublicationUnavailable('planning_summary_guards_changed')
        c.execute("SELECT prosrc,prosecdef FROM pg_proc WHERE oid='mta.guard_planning_summary()'::regprocedure")
        body=re.search(r'AS \$\$(.*?)\$\$;',FORWARD,re.S).group(1)
        if c.fetchone()!=(body,False):
            raise PublicationUnavailable('planning_summary_guard_definition_changed')
