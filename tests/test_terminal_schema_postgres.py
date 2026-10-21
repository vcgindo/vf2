"""Real second schema admission preserves the used eight-owner metadata.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib,json,tempfile
from pathlib import Path
from unittest.mock import patch
from django.db import connection,transaction,DatabaseError
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.graph import MigrationGraph
from tests.test_schema_compatibility_postgres import SchemaTransitionPostgresTests
from tests.test_ingestion_ownership_postgres import OWNER,RUNTIME
from mta.serialization import digest,storage
from mta.runtime import ingestion_authority as authority,ingestion_admission as admission
from release.advance_ingestion import schema_transition,preservation,catalogue,catalogue_delta,authority_history


class TerminalSchemaPostgresTests(SchemaTransitionPostgresTests):
    proof_database='vf_btr_terminal_admission_20261022'

    def test_second_admission_preserves_used_metadata_and_prior_registrar(self):
        leaves=MigrationGraph.leaf_nodes
        def old_leaves(graph,app=None):
            return [v for v in leaves(graph,app) if v[0]!='fresh_mta']+([('fresh_mta','0164_migration_history_ownership')] if app in (None,'fresh_mta') else [])
        # Reuse the accepted original0153->0164 proof to establish the actual
        # prior registrar chain; do not fabricate a live compatibility digest.
        with patch.object(MigrationGraph,'leaf_nodes',old_leaves):
            super().test_used_opening_schema_transition_and_atomic_failure()
        from mta.runtime.models import CalculationRun
        from mta.runtime.daily_feed_models import DailyFeedAttempt
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        with transaction.atomic(),connection.cursor() as c:
            c.execute('SET LOCAL session_replication_role=replica')
            parent=DailyFeedAttempt.objects.order_by('-created_at').first()
            child=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2026-04-08',
                execution_revision='metadata-stopped-finite',input_digest='6'*64,
                input_payload={'fixture':'METADATA_ONLY','schema':'fresh-captured-input-reference-v3'},status='RUNNING')
            values={f.attname:getattr(parent,f.attname) for f in parent._meta.concrete_fields
                if f.name not in ('id','attempt_id','created_at','updated_at')}
            values.update(run_id=child.pk,recovery_origin_id=parent.pk,request_key=digest('metadata8'),archive_path='/metadata/8')
            DailyFeedAttempt.objects.create(**values)
            cap=MdmDailyInputCapture.objects.get(run=parent.run)
            values={f.attname:getattr(cap,f.attname) for f in cap._meta.concrete_fields if f.name not in ('run','captured_at')}
            MdmDailyInputCapture.objects.create(run=child,**dict(values,origin_id=parent.run_id))
        self.prove_second_admission()

    def prove_second_admission(self):
        before=storage(preservation(self.owner));epochs=self.epochs()
        with connection.cursor() as c:
            old_history=authority_history(c,self.owner.pk);before_catalogue=catalogue(c)
        target=dict(source_commit='a'*40,manifest_sha256='b'*64)
        with transaction.atomic(),connection.cursor() as c:
            c.execute('SET LOCAL ROLE '+OWNER)
            executor=MigrationExecutor(connection);plan=executor.migration_plan(executor.loader.graph.leaf_nodes())
            pins=[[m.name,hashlib.sha256((Path(__file__).resolve().parents[1]/'mta/runtime/migrations'/(m.name+'.py')).read_bytes()).hexdigest()] for m,b in plan]
            self.assertEqual([n[:4] for n,h in pins],['0165'])
            executor.migrate(executor.loader.graph.leaf_nodes());c.execute('RESET ROLE')
            c.execute('GRANT EXECUTE ON FUNCTION mta.terminal_capture_prefix_digest(uuid),mta.terminal_capture_admit(mta.fresh_mta_dailyfeedattempt) TO '+RUNTIME)
            delta=storage(catalogue_delta(before_catalogue,catalogue(c)))
            transaction.set_rollback(True)
        spec=dict(contract=authority.SCHEMA_CONTRACT,initialization_id=str(self.owner.pk),
            previous_release=dict(source_commit='8'*40,manifest_sha256='9'*64),target_release=target,
            migration_pins=pins,catalogue_delta=delta)
        with tempfile.TemporaryDirectory() as td,patch('release.native_identity.require_current',return_value=target):
            path=Path(td)/'terminal.json';path.write_text(json.dumps(spec));pin=hashlib.sha256(path.read_bytes()).hexdigest()
            def run():return schema_transition(self.owner.pk,specification=path,expected_sha256=pin)
            def fail(c,body):c.execute('SELECT 1/0')
            with patch.object(authority,'append',side_effect=fail),self.assertRaises(DatabaseError):run()
            with connection.cursor() as c:
                self.assertEqual(catalogue(c),before_catalogue)
                self.assertEqual(authority_history(c,self.owner.pk),old_history)
            self.assertEqual(storage(preservation(self.owner)),before)
            result=run();self.assertEqual(result['status'],'SCHEMA_TRANSITION_COMMITTED_ORIGINAL_STATE_PRESERVED')
            self.assertEqual(run()['status'],'EXISTING_SCHEMA_TRANSITION_VERIFIED')
            with connection.cursor() as c:
                self.assertEqual(admission._admit(c,self.owner.pk,target,pending=True).certification_digest,self.cert.receipt_digest)
                history=authority_history(c,self.owner.pk)
                for table,rows in old_history.items():
                    for key,row in rows.items():self.assertEqual(history[table][key],row)
            self.assertEqual(storage(preservation(self.owner)),before);self.assertEqual(self.epochs(),epochs)
            output=__import__('os').environ.get('VF_TERMINAL_SCHEMA_PROOF_OUTPUT')
            if output:Path(output).write_text(json.dumps(dict(specification=spec,result=result,preserved_eight=True),indent=2))
        print('TERMINAL_SCHEMA_REAL_SQL_PASS second registrar chain exact8 fullmetadata originalreceipt epochs roles DDL+lateappend rollback')
