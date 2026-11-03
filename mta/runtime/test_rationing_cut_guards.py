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
    def tearDown(self):
        # Several cases intentionally leave pending cuts to test their refusal.
        # Every test transaction is discarded, never an application commit.
        transaction.set_rollback(True)

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS state_cut_complete DEFERRED')
        self.profile = {'delivery': {'site_code': 'IR1-GUARD'}}
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

    def new_run(self, ref=None, *, raw_change=None, predecessor=None):
        raw = dict(profile=self.profile, initialization_binding=dict(id=str(self.owner.pk),
            configuration_digest=self.owner.configuration_digest))
        if ref is not None:
            raw['execution_settings'] = ref
        if raw_change:
            raw_change(raw)
        run = CalculationRun.objects.create(input_digest=digest(raw), input_payload={},
            execution_revision=str(uuid.uuid4()), kind='DAILY_CHAIN', status='RUNNING',
            business_date=date(2026, 7, 10), predecessor=predecessor)
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
