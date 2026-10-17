"""Persistence protocol tests; stub outputs here are NOT business parity inputs."""
from copy import deepcopy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings
from mta.runtime.models import (CalculationRun, RunCommand, Checkpoint, PickBand, PickProjection,
                                ExcessInventoryRow, ExcessProjection,
                                FulfillmentSummaryRow,FulfillmentDetailRow,FulfillmentProjection,
                                ExpediteRow,ExpediteProjection,PickPostRow,PickPostProjection)
from mta.runtime.services import read_outputs
from mta.runtime.temporal import BOUNDARIES, record_command
from development.temporal import execute_day
from development.validation_storage import export_run
from parity.output_archive import OutputArchive


@override_settings(VF_MTA_DAILY_PUBLICATION=False)
class TemporalPersistenceTest(TransactionTestCase):
    available_apps=['mta.runtime','django.contrib.contenttypes']
    def setUp(self):
        import uuid
        self.revision=self._testMethodName[:55]+'-'+uuid.uuid4().hex[:12]
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.environment = patch.dict(os.environ, {'VF_EVIDENCE_ROOT': self.directory.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.profile = {'delivery': {'site_code': 'VECTORFLOW-DEMO'}}
        self.state = {'importer':{'MasterData':[]},'btr':{'ExpediteDispatches':[]},'orders':{'SpikeOrderData':[]},'dbm': {
            'DBMMaster': [{'SKUCode': '337', 'WhCode': 'AG515802', 'Norm': 220}],
            'Suggestions': [{'SKUCode': '337', 'WhCode': 'AG515802', 'NewNorm': 250}],
            'NormAcceptanceTbl': [], 'NormsInSleepModeTbl': [], 'SKULocStandardAttributes':[]}}
        self.opening = dict(identity='persistence-protocol-only', opening_date='2026-06-05', state=self.state)
        self.seen = []

    def calculate(self, prior, opening_date, day, profile, identity, calculate, exceptions):
        self.seen.append(deepcopy(prior))
        result = dict(ClosingState=[prior], DBMFinal=[prior['dbm']], Lineage=[],
                    CalculationOutputs=[dict(capability='r1_ration_bifurcation', rows=[]),
                                        dict(capability='r1_order_route',rows=[])],
                    BPRFinal=[dict(BPR_Table=[],vf_RationedReqReport=[])],
                    MajorBoundaries=[dict(boundary=name, state={}) for name in BOUNDARIES])
        from mta.evidence import validating
        if not validating():
            result.pop('MajorBoundaries')
            result['_CompletedBoundaries']=list(BOUNDARIES)
        return result

    def run_day(self, index=0, **kwargs):
        options = dict(day={'business_date': f'2026-06-{6+index:02d}'},
                       profile=self.profile, execution_revision=self.revision)
        options.update(kwargs)
        if 'predecessor' not in options:
            options['opening'] = self.opening
        with patch('mta.runtime.temporal.calculate_day', side_effect=self.calculate):
            return execute_day(**options)

    def action(self, run, operation='APPLY', **kwargs):
        options = dict(operation=operation, selected=[['337', 'AG515802']],
                       timestamp='2026-06-06T12:00:00+05:30', actor='protocol-test', idempotency_key='action-1')
        options.update(kwargs)
        return record_command(run, **options)

    def test_next_day_consumes_own_closing_and_command_without_mutating_previous(self):
        first = self.run_day()
        before = read_outputs(first)
        event = self.action(first)
        self.assertEqual(self.action(first).pk, event.pk)
        second = self.run_day(1, predecessor=first)
        self.assertEqual(second.predecessor_id, first.pk)
        self.assertEqual(self.seen[-1]['dbm']['NormAcceptanceTbl'], [dict(
            SKUCode='337', WhCode='AG515802', AcceptanceDate='2026-06-06', OldNorm=220, NewNorm=250)])
        self.assertEqual(read_outputs(first), before)
        self.assertEqual(read_outputs(second)['Lineage'][0]['run_id'], str(first.pk))
        self.assertEqual(read_outputs(second)['Lineage'][0]['commands'][0]['id'], event.pk)
        self.assertEqual(self.run_day(1, predecessor=first).pk, second.pk)
        self.assertEqual(CalculationRun.objects.filter(execution_revision=self.revision).count(), 2)

    def test_sleep_effect_and_same_key_different_payload_rejected(self):
        first = self.run_day()
        self.action(first, 'SLEEP')
        with self.assertRaisesMessage(ValueError, 'different command facts'):
            self.action(first)
        self.run_day(1, predecessor=first)
        self.assertEqual(self.seen[-1]['dbm']['Suggestions'], [])
        self.assertEqual(self.seen[-1]['dbm']['NormsInSleepModeTbl'], [dict(
            SKUCode='337', WhCode='AG515802', StartDate='2026-06-06')])

    def test_action_and_implicit_fork_rejected_after_consumption(self):
        first = self.run_day()
        self.run_day(1, predecessor=first)
        with self.assertRaisesMessage(ValueError, 'already been consumed'):
            self.action(first)
        with self.assertRaisesMessage(ValueError, 'no implicit timeline fork'):
            self.run_day(2, predecessor=first)

    def test_command_tamper_prevents_next_day(self):
        first = self.run_day()
        event = self.action(first)
        RunCommand.objects.filter(pk=event.pk).update(after_digest='0'*64)
        with self.assertRaisesMessage(ValueError, 'Command output drift'):
            self.run_day(1, predecessor=first)
        self.assertEqual(CalculationRun.objects.filter(execution_revision=self.revision).count(), 1)

    def test_same_opening_cannot_silently_start_another_timeline(self):
        first = self.run_day()
        self.assertEqual(self.run_day().pk, first.pk)
        with self.assertRaisesMessage(ValueError, 'Opening already used'):
            self.run_day(1)
        self.assertEqual(CalculationRun.objects.filter(execution_revision=self.revision).count(), 1)

    def test_actions_cannot_be_backdated_or_consumed_before_their_date(self):
        first = self.run_day()
        with self.assertRaisesMessage(ValueError, 'Command date precedes'):
            self.action(first, timestamp='2026-06-05T12:00:00+05:30')
        self.action(first, timestamp='2026-06-08T12:00:00+05:30')
        with self.assertRaisesMessage(ValueError, 'Command date precedes'):
            self.action(first, timestamp='2026-06-07T12:00:00+05:30', idempotency_key='action-2')
        with self.assertRaisesMessage(ValueError, 'Command date outside'):
            self.run_day(1, predecessor=first)
        self.run_day(2, predecessor=first)

    def test_changed_durable_input_cannot_receive_calculated_outputs(self):
        def corrupt(*args):
            output = self.calculate(*args)
            CalculationRun.objects.filter(pk=args[4]).update(input_payload={'changed':True})
            return output
        with patch('mta.runtime.temporal.calculate_day', side_effect=corrupt):
            with self.assertRaisesMessage(ValueError, 'Input snapshot changed'):
                execute_day(day={'business_date':'2026-06-06'}, profile=self.profile,
                            execution_revision=self.revision, opening=self.opening)
        run=CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(run.status,'FAILED')
        self.assertEqual(run.checkpoints.count(),0)

    def test_input_snapshot_and_predecessor_site_are_enforced(self):
        first = self.run_day()
        self.state['dbm']['DBMMaster'][0]['Norm'] = 999
        with self.assertRaisesMessage(ValueError, 'another site'):
            self.run_day(1, predecessor=first, profile={'delivery': {'site_code': 'ANOTHER'}})
        self.run_day(1, predecessor=first)
        self.assertEqual(self.seen[-1]['dbm']['DBMMaster'][0]['Norm'], 220)

    def test_incomplete_boundary_roster_is_durable_failed_not_publication(self):
        def incomplete(*args):
            output = self.calculate(*args)
            output['MajorBoundaries'].pop()
            return output
        with patch('mta.runtime.temporal.calculate_day', side_effect=incomplete):
            with self.assertRaisesMessage(ValueError, 'Incomplete daily boundary roster'):
                execute_day(day={'business_date': '2026-06-06'}, profile=self.profile,
                            execution_revision=self.revision, opening=self.opening)
        run = CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(run.status, 'FAILED')
        self.assertEqual(run.checkpoints.count(), 0)

    def test_validation_boundaries_are_external_and_exactly_verified(self):
        run = self.run_day()
        self.assertNotIn('MajorBoundaries', read_outputs(run))
        checkpoint = run.checkpoints.get(name='MajorBoundaries')
        self.assertEqual(checkpoint.rows, [])
        self.assertEqual(checkpoint.row_count, 8)
        manifest = export_run(run, Path(self.directory.name) / 'export')
        archive = OutputArchive(manifest)
        self.assertEqual([r['boundary'] for r in archive.iter_rows('MajorBoundaries')], list(BOUNDARIES))
        self.assertEqual(archive['ClosingState'], read_outputs(run)['ClosingState'])
        archive.verify(run.output_digest,run.validation_digest)
        Checkpoint.objects.filter(pk=checkpoint.pk).update(evidence_sha256='0'*64)
        with self.assertRaisesMessage(ValueError, 'evidence file drift'):
            export_run(run, Path(self.directory.name) / 'tampered-export')

    def test_atomic_failure_keeps_unpublished_trace_but_no_checkpoint_or_action(self):
        create = Checkpoint.objects.create
        def fail_trace(**fields):
            if fields['name'] == 'MajorBoundaries':
                raise RuntimeError('injected after external trace write')
            return create(**fields)
        with patch('mta.runtime.services.Checkpoint.objects.create', side_effect=fail_trace):
            with self.assertRaisesMessage(RuntimeError, 'after external trace'):
                self.run_day()
        run = CalculationRun.objects.get(execution_revision=self.revision)
        self.assertEqual(run.status, 'FAILED')
        self.assertEqual(run.checkpoints.count(), 0)
        self.assertEqual(run.commands.count(), 0)
        self.assertFalse(PickBand.objects.filter(run=run).exists())
        self.assertFalse(PickProjection.objects.filter(run=run).exists())
        self.assertFalse(ExcessInventoryRow.objects.filter(run=run).exists())
        self.assertFalse(ExcessProjection.objects.filter(run=run).exists())
        self.assertFalse(FulfillmentProjection.objects.filter(run=run).exists())
        self.assertFalse(FulfillmentSummaryRow.objects.filter(run=run).exists())
        self.assertFalse(FulfillmentDetailRow.objects.filter(run=run).exists())
        self.assertFalse(ExpediteProjection.objects.filter(run=run).exists())
        self.assertFalse(ExpediteRow.objects.filter(run=run).exists())
        self.assertFalse(PickPostProjection.objects.filter(run=run).exists())
        self.assertFalse(PickPostRow.objects.filter(run=run).exists())
        self.assertEqual(run.output_digest, '')
        self.assertTrue((Path(self.directory.name) / str(run.pk) / 'MajorBoundaries.jsonl.gz').is_file())

    def test_production_has_required_rows_without_validation_files_and_denies_mode_reuse(self):
        with patch('development.temporal.persist_trace',side_effect=AssertionError('diagnostic trace')):
            run=self.run_day(evidence_mode='production')
        self.assertEqual(run.validation_digest,'')
        self.assertEqual(run.checkpoints.count(),0)
        self.assertEqual(read_outputs(run)['ClosingState'],[self.state])
        self.assertFalse(list(Path(self.directory.name).rglob('*.gz')))
        from mta.presentation.pick_storage import read_pick_bands
        from mta.presentation.fulfillment_storage import read_fulfillment
        from mta.presentation.excess_storage import read_excess
        from mta.presentation.expedite_storage import read_expedite
        from mta.presentation.pick_post_storage import read_pick_post
        output=read_outputs(run);bands=read_pick_bands(run)
        self.assertEqual(bands,[])
        read_fulfillment(run,output=output)
        read_excess(run,output=output)
        read_expedite(run,output=output,bands=bands)
        read_pick_post(run,output=output,bands=bands)
        with self.assertRaisesMessage(ValueError,'evidence policy identity drift'):
            self.run_day(evidence_mode='validation')
        with self.assertRaisesMessage(ValueError,'requires validation evidence'):
            export_run(run,Path(self.directory.name)/'denied')
        PickProjection.objects.filter(run=run).update(calculation_digest='0'*64)
        with self.assertRaisesMessage(ValueError,'Required daily source receipt drift'):
            read_pick_bands(run)

    def test_typed_input_component_readback_and_tamper_denial(self):
        from django.db import connection
        from mta.runtime.input_reader import read_input
        from mta.runtime.receipt_integrity import audit_input
        run=self.run_day()
        raw=read_input(run)
        self.assertEqual(raw['opening'],self.opening)
        self.assertEqual(read_input(run,components=('opening',)),{'opening':self.opening})
        image=next(v for k,v in run.input_payload['images'].items() if k.endswith('/DBMMaster/values'))
        from mta.runtime.relational_state import table_sql
        with connection.cursor() as cursor:
            cursor.execute('UPDATE '+table_sql(image['table'])+' SET "Norm"=999 WHERE vf_run_id=%s AND vf_image=%s',[run.pk,image['image']])
        with self.assertRaisesMessage(ValueError,'Operational state value/type/multiplicity drift'):
            audit_input(run)
        with self.assertRaisesMessage(ValueError,'Operational state value/type/multiplicity drift'):
            read_outputs(run)

    def test_streamed_exports_preserve_empty_rows_and_typed_cells_and_reject_extra_cells(self):
        from django.db import connection
        from mta.runtime.relational_state import save_export,load_export
        from decimal import Decimal
        run=self.run_day()
        rows=[{'values':[]},{'values':[None,'1',1,False,1.25,Decimal('2.500')]},{'values':[]}]
        metadata=save_export(run,'export-proof',rows)
        self.assertNotIn('lengths',metadata)
        self.assertEqual(load_export(run,metadata),[{'values':[]},{'values':[None,'1',1,False,1.25,'2.500']},{'values':[]}])
        with connection.cursor() as cursor:
            cursor.execute('INSERT INTO mta_state.report_export_cell VALUES (%s,%s,99,0,%s,NULL,NULL,NULL,NULL)',[run.pk,'export-proof','null'])
        with self.assertRaisesMessage(ValueError,'Orphan report cells'):load_export(run,metadata)

    def _fixture_teardown(self):
        # Immutable production guards prohibit global flush. Each test has its
        # own execution revision; the owned database is retained for inspection.
        pass
