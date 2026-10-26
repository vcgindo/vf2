"""Affected configuration and source-to-file contracts; native proof is separate."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from mta.serialization import digest
from mta.runtime import scope_runtime_reports as contracts
from mta.runtime import runtime_report_publication as publication
from mta.runtime import runtime_report_candidates as candidates
from mta.application.runtime_report_configuration import SCHEMA,last_generated,definition_digest
from mta.application.runtime_report_hooks import SCHEMA as HOOK
from mta.runtime.runtime_report_catalogue import ANCHOR_SCHEMA
from tests.test_runtime_report_candidates import arguments


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)


def reference():
    config=arguments()['report_configuration']
    hook=dict(schema=HOOK,site_code='SUPPLIED-INSTANCE',placement='PostBPR',mode='declared-no-op',
              authority='explicit test fixture authorization',source_sha256='a'*64)
    anchor=dict(schema=ANCHOR_SCHEMA,kind='INITIALIZATION',identity=str(uuid4()),output_digest=None,
        configuration_digest=digest(config),definition_digest=definition_digest(config),catalogue={},
        last_generated=last_generated(config),evidence={'authority':'a'*64,'source':'b'*64})
    return dict(schema=contracts.PUBLICATION_REFERENCE,purpose='owned-postbpr-publication-test',
        configuration_json=canonical(config),configuration_digest=digest(config),hook_json=canonical(hook),
        catalogue_anchor_json=canonical(anchor),authority_sha256='a'*64)


class PublicationConfiguration(unittest.TestCase):
    def test_new_reference_preserves_complete_native_definitions_as_metadata(self):
        value=reference();config,hook,anchor=contracts.publication_configuration(value)
        self.assertEqual(config,arguments()['report_configuration'])
        self.assertEqual(anchor['last_generated'],last_generated(config))
        self.assertEqual(hook['site_code'],'SUPPLIED-INSTANCE')
        self.assertTrue(all(type(item) is str for item in value.values()))
        raw=canonical(value).encode()
        self.assertEqual(contracts.decode(raw,hashlib.sha256(raw).hexdigest()),value)

    def test_old_empty_test_bytes_keep_their_existing_reference(self):
        value=dict(schema=contracts.SCHEMA,purpose='owned-scoped-test',provenance='retained explicit approval',RuntimeReports=[])
        raw=json.dumps(value).encode();pin=hashlib.sha256(raw).hexdigest()
        expected=dict(schema=contracts.REFERENCE,sha256=pin,configuration=value,configuration_digest=digest(value))
        self.assertEqual(contracts.decode(raw,pin),expected)

    def test_wrong_or_rehashed_unsupported_selector_denies(self):
        value=reference();config=json.loads(value['configuration_json'])
        config['RuntimeReports'][0]['ReportName']='another-report'
        value['configuration_json']=canonical(config);value['configuration_digest']=digest(config)
        with self.assertRaisesRegex(ValueError,'selector'):contracts.publication_configuration(value)

    def test_duplicate_metadata_keys_and_noncanonical_bytes_deny(self):
        value=reference();value['configuration_json']='{"schema":"a","schema":"b"}'
        with self.assertRaises(ValueError):contracts.publication_configuration(value)
        value=reference();value['configuration_json']=' '+value['configuration_json']
        with self.assertRaisesRegex(ValueError,'Canonical'):contracts.publication_configuration(value)

    def test_missing_catalogue_and_wrong_filename_seed_deny(self):
        value=reference();anchor=json.loads(value['catalogue_anchor_json'])
        anchor['catalogue']=None;value['catalogue_anchor_json']=canonical(anchor)
        with self.assertRaises(ValueError):contracts.publication_configuration(value)
        value=reference();anchor=json.loads(value['catalogue_anchor_json'])
        anchor['last_generated'][0]['LastGeneratedFileName']='foreign-name'
        value['catalogue_anchor_json']=canonical(anchor)
        with self.assertRaisesRegex(ValueError,'seed'):contracts.publication_configuration(value)

    def test_compatibility_mode_cannot_start_a_new_publication(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,'does not enable'):contracts.require_publication_writer()
        with patch.dict(os.environ,{'VF_RUNTIME_REPORT_PUBLISH':'1'}):contracts.require_publication_writer()


class SourceContent(unittest.TestCase):
    def test_rehashed_other_source_csv_and_archive_are_rejected(self):
        values=arguments()
        with tempfile.TemporaryDirectory() as root:
            candidate=candidates.materialize(root=root,candidate_id=str(uuid4()),**values)
            definitions=sorted(values['report_configuration']['RuntimeReports'],key=lambda row:row['Id'])
            publication._content(definitions,values['inputs'],candidate)
            forged=deepcopy(candidate)
            for record in forged['reports'][0]['write']:
                record['members'][0]['sha256']='f'*64
            forged['digest']=digest({key:value for key,value in forged.items() if key!='digest'})
            with self.assertRaisesRegex(ValueError,'Source-derived archive'):
                publication._content(definitions,values['inputs'],forged)
            forged=deepcopy(candidate)
            for record in forged['reports'][1]['write']:record['sha256']='e'*64
            forged['digest']=digest({key:value for key,value in forged.items() if key!='digest'})
            with self.assertRaisesRegex(ValueError,'Source-derived report'):
                publication._content(definitions,values['inputs'],forged)
