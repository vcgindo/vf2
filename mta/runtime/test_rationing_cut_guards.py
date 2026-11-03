"""Actual PostgreSQL guard proofs; every fixture transaction is rolled back."""
from datetime import date
import json
import uuid

from django.db import connection, transaction, DatabaseError
from django.test import TestCase

from mta.serialization import digest, canonical_parts
from mta.runtime.models import CalculationRun, MdmSource, ProductionInitialization
from mta.runtime.state_cut_models import OperationalStateCut
from mta.runtime.mdm_daily_models import MdmDailyInputCapture
from mta.runtime.execution_setting_models import ExecutionSettingsVersion
from mta.runtime.execution_settings import reference
from mta.runtime.input_storage import save_input
from mta.domain.btr_rationing_history import COLUMNS


def setting(value):
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.production_initialization',%s,true)", [value])


class RationingCutGuardTests(TestCase):
    def test_actual_revision_watch_and_scoped_consumers_recognize_anchor_migration(self):
        from importlib import import_module
        from mta.runtime import ingestion_ownership as ownership
        migration = import_module('mta.runtime.migrations.0270_bpr_history_storage')
        with connection.cursor() as cursor:
            cursor.execute("SELECT p.prosrc,p.prosecdef,p.proconfig,pg_get_function_result(p.oid) "
                "FROM pg_proc p WHERE p.oid='mta.ingestion_watch()'::regprocedure")
            body, definer, configuration, returns = cursor.fetchone()
            self.assertEqual(body, migration.NEW)
            self.assertTrue(ownership.is_revision_guard(dict(name='mta.ingestion_watch()',
                body=body, security_definer=definer, configuration=configuration, returns=returns)))
            self.assertEqual(ownership.scoped_derived_body(cursor,
                minimum='0246_btr_scope_dimension_ingestion_ownership'), body)
            ownership.require_guard_coverage(cursor)

    def tearDown(self):
        # Several cases intentionally leave pending cuts to test their refusal.
        # Every test transaction is discarded, never an application commit.
        transaction.set_rollback(True)

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS state_cut_complete DEFERRED')
        self.profile = {'delivery': {'site_code': 'IR1-GUARD', 'btr_settings': {
            'CaptureDispatchExecutionEfficiency': 1, 'RationingHistoryHorizonBTR': 30}}}
        self.source = MdmSource.objects.create(digest='7'*64, database_name='ir1-guard',
            receipt={'schema': 'fresh-production-mdm-source-v1'})
        identity = uuid.uuid4()
        setting(str(identity))
        self.raw = dict(profile=self.profile, opening={'state': {'btr': {'RationingHistory': []}}})
        self.owner = ProductionInitialization.objects.create(id=identity, source=self.source,
            opening_identity=str(identity), opening_date=date(2026, 7, 9), input_sha256='7'*64,
            recipe_sha256='7'*64, configuration_digest=digest(self.profile),
            implementation_digest='7'*64, input_digest=digest(self.raw))

    def seal_initialization(self):
        from mta.runtime import opening_storage
        from mta.mdm.initialization import initialization_table
        self.owner.input_payload = save_input(self.owner, self.raw, version=3,
            image_writer=opening_storage.save_image, table_selector=initialization_table)
        self.owner.input_manifest_digest = digest(self.owner.input_payload)
        self.owner.receipt_digest = '7'*64
        self.owner.save(update_fields=['input_payload', 'input_manifest_digest', 'receipt_digest'])

    def anchor(self):
        return OperationalStateCut.objects.create(initialization=self.owner, family='rationing_history',
            position=0, input_digest=self.owner.input_digest, settings_digest=self.owner.configuration_digest)

    def seal_anchor(self, cut, *, facts_digest=None):
        image = self.owner.input_payload['images']['input/opening/state/btr/RationingHistory/values']
        body = dict(format='rationing-occurrences-v1', cut=str(cut.pk), initialization=str(self.owner.pk),
            family='rationing_history', position=0, run=None, parent=None, parent_root='0'*64,
            input_digest=cut.input_digest, settings_digest=cut.settings_digest, fields=image['fields'],
            count=image['count'], inserted=image['count'], revised=0, expired=0,
            facts_digest=facts_digest or digest([]),
            revisions_digest=digest([]), expiry_digest=digest([]), anchor=dict(owner_kind='INITIALIZATION',
            owner_id=str(self.owner.pk), manifest_digest=self.owner.input_manifest_digest,
            image=image['image'], digest=image['digest'], count=image['count']))
        cut.root_body = b''.join(canonical_parts(body)).decode('utf-8')
        cut.root_digest = digest(body)
        cut.save(update_fields=['root_body', 'root_digest'])
        return cut

    def denied(self, callback, message):
        with self.assertRaisesMessage(DatabaseError, message), transaction.atomic():
            callback()

    def constraints(self):
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS state_cut_complete IMMEDIATE')

    def test_nested_pending_anchor_seals_under_existing_initialization_owner(self):
        with transaction.atomic():
            cut = self.anchor()
            self.seal_initialization()
            self.seal_anchor(cut)
            self.constraints()
        self.assertEqual(OperationalStateCut.objects.count(), 1)

    def test_missing_flag_and_sealed_initialization_refuse_new_anchor(self):
        setting('')
        self.denied(self.anchor, 'Existing-state anchor requires normal trusted adoption')
        setting(str(self.owner.pk))
        self.seal_initialization()
        self.denied(self.anchor, 'Existing-state anchor requires normal trusted adoption')

    def test_pending_cut_cannot_commit_without_seal(self):
        self.anchor()
        self.denied(self.constraints, 'Unsealed operational cut cannot commit')

    def test_anchor_rechecks_final_initialization_input_and_settings(self):
        for name in ('input_digest', 'configuration_digest'):
            def changed():
                cut = self.anchor()
                ProductionInitialization.objects.filter(pk=self.owner.pk).update(**{name: 'a'*64})
                self.owner.refresh_from_db()
                self.seal_initialization()
                self.seal_anchor(cut)
                self.constraints()
            with self.subTest(name=name):
                self.denied(changed, 'Anchor final initialization ownership differs')
                self.owner.refresh_from_db()

    def new_run(self, ref=None, *, raw_change=None, predecessor=None, business_date=date(2026, 7, 10)):
        raw = dict(profile=self.profile, initialization_binding=dict(id=str(self.owner.pk),
            configuration_digest=self.owner.configuration_digest))
        if ref is not None:
            raw['execution_settings'] = ref
        if raw_change:
            raw_change(raw)
        run = CalculationRun.objects.create(input_digest=digest(raw), input_payload={},
            execution_revision=str(uuid.uuid4()), kind='DAILY_CHAIN', status='RUNNING',
            business_date=business_date, predecessor=predecessor)
        run.input_payload = save_input(run, raw)
        run.input_manifest_digest = digest(run.input_payload)
        run.save(update_fields=['input_payload', 'input_manifest_digest'])
        MdmDailyInputCapture.objects.create(run=run, source=self.source, request_digest='7'*64,
            revision_digest='7'*64, sku_revision_digest='7'*64, location_revision_digest='7'*64,
            skuloc_revision_digest='7'*64, sql_digest='7'*64, nms_active=True)
        return run

    def settings(self, run):
        with connection.cursor() as cursor:
            cursor.execute('SELECT mta.state_cut_settings(%s,%s)', [self.owner.pk, run.pk])
            return cursor.fetchone()[0]

    def version(self, effective_date=None):
        version = ExecutionSettingsVersion.objects.create(initialization=self.owner, revision=1,
            profile_digest='8'*64, values_digest='9'*64, reason='IR1 rollback fixture',
            actor='isolated-proof', effective_date=effective_date)
        version.status = 'COMMITTED'
        version.save(update_fields=['status'])
        return reference(version)

    def test_frozen_settings_original_and_versioned_owner(self):
        self.seal_initialization()
        self.assertEqual(self.settings(self.new_run()), self.owner.configuration_digest)
        ref = self.version()
        self.assertEqual(self.settings(self.new_run(ref)), ref['profile_digest'])
        bad = {**ref, 'profile_digest': 'a'*64}
        self.denied(lambda: self.settings(self.new_run(bad)), 'Frozen settings version/date/reference differs')
        self.denied(lambda: self.settings(self.new_run(raw_change=lambda raw:
            raw['initialization_binding'].update(id=str(uuid.uuid4())))), 'Frozen settings initialization/capture differs')

    def test_future_settings_refused(self):
        self.seal_initialization()
        ref = self.version(date(2026, 7, 11))
        self.denied(lambda: self.settings(self.new_run(ref)), 'Frozen settings version/date/reference differs')

    def test_cut_rejects_settings_digest_not_owned_by_frozen_run(self):
        cut = self.anchor()
        self.seal_initialization()
        self.seal_anchor(cut)
        run = self.new_run()
        kwargs = dict(initialization=self.owner, family='rationing_history', position=1, run=run,
                      parent=cut, input_digest=run.input_digest, settings_digest='a'*64)
        self.denied(lambda: OperationalStateCut.objects.create(**kwargs), 'Operational cut frozen settings differ')
        kwargs['settings_digest'] = self.owner.configuration_digest
        OperationalStateCut.objects.create(**kwargs)

    def test_field_roster_matches_canonical_order_and_null_representation(self):
        fields = [[c['name'], c['name'], 'str'] for c in COLUMNS]
        cases = [(fields, 2, True), (fields, 0, True), ([], 0, True), ([], 2, False),
                 (list(reversed(fields)), 2, False), ([['unknown', 'unknown', 'str']]*69, 2, False)]
        for value, count, expected in cases:
            with self.subTest(count=count, expected=expected):
                with connection.cursor() as cursor:
                    cursor.execute('SELECT mta.rationing_fields_valid(%s::jsonb,%s)', [json.dumps(value), count])
                    self.assertEqual(cursor.fetchone()[0], expected)

    def test_indexed_anchor_reader_preserves_typed_ordered_duplicate_facts(self):
        from tests.test_rationing_delta import row
        from mta.runtime.relational_state import copy_rows, db_value
        from mta.runtime.rationing_reader import read_cut, iter_occurrences
        from mta.runtime.rationing_delta import Occurrence
        from mta.serialization import storage
        from django.test.utils import CaptureQueriesContext
        rows = [row('2026-07-08'), row('2026-07-08'), row(None, Dispatch=0)]
        self.raw['opening']['state']['btr']['RationingHistory'] = rows
        self.owner.input_digest = digest(self.raw)
        self.owner.save(update_fields=['input_digest'])
        cut = self.anchor()
        self.seal_initialization()
        copy_rows('mta_state.rationing_fact', ['cut_id', 'vf_ordinal', *[c['name'] for c in COLUMNS]],
            ((cut.pk, n, *[db_value(r[c['name']], c['type']) for c in COLUMNS]) for n, r in enumerate(rows)))
        copy_rows('mta_state.rationing_lifetime',
            ['fact_cut_id', 'original_ordinal', 'initialization_id', 'born_position'],
            ((cut.pk, n, self.owner.pk, 0) for n in range(len(rows))))
        self.seal_anchor(cut, facts_digest=digest(rows))
        self.constraints()
        with CaptureQueriesContext(connection) as queries:
            actual = list(iter_occurrences(read_cut(cut.pk)))
        self.assertEqual(actual, [(Occurrence(0, n), storage(r)) for n, r in enumerate(rows)])
        self.assertLessEqual(len(queries), 3)

    def initialized_writer(self, rows):
        from mta.runtime.rationing_writer import begin_initial_anchor, seal_initial_anchor
        self.raw['opening']['state']['btr']['RationingHistory'] = rows
        self.owner.input_digest = digest(self.raw)
        self.owner.save(update_fields=['input_digest'])
        cut = begin_initial_anchor(self.owner)
        self.seal_initialization()
        seal_initial_anchor(cut, self.owner)
        self.constraints()
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS state_cut_complete DEFERRED')
        return cut

    def accept_storage_fixture(self, run, item, *, manifest=None):
        """Complete only this rollback-owned storage fixture, not a business run."""
        from django.utils import timezone
        from mta.runtime.rationing_reader import IMAGE
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.mdm_consuming_run',%s,true)", [str(run.pk)])
        MdmDailyInputCapture.objects.filter(run=run).update(status='CONSUMED', consumed_at=timezone.now())
        run.production_manifest = {'images': {IMAGE: item}} if manifest is None else manifest
        run.production_digest = digest(run.production_manifest)
        run.status = 'SUCCEEDED'
        run.save(update_fields=['production_manifest', 'production_digest', 'status'])
        self.constraints()
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS state_cut_complete DEFERRED')

    def test_report_sources_preserve_phase_values_and_rollback_on_actual_storage(self):
        from copy import deepcopy
        from unittest.mock import patch
        from mta.runtime import relational_state as typed, accepted_state_read, receipt_integrity
        from mta.presentation.report_verification import _consumer_graph
        from mta.serialization import storage
        self.initialized_writer([])
        run=self.new_run()
        closing=[{'Id':1,'Reason':'after'},{'Id':2,'Reason':None}]
        earlier=[{'Id':1,'Reason':'before'},{'Id':2,'Reason':None}]*300
        reports=[dict(stage=name,tables={},deferred={'kind':'storage-fixture'},
                      sources={'ReasonCodes':deepcopy(earlier)})
                 for name in ('norm-change-export','norm-change-history')]
        output=dict(ClosingState=[{'dbm':{'ReasonCodes':closing}}],Reports=reports,Lineage=[])
        original=typed.save_image
        def late_failure(*args,**kwargs):
            item=original(*args,**kwargs)
            if args[1].startswith('report-facts/'):
                raise RuntimeError('late report input failure')
            return item
        with self.assertRaisesRegex(RuntimeError,'late report input failure'):
            with transaction.atomic(),patch.object(typed,'save_image',side_effect=late_failure):
                typed.save_daily(run,output)
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM mta_state.dbm_reasoncodes WHERE vf_run_id=%s',[run.pk])
            self.assertEqual(cursor.fetchone(),(0,))
        manifest=typed.save_daily(run,output)
        self.assertEqual(manifest['reports'][0]['sources'],manifest['reports'][1]['sources'])
        self.assertNotEqual(manifest['reports'][0]['sources']['ReasonCodes'],
                            manifest['closing']['dbm']['tables']['ReasonCodes'])
        self.accept_storage_fixture(run,{},manifest=manifest)
        expected=storage(typed.production_projection(output))
        for reader in (typed.read_daily,accepted_state_read.read_accepted_daily,_consumer_graph):
            self.assertEqual(storage(reader(run)),expected)
        receipt_integrity.audit_output(run)
        with connection.cursor() as cursor:
            cursor.execute('SELECT vf_image,count(*) FROM mta_state.dbm_reasoncodes '
                           'WHERE vf_run_id=%s GROUP BY vf_image ORDER BY vf_image',[run.pk])
            self.assertEqual(cursor.fetchall(),[('closing/dbm/ReasonCodes',2),
                ('report-facts/norm-change-export/ReasonCodes',600)])
        # An equal next run still owns a distinct payload; the local reuse map
        # cannot smuggle a cross-run or mutable phase reference into its graph.
        successor=self.new_run(predecessor=run,business_date=date(2026,7,11))
        next_manifest=typed.save_daily(successor,output)
        self.accept_storage_fixture(successor,{},manifest=next_manifest)
        self.assertEqual(storage(typed.read_daily(run)),expected)
        self.assertEqual(storage(accepted_state_read.read_accepted_daily(successor)),expected)

    def test_btr_import_commit_requires_exact_retained_sources_and_amounts(self):
        from copy import deepcopy
        from mta.runtime import btr_import_image, btr_import_relation as bpr
        from mta.runtime.rationing_reader import IMAGE
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.relational_state import save_image
        self.initialized_writer([])
        parent = self.new_run()
        first = [dict(SKUCode='S',WHCode='W',Stock=2,ReportDate=parent.business_date.isoformat())]
        anchor = save_image(parent,bpr.HISTORY,bpr.HISTORY,first)
        first_cut = write_day(parent,[])
        self.accept_storage_fixture(parent,first_cut,manifest=dict(version=3,images={IMAGE:first_cut,bpr.HISTORY:anchor}))
        run = self.new_run(predecessor=parent,business_date=date(2026,7,11))
        daily = save_image(run,bpr.DAILY,bpr.DAILY,[dict(SKUCode='S',WhCode='W',Stock=4)]*2)
        logical = first+[dict(first[0],Stock=4,ReportDate=run.business_date.isoformat())]*2
        cut = write_day(run,[])
        item = btr_import_image.save(run,logical,daily)
        manifest=dict(version=3,images={IMAGE:cut,bpr.HISTORY:item,bpr.DAILY:daily})
        for field,value in (('owner',str(parent.pk)),('count',1),('digest','0'*64)):
            wrong=deepcopy(manifest)
            wrong['images'][bpr.HISTORY]['sources']['daily'][0][field]=value
            self.denied(lambda:self.accept_storage_fixture(run,cut,manifest=wrong),'differs from its accepted sources')
        self.accept_storage_fixture(run,cut,manifest=manifest)
        self.assertEqual(btr_import_image.load(run,item,audit=True),logical)
        altered=deepcopy(item)
        altered['sources']['anchor']['owner']=str(run.pk)
        with self.assertRaisesRegex(ValueError,'sealed sources'):
            btr_import_image.load(run,altered,audit=False)

    def test_admitted_opening_order_survives_new_facts_and_audit(self):
        from tests.test_rationing_delta import row
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import load_image, read_cut, load_cut
        from mta.runtime.rationing_audit import audit_image
        original = dict(reversed(row('2026-07-09').items()))
        anchor = self.initialized_writer([original, original])
        old_rows = load_cut(read_cut(anchor.pk))
        self.assertEqual(list(old_rows[0]), list(original))
        run = self.new_run()
        after = [dict(old, Dispatch=7) for old in old_rows] + [row('2026-07-10')]
        item = write_day(run, after)
        self.accept_storage_fixture(run, item)
        self.assertEqual([f[0] for f in item['fields']], list(original))
        self.assertEqual(load_image(run, item), after)
        self.assertEqual(audit_image(run, item)['count'], 3)
        self.assertEqual(load_cut(read_cut(anchor.pk)), [original, original])

    def test_large_accepted_history_reopens_its_database_cursor_for_each_projection(self):
        from tests.test_rationing_delta import row
        from mta.row_sequences import RecordRows
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import load_image
        from mta.runtime.runtime_report_sources import image_rows
        from mta.runtime.rationing_reader import TABLE
        from django.test.utils import CaptureQueriesContext
        self.initialized_writer([])
        run = self.new_run()
        rows = [row('2026-07-10', GIT=n % 3) for n in range(10001)]
        item = write_day(run, rows)
        self.accept_storage_fixture(run, item)
        self.assertIsInstance(load_image(run, item), RecordRows)
        expected = digest([{'GIT': r['GIT'], 'Dispatch': None} for r in rows])
        with CaptureQueriesContext(connection) as queries:
            projected = image_rows(run, item, expected_table=TABLE, fields=('GIT', 'Dispatch'))
            for _ in range(2):
                with transaction.atomic():
                    self.assertEqual(digest(projected), expected)
        scans = [q for q in queries if 'FROM mta_state.rationing_lifetime L' in q['sql']]
        self.assertEqual(len(scans), 2)

    def test_daily_descriptor_cannot_invent_a_different_column_order(self):
        from unittest.mock import patch
        from tests.test_rationing_delta import row
        from mta.runtime import rationing_writer as writer
        self.initialized_writer([row('2026-07-09')])
        run = self.new_run()
        real = writer._seal
        def wrong_order(cut, **options):
            options['fields'] = list(reversed(options['fields']))
            return real(cut, **options)
        with self.assertRaisesMessage(DatabaseError, 'Operational commitment context differs'), transaction.atomic():
            with patch.object(writer, '_seal', side_effect=wrong_order):
                item = writer.write_day(run, [row('2026-07-09'), row('2026-07-10')])
            self.accept_storage_fixture(run, item)
        self.assertFalse(OperationalStateCut.objects.filter(run=run).exists())

    def test_writer_first_successor_expiry_and_historical_reads_exact(self):
        from copy import deepcopy
        from unittest.mock import patch
        from tests.test_rationing_delta import row
        from mta.domain.btr_rationing_history import collect, SOURCE_FIELDS
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import load_image
        from mta.runtime.rationing_audit import audit_image
        from django.test.utils import CaptureQueriesContext
        before = [row('2026-07-09'), row('2026-07-09'), row(None)]
        self.initialized_writer(before)
        old = deepcopy(before)
        accepted = []
        parent = None
        for day, git, receipts in [('2026-07-10', 14, 3), ('2026-07-11', 16, 1), ('2026-08-15', 20, 0)]:
            current = row(day, GIT=git)
            after = collect(day, before, [{name: current[name] for name in SOURCE_FIELDS}],
                [dict(SKUCode='S', WHCode='W', ReportDate=day, Receipts=receipts, Consumption=2)], [], 30)
            if not accepted:
                self.assertEqual([r['Dispatch'] for r in after[:2]], [7, 7])
            run = self.new_run(predecessor=parent, business_date=date.fromisoformat(day))
            with patch('mta.runtime.rationing_writer.summary') as observation:
                item = write_day(run, after)
            observation.assert_called_once()
            name = observation.call_args.args[0]
            work = observation.call_args.kwargs
            self.assertEqual(name, 'rationing_delta_work')
            self.assertEqual(work['logical_prior_rows'], len(before))
            self.assertEqual(work['logical_closing_rows'], len(after))
            self.assertEqual(work['inserted_facts'], 1)
            self.assertEqual(work['canonical_delta_hash_bytes'], work['canonical_readback_hash_bytes'])
            self.assertGreater(work['canonical_delta_hash_bytes'], 6)
            self.assertLess(work['root_bytes'], 32768)
            self.accept_storage_fixture(run, item)
            self.assertEqual(load_image(run, item), after)
            accepted.append((run, item, deepcopy(after)))
            before, parent = after, run
        for run, item, expected in accepted:
            self.assertEqual(load_image(run, item), expected)
            from mta.runtime.runtime_report_sources import image_rows
            for fields in [('Dispatch', 'SKUCode'), ('SKUCode',)]:
                with CaptureQueriesContext(connection) as capture:
                    rows = list(image_rows(run, item, expected_table='BTR/RationingHistory', fields=fields))
                self.assertEqual(rows, [{key: row[key] for key in fields} for row in expected])
                statements = [q['sql'] for q in capture if 'FROM mta_state.rationing_lifetime L' in q['sql']]
                self.assertEqual(len(statements), 1)
                self.assertNotIn('F."ParentWhName"', statements[0])
                self.assertEqual('JOIN LATERAL' in statements[0], 'Dispatch' in fields)
            with CaptureQueriesContext(connection) as queries:
                audited = audit_image(run, item)
            self.assertEqual(audited['count'], len(expected))
            self.assertEqual(audited['root_digest'], item['digest'])
            self.assertLessEqual(len(queries), 6)  # independent of prefix length
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM mta_state.rationing_fact')
            self.assertEqual(cursor.fetchone()[0], len(old)+3)
            cursor.execute('SELECT count(*) FROM mta_state.rationing_expiry')
            self.assertEqual(cursor.fetchone()[0], 4)

    def test_late_mismatch_rolls_back_written_batches_and_can_retry(self):
        from tests.test_rationing_delta import row
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import load_image
        self.initialized_writer([])
        run = self.new_run()
        after = [row('2026-07-10') for _ in range(501)]
        bad = after + [row('2026-07-09')]
        with self.assertRaisesMessage(ValueError, 'current producer'):
            write_day(run, bad)
        with connection.cursor() as cursor:
            cursor.execute('SELECT (SELECT count(*) FROM mta_state.rationing_fact),'
                           '(SELECT count(*) FROM mta_state.rationing_lifetime),'
                           '(SELECT count(*) FROM mta.fresh_mta_operationalstatecut)')
            self.assertEqual(cursor.fetchone(), (0, 0, 1))
        item = write_day(run, after)
        self.accept_storage_fixture(run, item)
        self.assertEqual(load_image(run, item), after)

    def test_disabled_capture_writes_only_bounded_cut_metadata(self):
        from unittest.mock import patch
        from tests.test_rationing_delta import row
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import read_cut, load_image
        self.profile['delivery']['btr_settings']['CaptureDispatchExecutionEfficiency'] = 0
        self.owner.configuration_digest = digest(self.profile)
        self.owner.save(update_fields=['configuration_digest'])
        before = [row('2026-07-09', Dispatch=-4), row(None)]
        self.initialized_writer(before)
        run = self.new_run()
        with patch('mta.runtime.rationing_writer.summary') as observation:
            item = write_day(run, before)
        work = observation.call_args.kwargs
        self.assertEqual(work['canonical_delta_hash_bytes'], 6)  # three empty arrays
        self.assertEqual(work['canonical_readback_hash_bytes'], 6)
        self.assertEqual([work[k] for k in ('inserted_facts', 'dispatch_revisions', 'expired_occurrences')], [0, 0, 0])
        self.accept_storage_fixture(run, item)
        cut = read_cut(item['cut_id'])
        self.assertEqual([cut.body[k] for k in ('inserted', 'revised', 'expired')], [0, 0, 0])
        self.assertEqual(load_image(run, item), before)
        with connection.cursor() as cursor:
            cursor.execute('SELECT (SELECT count(*) FROM mta_state.rationing_fact),'
                           '(SELECT count(*) FROM mta_state.rationing_dispatch),'
                           '(SELECT count(*) FROM mta_state.rationing_expiry)')
            self.assertEqual(cursor.fetchone(), (2, 0, 0))

    def test_persisted_value_mismatch_refuses_seal_and_rolls_back(self):
        from unittest.mock import patch
        from dataclasses import replace
        from tests.test_rationing_delta import row
        from mta.runtime import rationing_writer as writer
        self.initialized_writer([])
        run = self.new_run()
        original = writer._facts
        def corrupted(cut, rows):
            changed = [replace(e, values={**e.values, 'GIT': e.values['GIT']+1}) for e in rows]
            original(cut, changed)
        with patch.object(writer, '_facts', corrupted):
            with self.assertRaisesMessage(ValueError, 'persisted delta values/type/order differ'):
                writer.write_day(run, [row('2026-07-10')])
        with connection.cursor() as cursor:
            cursor.execute('SELECT (SELECT count(*) FROM mta_state.rationing_fact),'
                           '(SELECT count(*) FROM mta.fresh_mta_operationalstatecut)')
            self.assertEqual(cursor.fetchone(), (0, 1))

    def test_serving_role_cannot_write_operational_cut_or_delta_tables(self):
        with connection.cursor() as cursor:
            for table in ('mta.fresh_mta_operationalstatecut', 'mta_state.rationing_fact',
                          'mta_state.rationing_dispatch', 'mta_state.rationing_expiry',
                          'mta_state.rationing_lifetime'):
                for privilege in ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'):
                    cursor.execute('SELECT has_table_privilege(%s,%s,%s)',
                                   ['vectorflow_mta_runtime', table, privilege])
                    self.assertFalse(cursor.fetchone()[0], (table, privilege))

    def test_explicit_audit_empty_anchor_and_many_facts(self):
        from django.test.utils import CaptureQueriesContext
        from tests.test_rationing_delta import row
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import read_cut, load_image
        from mta.runtime.rationing_audit import audit_cut, audit_image
        cut = self.initialized_writer([])
        self.assertEqual(audit_cut(read_cut(cut.pk))['facts'], 0)
        run = self.new_run()
        after = [row('2026-07-10') for _ in range(1001)]
        item = write_day(run, after)
        self.accept_storage_fixture(run, item)
        with CaptureQueriesContext(connection) as queries:
            audited = audit_image(run, item)
        self.assertEqual((audited['cuts'], audited['facts'], audited['count']), (2, 1001, 1001))
        self.assertLessEqual(len(queries), 6)
        # The accepted path never invokes the full physical audit.
        from unittest.mock import patch
        with patch('mta.runtime.rationing_audit.audit_cut', side_effect=AssertionError('routine audit')):
            self.assertEqual(load_image(run, item), after)

    def test_explicit_audit_detects_corrupt_fact_despite_valid_header(self):
        from unittest.mock import patch
        from dataclasses import replace
        from tests.test_rationing_delta import row
        from mta.runtime import rationing_writer as writer
        from mta.runtime.rationing_audit import audit_image
        self.initialized_writer([])
        run = self.new_run()
        facts, seal = writer._facts, writer._seal
        def corrupt(cut, events):
            facts(cut, [replace(e, values={**e.values, 'GIT': e.values['GIT']+1}) for e in events])
        def faulty_verifier(cut, **kwargs):
            # Deliberate isolated producer-verifier fault. All DB guards stay
            # enabled; an independent audit must not trust writer hash claims.
            with patch.object(writer, '_stored_digests', return_value=kwargs['checks']):
                return seal(cut, **kwargs)
        with patch.object(writer, '_facts', corrupt), patch.object(writer, '_seal', faulty_verifier):
            item = writer.write_day(run, [row('2026-07-10')])
        self.accept_storage_fixture(run, item)
        with self.assertRaisesMessage(ValueError, 'audit facts values/type/order differ'):
            audit_image(run, item)
        from mta.runtime.state_image_read import load_image
        with self.assertRaisesMessage(ValueError, 'audit facts values/type/order differ'):
            load_image(run, item)
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_explicit_audit_detects_corrupt_dispatch(self):
        from unittest.mock import patch
        from dataclasses import replace
        from tests.test_rationing_delta import row
        from mta.domain.btr_rationing_history import collect, SOURCE_FIELDS
        from mta.runtime import rationing_writer as writer
        from mta.runtime.rationing_delta import DispatchRevision
        from mta.runtime.rationing_audit import audit_image
        before = [row('2026-07-09')]
        self.initialized_writer(before)
        run = self.new_run()
        current = row('2026-07-10', GIT=14)
        after = collect('2026-07-10', before, [{k: current[k] for k in SOURCE_FIELDS}],
            [dict(SKUCode='S', WHCode='W', ReportDate='2026-07-10', Receipts=3, Consumption=2)], [], 30)
        flush, seal = writer._flush, writer._seal
        def corrupt(cut, events):
            flush(cut, [replace(e, dispatch=e.dispatch+1) if type(e) is DispatchRevision else e for e in events])
        def faulty_verifier(cut, **kwargs):
            with patch.object(writer, '_stored_digests', return_value=kwargs['checks']):
                return seal(cut, **kwargs)
        with patch.object(writer, '_flush', corrupt), patch.object(writer, '_seal', faulty_verifier):
            item = writer.write_day(run, after)
        self.accept_storage_fixture(run, item)
        with self.assertRaisesMessage(ValueError, 'audit revisions values/type/order differ'):
            audit_image(run, item)

    def test_old_new_reader_dispatch_preserves_exact_values_and_refuses_foreign_formats(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from tests.test_rationing_delta import row
        from mta.runtime import accepted_state_read, relational_state, state_image_read
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import IMAGE, TABLE
        self.initialized_writer([])
        run = self.new_run()
        rows = [row('2026-07-10'), row('2026-07-10')]
        legacy = relational_state.save_image(run, IMAGE, IMAGE, rows)
        item = write_day(run, rows)
        self.accept_storage_fixture(run, item)
        for metadata in (legacy, item):
            self.assertEqual(state_image_read.load_image(run, metadata), rows)
            self.assertEqual(list(state_image_read.iter_image(run, metadata)), rows)
            with patch('mta.runtime.rationing_audit.audit_cut', side_effect=AssertionError('routine audit')):
                self.assertEqual(accepted_state_read.load_accepted_image(run, metadata), rows)
                self.assertEqual(list(accepted_state_read.iter_accepted_image(run, metadata)), rows)
        for read in (state_image_read.load_image, accepted_state_read.load_accepted_image):
            for invalid in ({**item, 'storage_format': 'unknown-v9'},
                            {k: v for k, v in item.items() if k != 'storage_format'},
                            {**item, 'image': 'foreign'},
                            {**item, 'digest': '0'*64}, {**item, 'count': 1}):
                with self.subTest(read=read.__name__, invalid=invalid), self.assertRaises(ValueError):
                    read(run, invalid)
            with self.assertRaisesMessage(ValueError, 'Unknown operational table'):
                read(run, item, table_registry={})
            with self.assertRaisesMessage(ValueError, 'exact accepted run/cut'):
                read(SimpleNamespace(pk=uuid.uuid4()), item)
        self.assertEqual(item['table'], TABLE)

    def test_daily_storage_integration_reuses_frozen_profile_and_serves_typed_projection(self):
        from unittest.mock import patch
        from tests.test_rationing_delta import row
        from mta.runtime import relational_state, accepted_state_read, runtime_report_sources, receipt_integrity
        from mta.runtime.input_reader import read_execution_input
        from mta.runtime.rationing_reader import IMAGE, TABLE
        self.initialized_writer([])
        run = self.new_run()
        rows = [row('2026-07-10'), row('2026-07-10')]
        output = dict(ClosingState=[dict(dbm={}, btr={'RationingHistory': rows})], Lineage=[])
        frozen = read_execution_input(run, components=('profile', 'execution_settings', 'initialization_binding'))
        profile_digest = digest(frozen['profile'])
        with patch('mta.runtime.input_reader.read_execution_input', side_effect=AssertionError('extra profile read')):
            manifest = relational_state.save_daily(run, output, frozen=frozen, profile_digest=profile_digest)
        manifest['version'] = 3
        item = manifest['images'][IMAGE]
        self.assertEqual(item['storage_format'], 'rationing-occurrences-v1')
        self.accept_storage_fixture(run, item, manifest=manifest)
        self.assertEqual(relational_state.read_daily(run, include_reports=False)['BTRFinal'][0]['RationingHistory'], rows)
        self.assertEqual(accepted_state_read.read_accepted_daily(run, include_reports=False)['BTRFinal'][0]['RationingHistory'], rows)
        # The public diagnostic owner must dispatch too; testing only its
        # lower-level reader does not qualify whole-output audits.
        receipt_integrity.audit_output(run)
        with patch('mta.runtime.state_image_read.audit_cut', side_effect=ValueError('physical audit refusal')):
            with self.assertRaisesMessage(ValueError, 'physical audit refusal'):
                receipt_integrity.audit_output(run)
        with patch('mta.runtime.rationing_audit.audit_cut', side_effect=AssertionError('routine prefix audit')):
            projected = runtime_report_sources.image_rows(run, item, expected_table=TABLE,
                fields=('SKUCode', 'ReportDate', 'Dispatch'))
            self.assertEqual(list(projected), [dict(SKUCode='S', ReportDate=date(2026, 7, 10), Dispatch=None)]*2)
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM mta_state.btr_rationinghistory WHERE vf_run_id=%s', [run.pk])
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_prior_cursor_expiry_flush_rolls_back_and_preserves_parent(self):
        from tests.test_rationing_delta import row
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import read_cut, iter_occurrences, load_image
        before = [row('2026-07-09') for _ in range(501)]
        anchor = self.initialized_writer(before)
        run = self.new_run(business_date=date(2026, 8, 15))
        with self.assertRaisesMessage(ValueError, 'current producer'):
            write_day(run, [row('2026-08-14')])
        self.assertEqual([r for _, r in iter_occurrences(read_cut(anchor.pk))], before)
        with connection.cursor() as cursor:
            cursor.execute('SELECT (SELECT count(*) FROM mta_state.rationing_expiry),'
                           '(SELECT count(*) FROM mta_state.rationing_lifetime WHERE end_position IS NOT NULL)')
            self.assertEqual(cursor.fetchone(), (0, 0))
        after = [row('2026-08-15')]
        item = write_day(run, after)
        self.accept_storage_fixture(run, item)
        self.assertEqual(load_image(run, item), after)
        self.assertEqual([r for _, r in iter_occurrences(read_cut(anchor.pk))], before)

    def test_prior_cursor_revision_flush_rolls_back_and_preserves_parent(self):
        from copy import deepcopy
        from tests.test_rationing_delta import row
        from mta.domain.btr_rationing_history import collect, SOURCE_FIELDS
        from mta.runtime.rationing_writer import write_day
        from mta.runtime.rationing_reader import read_cut, iter_occurrences, load_image
        before = [row('2026-07-09') for _ in range(501)]
        anchor = self.initialized_writer(before)
        current = row('2026-07-10', GIT=14)
        after = collect('2026-07-10', before, [{k: current[k] for k in SOURCE_FIELDS}],
            [dict(SKUCode='S', WHCode='W', ReportDate='2026-07-10', Receipts=3, Consumption=2)], [], 30)
        self.assertEqual([r['Dispatch'] for r in after[:501]], [7]*501)
        bad = deepcopy(after)
        bad[500]['GIT'] += 1
        run = self.new_run()
        with self.assertRaisesMessage(ValueError, 'immutable values/type/order differ'):
            write_day(run, bad)
        self.assertEqual([r for _, r in iter_occurrences(read_cut(anchor.pk))], before)
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM mta_state.rationing_dispatch')
            self.assertEqual(cursor.fetchone()[0], 0)
        item = write_day(run, after)
        self.accept_storage_fixture(run, item)
        self.assertEqual(load_image(run, item), after)
        self.assertEqual([r for _, r in iter_occurrences(read_cut(anchor.pk))], before)

    def test_declared_population_mismatch_rolls_back(self):
        from tests.test_rationing_delta import row
        from mta.row_sequences import RecordRows
        from mta.runtime.rationing_writer import write_day
        self.initialized_writer([])
        run = self.new_run()
        with self.assertRaisesMessage(ValueError, 'History factory population drift'):
            write_day(run, RecordRows(2, lambda: iter([row('2026-07-10')])))
        self.assertEqual(OperationalStateCut.objects.count(), 1)

    def test_database_failure_after_flush_leaves_same_connection_usable(self):
        from unittest.mock import patch
        from tests.test_rationing_delta import row
        from mta.runtime import rationing_writer as writer
        from mta.runtime.rationing_reader import read_cut, iter_occurrences
        # Second flush happens while the named prior cursor still has one
        # unread occurrence, so cleanup also runs in an aborted SQL TX.
        before = [row('2026-07-09') for _ in range(1001)]
        anchor = self.initialized_writer(before)
        run = self.new_run()
        after = [{**r, 'Dispatch': 7} for r in before] + [row('2026-07-10')]
        flush = writer._flush
        calls = 0
        def fail_second(cut, events):
            nonlocal calls
            calls += 1
            if calls == 2:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT 1/0')
            flush(cut, events)
        with patch.object(writer, '_flush', fail_second):
            with self.assertRaisesMessage(DatabaseError, 'division by zero'):
                writer.write_day(run, after)
        self.assertEqual(calls, 2)
        self.assertEqual([r for _, r in iter_occurrences(read_cut(anchor.pk))], before)
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM mta_state.rationing_dispatch')
            self.assertEqual(cursor.fetchone()[0], 0)
        item = writer.write_day(run, after)
        self.accept_storage_fixture(run, item)
