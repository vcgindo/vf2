"""Retained suspension transitions through sealed and PostgreSQL row readers."""
from copy import deepcopy
import os
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from mta.domain import dbm_suspensions as service
from mta.row_sequences import RecordRows
from mta.serialization import digest
from tests.test_dbm_owned_memory import state as control_state
from tests import test_dbm_state_scan_indexes as scan_cases

TODAY = '2026-06-06'


def values(value):
    if isinstance(value, dict):
        return {key: values(item) for key, item in value.items()}
    if isinstance(value, (list, RecordRows)):
        return [values(item) for item in value]
    return value


def typed(value):
    if isinstance(value, dict):
        return [(key, typed(item)) for key, item in value.items()]
    if isinstance(value, (list, RecordRows)):
        return [typed(item) for item in value]
    return type(value).__name__, repr(value)


def cases():
    """Release, retain, replace and insert with duplicate and NULL records."""
    def base():
        return dict(
            LastBatchRunTbl=[dict(LastRunDate=TODAY + 'T00:00:00')],
            DBMMaster=[dict(SKUCode=k, WhCode='W', Norm=9, RLT=2) for k in ('A', 'B', 'C')],
            DailyConsumption=[dict(SKUCode=k, WhCode='W', ReportDate=TODAY,
                                   Receipts=receipts, Stock=stock, Consumption=consumption, BlueZone=0)
                              for k, receipts, stock, consumption in
                              [('A', 0, 0, 4), ('B', 3, 0, 0), ('C', 0, 9, 0)]],
            IntermediateTables=[dict(table='scratch', rows=[dict(v=1)])])
    state = base()
    state['DailyConsumption'][0]['Stock'] = 20
    state['DailyConsumption'].insert(0, deepcopy(state['DailyConsumption'][0]))
    state['SuspendWhitesTbl'] = [dict(SKUCode=k, WhCode='W', IsRedEnabled=flag)
                                for k, flag in [('B', False), ('B', False), ('A', False), (None, None)]]
    yield 'apply_white', state, 'SuspendWhitesTbl'
    state = base()
    state['DailyConsumption'][2]['Receipts'] = None
    state['SuspendSpikeTbl'] = [dict(SKUCode=k, WhCode='W', WaitStartDate='2026-06-05',
                                     WaitTillDate=None, IsRedEnabled=False, IsGreenEnabled=True)
                               for k in ('B', 'B', 'A', 'C')]
    yield 'apply_spike', state, 'SuspendSpikeTbl'
    state = base()
    state['SuspendSupplyIssueTbl'] = [dict(SKUCode=k, WhCode='W', SuspendDate='2026-06-05',
                                           ReceiptDate=receipt, IsRedEnabled=False)
                                     for k, receipt in [('B', None), ('B', None), ('A', None),
                                                        ('C', '2026-06-05'), ('D', None)]]
    yield 'apply_supply', state, 'SuspendSupplyIssueTbl'
    state = control_state()
    state['DailyConsumption'] = [dict(SKUCode='S', WhCode='W', ReportDate=TODAY, Receipts=1)]
    state['SuspendExistingDisabledNormsTbl'] = [dict(SKUCode='S', WhCode='W',
        WaitTillDate='2026-06-05', WaitForReceipt=False, IsRedEnabled=False, IsGreenEnabled=False)] * 2
    yield 'apply_existing_disabled', state, 'SuspendExistingDisabledNormsTbl'
    state = control_state()
    state['SuspendNormsInSleepModeTbl'] = [dict(SKUCode='old', WhCode='W',
        WaitStartDate='2026-06-01', WaitTillDate='2026-06-05', WaitForReceipts=False,
        IsRedEnabled=False, IsGreenEnabled=False)] * 2
    state['NormsInSleepModeTbl'] = [dict(SKUCode='S', WhCode='W', StartDate=TODAY)]
    yield 'apply_sleep', state, 'SuspendNormsInSleepModeTbl'
    for name, reason in [('apply_forced_norm_consumption', 101), ('apply_accepted_norm_consumption', 6)]:
        state = control_state()
        state['NormChangeLogTbl'] = [dict(SKUCode='S', WhCode='W', NormChangeReason=reason,
                                         NormChangeDate=TODAY)] * 2
        state['SuspendConsumptionType'] *= 2
        yield name, state, 'SuspendConsumptionType'
    state = scan_cases.DbmStateScanIndexTests.forced_state()
    state['SuspendStockType'].insert(0, deepcopy(state['SuspendStockType'][0]))
    yield 'apply_forced_norm_stock', state, 'SuspendStockType'
    for name in ('suspend_accepted_norm_stock', 'apply_accepted_norm_stock'):
        state = scan_cases.DbmStateScanIndexTests.accepted_state()
        state['SuspendStockType'].insert(0, deepcopy(state['SuspendStockType'][0]))
        yield name, state, 'SuspendStockType'


