"""Statement-level revision invalidation and installer-only authority metadata.

Frozen ownership catalogue for 0144; future participants require a new migration.
"""
from django.db import migrations

SCHEMAS = ('mta', 'mta_state', 'mta_opening')
METADATA = ('fresh_mta_initializationcertification', 'fresh_mta_masterinputrevision',
            'fresh_mta_ingestionreleasecompatibility')
IMMUTABLE = ('fresh_mta_productioninitialization', 'fresh_mta_mdmsource',
             'fresh_mta_mdmfamilysource', 'fresh_mta_mdmsourceintegration')
MASTER = tuple('fresh_mta_' + n for n in ('mdmskuattributes','mdmskudescription',
    'mdmlocationattributes','mdmlocationdescription','mdmskulocpair','mdmskulocmasterpair',
    'mdmskuloccurrent','mdmskuuse','mdmlocationuse'))
FACT = ('fresh_mta_dailyfeedattempt', 'fresh_mta_mdmdailyinputcapture', 'fresh_mta_mdmdailyinputoccurrence')

SQL = r'''
CREATE FUNCTION mta.ingestion_authority_guard() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog,mta AS $$
DECLARE owner_name text;
BEGIN
 IF TG_OP='TRUNCATE' THEN RAISE EXCEPTION 'Ingestion authority cannot be truncated'; END IF;
 SELECT pg_get_userbyid(relowner) INTO owner_name FROM pg_class WHERE oid=TG_RELID;
 IF current_user<>owner_name AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND rolsuper)
 THEN RAISE EXCEPTION 'Ingestion authority requires its trusted table owner'; END IF;
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Ingestion authority is retained'; END IF;
 IF TG_OP='UPDATE' THEN
  IF TG_TABLE_NAME='fresh_mta_ingestionreleasecompatibility' THEN
   RAISE EXCEPTION 'Ingestion compatibility receipt is immutable';
  ELSIF TG_TABLE_NAME='fresh_mta_masterinputrevision' THEN
   IF NOT (OLD.status='CANDIDATE' AND NEW.status='ACCEPTED'
     AND (to_jsonb(OLD)-'status')=(to_jsonb(NEW)-'status'))
   THEN RAISE EXCEPTION 'Master input revision is immutable'; END IF;
  ELSIF (to_jsonb(OLD)-ARRAY['status','master_epoch','configuration_epoch','fact_epoch','operational_epoch','action_epoch'])
    IS DISTINCT FROM
    (to_jsonb(NEW)-ARRAY['status','master_epoch','configuration_epoch','fact_epoch','operational_epoch','action_epoch'])
  THEN RAISE EXCEPTION 'Initialization certification body is immutable';
  ELSIF NEW.master_epoch<OLD.master_epoch OR NEW.configuration_epoch<OLD.configuration_epoch
    OR NEW.fact_epoch<OLD.fact_epoch OR NEW.operational_epoch<OLD.operational_epoch OR NEW.action_epoch<OLD.action_epoch
  THEN RAISE EXCEPTION 'Ingestion revision cannot regress';
  END IF;
 END IF;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION mta.ingestion_authority_guard() FROM PUBLIC;

CREATE FUNCTION mta.ingestion_watch() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,mta AS $$
DECLARE kind text:=TG_ARGV[0]; static_change boolean:=true;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM mta.fresh_mta_initializationcertification WHERE status='CERTIFIED') THEN RETURN NULL; END IF;
 IF TG_OP='TRUNCATE' THEN RAISE EXCEPTION 'Certified ingestion populations cannot be truncated'; END IF;
 IF TG_OP='DELETE' THEN
  IF NOT EXISTS(SELECT 1 FROM old_rows) THEN RETURN NULL; END IF;
 ELSE
  IF NOT EXISTS(SELECT 1 FROM new_rows) THEN RETURN NULL; END IF;
 END IF;
 IF TG_OP='UPDATE' THEN
  IF NOT EXISTS(SELECT * FROM new_rows EXCEPT ALL SELECT * FROM old_rows) THEN RETURN NULL; END IF;
 END IF;
 IF kind='immutable' THEN RAISE EXCEPTION 'Certified opening and source identity are immutable'; END IF;
 IF kind='mixed' AND TG_OP='UPDATE' THEN
  SELECT EXISTS(SELECT to_jsonb(n)-'Norm' FROM new_rows n
    EXCEPT ALL SELECT to_jsonb(o)-'Norm' FROM old_rows o) INTO static_change;
 END IF;
 IF kind='master' OR kind='mixed' THEN
  UPDATE mta.fresh_mta_initializationcertification SET
    master_epoch=master_epoch+CASE WHEN static_change THEN 1 ELSE 0 END,
    configuration_epoch=configuration_epoch+CASE WHEN static_change THEN 1 ELSE 0 END,
    operational_epoch=operational_epoch+CASE WHEN kind='mixed' THEN 1 ELSE 0 END
    WHERE status='CERTIFIED';
 ELSIF kind='configuration' THEN
  UPDATE mta.fresh_mta_initializationcertification SET configuration_epoch=configuration_epoch+1 WHERE status='CERTIFIED';
 ELSIF kind='fact' THEN
  UPDATE mta.fresh_mta_initializationcertification SET fact_epoch=fact_epoch+1 WHERE status='CERTIFIED';
 ELSIF kind='action' THEN
  UPDATE mta.fresh_mta_initializationcertification SET action_epoch=action_epoch+1 WHERE status='CERTIFIED';
 ELSIF kind='operational' THEN
  UPDATE mta.fresh_mta_initializationcertification SET operational_epoch=operational_epoch+1 WHERE status='CERTIFIED';
 ELSE RAISE EXCEPTION 'Unknown ingestion revision domain'; END IF;
 RETURN NULL;
END $$;
REVOKE ALL ON FUNCTION mta.ingestion_watch() FROM PUBLIC;
'''


