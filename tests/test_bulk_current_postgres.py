"""Owned SQL current-writer equivalence, guards and rollback; no day replay."""
import os
import unittest
from copy import deepcopy
from datetime import date
from decimal import Decimal


def fixture_rows(model, count=1003):
    from mta.mdm.master_owners import business_fields, typed
    row = {}
    for field in business_fields(model):
        kind = field.get_internal_type()
        row[field.name] = (None if field.null else Decimal('1').quantize(Decimal(1).scaleb(-field.decimal_places))
            if kind == 'DecimalField' else 1 if 'IntegerField' in kind else
            False if kind == 'BooleanField' else date(2026, 4, 8) if kind == 'DateField' else 'S')
    return typed(model, [dict(row) for _ in range(count)])


@unittest.skipUnless(os.environ.get('VF_BULK_CURRENT_PROOF') == '1', 'Explicit owned current-writer SQL proof required')
class BulkCurrentPostgresTests(unittest.TestCase):
    def test_occurrences_types_guards_and_late_rollback(self):
        from django.db import connection, transaction, DatabaseError
        from django.utils import timezone
        from mta.mdm import daily_current as writer
        from mta.mdm.master_owners import business_fields, typed
        from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent as Model
        from mta.runtime.mdm_models import MdmSource
        from mta.runtime.models import CalculationRun
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        from mta.mdm.daily_source import SCHEMA, APPROVAL_DAY_ARTIFACT_SHA
        from mta.serialization import storage
        self.assertEqual(connection.settings_dict['NAME'], 'vf_minimum_closeout_20261022')
        with connection.cursor() as cursor:
            cursor.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(cursor.fetchone()[0], 'owned Section11 minimum closeout thread01a16058 20261022; synthetic only')

        def guc(name, value):
            with connection.cursor() as cursor:
                cursor.execute('SELECT set_config(%s,%s,true)', [name, value])

        names = [f.name for f in business_fields(Model)]
        def read(source):
            records = list(Model.objects.filter(source=source, owner='Importer').order_by('ordinal')
                           .values('pk', 'ordinal', *names))
            return records

        with transaction.atomic():
            source = MdmSource.objects.create(digest='c'*64, dll_digest='c'*64,
                database_name='synthetic-current-edge-proof',
                receipt={'schema': SCHEMA, 'artifact_sha256': APPROVAL_DAY_ARTIFACT_SHA})
            rows = fixture_rows(Model)
            guc('fresh.mdm_current_bootstrap', str(source.pk))
            Model.objects.bulk_create([Model(source=source, owner='Importer', ordinal=i+1, **r)
                for i,r in enumerate(rows)], batch_size=500)
            guc('fresh.mdm_current_bootstrap', '')
            before = read(source)
            run = CalculationRun.objects.create(kind='DAILY_CHAIN', business_date='2026-04-08',
                input_digest='synthetic-current-edges', execution_revision='synthetic-current-edges', input_payload={}, status='RUNNING')
            capture = MdmDailyInputCapture.objects.create(run=run,source=source, request_digest='c'*64,
                revision_digest='c'*64,sku_revision_digest='c'*64,location_revision_digest='c'*64,
                skuloc_revision_digest='c'*64,sql_digest='c'*64,nms_active=True)
            guc('fresh.mdm_consuming_run',str(run.pk))
            capture.status='CONSUMED';capture.consumed_at=timezone.now()
            capture.save(update_fields=['status','consumed_at'])
            guc('fresh.mdm_current_run',str(run.pk))
            target = deepcopy(rows)
            for i,r in enumerate(target):
                if i % 5: r['Norm'] = 2
                if i % 3: r['SKUDescription'] = 'typed change'
            decimal_field = next(f for f in business_fields(Model) if f.get_internal_type() == 'DecimalField')
            target[1][decimal_field.name] = Decimal('2').quantize(Decimal(1).scaleb(-decimal_field.decimal_places))
            target.append(dict(target[0]))  # Duplicate business key, new occurrence.
            frozen = deepcopy(target)
            self.assertEqual(writer._write_partition(source,Model,{'owner':'Importer'},target,'/synthetic/edges'),
                {'updated':936,'inserted':1,'deleted':0})
            after = read(source)
            self.assertEqual([r['pk'] for r in after[:1003]], [r['pk'] for r in before])
            self.assertEqual([r['ordinal'] for r in after], list(range(1,1005)))
            self.assertEqual(storage([{n:r[n] for n in names} for r in after]),storage(target))
            self.assertEqual(target,frozen)
            self.assertEqual(writer._write_partition(source,Model,{'owner':'Importer'},target,'/synthetic/equal'),
                {'updated':0,'inserted':0,'deleted':0})
            short = target[:-2]
            writer._write_partition(source,Model,{'owner':'Importer'},short,'/synthetic/shrink')
            self.assertEqual([r['pk'] for r in read(source)], [r['pk'] for r in after[:len(short)]])
            stable = read(source)
            with self.assertRaisesRegex(RuntimeError, 'late injected failure'), transaction.atomic():
                changed=deepcopy(short)
                for r in changed:r['Norm']=3
                writer._write_partition(source,Model,{'owner':'Importer'},changed,'/synthetic/late')
                raise RuntimeError('late injected failure')
            self.assertEqual(read(source),stable)
            with self.assertRaises(DatabaseError),transaction.atomic():
                bad=deepcopy(short);bad[-1]['Norm']=2147483648
                writer._write_partition(source,Model,{'owner':'Importer'},bad,'/synthetic/overflow')
            self.assertEqual(read(source),stable)
            guc('fresh.mdm_current_run','foreign')
            with self.assertRaises(DatabaseError),transaction.atomic():
                bad=deepcopy(short);bad[0]['Norm']=7
                writer._write_partition(source,Model,{'owner':'Importer'},bad,'/synthetic/denied')
            self.assertEqual(read(source),stable)
            # Validate the same typed projection boundary used by publish before
            # DML; PostgreSQL casts are not a substitute for precision checks.
            from django.core.exceptions import ValidationError
            bad=deepcopy(short[:1])
            bad[0][decimal_field.name]=Decimal('1').scaleb(-(decimal_field.decimal_places+1))
            with self.assertRaises((ValueError,ValidationError)):
                typed(Model,bad)
            guc('fresh.mdm_current_run',str(run.pk))
            with self.assertRaises(DatabaseError),transaction.atomic():
                Model.objects.filter(source=source).update(ordinal=99)
            self.assertEqual(read(source),stable)
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) UPDATE '+connection.ops.quote_name(Model._meta.db_table)+
                        ' SET "Norm"="Norm" WHERE source_id=%s AND ordinal<=500',[source.pk])
                    plan=cursor.fetchone()[0]
                if os.environ.get('VF_BULK_CURRENT_PROOF_OUTPUT'):
                    import json
                    from pathlib import Path
                    Path(os.environ['VF_BULK_CURRENT_PROOF_OUTPUT']).write_text(json.dumps(plan,indent=2))
                transaction.set_rollback(True)
            self.assertEqual(read(source),stable)
            transaction.set_rollback(True)
        self.assertFalse(MdmSource.objects.filter(database_name='synthetic-current-edge-proof').exists())
