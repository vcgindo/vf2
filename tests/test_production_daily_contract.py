import copy
import hashlib
import json
import os
import unittest
os.environ.setdefault('VF_SECRET_KEY', 'unit-contract-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.runtime.production_daily import decode
from mta.mdm.initialization_contract import decode as initialized_decode
from tests.initialization_input_fixture import encoded
from tests.production_daily_fixture import initialized_input, day_input


def encoded_day(value):
    raw = (json.dumps(value, separators=(',', ':'))+'\n').encode()
    return raw, hashlib.sha256(raw).hexdigest()


class ProductionDailyContractTests(unittest.TestCase):
    def test_enabled_norm_exports_require_existing_selected_layout(self):
        value = initialized_input()
        raw, sha, args = encoded(value)
        _, frame, _ = initialized_decode(raw, sha, **args)
        self.assertEqual(frame['opening']['state']['dbm']['ui_ReportConfigurations'],
            value['opening']['state']['dbm']['ui_ReportConfigurations'])
        mutations = (lambda rows: rows.clear(), lambda rows: rows.append(copy.deepcopy(rows[0])),
            lambda rows: rows[1].update(Col_Position=1), lambda rows: rows[0].update(Col_Code='WHCode'),
            lambda rows: rows[0].update(Col_Position='1'), lambda rows: rows[0].update(Visible=None))
        for mutate in mutations:
            changed = copy.deepcopy(value)
            mutate(changed['opening']['state']['dbm']['ui_ReportConfigurations'])
            raw, sha, args = encoded(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                initialized_decode(raw, sha, **args)
        from mta.domain.dbm_norm012 import export_stage
        exported = export_stage({'ui_ReportConfigurations': frame['opening']['state']['dbm']['ui_ReportConfigurations'],
                                 'Norm0_1_2ReportDetails': []})
        self.assertEqual(exported['ReportHeader'][0]['values'],
            [row['Col_Code'] for row in frame['opening']['state']['dbm']['ui_ReportConfigurations']])
        self.assertEqual(exported['ReportRows'], [])

    def test_dbm_scratch_must_be_explicit_empty_and_roundtrip_without_rows(self):
        from types import SimpleNamespace
        from mta.runtime.input_storage import save_input, read_input
        from mta.mdm.initialization_rows import select
        value = initialized_input()
        for bad in (None, {}, ['named'], [{'table': 'arbitrary', 'rows': []}]):
            changed = copy.deepcopy(value)
            changed['opening']['state']['dbm']['IntermediateTables'] = bad
            raw, sha, args = encoded(changed)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                initialized_decode(raw, sha, **args)
        missing = copy.deepcopy(value)
        del missing['opening']['state']['dbm']['IntermediateTables']
        raw, sha, args = encoded(missing)
        with self.assertRaises(ValueError):
            initialized_decode(raw, sha, **args)
        frame = {'profile': {'delivery': {'site_code': 'SUPPLIED'}},
                 'opening': {'state': {'dbm': {'IntermediateTables': []}}}}
        from mta.serialization import digest
        run = SimpleNamespace(input_digest=digest(frame))
        run.input_payload = save_input(run, frame, table_selector=select,
            image_writer=lambda *a, **k: self.fail('Empty scratch has no typed rows'))
        run.input_manifest_digest = digest(run.input_payload)
        self.assertEqual(run.input_payload['images'], {})
        self.assertEqual(read_input(run), frame)

    def test_selected_spike_configuration_requires_singletons_and_existing_parser(self):
        for name in ('SpikeRuleHorizon', 'SpikeRuleParCount'):
            for replacement in ([], [dict(Parameter=name, Value='7')] * 2,
                                [dict(Parameter=name, Value='7.0')],
                                [dict(Parameter=name, Value=None)]):
                value = initialized_input()
                value['opening']['state']['dbm']['DBMSettingsTbl'] = [row for row in
                    value['opening']['state']['dbm']['DBMSettingsTbl'] if row['Parameter'] != name] + replacement
                raw, sha, args = encoded(value)
                with self.subTest(name=name, replacement=replacement), self.assertRaises(ValueError):
                    initialized_decode(raw, sha, **args)
        value = initialized_input()
        value['opening']['state']['dbm']['DBMSettingsTbl'][0]['Value'] = ' +07 '
        raw, sha, args = encoded(value)
        _, frame, _ = initialized_decode(raw, sha, **args)
        self.assertEqual(frame['opening']['state']['dbm']['DBMSettingsTbl'][0]['Value'], ' +07 ')

    def test_selected_introduction_configuration_requires_typed_singleton(self):
        for bag in ([], [dict(ReplenishmentPercentage=50)] * 2,
                    [dict(ReplenishmentPercentage=None)]):
            value = initialized_input()
            value['opening']['state']['dbm']['FirstReplenishmentPercentageTbl'] = bag
            raw, sha, args = encoded(value)
            with self.subTest(bag=bag), self.assertRaises(ValueError):
                initialized_decode(raw, sha, **args)
        raw, sha, args = encoded(initialized_input())
        _, frame, _ = initialized_decode(raw, sha, **args)
        self.assertEqual(frame['opening']['state']['dbm']['FirstReplenishmentPercentageTbl'],
            [dict(ReplenishmentPercentage=50)])

    def test_initialization_requires_one_supported_daily_stock_mode(self):
        for settings in ([], [dict(Parameter='MissingDailyDataHandling', Value='0')],
                         [dict(Parameter='MissingDailyDataHandling', Value='1')] * 2):
            value = initialized_input()
            value['configuration']['daily']['settings'] = settings
            raw, sha, args = encoded(value)
            with self.subTest(settings=settings), self.assertRaisesRegex(ValueError, 'One supported'):
                initialized_decode(raw, sha, **args)

    def test_empty_owned_queue_revisions_preserve_empty_shape(self):
        from mta.runtime.input_storage import save_input
        from mta.runtime.production_daily import input_table
        from types import SimpleNamespace
        value = {'profile': {'delivery': {'site_code': 'SUPPLIED'}},
            'mdm_input': {'supplier': {'task_revisions': []}}}
        run = SimpleNamespace(input_digest='x')
        manifest = save_input(run, value, table_selector=input_table,
            image_writer=lambda *args, **kwargs: self.fail('Empty revision must not create an image'))
        self.assertEqual(manifest['images'], {})

    def test_supplied_initialization_and_first_successor_contracts(self):
        raw, sha, args = encoded(initialized_input())
        initialized_decode(raw, sha, **args)
        for day, root in (('2037-04-10', True), ('2037-04-11', False)):
            value = day_input(day, root=root)
            raw, sha = encoded_day(value)
            self.assertEqual(decode(raw, sha), value)

    def test_hash_unknown_missing_calculated_and_queue_override_denials(self):
        raw, sha = encoded_day(day_input('2037-04-10', root=True))
        with self.assertRaises(ValueError):
            decode(raw+b' ', sha)
        mutations = [lambda q: q['day'].update(DBMMaster=[]),
            lambda q: q['day'].pop('raw_daily'),
            lambda q: q['day']['raw_daily'][0].update(Stock='bad'),
            lambda q: q['day']['raw_daily'][0].update(ReportDate='2037-04-11'),
            lambda q: q['day']['raw_daily'][0].update(computed_blue_zone=5),
            lambda q: q['day'].update(phase_controls_input_validation='true'),
            lambda q: q['day']['control_requests'].update(phase_stops=[{'SKUCode':'x','WhCode':'y'}]),
            lambda q: q['consumer_opening']['remarks'].update(bpr=[{}])]
        for change in mutations:
            value = day_input('2037-04-10', root=True)
            change(value)
            raw, sha = encoded_day(value)
            with self.subTest(change=change), self.assertRaises(ValueError):
                decode(raw, sha)
