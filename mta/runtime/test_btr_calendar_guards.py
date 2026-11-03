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
    def test_compact_generation_seals_only_direct_local_references_and_own_calendar(self):
        from mta.presentation import btr_snapshot_storage as snapshot
        previous = self.create_run(date(2026, 4, 8))
        prior = advance(previous)
        self.seal(self.start(previous, 2), prior)
        run = self.create_run(date(2026, 4, 9), previous)
        row = self.start(run, 3)
        current = advance(run, predecessor=previous, directory=prior)
        def seal(item, calendar):
            metadata = dict(schema='fresh-derived-report-generation-v3', btr_calendar=calendar,
                            images={snapshot.PATH: item})
            DailyReportGeneration.objects.filter(pk=row.pk).update(
                metadata=metadata, digest=digest(metadata), status='READY', sealed_at=timezone.now())
        with connection.cursor() as c:
            c.execute("SELECT set_config('fresh.report_generation',%s,true)", [str(run.pk)])
            item = snapshot.save(run, [dict.fromkeys(snapshot.XML, 'a')]*2)
            with self.assertRaisesMessage(DatabaseError, 'owner, count or ordinal'), transaction.atomic():
                seal(dict(item, reuse_before=0), current)
            with self.assertRaisesMessage(DatabaseError, 'source lineage'), transaction.atomic():
                seal(item, advance(run))
            with self.assertRaisesMessage(DatabaseError, 'owner, count or ordinal'), transaction.atomic():
                c.execute('INSERT INTO mta_state.btr_btrsnapshotforui '
                          '(vf_run_id,vf_image,vf_ordinal,vf_xml_ordinal) VALUES (%s,%s,2,1)',
                          [run.pk, snapshot.PATH])
                seal(dict(item, count=3), current)
            seal(item, current)
            with self.assertRaises(DatabaseError), transaction.atomic():
                c.execute('INSERT INTO mta_state.btr_btrsnapshotforui '
                          '(vf_run_id,vf_image,vf_ordinal,vf_xml_ordinal) VALUES (%s,%s,2,0)',
                          [run.pk, snapshot.PATH])
            self.assertEqual(len(list(snapshot.verified_rows(run, item))), 2)

    def test_snapshot_xml_ordinal_roundtrip_and_prior_recipe_refusal(self):
        from unittest.mock import patch
        from mta.presentation import btr_snapshot_storage as snapshot
        run = self.create_run(date(2026, 4, 8))
        generation = self.start(run, 2)
        rows = [dict(SKUCode=str(i), **dict.fromkeys(snapshot.XML, value))
                for i, value in enumerate(('<X/>', '<X/>', '', '<X/>', '', '<X D1="9"/>'))]
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.report_generation',%s,true)", [str(run.pk)])
        with patch.object(snapshot, 'MAX_ENTRIES', 1):
            item = snapshot.save(run, rows)
            self.assertEqual(item['reuse_before'], 2)
            self.assertEqual(snapshot.load(run, item), rows)
        relation, bindings = snapshot.relation(run, item)
        with connection.cursor() as cursor:
            cursor.execute('SELECT vf_xml_ordinal,"BPPTech" FROM mta_state.btr_btrsnapshotforui '
                           'WHERE vf_run_id=%s ORDER BY vf_ordinal', [run.pk])
            self.assertEqual(cursor.fetchall(), [(0,'<X/>'), (0,None), (2,''), (0,None), (4,''), (5,'<X D1="9"/>')])
            cursor.execute('SELECT vf_ordinal FROM ('+relation+') x WHERE "BPPTech"=%s ORDER BY 1',
                           bindings + ['<X/>'])
            self.assertEqual(cursor.fetchall(), [(0,), (1,), (3,)])
        with self.assertRaisesMessage(ValueError, 'logical image differs'):
            list(snapshot.verified_rows(run, dict(item, digest='a'*64)))
        with self.assertRaisesMessage(DatabaseError, 'compatible report generation'), transaction.atomic():
            self.seal(generation, advance(run))

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
