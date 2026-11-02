"""Native capture handoff ownership, unchanged inputs and downstream consumers."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import gc
import os
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import patch
import uuid
import weakref

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'native-capture-lifetime-unit-only')
import django
django.setup()

from mta.runtime import production_daily as native, temporal
from mta.runtime import opening_scope
from mta.serialization import storage


class WeakGraph(dict):
    pass


def arguments(**overrides):
    values = dict.fromkeys(native._NativeCaptureInputs.FIELDS)
    values.update(day={'business_date': '2037-04-10'}, profile={'delivery': {'site_code': 'SUPPLIED'}},
                  execution_revision='same-native-revision')
    values.update(overrides)
    return values


class NativeCaptureLifetimeTests(unittest.TestCase):
    def test_eager_preflight_failure_still_stops_before_day_owner(self):
        with patch.object(native, '_prepare_execution', side_effect=ValueError('preflight denied')), \
                patch.object(temporal, 'execute_day') as execute:
            with self.assertRaisesRegex(ValueError, 'preflight denied'):
                native.execute(b'raw', 'a'*64, initialization_id='owner', source_digest='source',
                    configuration_digest='config', execution_revision='revision', pick_output_root='/owned')
            execute.assert_not_called()

    def test_all_prepared_arguments_transfer_without_value_or_identity_changes(self):
        for scope, retry in ((None, None), ({'scope': 'Full'}, 'origin'), ({'scope': 'UptoBPR'}, None)):
            with self.subTest(scope=scope, retry=retry):
                source = arguments(scope_request=scope, mdm_retry=retry,
                    prepared_state=object(), production_initialization=object(), predecessor=object())
                holder = native._NativeCaptureInputs(source)
                actual = dict(zip(holder.FIELDS, holder.take(source['execution_revision'])))
                for field in holder.FIELDS:
                    self.assertIs(actual[field], source[field])
                self.assertIsNone(holder._arguments)
                with self.assertRaisesRegex(ValueError, 'already consumed'):
                    holder.take(source['execution_revision'])

    def test_revision_mismatch_does_not_consume_the_handoff(self):
        source = arguments()
        holder = native._NativeCaptureInputs(source)
        with self.assertRaisesRegex(ValueError, 'revision differs'):
            holder.take('foreign')
        self.assertIs(holder._arguments, source)

    def test_handoff_rejects_foreign_and_competing_arguments_before_sql(self):
        for field in ('day', 'profile', 'opening', 'mdm_source', 'prepared_state',
                      '_captured_retry', 'scope_request', 'report_registration_request'):
            holder = native._NativeCaptureInputs(arguments())
            options = dict(day=None, profile=None, execution_revision='same-native-revision',
                           _native_preparation=holder)
            options[field] = {'competing': True}
            with self.subTest(field=field), patch('django.db.backends.utils.CursorWrapper.execute',
                    side_effect=AssertionError('No SQL')):
                with self.assertRaisesRegex(ValueError, 'cannot replace supplied arguments'):
                    temporal.execute_day(**options)
                self.assertIsNotNone(holder._arguments)
        with self.assertRaisesRegex(ValueError, 'cannot replace supplied arguments'):
            temporal.execute_day(day=None, profile=None, execution_revision='same-native-revision',
                                 _native_preparation=object())

    def test_caller_and_capture_roots_die_before_calculation_while_working_values_survive(self):
        references = {}
        rows = [{'SKUCode': 'A', 'value': None, 'amount': Decimal('2.125'), 'active': False},
                {'SKUCode': 'A', 'value': None, 'amount': Decimal('2.125'), 'active': False}]
        expected = storage(rows)
        def prepare(*args, **kwargs):
            frame = WeakGraph(profile=WeakGraph(rows=deepcopy(rows)),
                opening=WeakGraph(state={'rows': deepcopy(rows)}, opening_date=date(2037, 4, 9)),
                capture_only=WeakGraph(unused=[1, 2, 3]))
            references.update({key: weakref.ref(value) for key, value in frame.items()})
            references['frame'] = weakref.ref(frame)
            opening_scope._current.get().cache['unit-owned-frame'] = frame
            return arguments(profile=frame['profile'], opening=frame['opening'])
        def consume(**options):
            self.assertIsNone(options['day']); self.assertIsNone(options['profile'])
            holder = options['_native_preparation']
            transferred = dict(zip(holder.FIELDS, holder.take(options['execution_revision'])))
            profile = storage(transferred.pop('profile'))
            initial = storage(transferred.pop('opening'))
            persisted_opening = deepcopy(initial)
            prior = deepcopy(initial['state'])
            opening_scope.release_opening()
            del initial
            gc.collect()
            self.assertTrue(all(reference() is None for reference in references.values()))
            self.assertEqual(profile['rows'], expected)
            self.assertEqual(prior['rows'], expected)
            self.assertEqual(persisted_opening['state']['rows'], expected)
            self.assertEqual(persisted_opening['opening_date'], '2037-04-09')
            self.assertEqual([list(row) for row in prior['rows']], [list(row) for row in expected])
            return 'owned-output'
        with patch.object(native, '_prepare_execution', side_effect=prepare), \
                patch.object(temporal, 'execute_day', side_effect=consume):
            result = native.execute(b'raw', 'a'*64, initialization_id='owner', source_digest='source',
                configuration_digest='config', execution_revision='same-native-revision', pick_output_root='/owned')
        self.assertEqual(result, 'owned-output')

    def test_full_calculation_consumers_use_prior_and_explicit_publication_opening(self):
        from mta.runtime.runtime_report_request import SCHEMA
        for registered in (False, True):
            run = Obj(pk=uuid.uuid4(), input_digest='d'*64, production_manifest={})
            prior = {'rows': [{'value': None}, {'value': None}]}
            day = {'business_date': '2037-04-10'}
            profile = {'delivery': {'site_code': 'SUPPLIED'}}
            raw = {'day': day, 'profile': profile}
            if registered: raw['scope_request'] = {'schema': SCHEMA}
            publication = {'supplier': {'rows': [{'value': None}, {'value': None}]}}
            result = {'_CompletedBoundaries': list(temporal.BOUNDARIES), 'ClosingState': [deepcopy(prior)]}
            work = object() if registered else None
            def calculate(actual_prior, opening_date, actual_day, actual_profile, identity, *a, **kw):
                self.assertIs(actual_prior, prior); self.assertIs(actual_day, day)
                self.assertIs(actual_profile, profile); self.assertEqual(opening_date, '2037-04-09')
                if registered: self.assertIs(kw['opening'], publication)
                return (deepcopy(result), work) if registered else deepcopy(result)
            def registered_calculate(actual_run, *args, **kwargs):
                self.assertIs(actual_run, run)
                return calculate(*args, **kwargs)
            with self.subTest(registered=registered), \
                    patch.object(temporal, 'calculate_day', side_effect=calculate), \
                    patch('mta.runtime.runtime_report_execution.calculate_full', side_effect=registered_calculate), \
                    patch.object(temporal, 'fail_run', side_effect=AssertionError('No SQL failure writer in unit proof')) as fail, \
                    patch.object(temporal, 'finish_run', return_value='finished') as finish:
                actual = temporal._finish_captured_day(run, raw, prior, '2037-04-09', {}, publication,
                    False, None, {}, None, True)
                self.assertEqual(actual, 'finished')
                self.assertEqual(finish.call_args.kwargs['expected_digest'], run.input_digest)
                self.assertIs(finish.call_args.kwargs['publication_opening'], publication)
                self.assertIs(finish.call_args.kwargs['_report_work'], work)
                self.assertEqual(finish.call_args.args[1]['ClosingState'], [prior])
                fail.assert_not_called()
