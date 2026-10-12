"""Immutable, explicitly built report-only aggregates in the existing database."""
TABLES = ('fresh_mta_guidedhistoryaggregate', 'fresh_mta_reportscopemember',
          'fresh_mta_reportaggregatereceipt')
FORWARD = r'''
CREATE FUNCTION mta.guard_report_aggregate_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF current_setting('fresh.report_aggregate_build',true) IS DISTINCT FROM NEW.run_id::text THEN
  RAISE EXCEPTION 'Report aggregate insertion requires the offline builder';
 END IF;
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_reportaggregatereceipt WHERE run_id=NEW.run_id) THEN
  RAISE EXCEPTION 'Report aggregate generation is sealed';
 END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION mta.deny_report_aggregate_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Report aggregate generation is immutable'; END $$;
'''
for table in TABLES:
    FORWARD += f'''
CREATE TRIGGER report_aggregate_insert BEFORE INSERT ON mta.{table}
 FOR EACH ROW EXECUTE FUNCTION mta.guard_report_aggregate_insert();
CREATE TRIGGER report_aggregate_mutation BEFORE UPDATE OR DELETE ON mta.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_report_aggregate_mutation();
CREATE TRIGGER report_aggregate_truncate BEFORE TRUNCATE ON mta.{table}
 FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_report_aggregate_mutation();
'''
REVERSE = '\n'.join(f'DROP TRIGGER {name} ON mta.{table};' for table in TABLES
                    for name in ('report_aggregate_insert','report_aggregate_mutation','report_aggregate_truncate'))
REVERSE += '\nDROP FUNCTION mta.guard_report_aggregate_insert(); DROP FUNCTION mta.deny_report_aggregate_mutation();'


def verify_guards(connection):
    import re
    from mta.presentation.context import PublicationUnavailable
    with connection.cursor() as cursor:
        cursor.execute("""SELECT c.relname,t.tgname,t.tgenabled,t.tgtype,t.tgqual::text,t.tgnargs,p.proname,nf.nspname
          FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
          JOIN pg_namespace n ON n.oid=c.relnamespace
          JOIN pg_proc p ON p.oid=t.tgfoid JOIN pg_namespace nf ON nf.oid=p.pronamespace
          WHERE n.nspname='mta' AND c.relname=ANY(%s)
          AND t.tgname LIKE 'report_aggregate_%%'""", [list(TABLES)])
        rows = cursor.fetchall()
        expected = {(table,name,'O',flags,None,0,function,'mta') for table in TABLES
            for name,flags,function in (
                ('report_aggregate_insert',7,'guard_report_aggregate_insert'),
                ('report_aggregate_mutation',26,'deny_report_aggregate_mutation'),
                ('report_aggregate_truncate',34,'deny_report_aggregate_mutation'))}
        if set(rows) != expected:
            raise PublicationUnavailable('Report_aggregate_guards_changed')
        functions = dict(re.findall(r'CREATE FUNCTION mta\.(\w+)\(\).*?AS \$\$(.*?)\$\$;',FORWARD,flags=re.S))
        cursor.execute("""SELECT p.proname,p.prosrc,p.prosecdef,l.lanname FROM pg_proc p
            JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang
            WHERE n.nspname='mta' AND p.proname=ANY(%s) AND p.pronargs=0""",[list(functions)])
        if {name:(body,security,language) for name,body,security,language in cursor.fetchall()} != {
                name:(body,False,'plpgsql') for name,body in functions.items()}:
            raise PublicationUnavailable('Report_aggregate_guard_definition_changed')
