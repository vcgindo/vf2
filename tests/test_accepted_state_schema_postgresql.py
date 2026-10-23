"""Owned metadata-only authority integration, never business certification.

Uses actual migrations, schema authority and admission against native-shaped
restricted roles. Only release/predecessor fingerprints are fixture-bound.
The positive case has no READY business publications; a malformed READY fixture
must fail the real qualification hook after DDL and roll all appends back.
"""
import hashlib
import json
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.graph import MigrationGraph

from tests import test_ingestion_ownership_postgres as original
from mta.serialization import digest, storage
from mta.runtime import ingestion_authority as authority, ingestion_admission as admission
from mta.runtime import report_guard_transition as report_guard, accepted_state_transition as ownership
from release import advance_ingestion as upgrade


class AcceptedStateSchemaPostgresTests(original.IngestionPostgresTests):
    proof_database='VFTEST_Fresh_LifecycleG1_20261024_authority'

    def rollback(self):
        if self.atomic is not None:
            super().rollback()

    def setUp(self):
        self.assertEqual(connection.settings_dict['NAME'],self.proof_database)
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('fresh_control.owned_namespace')")
            exists=cursor.fetchone()[0] is not None
        if not exists:
            super().setUp()
            return
        # Preserve the earlier failed attempt's committed fixture and resume its
        # actual prefix; never recreate accepted test authority or reset the DB.
        from mta.runtime.initialization_models import ProductionInitialization
        from mta.runtime.ingestion_models import InitializationCertification,MasterInputRevision
        self.atomic=transaction.atomic();self.atomic.__enter__()
        self.addCleanup(self.rollback)
        self.owner=ProductionInitialization.objects.select_related('source').get()
        self.source=self.owner.source
        self.assertEqual(self.source.receipt.get('schema'),'TEST_METADATA_ONLY')
        self.cert=InitializationCertification.objects.get(initialization=self.owner)
        self.revision=MasterInputRevision.objects.get(initialization=self.owner)
        with connection.cursor() as cursor:
            self.body=authority.read(cursor,self.owner.pk,self.cert.release_digest)
        self.release=dict(source_commit=self.body['target_commit'],manifest_sha256=self.body['target_release'])

    def advance_fixture(self,name,previous,target):
        """Preview and apply actual old DDL with portable full-delta checks."""
        from mta.mdm.owned_namespace import _application_catalogue
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1 FROM fresh_control.ingestion_release_authority '
                           'WHERE initialization_id=%s AND target_release=%s',
                           [self.owner.pk,target['manifest_sha256']])
            if cursor.fetchone():
                admission._admit(cursor,self.owner.pk,target,pending=True)
                return
        with transaction.atomic(),connection.cursor() as cursor:
            before=upgrade.catalogue(cursor)
            old=_application_catalogue(cursor)
            cursor.execute('SELECT to_regclass(%s)',[authority.SCHEMA_TABLE])
            has_schema=cursor.fetchone()[0] is not None
            cursor.execute('SET LOCAL ROLE '+original.OWNER)
            if not has_schema:
                from importlib import import_module
                cursor.execute(import_module('mta.runtime.migrations.0164_migration_history_ownership').FORWARD)
            executor=MigrationExecutor(connection)
            targets=executor.loader.graph.leaf_nodes()
            plan=executor.migration_plan(targets)
            pins=[[m.name,hashlib.sha256((Path(__file__).resolve().parents[1]/
                'mta/runtime/migrations'/(m.name+'.py')).read_bytes()).hexdigest()] for m,b in plan]
            executor.migrate(targets)
            cursor.execute('RESET ROLE')
            if not has_schema:
                authority.bootstrap_schema_transition(cursor,[original.OWNER,original.RUNTIME])
            current=_application_catalogue(cursor)
            old_objects={o['name'] for o in old['objects']}
            for obj in current['objects']:
                if obj['name'] not in old_objects and obj['kind']!='S':
                    cursor.execute('GRANT SELECT ON '+obj['name']+' TO '+original.RUNTIME)
            old_functions={f['name'] for f in old['functions']}
            for function in current['functions']:
                if function['name'] not in old_functions:
                    cursor.execute('SELECT %s::oid::regprocedure::text',[function['oid']])
                    cursor.execute('REVOKE EXECUTE ON FUNCTION '+cursor.fetchone()[0]+' FROM PUBLIC')
            grants={'0164':('finite_capture_prefix_digest(uuid)',),
                '0165':('terminal_capture_prefix_digest(uuid)','terminal_capture_admit(mta.fresh_mta_dailyfeedattempt)'),
                '0166':('retry_capture_prefix_digest(uuid)','retry_capture_admit(mta.fresh_mta_dailyfeedattempt)'),
                '0167':('final_capture_prefix_digest(uuid)','final_capture_admit(mta.fresh_mta_dailyfeedattempt)')}
            for function in grants[name[:4]]:
                cursor.execute('GRANT EXECUTE ON FUNCTION mta.'+function+' TO '+original.RUNTIME)
            delta=storage(upgrade.catalogue_delta(before,upgrade.catalogue(cursor)))
            transaction.set_rollback(True)
        spec=dict(contract=authority.SCHEMA_CONTRACT,initialization_id=str(self.owner.pk),
                  previous_release=previous,target_release=target,migration_pins=pins,catalogue_delta=delta)
        with tempfile.TemporaryDirectory() as directory,patch('release.native_identity.require_current',return_value=target):
            path=Path(directory)/'old-metadata-only-transition.json'
            path.write_text(json.dumps(spec),encoding='utf-8')
            result=upgrade.schema_transition(self.owner.pk,specification=path,
                                             expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(result['status'],'SCHEMA_TRANSITION_COMMITTED_ORIGINAL_STATE_PRESERVED')

    def test_real_authority_upgrade_late_audit_rollback_and_empty_roster_commit(self):
        def stop_at(name):
            def stopped(graph,app=None):
                # This historical metadata fixture certified only MTA. Do not
                # introduce unrelated, uncertified content-types DDL into its
                # reviewed MTA-only transition specification.
                return [('fresh_mta',name)] if app in (None,'fresh_mta') else []
            return stopped

        from mta.runtime.models import CalculationRun
        if not CalculationRun.objects.exists():
            # Small explicit metadata fixture for a genuinely fresh proof DB.
            # No calculation/output graph is supplied or claimed accepted.
            apps=MigrationExecutor(connection).loader.project_state(
                [('fresh_mta','0153_incremental_current_guards')]).apps
            Attempt=apps.get_model('fresh_mta','DailyFeedAttempt')
            Capture=apps.get_model('fresh_mta','MdmDailyInputCapture')
            with connection.cursor() as cursor:
                cursor.execute('SET LOCAL session_replication_role=replica')
                run=CalculationRun.objects.create(kind='DAILY_CHAIN',business_date='2026-04-08',
                    execution_revision='ownership-authority-metadata-only',evidence_mode='production',
                    input_digest='6'*64,input_payload={'fixture':'METADATA_ONLY'},status='FAILED')
                Attempt.objects.create(initialization_id=self.owner.pk,business_date='2026-04-08',
                    batch_id='metadata-only',request_key=digest('ownership-authority-metadata-only'),
                    batch_digest='7'*64,binding_digest='8'*64,input_sha256='9'*64,run_id=run.pk,
                    status='FAILED',phase='CALCULATE',archive_path='/metadata/ownership',
                    certification_id=self.cert.pk,master_revision_id=self.revision.pk)
                Capture.objects.create(run_id=run.pk,source_id=self.source.pk,request_digest='a'*64,
                    revision_digest='b'*64,sku_revision_digest='c'*64,location_revision_digest='d'*64,
                    skuloc_revision_digest='e'*64,sql_digest='f'*64,nms_active=False)
                cursor.execute('SET LOCAL session_replication_role=origin')
        self.atomic.__exit__(None,None,None);self.atomic=None
        # Establish or resume the four real DDL authorities. The previously
        # committed metadata fixture remains unchanged across failed attempts.
        prior=self.release
        for name,commit,manifest in (
                ('0164_migration_history_ownership','8','9'),
                ('0165_terminal_capture_admission','a','b'),
                ('0166_failed_terminal_retry','c','d'),
                ('0167_final_attempt_admission','e','f')):
            result=dict(source_commit=commit*40,manifest_sha256=manifest*64)
            with patch.object(MigrationGraph,'leaf_nodes',stop_at(name)):
                self.advance_fixture(name,prior,result)
            prior=result

        previous=dict(source_commit='e'*40,manifest_sha256='f'*64)
        report_release=dict(source_commit='6'*40,manifest_sha256='7'*64)
        target=dict(source_commit='4'*40,manifest_sha256='5'*64)
        with ExitStack() as stack:
            for module,prior in ((report_guard,previous),(ownership,report_release)):
                stack.enter_context(patch.object(module,'PREVIOUS_RELEASE',prior['manifest_sha256']))
            for name,module,prior,result in (
                    ('0168_report_guard_owner_sets',report_guard,previous,report_release),
                    ('0170_command_writer_compatibility',ownership,report_release,target)):
                with connection.cursor() as cursor:
                    before_schema=__import__('release.native_schema',fromlist=['schema_digest']).schema_digest(cursor)
                    before_guard=admission.security_digest(cursor,admission._certificate(self.owner.pk)['authority_roles'])
                stack.enter_context(patch.object(module,'BEFORE_SCHEMA',before_schema))
                stack.enter_context(patch.object(module,'BEFORE_GUARD',before_guard))
                spec=dict(contract=authority.SCHEMA_CONTRACT,initialization_id=str(self.owner.pk),
                          previous_release=prior,target_release=result,
                          migration_pins=module.migration_pins(),catalogue_delta=module.catalogue_delta())
                with tempfile.TemporaryDirectory() as directory, \
                     patch.object(MigrationGraph,'leaf_nodes',stop_at(name)), \
                     patch('release.native_identity.require_current',return_value=result):
                    path=Path(directory)/'metadata-only-transition.json'
                    path.write_text(json.dumps(spec),encoding='utf-8')
                    pin=hashlib.sha256(path.read_bytes()).hexdigest()

                    def invoke():
                        return upgrade.schema_transition(self.owner.pk,specification=path,expected_sha256=pin)

                    if module is report_guard:
                        self.assertEqual(invoke()['status'],'SCHEMA_TRANSITION_COMMITTED_ORIGINAL_STATE_PRESERVED')
                        continue

                    from mta.runtime.models import CalculationRun,DailyUiPublication
                    # Deliberately invalid test fixture, never called accepted
                    # business evidence. Replica mode is confined to fixture
                    # insertion/removal and restored before the tested upgrade.
                    fixture_run=CalculationRun.objects.order_by('pk').first()
                    with transaction.atomic(),connection.cursor() as cursor:
                        cursor.execute('SET LOCAL session_replication_role=replica')
                        DailyUiPublication.objects.create(run=fixture_run,status='READY',output_digest='a'*64,
                            source_digest='b'*64,configuration_digest='c'*64,recipe_digest='d'*64,
                            seal_digest='e'*64,layers={})
                    before=storage(upgrade.preservation(self.owner))
                    with connection.cursor() as cursor:
                        before_catalogue=upgrade.catalogue(cursor)
                        before_history=upgrade.authority_history(cursor,self.owner.pk)
                    reached=[]
                    qualify=upgrade._qualify_owned_publications

                    def observe_actual_audit(owner,release,check):
                        with connection.cursor() as cursor:
                            cursor.execute("SELECT count(*) FROM mta.django_migrations WHERE app='fresh_mta' "
                                           "AND name IN ('0169_accepted_state_ownership','0170_command_writer_compatibility')")
                            self.assertEqual(cursor.fetchone(),(2,))
                            self.assertIsNotNone(authority.read(cursor,owner.pk,release['manifest_sha256']))
                        reached.append('real qualification after DDL and authority appends')
                        return qualify(owner,release,check)

                    with patch.object(upgrade,'_qualify_owned_publications',side_effect=observe_actual_audit), \
                         self.assertRaises(ValueError) as failure:
                        invoke()
                    self.assertEqual(len(reached),1)
                    self.assertTrue(str(failure.exception))
                    with connection.cursor() as cursor:
                        self.assertEqual(upgrade.catalogue(cursor),before_catalogue)
                        self.assertEqual(upgrade.authority_history(cursor,self.owner.pk),before_history)
                    self.assertEqual(storage(upgrade.preservation(self.owner)),before)
                    # Remove only the intentionally malformed test row. No
                    # production acceptance record or source population exists.
                    with transaction.atomic(),connection.cursor() as cursor:
                        cursor.execute('SET LOCAL session_replication_role=replica')
                        DailyUiPublication.objects.filter(run=fixture_run).delete()
                    result=invoke()
                    self.assertEqual(result['qualified_read_ready_runs'],[])
                    self.assertEqual(invoke()['status'],'EXISTING_SCHEMA_TRANSITION_VERIFIED')
                    with connection.cursor() as cursor:
                        self.assertEqual(admission._admit(cursor,self.owner.pk,target,pending=True).certification_digest,
                                         self.cert.receipt_digest)
                    print('OWNERSHIP_AUTHORITY_REAL_SQL_PASS metadata_only=True empty_READY_roster=True '
                          'late_real_audit_failure='+str(failure.exception))