def domain(schema, table):
    if schema=='mta_opening' or table in IMMUTABLE: return 'immutable'
    if table in MASTER: return 'mixed' if table in ('fresh_mta_mdmskuloccurrent','fresh_mta_mdmskulocmasterpair') else 'master'
    if table in FACT or schema=='mta_state' and table.startswith('input_'): return 'fact'
    if any(s in table for s in ('configuration','setting')): return 'configuration'
    if any(s in table for s in ('draft','request','task','queue','liveremark','annotation')): return 'action'
    return 'operational'


def install(apps, editor):
    if editor.connection.vendor!='postgresql': raise RuntimeError('Ingestion guards require PostgreSQL')
    q=editor.quote_name
    with editor.connection.cursor() as c:
        c.execute(SQL)
        c.execute("SELECT n.nspname,r.relname FROM pg_class r JOIN pg_namespace n ON n.oid=r.relnamespace "
            "WHERE n.nspname=ANY(%s) AND r.relkind IN ('r','p') ORDER BY 1,2",[list(SCHEMAS)])
        tables=c.fetchall()
        for schema,table in tables:
            target=q(schema)+'.'+q(table)
            if table in METADATA:
                c.execute('CREATE TRIGGER ingestion_authority BEFORE INSERT OR UPDATE OR DELETE ON '+target+
                    ' FOR EACH ROW EXECUTE FUNCTION mta.ingestion_authority_guard()')
                c.execute('CREATE TRIGGER ingestion_authority_truncate BEFORE TRUNCATE ON '+target+
                    ' FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_authority_guard()')
                continue
            kind=domain(schema,table)
            for op,ref in (('INSERT','NEW TABLE AS new_rows'),('UPDATE','OLD TABLE AS old_rows NEW TABLE AS new_rows'),
                           ('DELETE','OLD TABLE AS old_rows'),('TRUNCATE','')):
                c.execute('CREATE TRIGGER ingestion_watch_'+op.lower()+' AFTER '+op+' ON '+target+
                    (' REFERENCING '+ref if ref else '')+
                    ' FOR EACH STATEMENT EXECUTE FUNCTION mta.ingestion_watch(%s)',[kind])


def uninstall(apps,editor):
    q=editor.quote_name
    with editor.connection.cursor() as c:
        c.execute("SELECT n.nspname,r.relname,t.tgname FROM pg_trigger t JOIN pg_class r ON r.oid=t.tgrelid "
            "JOIN pg_namespace n ON n.oid=r.relnamespace WHERE n.nspname=ANY(%s) "
            "AND (t.tgname LIKE 'ingestion_watch_%%' OR t.tgname IN ('ingestion_authority','ingestion_authority_truncate'))",[list(SCHEMAS)])
        for schema,table,trigger in c.fetchall():
            c.execute('DROP TRIGGER '+q(trigger)+' ON '+q(schema)+'.'+q(table))
        c.execute('DROP FUNCTION mta.ingestion_watch(); DROP FUNCTION mta.ingestion_authority_guard()')


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0144_ingestion_ownership_foundation')]
    operations=[migrations.RunPython(install,uninstall)]
