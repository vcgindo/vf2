import copy
import os
import unittest

os.environ.setdefault('VF_SECRET_KEY', 'unit-contract-only-not-a-deployment-secret')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.mdm.initialization_contract import decode
from tests.initialization_input_fixture import supplied_input, encoded


class InitializationContractTest(unittest.TestCase):
    def test_unrelated_supplied_codes_date_counts_nulls_duplicates(self):
        value = supplied_input()
        raw, sha, args = encoded(value)
        _, frame, batches = decode(raw, sha, **args)
        self.assertEqual(frame['opening']['opening_date'], '2037-04-09')
        self.assertEqual(frame['opening']['state']['importer']['SkuAttributeData'][0]['SKUCode'], 'SUPPLIED-Z9')
        self.assertEqual(frame['opening']['state']['importer']['SkuAttributeData'][0]['Weight'], '2.125')
        self.assertIsNone(frame['opening']['state']['importer']['SkuAttributeData'][0]['Volume'])
        self.assertEqual(len(frame['opening']['state']['consumer_context']['NMSAllItems']), 3)
        self.assertEqual(frame['opening']['state']['importer']['SkuAttributeData'][0],
                         frame['opening']['state']['importer']['SkuAttributeData'][1])
        self.assertEqual(len(batches), 16)

    def test_input_configuration_recipe_integrity_denied(self):
        value = supplied_input()
        raw, sha, args = encoded(value)
        cases = [(raw+b' ', sha, args), (raw, sha, {**args, 'expected_configuration': '0'*64}),
                 (raw, sha, {**args, 'expected_recipe': '0'*64})]
        for body, identity, parameters in cases:
            with self.subTest(parameters=parameters), self.assertRaises(ValueError):
                decode(body, identity, **parameters)

    def test_missing_unknown_invalid_and_conflicting_populations_denied(self):
        mutations = [lambda q: q['masters']['importer'].pop('MasterData'),
            lambda q: q['masters']['importer'].update(UnknownPopulation=[]),
            lambda q: q['masters']['importer']['SkuAttributeData'][0].pop('Weight'),
            lambda q: q['masters']['importer']['SkuAttributeData'][0].update(SKUCode=42),
            lambda q: q['masters']['importer']['SkuAttributeData'][0].update(Weight='2.1251'),
            lambda q: q['opening']['state']['importer'].update(MasterData=[]),
            lambda q: q['opening']['state']['controls'].pop('last_batch'),
            lambda q: q['opening']['state']['controls'].update(UnknownPopulation=[]),
            lambda q: q['opening']['state']['dbm'].update(Suggestions=[{'fake': 'future'}]),
            lambda q: q.update(schema='unknown'),
            lambda q: q['configuration'].update(oracle_file='unavailable'),
            lambda q: q.pop('pair_exclusions')]
        for change in mutations:
            value = supplied_input()
            change(value)
            raw, sha, args = encoded(value)
            with self.subTest(change=change), self.assertRaises(ValueError):
                decode(raw, sha, **args)

    def test_duplicate_object_keys_and_nonfinite_numbers_denied(self):
        import hashlib
        for raw in (b'{"schema":1,"schema":2}', b'{"schema":NaN}'):
            with self.assertRaises(ValueError):
                decode(raw, hashlib.sha256(raw).hexdigest(), expected_configuration='0'*64, expected_recipe='0'*64)

    def test_explicit_path_fields_types_and_initial_outcomes_denied(self):
        mutations = [
            lambda q: q['configuration']['calculation'].update(skus=[{'bogus': 1}]),
            lambda q: q['configuration']['daily'].update(settings=[{'bogus': 1}]),
            lambda q: q['configuration'].update(operational_sources='bogus'),
            lambda q: q['opening']['state']['dbm'].update(DBMMaster=[{'SKUCode': 'x'}]),
            lambda q: q['opening']['state']['controls'].update(log=[{'bogus': 1}]),
            lambda q: q['opening']['state']['dbm'].update(Norm1IncreaseSuggestions=[{'bogus': 1}]),
            lambda q: q['opening']['state']['dbm'].update(Norm0Norm1Norm2Report=[{'bogus': 1}]),
            lambda q: q['opening']['state']['btr'].update(BTRSnapshotForUI=[{'bogus': 1}]),
            lambda q: q['opening']['state']['complete']['ScriptExecutedFlag'][0].update(IsScriptExecuted=1),
            lambda q: q['opening']['state']['importer_settings'][4].update(Value='1'),
        ]
        for change in mutations:
            value = supplied_input()
            change(value)
            raw, sha, args = encoded(value)
            with self.subTest(change=change), self.assertRaises(ValueError):
                decode(raw, sha, **args)

    def test_typed_computed_populations_and_future_history_denied(self):
        from mta.mdm.initialization_rows import schema
        for section, name in (('dbm', 'Norm1IncreaseSuggestions'),
                              ('dbm', 'Norm0Norm1Norm2Report'), ('btr', 'BTRSnapshotForUI')):
            value = supplied_input()
            _, fields = schema('input/opening/state/'+section+'/'+name+'/values', [])
            value['opening']['state'][section][name] = [dict.fromkeys(fields)]
            raw, sha, args = encoded(value)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'calculated output'):
                decode(raw, sha, **args)
        value = supplied_input()
        _, fields = schema('input/opening/state/controls/log/values', [])
        value['opening']['state']['controls']['log'] = [{**dict.fromkeys(fields), 'NormChangeDate': '2037-04-10'}]
        raw, sha, args = encoded(value)
        with self.assertRaisesRegex(ValueError, 'history/date exceeds'):
            decode(raw, sha, **args)

    def test_complete_declared_configuration_and_history_values(self):
        from mta.mdm.initialization_rows import schema
        value = supplied_input()
        value['configuration']['calculation']['skus'] = [{'sku_code': 'SUPPLIED-Z9', 'description': 'Supplied'}]*2
        _, fields = schema('input/opening/state/controls/log/values', [])
        row = {**dict.fromkeys(fields), 'SKUCode': 'SUPPLIED-Z9', 'WHCode': 'OWN-WH8',
            'OldNorm': 7, 'NewNorm': 8, 'NormChangeDate': '2037-04-08', 'NormChangeReason': 5}
        value['opening']['state']['controls']['log'] = [row, copy.deepcopy(row)]
        raw, sha, args = encoded(value)
        frame = decode(raw, sha, **args)[1]
        self.assertEqual(frame['opening']['state']['controls']['log'], [row, row])

    def test_required_configuration_identities_cannot_be_null(self):
        for population, field in (('skus', 'sku_code'), ('locations', 'location_code'),
                ('stock_openings', 'sku_code'), ('policies', 'location_code')):
            value = supplied_input()
            value['configuration']['calculation'][population][0][field] = None
            raw, sha, args = encoded(value)
            with self.subTest(population=population), self.assertRaisesRegex(ValueError, 'NULL in required'):
                decode(raw, sha, **args)