class RetainedSuspensionRowsTests(unittest.TestCase):
    def compare(self, name, source, table):
        before = values(source)
        expected = getattr(service, name)(TODAY, deepcopy(before))
        actual = getattr(service, name)(TODAY, source)
        self.assertEqual(typed(actual), typed(expected))
        self.assertEqual(typed(source), typed(before))
        self.assertIsInstance(actual[table], list)
        if actual[table]:
            original_key = actual[table][0]['SKUCode']
            actual[table][0]['SKUCode'] = 'only-the-new-generation'
            self.assertEqual(typed(source), typed(before))
            actual[table][0]['SKUCode'] = original_key
        return actual

    def test_all_retained_writers_preserve_values_types_duplicates_order_and_source(self):
        for name, state, table in cases():
            with self.subTest(writer=name):
                state[table] = RecordRows.from_rows(state[table])
                self.compare(name, state, table)
                self.assertIs(deepcopy(state[table]), state[table])
                with self.assertRaisesRegex(TypeError, 'Immutable history row'):
                    state[table][0]['SKUCode'] = 'forbidden'

    def test_white_spike_supply_expected_transitions(self):
        white, spike, supply = list(cases())[:3]
        name, state, table = white
        result = getattr(service, name)(TODAY, state)[table]
        self.assertEqual([(r['SKUCode'], r['IsRedEnabled']) for r in result],
                         [('B', True), ('B', True), (None, True), ('A', False), ('A', False)])
        name, state, table = spike
        result = getattr(service, name)(TODAY, state)[table]
        self.assertEqual([(r['SKUCode'], r['IsRedEnabled']) for r in result],
                         [('B', True), ('B', True), ('C', False), ('A', False)])
        name, state, table = supply
        result = getattr(service, name)(TODAY, state)[table]
        self.assertEqual([(r['SKUCode'], r['ReceiptDate'], r['IsRedEnabled']) for r in result],
                         [('B', TODAY, True), ('B', TODAY, True), ('C', '2026-06-05', True),
                          ('D', None, False), ('A', None, False)])

    def test_declared_current_suspension_writers_isolate_default_and_owned_calls(self):
        for name, tables in (
            ('finalize_stock_suspensions', ('SuspendStockType', 'SuspendAggrCommon', 'SuspendAggrStockType')),
            ('finalize_consumption_suspensions', ('SuspendConsumptionType', 'SuspendAggrCommon', 'SuspendAggrConsumptionType')),
            ('finalize_order_suspensions', ('SuspendOrderType', 'SuspendAggrCommonWithOrderType')),
            ('suppress_insufficient_data', ('SuspendStockType', 'SuspendConsumptionType'))):
            for owned in (False, True):
                source = control_state()
                before = deepcopy(source)
                expected = getattr(service, name)(TODAY, deepcopy(source))
                for table in tables:
                    source[table] = RecordRows.from_rows(source[table])
                with self.subTest(writer=name, owned=owned):
                    actual = getattr(service, name)(TODAY, source, _owned=owned)
                    self.assertEqual(typed(actual), typed(expected))
                    self.assertEqual(typed(source), typed(before))


