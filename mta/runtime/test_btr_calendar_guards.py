"""Dated report ownership on a migrated PostgreSQL database."""
from copy import deepcopy
from datetime import date, timedelta

from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from mta.presentation.btr_calendar_sources import DAILY, HISTORY, OPERANDS, advance
from mta.runtime.models import CalculationRun, DailyReportGeneration
from mta.serialization import digest


class BtrDirectoryGuardTests(TestCase):
    def test_sparse_store_recovers_nonnull_values_and_rejects_late_divergence(self):
        from mta.presentation import btr_calendar_images as calendar
        from mta.runtime import relational_state as typed
        day = date(2026, 4, 8)
        run = CalculationRun.objects.create(kind='DAILY_CHAIN', status='RUNNING', input_payload={},
            execution_revision='dated-roster', input_digest=digest(day), business_date=day, evidence_mode='production')
        raw = dict(SKUCode='S', WHCode='L', ReportDate=day.isoformat())
        raw.update({key: ('7.50' if key.endswith('Pen') else 'Green') for key in OPERANDS})
        history = typed.save_image(run, HISTORY, HISTORY, [raw, dict(raw, WHCode=None, PhysicalInventoryPen='3.00')])
        run.production_manifest = dict(version=3, images={HISTORY: history})
        run.production_digest = digest(run.production_manifest)
        run.status = 'SUCCEEDED'
        run.save(update_fields=['status', 'production_digest', 'production_manifest'])
        row = self.start(run, 2)
        directory = advance(run)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.report_generation',%s,true)", [str(run.pk)])
        # The same current key can occur more than once in the report roster.
        roster = [dict(SKUCode='S', WhCode='L', D1=None, D90='7.50')]*2
        roster.append(dict(roster[0], WhCode=None, D90='3.00'))
        item = calendar.save(run, directory, 'BPPTrendPhysicalInv', roster)
        self.assertEqual(calendar.load(run, directory, item), roster)
        with connection.cursor() as cursor:
            cursor.execute('SELECT "D90" FROM '+typed.table_sql(item['table'])+
                           ' WHERE vf_run_id=%s AND vf_image=%s', [run.pk, item['image']])
            self.assertEqual(cursor.fetchall(), [(None,)]*3)
        with self.assertRaisesMessage(ValueError, 'logical image differs'), transaction.atomic():
            calendar.save(run, directory, 'BPPTrendDispatch', [dict(roster[0], D90='8.00')])
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM '+typed.table_sql('BTR/BPPTrendDispatch')+
                           ' WHERE vf_run_id=%s', [run.pk])
            self.assertEqual(cursor.fetchone(), (0,))
        self.seal(row, directory)

    def create_run(self, day, predecessor=None):
        fields = [[name, name, 'str'] for name in OPERANDS]
        images = {path: dict(image=path, table=table, fields=fields, count=1, digest=digest([day, path]))
                  for path, table in ((DAILY, 'BPR/vf_RationedReqReport'), (HISTORY, 'BTR/BPR'))}
        manifest = dict(version=3, images=images)
        return CalculationRun.objects.create(kind='DAILY_CHAIN', status='SUCCEEDED', input_payload={},
            execution_revision='dated-guard', input_digest=digest(day), business_date=day, predecessor=predecessor,
            evidence_mode='production', production_manifest=manifest, production_digest=digest(manifest))

    def start(self, run, version):
        return DailyReportGeneration.objects.create(run=run, version=version, source_digest=run.production_digest,
                                                  recipe_digest='a'*64)

    def seal(self, row, directory):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.report_generation',%s,true)", [str(row.pk)])
        metadata = dict(schema='fresh-derived-report-generation-v' + str(row.version))
        if directory is not None:
            metadata['btr_calendar'] = directory
        DailyReportGeneration.objects.filter(pk=row.pk).update(
            metadata=metadata, digest=digest(metadata), status='READY', sealed_at=timezone.now())

    def test_first_successor_and_expiry_require_exact_owned_sources(self):
        old = self.create_run(date(2026, 4, 7))
        self.seal(self.start(old, 1), None)
        first = self.create_run(old.business_date + timedelta(days=1), old)
        anchor = advance(first)
        self.seal(self.start(first, 2), anchor)
        second = self.create_run(first.business_date + timedelta(days=1), first)
        current = self.start(second, 2)
        directory = advance(second, predecessor=first, directory=anchor)
        for wrong in (advance(second), {**directory, 'anchor': None},
                      {**directory, 'daily': directory['daily'] * 2}):
            with self.assertRaisesMessage(DatabaseError, 'source lineage'), transaction.atomic():
                self.seal(current, wrong)
        for field in ('source','wire','run','day'):
            wrong = deepcopy(directory)
            wrong['daily'][0][field] = directory['anchor'][field] if field != 'wire' else ['int']*8
            with self.assertRaisesMessage(DatabaseError, 'source lineage'), transaction.atomic():
                self.seal(current, wrong)
        self.seal(current, directory)
        late = self.create_run(first.business_date + timedelta(days=90), second)
        window = advance(late, predecessor=second, directory=directory)
        self.assertIsNone(window['anchor'])
        self.assertEqual([b['run'] for b in window['daily']], [str(second.pk), str(late.pk)])
        self.seal(self.start(late, 2), window)
        self.assertEqual(DailyReportGeneration.objects.get(pk=first.pk).metadata['btr_calendar'], anchor)

    def test_unsealed_parent_cannot_be_replaced_by_a_new_anchor(self):
        first = self.create_run(date(2026, 4, 8))
        self.start(first, 2)
        second = self.create_run(first.business_date + timedelta(days=1), first)
        with self.assertRaisesMessage(DatabaseError, 'sealed earlier predecessor'), transaction.atomic():
            self.seal(self.start(second, 2), advance(second))
