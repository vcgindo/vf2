"""Observation cannot change results, guard failures or transport batching."""
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from mta.application import stage_observation as observation


def events(logger):
    return [json.loads(call.args[1]) for call in logger.call_args_list]


class StageObservationTests(TestCase):
    def test_nested_phases_have_inclusive_parentage_and_restore_context(self):
        with patch.object(observation._logger, 'warning') as logger:
            with observation.operation('attempt'), observation.stage('restore', rows=2):
                with observation.operation('run'), observation.stage('read'):
                    observation.summary('transport', rows=2, batches=1)
            observation.summary('outside', rows=99)
        rows = events(logger)
        self.assertEqual([(r['stage'], r['event']) for r in rows],
            [('restore','begin'),('read','begin'),('transport','summary'),('read','end'),('restore','end')])
        self.assertEqual(rows[1]['stage_path'], 'restore/read')
        self.assertEqual(rows[1]['parent_owner'], 'attempt')
        self.assertEqual(rows[1]['owner'], 'run')
        self.assertEqual(rows[-1]['rows'], 2)
        self.assertTrue(all(r['timing']=='inclusive' and r['observed_at_unix']>0 for r in rows))
        self.assertTrue(all(rows[i]['seconds']>=0 and rows[i]['cpu_seconds']>=0 for i in (3,4)))
        self.assertIsNone(observation._owner.get())
        self.assertEqual(observation._stages.get(), ())

    def test_entry_decorator_preserves_value_arguments_and_existing_owner(self):
        value = object()
        @observation.observed('intake', owner_parameter='attempt_id')
        def intake(attempt_id, supplied):
            self.assertIs(supplied, value)
            return supplied
        with patch.object(observation._logger, 'warning') as logger:
            self.assertIs(intake('123', value), value)
            with observation.operation('outer'):
                self.assertIs(intake(attempt_id='456', supplied=value), value)
        self.assertEqual([row['owner'] for row in events(logger)], ['intake:123']*2+['outer']*2)

    def test_failure_identity_and_log_sink_failure_do_not_change_control_flow(self):
        original = ValueError('business failure')
        with patch.object(observation._logger, 'warning') as logger:
            with self.assertRaises(ValueError) as caught:
                with observation.operation('run'), observation.stage('capture'):
                    raise original
        self.assertIs(caught.exception, original)
        self.assertEqual(events(logger)[-1]['error_type'], 'ValueError')
        with patch.object(observation._logger, 'warning', side_effect=OSError('sink unavailable')):
            with observation.operation('run'), observation.stage('success'):
                observation.stock_rejection(sku_code='S', location_code='L', business_date='2026-04-08',
                    match_count=0, reason='missing', identity='run')
            with self.assertRaises(ValueError) as caught:
                with observation.operation('run'), observation.stage('failure'):
                    raise original
        self.assertIs(caught.exception, original)
        self.assertEqual(observation._stages.get(), ())

    def test_executemany_still_consumes_one_batch_at_a_time_and_preserves_values(self):
        from mta.runtime import relational_state
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        consumed = []
        def records():
            for ordinal in range(1001):
                consumed.append(ordinal)
                yield ordinal, None, 'duplicate' if ordinal<2 else '', True
        expected = list(records()); consumed.clear()
        sent = []
        def execute(sql, batch):
            self.assertEqual(sql, 'owned insert')
            self.assertEqual(len(consumed), min((len(sent)+1)*500,1001))
            sent.append(list(batch))
        cursor.executemany.side_effect = execute
        with patch.object(relational_state, 'connection', connection), \
                patch.object(observation._logger, 'warning') as logger, observation.operation('attempt'):
            relational_state.bulk('owned insert', records())
        self.assertEqual([len(batch) for batch in sent], [500,500,1])
        self.assertEqual([row for batch in sent for row in batch], expected)
        metrics = events(logger)[-1]
        self.assertEqual((metrics['rows'],metrics['batches'],metrics['transport']), (1001,3,'executemany'))
        self.assertTrue(all(metrics[name]>=0 for name in
            ('records_prepare_seconds','records_prepare_cpu_seconds','execute_seconds','execute_cpu_seconds')))

    def test_transport_failure_retains_original_exception_and_does_not_consume_next_batch(self):
        from mta.runtime import relational_state
        connection = MagicMock()
        original = ValueError('database rejection')
        connection.cursor.return_value.__enter__.return_value.executemany.side_effect = original
        consumed = []
        def records():
            for ordinal in range(501):
                consumed.append(ordinal)
                yield (ordinal,)
        with patch.object(relational_state,'connection',connection), self.assertRaises(ValueError) as caught:
            relational_state.bulk('owned insert',records())
        self.assertIs(caught.exception,original)
        self.assertEqual(len(consumed),500)

    def test_transaction_exit_timer_excludes_body_and_preserves_error_ownership(self):
        original = ValueError('body rejected')
        order = []
        @contextmanager
        def transaction():
            order.append('enter')
            try:
                yield
            finally:
                order.append('exit')
        def log(format, raw):
            event = json.loads(raw)
            order.append(event['event'])
        with patch.object(observation._logger,'warning',side_effect=log), observation.operation('attempt'):
            with observation.observe_exit(transaction(),'commit'):
                order.append('body')
        self.assertEqual(order,['enter','body','begin','exit','end'])
        with patch.object(observation._logger,'warning') as logger, observation.operation('attempt'):
            with self.assertRaises(ValueError) as caught:
                with observation.observe_exit(transaction(),'rollback'):
                    raise original
        self.assertIs(caught.exception,original)
        self.assertTrue(events(logger)[-1]['body_failed'])
        self.assertEqual(observation._stages.get(),())

    def test_transaction_exit_failure_and_suppression_remain_with_original_context(self):
        original = ValueError('commit failed')
        @contextmanager
        def failing_exit():
            yield
            raise original
        with patch.object(observation._logger,'warning') as logger, observation.operation('attempt'):
            with self.assertRaises(ValueError) as caught:
                with observation.observe_exit(failing_exit(),'commit'):
                    pass
        self.assertIs(caught.exception,original)
        self.assertFalse(events(logger)[-1]['body_failed'])
        @contextmanager
        def suppressing_exit():
            try:
                yield
            except ValueError:
                pass
        with patch.object(observation._logger,'warning') as logger, observation.operation('attempt'):
            with observation.observe_exit(suppressing_exit(),'exit'):
                raise ValueError('context owns suppression')
        self.assertEqual(events(logger)[-1]['event'],'end')
        self.assertTrue(events(logger)[-1]['body_failed'])

    def test_streamed_readback_does_not_hold_a_phase_across_yield(self):
        from mta.runtime import batch_storage
        from tests.test_batch_storage import attempt, empty, identity, Cursor, SCHEMA
        owner = attempt()
        populations = empty(SCHEMA)
        row = dict(SKUCode='A',WhCode=None,Stock=7,Consumption=0,GIT=None,
            Receipts=2,PSO=1,ReportDate='2026-10-21')
        populations['DailyDataRaw.csv'] = [row,row]
        inserted = {}
        def capture(sql,records):
            table=sql.split('INSERT INTO mta_state."',1)[1].split('"',1)[0]
            inserted[table]=list(records)
        with patch.object(batch_storage,'bulk',side_effect=capture):
            manifest=batch_storage.save_populations(owner,SCHEMA,populations,_identity_resolver=identity)
        entry=next(item for item in manifest['feeds'] if item['filename']=='DailyDataRaw.csv')
        records={entry['table']:[record[1:] for record in inserted[entry['table']]]}
        connection=SimpleNamespace(chunked_cursor=lambda:Cursor(records))
        with patch.object(batch_storage,'connection',connection), \
                patch.object(observation._logger,'warning') as logger, \
                observation.operation('attempt'), observation.stage('consumer'):
            parent=observation._stages.get()
            iterator=batch_storage._iter_population(owner,entry)
            self.assertEqual(next(iterator),row)
            self.assertEqual(observation._stages.get(),parent)
            self.assertEqual(list(iterator),[row])
        metrics=next(item for item in events(logger) if item['stage']=='batch_readback')
        self.assertEqual((metrics['rows'],metrics['fetch_calls']),(2,2))
        self.assertTrue(all(metrics[name]>=0 for name in
            ('query_seconds','query_cpu_seconds','fetch_seconds','fetch_cpu_seconds')))
