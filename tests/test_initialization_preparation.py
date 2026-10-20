"""The private preparation owner validates once and cannot be reused as a bypass.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','preparation-unit-only')
import django
django.setup()
from mta.mdm import initialization_contract as contract
from mta.mdm.initialization_preparation import prepare,PreparedInitialization
from mta.serialization import digest
from tests.initialization_input_fixture import supplied_input,encoded


class PreparationTests(unittest.TestCase):
    def test_one_parse_one_authoritative_decode_and_single_exact_claim(self):
        raw,sha,args=encoded(supplied_input())
        from mta.runtime import production_preflight as preflight
        with patch.object(preflight,'parse',wraps=preflight.parse) as parse, \
                patch.object(contract,'decode_value',wraps=contract.decode_value) as decode:
            prepared=prepare(raw,sha,**args)
        self.assertEqual((parse.call_count,decode.call_count),(1,1))
        with self.assertRaisesRegex(ValueError,'identity differs'):
            prepared.claim('0'*64,args['expected_configuration'],args['expected_recipe'])
        _,frame,_=prepared.claim(sha,args['expected_configuration'],args['expected_recipe'])
        self.assertEqual(digest(frame),prepared.content_digest)
        with self.assertRaisesRegex(ValueError,'already consumed'):
            prepared.claim(sha,args['expected_configuration'],args['expected_recipe'])
        with self.assertRaises(ValueError):
            PreparedInitialization(None,(None,frame,[]),(),{})

    def test_csv_enters_same_preparation_once_and_releases_exclusive_envelope(self):
        from mta.application.initialization_csv import create,read_prepared,MANIFEST
        value=supplied_input()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'opening';manifest,_=create(value,root)
            pin=hashlib.sha256((root/MANIFEST).read_bytes()).hexdigest()
            args=dict(expected_configuration=manifest['configuration_digest'],expected_recipe=manifest['recipe_digest'])
            with patch.object(contract,'decode_value',wraps=contract.decode_value) as decode:
                prepared=read_prepared(root,pin,**args)
            self.assertEqual(decode.call_count,1)
            self.assertIsNone(prepared._decoded[0])
            with self.assertRaises(ValueError):
                read_prepared(root,'0'*64,**args)

    def test_invalid_payload_retains_aggregated_diagnostics(self):
        value=supplied_input()
        value['masters']['importer'].pop('SKUDescriptionTbl')
        raw,sha,args=encoded(value)
        from mta.runtime.production_preflight import PreflightError
        with self.assertRaises(PreflightError) as error:
            prepare(raw,sha,**args)
        report=error.exception.report
        self.assertFalse(report['stage_eligibility']['installation'])
        self.assertGreater(len(report['issues']),1)
