import json
from pathlib import Path
import tempfile
import unittest
import uuid
from datetime import date
from types import SimpleNamespace as NS
from unittest.mock import patch
from mta.serialization import digest
from mta.presentation import scoped_selection as module


def anchor():
    value = {field: 'a' * 64 for field in module.FIELDS}
    value.update(schema=module.SCHEMA, run_id=str(uuid.uuid4()), phase_id=str(uuid.uuid4()), business_date='2037-04-10')
    value['selection_digest'] = digest({k: v for k, v in value.items() if k != 'selection_digest'})
    return value


class ScopedSelectionTests(unittest.TestCase):
    def test_dbm_anchor_has_separate_schema_and_checksum_without_changing_bpr_shape(self):
        value=anchor()
        dbm=dict(value,schema=module.DBM_SCHEMA)
        with self.assertRaises(ValueError):module.validate(dbm)
        dbm['selection_digest']=digest({k:v for k,v in dbm.items() if k!='selection_digest'})
        self.assertEqual(module.validate(dbm),dbm)
        self.assertEqual(module.validate(value),value)
        self.assertEqual(set(dbm),set(value))

    def test_exact_codec_atomic_readback_duplicate_and_bound_denials(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'selection.json'
            value = anchor(); module.write(path, value)
            self.assertEqual(module.read(path), value)
            self.assertEqual(list(Path(directory).iterdir()), [path])
            for raw in (json.dumps(dict(value, selection_digest='b' * 64)),
                        json.dumps(value)[:-1] + ',"schema":' + json.dumps(module.SCHEMA) + '}', ' ' * 8193):
                path.write_text(raw)
                with self.assertRaises(ValueError): module.read(path)

    def test_full_bundle_unknown_fields_types_and_invalid_digest_deny(self):
        for change in (dict(schema='fresh-production-selection-v1'), dict(run_id='invalid'),
                       dict(phase_digest='g' * 64), dict(business_date='10-Apr-2037'), dict(native_digest=True), dict(extra='x')):
            with self.subTest(change=change), self.assertRaises(ValueError): module.validate(dict(anchor(), **change))

    def test_invalid_atomic_candidate_leaves_prior_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'selection.json'; value = anchor(); module.write(path, value)
            with self.assertRaises(ValueError): module.write(path, dict(value, capture_digest='b' * 64))
            self.assertEqual(module.read(path), value)


class NativePhaseIdentityTests(unittest.TestCase):
    def setUp(self):
        from django.test import override_settings
        from mta.presentation.context import PublicationUnavailable
        self.denied = PublicationUnavailable
        self.enterContext(override_settings(VF_MTA_NATIVE_PUBLICATION=True, VF_MTA_DAILY_PUBLICATION=True))
        self.run = NS(pk=uuid.uuid4(), kind='DAILY_CHAIN', evidence_mode='production', status='RUNNING',
            input_payload={}, predecessor_id=None, business_date=date(2037, 4, 10))
        self.profile = {'declared': 'native-contract-unit'}
        self.owner = NS(pk=uuid.uuid4(), source=NS(digest='source'), input_sha256='input', input_digest='content',
            configuration_digest=digest(self.profile), opening_date=date(2037, 4, 9))
        self.binding = dict(id=str(self.owner.pk), source_digest='source', input_sha256='input',
            content_digest='content', configuration_digest=self.owner.configuration_digest)
        self.capture = NS(status='CAPTURED', source_id=17, revision_digest='revision',
            source=NS(receipt={'schema': 'fresh-production-mdm-source-v1'}))
        phase = NS(source_id=17, capture_digest='revision')
        self.view = NS(run=self.run, bpr=NS(reports=NS(generation=NS(phase=phase,
            configuration_digest=self.owner.configuration_digest))))
        self.inputs = dict(initialization_binding=self.binding, profile=self.profile, lineage={})
        self.enterContext(patch('mta.runtime.input_reader.read_input', return_value=self.inputs))
        owner = self.enterContext(patch('mta.runtime.initialization_models.ProductionInitialization.objects.select_related'))
        owner.return_value.get.return_value = self.owner
        capture = self.enterContext(patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.select_related'))
        capture.return_value.get.return_value = self.capture

    def test_captured_phase_and_consumed_completed_run_have_same_immutable_native_identity(self):
        first = module.native_identity(self.view)
        self.run.status = 'SUCCEEDED'; self.capture.status = 'CONSUMED'
        self.assertEqual(module.native_identity(self.view), first)

    def test_wrong_source_capture_profile_initialization_and_opening_date_deny(self):
        for target, key, wrong in ((self.capture, 'status', 'CONSUMED'),
                (self.capture, 'source_id', 99), (self.capture, 'revision_digest', 'wrong'),
                (self.owner, 'opening_date', date(2037, 4, 8))):
            original = getattr(target, key); setattr(target, key, wrong)
            with self.subTest(key=key), self.assertRaises(self.denied): module.native_identity(self.view)
            setattr(target, key, original)
        self.inputs['initialization_binding'] = dict(self.binding, id=str(uuid.uuid4()))
        with self.assertRaises(self.denied): module.native_identity(self.view)
        self.inputs['initialization_binding'] = self.binding
        self.inputs['profile'] = {'changed': True}
        with self.assertRaises(self.denied): module.native_identity(self.view)

    def test_predecessor_requires_exact_initialized_consecutive_completed_parent(self):
        parent = NS(pk=uuid.uuid4(), kind='DAILY_CHAIN', status='SUCCEEDED', business_date=date(2037, 4, 9), output_digest='parent-output')
        self.run.predecessor = parent; self.run.predecessor_id = parent.pk
        self.inputs['lineage'] = dict(run_id=str(parent.pk), output_digest='parent-output')
        module.native_identity(self.view)
        self.inputs['lineage']['output_digest'] = 'wrong'
        with self.assertRaises(self.denied): module.native_identity(self.view)
