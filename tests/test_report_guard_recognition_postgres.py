"""Actual installed guard through all three existing recognition consumers."""
import json,os,unittest
from copy import deepcopy
from importlib import import_module
from pathlib import Path
from django.db import connection,transaction
from psycopg import sql
from mta.runtime import ingestion_admission as admission,ingestion_ownership as ownership
from mta.mdm import owned_namespace as namespace

migration=import_module('mta.runtime.migrations.0168_report_guard_owner_sets')


@unittest.skipUnless(os.environ.get('VF_REPORT_GUARD_PROOF')=='1','Explicit owned resource required')
class ReportGuardRecognitionPostgresTests(unittest.TestCase):
    def test_all_real_consumers_and_denials(self):
        self.assertEqual(connection.settings_dict['NAME'],'vf_btr_terminal_admission_20261022')
        with connection.cursor() as c:
            c.execute("SELECT oid,shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(c.fetchone(),(1598463,'owned terminal SMALL takeover thread01a16058 20261022; not working/serving'))
            c.execute('SELECT authority_roles FROM mta.fresh_mta_initializationcertification')
            roles=admission._json(c.fetchone()[0])
            registration=namespace._registered_identity(c)
            baseline=namespace._application_catalogue(c)
            candidate=next(f for f in baseline['functions'] if f['name']=='mta.ingestion_watch()')
            self.assertEqual(candidate['body'],migration.NEW_INGESTION)
            c.execute("SELECT tgname FROM pg_trigger WHERE tgrelid='mta.fresh_mta_btrjoinreference'::regclass AND NOT tgisinternal ORDER BY tgname")
            rows=c.fetchall()
            self.assertTrue(any(r[0]=='ingestion_watch_insert' for r in rows))
            def consumers():
                ownership.require_guard_coverage(c)
                guard_digest=admission.security_digest(c,roles)
                self.assertEqual(ownership.business_trigger_rows(c,rows),[r for r in rows if not r[0].startswith('ingestion_watch_')])
                current=namespace._application_catalogue(c)
                result=namespace._check_application_grants(current,registration,logistics=True,production=True)
                return dict(guard_digest=guard_digest,application=result)
            candidate_result=consumers()
            with transaction.atomic():
                c.execute(migration.REVERSE)
                old_result=consumers()
                transaction.set_rollback(True)
            self.assertEqual(namespace._application_catalogue(c),baseline)
            negatives=[]
            def deny(kind,ddl,expected):
                with transaction.atomic():
                    c.execute(ddl)
                    for name in expected:
                        with self.assertRaises(ValueError,msg=kind+':'+name):
                            if name=='security_digest':admission.security_digest(c,roles)
                            elif name=='business_trigger_rows':ownership.business_trigger_rows(c,rows)
                            elif name=='guard_coverage':ownership.require_guard_coverage(c)
                            else:namespace._check_application_grants(namespace._application_catalogue(c),registration,logistics=True,production=True)
                    negatives.append(dict(case=kind,denied=expected))
                    transaction.set_rollback(True)
                self.assertEqual(namespace._application_catalogue(c),baseline)
            all_three=['security_digest','business_trigger_rows','application_authority']
            altered=migration.NEW_INGESTION+'\n-- unrecognized body\n'
            deny('body',sql.SQL('CREATE OR REPLACE FUNCTION mta.ingestion_watch() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,mta AS {}').format(sql.Literal(altered)),all_three)
            deny('search_path','ALTER FUNCTION mta.ingestion_watch() SET search_path=public,mta',all_three)
            # Ordinary functions remain allowed in the generic application
            # profile; the ingestion-specific consumers require the definer.
            deny('definer','ALTER FUNCTION mta.ingestion_watch() SECURITY INVOKER',['security_digest','business_trigger_rows'])
            deny('owner','ALTER FUNCTION mta.ingestion_watch() OWNER TO postgres',['security_digest','application_authority'])
            deny('public_execute','GRANT EXECUTE ON FUNCTION mta.ingestion_watch() TO PUBLIC',['application_authority'])
            deny('disabled_watch','ALTER TABLE mta.fresh_mta_btrjoinreference DISABLE TRIGGER ingestion_watch_insert',['security_digest','business_trigger_rows','guard_coverage'])
            # Name/return mutation cannot safely be installed with dependent
            # triggers. Test the exact predicate on the real metadata record.
            for field,value in (('name','mta.foreign_watch()'),('returns','text')):
                self.assertFalse(ownership.is_revision_guard({**candidate,field:value}))
            self.assertEqual(consumers(),candidate_result)
            result=dict(status='PASS_ALL_THREE_REAL_CONSUMERS',database=connection.settings_dict['NAME'],
                actual_candidate_metadata={k:v for k,v in candidate.items() if k!='body'},
                body_exact_frozen_0168=True,old_and_new_consumer_results=[old_result,candidate_result],
                rollback_only_negative_cases=negatives,
                predicate_only_negatives=['name','returns'],
                limits=['No full schema_transition or fresh-process working admission claimed; these remain mandatory in replacement operation',
                    'Generic application authority permits ordinary non-definer functions; ingestion-specific consumers deny definer removal'],
                all_catalogue_acl_identity_restored=True,no_business_dml=True)
            Path(os.environ['VF_REPORT_GUARD_RECOGNITION_OUTPUT']).write_text(json.dumps(result,indent=2))