@unittest.skipUnless(os.environ.get('VF_RETAINED_SUSPENSION_PG_PROOF') == '1',
                     'Explicit isolated PostgreSQL transition proof required')
class PersistedSuspensionRowsTests(unittest.TestCase):
    compare = RetainedSuspensionRowsTests.compare

    def test_actual_postgresql_reader_threshold_and_all_retained_transitions(self):
        from django.db import connection, transaction
        from mta.runtime import relational_state as relational
        for name, state, table in cases():
            # Include both sides of the reader threshold on the actual failing writer.
            for count in ((10000, 10001) if name == 'apply_white' else (10001,)):
                with self.subTest(writer=name, rows=count), tempfile.TemporaryDirectory() as cache:
                    seed = state[table]
                    rows = [deepcopy(seed[i % len(seed)]) for i in range(count)]
                    state[table] = rows
                    fields = []
                    sql_types = []
                    for key in rows[0]:
                        value = next((r[key] for r in rows if r[key] is not None), '')
                        kind = 'bool' if type(value) is bool else 'int' if type(value) is int else 'str'
                        fields.append([key, key, kind])
                        sql_types.append('boolean' if kind == 'bool' else 'bigint' if kind == 'int' else 'text')
                    physical = relational.quote('suspension_' + uuid4().hex)
                    run = SimpleNamespace(pk=uuid4())
                    item = dict(table='fixture', image='fixture/' + name, count=count,
                                fields=fields, digest=digest(rows))
                    with transaction.atomic(), connection.cursor() as cursor:
                        cursor.execute('CREATE TEMP TABLE ' + physical +
                            ' (vf_run_id uuid, vf_image text, vf_ordinal bigint, ' +
                            ','.join(relational.quote(f[0]) + ' ' + t for f, t in zip(fields, sql_types)) +
                            ') ON COMMIT DROP')
                        cursor.executemany('INSERT INTO ' + physical + ' VALUES (' +
                            ','.join(['%s'] * (len(fields) + 3)) + ')',
                            [(run.pk, item['image'], i, *row.values()) for i, row in enumerate(rows)])
                        with patch.object(relational, 'table_sql', return_value=physical), \
                                patch.dict(os.environ, {'VF_WORK_ROOT': cache}):
                            source = deepcopy(state)
                            source[table] = relational.load_image(run, item, table_registry={'fixture': fields})
                            self.assertIsInstance(source[table], RecordRows if count > 10000 else list)
                            self.assertEqual(typed(source[table]), typed(rows))
                            expected = getattr(service, name)(TODAY, deepcopy(values(source)))[table]
                            actual = self.compare(name, source, table)
                            # Write/read a distinct output owner through the real typed
                            # transport too; the fixture only redirects its SQL table.
                            output_run = SimpleNamespace(pk=uuid4())
                            columns = [(f[0], 'bit' if f[2] == 'bool' else
                                        'bigint' if f[2] == 'int' else 'nvarchar') for f in fields]
                            with patch.dict(relational.STORAGE_TABLES, {'fixture': columns}):
                                output = relational.save_image(output_run, 'transition/' + name,
                                                               None, actual[table], table='fixture')
                                restored = relational.load_image(output_run, output,
                                                                  table_registry={'fixture': columns})
                                # The established writer declares one field order for
                                # the whole image, including newly appended records.
                                self.assertEqual([f[0] for f in output['fields']], list(expected[0]))
                                canonical = [{field: row[field] for field, _, _ in output['fields']}
                                             for row in expected]
                                self.assertEqual(typed(restored), typed(canonical))
                            cursor.execute('SELECT ' + ','.join(relational.quote(f[0]) for f in fields) +
                                           ' FROM ' + physical + ' WHERE vf_run_id=%s ORDER BY vf_ordinal',
                                           [run.pk])
                            self.assertEqual(cursor.fetchall(), [tuple(row.values()) for row in rows])
                        transaction.set_rollback(True)


if __name__ == '__main__':
    unittest.main()
