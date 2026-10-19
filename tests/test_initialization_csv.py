"""Opening CSV uses the unchanged native contract and initializer.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from datetime import date
import zipfile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'offline-csv-contract-only')
import django
django.setup()

from mta.application.initialization_csv import create, read, MANIFEST, _value
from mta.mdm.initialization_contract import decode
from mta.serialization import digest
from tools.create_daily_csv_example import create as daily_example

ROOT = Path(__file__).resolve().parents[1]


class OpeningCsvTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'opening'
        with zipfile.ZipFile(ROOT / 'examples/starter-data/vectorflow-starter-inputs-v1.zip') as z:
            self.original = z.read('initialization.json')
        self.value = json.loads(self.original)
        self.manifest, self.raw = create(self.value, self.root)
        self.options = dict(expected_configuration=digest(self.value['configuration']),
                            expected_recipe=digest(self.value['recipe']))

    def tearDown(self):
        self.temp.cleanup()

    def pin(self):
        return hashlib.sha256((self.root / MANIFEST).read_bytes()).hexdigest()

    def change_csv(self, filename, payload):
        (self.root / filename).write_bytes(payload)
        self.manifest['populations'][filename]['sha256'] = hashlib.sha256(payload).hexdigest()
        (self.root / MANIFEST).write_text(json.dumps(self.manifest))

    def test_complete_native_frame_values_nulls_dates_and_order_are_identical(self):
        original = decode(self.original, hashlib.sha256(self.original).hexdigest(), **self.options)
        actual = read(self.root, self.pin(), **self.options)
        self.assertEqual(json.loads(actual), self.value)
        self.assertEqual(decode(actual, hashlib.sha256(actual).hexdigest(), **self.options), original)
        self.assertEqual(len(list(self.root.glob('*.csv'))), len(self.manifest['populations']))
        self.assertNotIn('"SKUCode"', json.dumps(self.manifest['template']))

    def test_text_null_numbers_booleans_and_duplicate_ordinals_are_lossless(self):
        self.assertEqual([_value(x, 'text') for x in ('00337', '', 'a,b\nnext', '\\N')],
                         ['00337', '', 'a,b\nnext', None])
        self.assertIs(type(_value('1', 'number')), int)
        self.assertIs(type(_value('1.0', 'number')), float)
        self.assertIs(_value('true', 'bit'), True)
        self.assertIs(type(_value('1', 'bit')), int)
        for token in ('NaN', 'Infinity', '01', '1,2', ''):
            with self.assertRaises(ValueError):
                _value(token, 'number')
        # Duplicate occurrences are legitimate native exclusions, not deduplicated.
        value = json.loads(self.original)
        value['pair_exclusions'] = [dict(SKUCode='00337', WhCode='X'), dict(SKUCode='00337', WhCode='X')]
        _, raw = create(value, Path(self.temp.name) / 'duplicates')
        self.assertEqual(json.loads(raw)['pair_exclusions'], value['pair_exclusions'])

    def test_corruption_and_configuration_mismatch_are_rejected(self):
        name = next(iter(self.manifest['populations']))
        (self.root / name).write_bytes((self.root / name).read_bytes() + b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            read(self.root, self.pin(), **self.options)
        with self.assertRaisesRegex(ValueError, 'matching'):
            read(self.root, self.pin(), **dict(self.options, expected_recipe='0' * 64))

    def test_headers_and_values_rejected_even_with_updated_file_hash(self):
        name = next(n for n, s in self.manifest['populations'].items()
                    if s['path'] == 'input/configuration/calculation/stock_openings')
        raw = (self.root / name).read_bytes()
        self.change_csv(name, raw.replace(b'sku_code', b'wrong', 1))
        with self.assertRaisesRegex(ValueError, 'headers'):
            read(self.root, self.pin(), **self.options)
        # Choose a known numeric cell rather than relying on a fixture quantity.
        import csv
        stream = io.StringIO(raw.decode(), newline='');rows = list(csv.reader(stream))
        rows[1][rows[0].index('stock')] = 'nonnumeric'
        out = io.StringIO(newline='');csv.writer(out).writerows(rows)
        self.change_csv(name, out.getvalue().encode())
        with self.assertRaisesRegex(ValueError, 'stock'):
            read(self.root, self.pin(), **self.options)

    def test_missing_ready_file_or_extra_file_never_admitted(self):
        (self.root / 'unexpected.csv').write_bytes(b'x')
        with self.assertRaisesRegex(ValueError, 'roster'):
            read(self.root, self.pin(), **self.options)
        (self.root / 'unexpected.csv').unlink()
        (self.root / 'READY').unlink()
        with self.assertRaises(FileNotFoundError):
            read(self.root, self.pin(), **self.options)

    def test_existing_atomic_initializer_receives_exact_validated_bytes_once(self):
        from mta.runtime.management.commands.initialize_production import Command
        output = io.StringIO()
        owner = SimpleNamespace(source_id=1, source=SimpleNamespace(digest='a'*64), pk='owned',
            opening_identity='opening', opening_date=date(2026,10,17), input_sha256='b'*64,
            configuration_digest=self.options['expected_configuration'], recipe_sha256=self.options['expected_recipe'],
            implementation_digest='c'*64, input_digest='d'*64)
        options = dict(input=self.root, sha256=self.pin(), csv=True, inspect=False,
            configuration_digest=self.options['expected_configuration'], recipe_digest=self.options['expected_recipe'])
        with patch('mta.presentation.native_mode.require_configuration'), \
             patch('mta.runtime.management.commands.initialize_production.initialize', return_value=(owner, True)) as initialize:
            Command(stdout=output).handle(**options)
        initialize.assert_called_once_with(self.raw, hashlib.sha256(self.raw).hexdigest(), **self.options)
        output = io.StringIO()
        with patch('mta.presentation.native_mode.require_configuration'), \
             patch('mta.runtime.management.commands.initialize_production.initialize') as initialize:
            from django.core.management.base import CommandError
            with self.assertRaises(CommandError):
                Command(stdout=output).handle(**dict(options, sha256='0'*64))
            initialize.assert_not_called()

    def test_developer_pack_contains_csv_opening_and_two_daily_batches(self):
        root = daily_example(ROOT / 'examples/starter-data/vectorflow-starter-inputs-v1.zip',
                             Path(self.temp.name) / 'starter', csv_onboarding=True)
        self.assertFalse((root / 'initialization.json').exists())
        self.assertEqual(json.loads((root / 'native-opening.json').read_bytes()), self.value)
        for day in ('2026-10-18', '2026-10-19'):
            self.assertEqual(len(list((root / day).glob('*.csv'))), 10)
        binding = json.loads((root / 'binding-template.json').read_bytes())
        self.assertEqual(binding['opening_sha256'], self.manifest['native_input_sha256'])


if __name__ == '__main__':
    unittest.main()
