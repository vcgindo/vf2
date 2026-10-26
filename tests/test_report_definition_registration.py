"""Typed definition/seed custody; no database registration or native claims."""
from copy import deepcopy
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from mta.runtime import report_definition_registration as registration
from mta.serialization import digest
from tests.test_runtime_report_request import fixture, canonical, replace_config


INIT = '10000000-0000-4000-8000-000000000001'
CERT = '10000000-0000-4000-8000-000000000002'


def encode(reference=None):
    return registration.encode(reference or fixture(), initialization_id=INIT,
        source_digest='b'*64, certificate_id=CERT, certificate_digest='c'*64)


class DefinitionRegistrationTests(unittest.TestCase):
    def test_independent_native_columns_and_seed_round_trip(self):
        source = fixture(); before = deepcopy(source)
        packed = encode(source)
        self.assertEqual(registration.decode(packed), source)
        self.assertEqual(source, before)
        self.assertEqual([r['Id'] for r in packed['report_rows']], [2,3,4,5,6,7,8,10])
        for row in packed['report_rows']:
            self.assertEqual(len(row), 16)  # fifteen definition columns plus ordinal
            self.assertNotIn('LastGeneratedFileName', row)
            self.assertIsNone(row['TemplateName'])
            self.assertIsNone(row['TemplateLoc'])
            self.assertEqual(row['Delimeter'], ',')
        self.assertEqual(packed['seed_rows'][-1], dict(ordinal=7, Id=10,
            LastGeneratedFileName='TotalReqReport_20260407'))
        self.assertEqual(packed['ui_rows'], [dict(ordinal=0, ReportName='RRR', Active=False,
            GenerationScope='PostBPR', DestFolder='%ReportsDownloadLoc%')])
        self.assertEqual(packed['header']['reference_digest'], digest(source))

    def test_row_join_cannot_hide_duplicate_missing_reordered_or_foreign_seed(self):
        for change in ('missing', 'duplicate', 'order', 'foreign', 'bool-ordinal', 'extra'):
            value = encode()
            if change == 'missing': value['seed_rows'].pop()
            elif change == 'duplicate': value['seed_rows'][1] = deepcopy(value['seed_rows'][0])
            elif change == 'order': value['seed_rows'].reverse()
            elif change == 'foreign': value['seed_rows'][0]['Id'] = 100
            elif change == 'bool-ordinal': value['seed_rows'][0]['ordinal'] = False
            else: value['report_rows'][0]['LastGeneratedFileName'] = 'hidden'
            with self.subTest(change=change), self.assertRaises(ValueError):
                registration.decode(value)

    def test_rehashed_definition_policy_and_seed_edits_do_not_expand_supported_boundary(self):
        for change in ('query', 'destination', 'template', 'hook', 'seed', 'ui-empty', 'ui-inactive'):
            value = fixture(); config = json.loads(value['configuration_json'])
            if change == 'query': config['RuntimeReports'][0]['Query'] += ' '
            elif change == 'destination': config['RuntimeReports'][0]['DestFolder'] = '/tmp'
            elif change == 'template': config['RuntimeReports'][0]['TemplateName'] = 'new'
            elif change == 'seed': config['RuntimeReports'][0]['LastGeneratedFileName'] = 'new'
            elif change == 'ui-empty': config['DownloadableUIReportSettings'] = []
            elif change == 'ui-inactive': config['DownloadableUIReportSettings'][0]['ReportName'] = 'OTHER'
            else:
                policy = json.loads(value['disposition_json']); policy['hooks']['PostBPR'] = 'execute'
                value['disposition_json'] = canonical(policy)
            replace_config(value, config)
            with self.subTest(change=change), self.assertRaises(ValueError): encode(value)

    def test_persisted_header_and_rows_are_checked_independently(self):
        for field in ('configuration_digest', 'definition_digest', 'seed_digest',
                      'policy_digest', 'reference_digest'):
            value = encode(); value['header'][field] = 'f'*64
            value['registration_digest'] = digest(value['header'])
            with self.subTest(field=field), self.assertRaises(ValueError): registration.decode(value)
        value = encode(); value['report_rows'][0]['HeaderList'] = None
        with self.assertRaises(ValueError): registration.decode(value)

    def test_source_and_certificate_have_distinct_registration_identities(self):
        reference = fixture()
        original = encode(reference)
        other = registration.encode(reference, initialization_id=INIT, source_digest='d'*64,
            certificate_id=CERT, certificate_digest='c'*64)
        self.assertNotEqual(original['registration_digest'], other['registration_digest'])
        self.assertEqual(registration.decode(other), reference)
        # Codec equality alone is not authority for a different source; the
        # future database registrar must authenticate these caller-owned pins.
        with self.assertRaises(ValueError):
            registration.encode(reference, initialization_id=CERT, source_digest='b'*64,
                certificate_id=CERT, certificate_digest='c'*64)

    def test_null_empty_and_scalar_tags_are_not_normalized(self):
        value = encode(); value['report_rows'][0]['TemplateName'] = ''
        with self.assertRaises(ValueError): registration.decode(value)
        for bit in (0, None):
            reference = fixture(); config = json.loads(reference['configuration_json'])
            config['DownloadableUIReportSettings'][0]['Active'] = bit
            replace_config(reference, config)
            with self.subTest(bit=bit), self.assertRaises(ValueError): encode(reference)

    def test_noncanonical_config_bytes_are_not_silently_resealed(self):
        reference = fixture()
        reference['configuration_json'] = json.dumps(json.loads(reference['configuration_json']), indent=2)
        with self.assertRaisesRegex(ValueError, 'Canonical report metadata bytes differ'):
            encode(reference)

    def test_command_input_is_hash_bound_and_rejects_duplicate_keys(self):
        from mta.runtime.management.commands.register_runtime_report_configuration import read_reference
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'configuration.json'
            raw = canonical(fixture()).encode(); path.write_bytes(raw)
            self.assertEqual(read_reference(path, hashlib.sha256(raw).hexdigest()), fixture())
            with self.assertRaises(ValueError): read_reference(path, '0'*64)
            raw = b'{"schema":"first","schema":"second"}'; path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                read_reference(path, hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':
    unittest.main()
