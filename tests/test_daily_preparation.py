"""Changed daily intake boundary; no business day or serving instance is run.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
if not os.environ.get('VF_SECRET_KEY_FILE'):
    os.environ.setdefault('VF_SECRET_KEY','daily-preparation-unit-only')
import django
django.setup()
from mta.runtime import production_daily as native
from mta.runtime import daily_preparation as preparation
from mta.runtime.accepted_daily import split, join
from mta.application.production_csv import assemble
from mta.application.production_csv_files import load_binding
from tests.production_daily_fixture import day_input
from tests.test_production_daily_contract import encoded_day


class DailyPreparationTests(unittest.TestCase):
    def test_validated_native_parse_has_one_owner_and_no_repeat_typed_decode(self):
        value=day_input('2037-04-10',root=True)
        raw, sha = encoded_day(value)
        with patch.object(native,'decode_value',wraps=native.decode_value) as decoder:
            owned = preparation.prepare(raw, sha)
            self.assertEqual(native.decode(owned,sha),value)
            self.assertIs(preparation.prepare(owned,sha),owned)
            self.assertEqual(decoder.call_count,1)
            with self.assertRaises(ValueError): native.decode(owned,'a'*64)
            owned.release()
            with self.assertRaises(ValueError): native.decode(owned,sha)
        with self.assertRaises(ValueError): preparation.PreparedDaily(None,value,sha)

    def test_invalid_csv_graph_is_not_consumed_before_aggregated_diagnostics(self):
        from mta.application.streamed_input import StreamedInput
        from mta.serialization import canonical_parts
        value = day_input('2037-04-10',root=True); value['day']['raw_daily'][0]['Stock']='invalid'
        sha=hashlib.sha256(b''.join(canonical_parts(value,ensure_ascii=False))).hexdigest()
        raw=StreamedInput.take(value,sha)
        with self.assertRaises(ValueError): preparation.prepare(raw,sha)
        self.assertIsNotNone(raw._value)

    def test_csv_transfer_and_fact_metadata_roundtrip_preserve_all_populations(self):
        from tools.create_daily_csv_example import create
        from mta.serialization import digest
        archive=Path(__file__).resolve().parents[1]/'examples/starter-data/vectorflow-starter-inputs-v1.zip'
        with tempfile.TemporaryDirectory() as directory:
            root=create(archive,Path(directory)/'csv')
            binding=load_binding(root/'binding-template.json')
            for business_date, first in (('2026-10-18',True),('2026-10-19',False)):
                batch=json.loads((root/business_date/'batch.json').read_bytes())
                payloads={name:root/business_date/name for name,state in batch['feeds'].items() if state=='PRESENT'}
                target=Path(directory)/(business_date+'.json')
                raw,positions=assemble(batch,binding,payloads,first_day=first,output_file=target,_transfer=True)
                sha=hashlib.sha256(target.read_bytes()).hexdigest()
                self.assertEqual(raw.sha256,sha)
                parsed=preparation.prepare(raw,sha).checked(sha)
                tree,populations=split(parsed,binding['intake_schema'])
                self.assertEqual(digest(join(tree,populations)),digest(parsed))
                self.assertFalse(any(isinstance(v,list) and v and isinstance(v[0],dict)
                    for v in tree.values()))
                expected=len(batch['feeds'])+(4 if first else 0)
                self.assertEqual(len(populations),expected)
