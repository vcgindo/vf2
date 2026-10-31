"""Typed operand preservation and transaction lifetime on an owned proof DB."""
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4


@unittest.skipUnless(os.environ.get('VF_BTR_OPERAND_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class BtrSnapshotOperandTests(unittest.TestCase):
    def setUp(self):
        from django.db import connection
        self.assertEqual(connection.settings_dict['NAME'], 'vftest_fresh_btr_cursor_20261031')
        with connection.cursor() as cursor:
            cursor.execute("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()")
            self.assertEqual(cursor.fetchone()[0], 'owned 8092 BTR cursor reproduction 20261031; copied typed operands only; not business certification')

    @contextmanager
    def fixture(self):
        from django.db import connection, transaction
        from mta.presentation import btr_snapshot as snapshot
        reference = SimpleNamespace(pk=uuid4())
        source_sql = ("SELECT * FROM (VALUES (9::bigint,'A'::text,'X'::text,1.25::numeric(12,4),DATE '2026-04-08',true),"
                      "(2::bigint,'A'::text,'X'::text,NULL::numeric(12,4),NULL::date,false),"
                      "(15::bigint,NULL::text,NULL::text,-2.5::numeric(12,4),DATE '2026-04-09',NULL::boolean))"
                      ' s(vf_ordinal,"SKUCode","WhCode",value,day,flag)')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout='60s'; SET LOCAL work_mem='32MB'")
                cursor.execute('CREATE TEMP TABLE operand_reference_fixture '
                    '(id bigint,generation_id uuid,branch text,export boolean,payload numeric(12,4)) ON COMMIT DROP')
                cursor.executemany('INSERT INTO operand_reference_fixture VALUES (%s,%s,%s,%s,%s)',
                    [(7,reference.pk,'tech',False,Decimal('1.25')),
                     (3,reference.pk,'tech',False,None), (12,reference.pk,'eco',False,Decimal('-2.5')),
                     (20,reference.pk,'tech',True,Decimal('99')), (21,uuid4(),'tech',False,Decimal('88'))])
            with patch.object(snapshot.btr_reporting, 'REF_TABLE', 'pg_temp.operand_reference_fixture'), \
                    patch.object(snapshot, 'image_query', return_value=(source_sql, [])):
                yield snapshot, reference

    def tables(self):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT relname FROM pg_class WHERE relnamespace=pg_my_temp_schema() "
                "AND relkind='r' AND relname LIKE 'vf_btr_snapshot_%%'")
            return cursor.fetchall()

    def test_complete_types_nulls_duplicate_business_keys_order_and_commit_cleanup(self):
        from django.db import connection
        with self.fixture() as (snapshot, reference):
            operands = snapshot._source_operands(SimpleNamespace(pk=uuid4()), reference, SimpleNamespace(pk=uuid4()))
            self.assertEqual(len(operands['sources']), 11)
            with connection.cursor() as cursor:
                cursor.execute('SELECT id,payload FROM ' + operands['reference'] + ' ORDER BY id')
                self.assertEqual(cursor.fetchall(), [(3,None),(7,Decimal('1.2500')),(12,Decimal('-2.5000'))])
                for table in operands['sources'].values():
                    cursor.execute('SELECT * FROM ' + table + ' ORDER BY vf_ordinal')
                    self.assertEqual(cursor.fetchall(), [(2,'A','X',None,None,False),
                        (9,'A','X',Decimal('1.2500'),date(2026,4,8),True),
                        (15,None,None,Decimal('-2.5000'),date(2026,4,9),None)])
                cursor.execute("SELECT current_setting('statement_timeout'),current_setting('work_mem')")
                self.assertEqual(cursor.fetchone(), ('1min','32MB'))
        self.assertEqual(self.tables(), [])

    def test_failure_rollback_and_same_connection_new_attempt(self):
        from django.db import transaction
        class Interrupted(Exception): pass
        with self.fixture() as (snapshot, reference):
            with self.assertRaises(Interrupted), transaction.atomic():
                snapshot._source_operands(SimpleNamespace(pk=uuid4()), reference, SimpleNamespace(pk=uuid4()))
                self.assertEqual(len(self.tables()), 12)
                raise Interrupted('after all operands were created')
            self.assertEqual(self.tables(), [])
            snapshot._source_operands(SimpleNamespace(pk=uuid4()), reference, SimpleNamespace(pk=uuid4()))
            self.assertEqual(len(self.tables()), 12)
        self.assertEqual(self.tables(), [])
