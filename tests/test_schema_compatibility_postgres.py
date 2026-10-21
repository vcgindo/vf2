"""Actual used-certificate DDL/registrar transition on a disposable SMALL DB.

The inherited fixture is explicitly metadata-only, with seven populated owner
and capture records. Native business capture/execution is proved separately.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib,json,os,tempfile
from importlib import import_module
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from django.db import connection,transaction,DatabaseError
from django.db.migrations.executor import MigrationExecutor
from mta.serialization import digest,storage
from tests.test_ingestion_ownership_postgres import IngestionPostgresTests,OWNER,RUNTIME,ROLES
from mta.runtime import ingestion_authority as authority,ingestion_admission as admission
from release.advance_ingestion import catalogue,catalogue_delta,preservation,schema_transition


class SchemaTransitionPostgresTests(IngestionPostgresTests):
    proof_database='vf_admission_schema_20261022'

    def rollback(self):
        if self.atomic is not None:super().rollback()

    def test_used_opening_schema_transition_and_atomic_failure(self):
        # Build metadata records with the actual historical0153 model; the new
        # nullable field must not be assumed present before the upgrade.
        old_apps=MigrationExecutor(connection).loader.project_state([('fresh_mta','0153_incremental_current_guards')]).apps
        Attempt=old_apps.get_model('fresh_mta','DailyFeedAttempt')
        from mta.runtime.models import CalculationRun
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        # Explicit metadata-only fixture population, matching the inherited
        # certification fixture. Production guards are restored BEFORE DDL and
        # every tested operation. Genuine capture guards are tested separately.
        with connection.cursor() as c:c.execute('SET LOCAL session_replication_role=replica')
        parent=None
        for i in range(7):
            run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2026-04-08',
                execution_revision='schema-used-'+str(i),evidence_mode='production',input_digest='6'*64,
                input_payload={'fixture':'METADATA_ONLY','ordinal':i},status='RUNNING' if i==6 else 'FAILED')
            attempt=Attempt.objects.create(initialization_id=self.owner.pk,business_date='2026-04-08',
                batch_id='frozen',request_key=digest(str(i)),batch_digest='7'*64,binding_digest='8'*64,
                input_sha256='9'*64,run_id=run.pk,status=run.status,phase='CALCULATE',archive_path='/metadata/'+str(i),
                certification_id=self.cert.pk,master_revision_id=self.revision.pk)
            parent=MdmDailyInputCapture.objects.create(run=run,source=self.source,origin=parent,
                request_digest='a'*64,revision_digest='b'*64,sku_revision_digest='c'*64,
                location_revision_digest='d'*64,skuloc_revision_digest='e'*64,sql_digest='f'*64,nms_active=False)
        with connection.cursor() as c:c.execute('SET LOCAL session_replication_role=origin')
        # Commit the fixture: the production operation must own a genuine outer
        # transaction, not a savepoint inside a test's hidden transaction.
        self.atomic.__exit__(None,None,None);self.atomic=None
        before=storage(preservation(self.owner));old_epochs=self.epochs()
        target=dict(source_commit='8'*40,manifest_sha256='9'*64)
        # An independently inspected complete delta is frozen before invoking
        # the production entrypoint. Preview DDL rolls back, including records.
        with transaction.atomic(),connection.cursor() as c:
            before_catalogue=catalogue(c)
            c.execute('SET LOCAL ROLE '+OWNER)
            c.execute(import_module('mta.runtime.migrations.0164_migration_history_ownership').FORWARD)
            executor=MigrationExecutor(connection)
            plan=executor.migration_plan(executor.loader.graph.leaf_nodes())
            pins=[[m.name,hashlib.sha256((Path(__file__).resolve().parents[1]/'mta/runtime/migrations'/(m.name+'.py')).read_bytes()).hexdigest()] for m,b in plan]
            executor.migrate(executor.loader.graph.leaf_nodes());c.execute('RESET ROLE')
            authority.bootstrap_schema_transition(c,[OWNER,RUNTIME])
            c.execute('GRANT SELECT ON mta.fresh_mta_dailyreportgeneration,mta.fresh_mta_dailyreportorderroutesource TO '+RUNTIME)
            for name in ('guard_report_route_source','guard_report_generation','guard_v3_derived_report_rows',
                         'finite_capture_attempt_guard','finite_capture_preserved_guard','guard_migration_history'):
                c.execute('REVOKE EXECUTE ON FUNCTION mta.'+name+'() FROM PUBLIC')
            c.execute('GRANT EXECUTE ON FUNCTION mta.finite_capture_prefix_digest(uuid) TO '+RUNTIME)
            delta=storage(catalogue_delta(before_catalogue,catalogue(c)))
            self.assertEqual(self.epochs(),old_epochs)
            self.assertEqual(storage(preservation(self.owner)),before)
            # Only the approved structures/guards may change; no old data field
            # disappears and no privilege is granted on an old object.
            self.assertFalse(any(v['after'] is None and k.startswith('column:') for k,v in delta.items()))
            self.assertFalse(any(k.startswith('grants:') and v['before'] is not None for k,v in delta.items()))
            transaction.set_rollback(True)
        spec=dict(contract=authority.SCHEMA_CONTRACT,initialization_id=str(self.owner.pk),
            previous_release=self.release,target_release=target,migration_pins=pins,catalogue_delta=delta)
        with tempfile.TemporaryDirectory() as td,patch('release.native_identity.require_current',return_value=target):
            path=Path(td)/'schema.json';path.write_text(json.dumps(spec));pin=hashlib.sha256(path.read_bytes()).hexdigest()
            def run():return schema_transition(self.owner.pk,specification=path,expected_sha256=pin)
            # Each actual late SQL failure occurs AFTER DDL/receipt, not before
            # mutation. Outer rollback must restore catalogue and all rows.
            append=authority.append
            def late_failure(c,body):
                c.execute('SELECT 1/0')
            with patch.object(authority,'append',side_effect=late_failure),self.assertRaises(DatabaseError):run()
            with connection.cursor() as c:
                self.assertEqual(catalogue(c),before_catalogue)
                c.execute('SELECT to_regclass(%s)',[authority.SCHEMA_TABLE]);self.assertIsNone(c.fetchone()[0])
            self.assertEqual(storage(preservation(self.owner)),before);self.assertEqual(self.epochs(),old_epochs)
            self.assertEqual(self.admit().certification_digest,self.cert.receipt_digest)
            result=run();self.assertEqual(result['status'],'SCHEMA_TRANSITION_COMMITTED_ORIGINAL_STATE_PRESERVED')
            self.assertEqual(run()['status'],'EXISTING_SCHEMA_TRANSITION_VERIFIED')
            with connection.cursor() as c:
                admitted=admission._admit(c,self.owner.pk,target)
                self.assertEqual(admitted.certification_digest,self.cert.receipt_digest)
                self.assertEqual(storage(preservation(self.owner)),before);self.assertEqual(self.epochs(),old_epochs)
                from mta.runtime.daily_feed_models import DailyFeedAttempt
                self.assertFalse(DailyFeedAttempt.objects.exclude(recovery_origin=None).exists())
                for role in (OWNER,RUNTIME):
                    with self.subTest(role=role),self.assertRaises(DatabaseError),transaction.atomic():
                        c.execute('SET LOCAL ROLE '+role)
                        c.execute('INSERT INTO '+authority.SCHEMA_TABLE+' SELECT * FROM '+authority.SCHEMA_TABLE)
                for statement in ('UPDATE '+authority.SCHEMA_TABLE+' SET receipt_digest=receipt_digest',
                    'DELETE FROM '+authority.SCHEMA_TABLE,'TRUNCATE '+authority.SCHEMA_TABLE,
                    "DELETE FROM mta.django_migrations WHERE name LIKE '0164_%'"):
                    with self.subTest(statement=statement),self.assertRaises(DatabaseError),transaction.atomic():c.execute(statement)
                for statement in ('ALTER TABLE mta.django_migrations DISABLE TRIGGER migration_history_append',
                    'ALTER TABLE '+authority.SCHEMA_TABLE+' DISABLE TRIGGER ingestion_schema_transition_immutable',
                    'GRANT INSERT ON '+authority.SCHEMA_TABLE+' TO '+RUNTIME):
                    with transaction.atomic():
                        c.execute(statement)
                        with self.assertRaises(ValueError):admission._admit(c,self.owner.pk,target)
                        transaction.set_rollback(True)
                self.assertEqual(admission._admit(c,self.owner.pk,target).certification_digest,self.cert.receipt_digest)
            output=os.environ.get('VF_SCHEMA_PROOF_OUTPUT')
            if output:Path(output).write_text(json.dumps(dict(specification=spec,result=result,original_epochs=old_epochs,
                preserved_seven_owners_and_captures=True,metadata_fixture_only=True),indent=2))
            print('SCHEMA_TRANSITION_ATOMIC_REAL_SQL_PASS originalcert sevenowners captures statuses ACLroles epochs preserved')
