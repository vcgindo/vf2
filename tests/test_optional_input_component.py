"""Optional-policy absence requires authenticated, explicit object structure."""
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch

from tests.test_input_storage_v3 import MemoryImages, identity, table, OWNER
from mta.runtime import input_storage, input_v3
from mta.serialization import digest


class OptionalComponentTests(TestCase):
    def owner(self, raw, version):
        raw = deepcopy(raw)
        original_profile = raw['profile']
        unsupported = not isinstance(original_profile, dict)
        if unsupported:
            raw['profile'] = {}
        raw['profile'].setdefault('delivery', {'site_code': 'PURE'})
        images = MemoryImages()
        owner = NS(pk=OWNER, input_digest=digest(raw))
        options = dict(image_writer=images.write, table_selector=table)
        if version == 3:
            options['identity_resolver'] = identity
        owner.input_payload = input_storage.save_input(owner, raw, version=version, **options)
        if unsupported:
            for pair in owner.input_payload['tree']['object']:
                if pair[0] == 'profile':
                    pair[1] = {'empty': []} if original_profile == [] else {'scalar': None}
        owner.input_manifest_digest = digest(owner.input_payload)
        return owner

    def test_v2_v3_absence_present_null_and_unsupported_profile(self):
        with patch.object(input_v3, '_live_identity', side_effect=lambda owner, **kw: identity(owner)):
            for version in (2, 3):
                for raw, expected in (({'profile': {'other': 1}}, True),
                        ({'profile': {'native_upload_audit': None}}, False),
                        ({'profile': []}, False), ({'profile': None}, False)):
                    owner = self.owner(raw, version)
                    self.assertEqual(input_v3.component_absent(owner,
                        'input/profile/native_upload_audit'), expected)

    def test_manifest_drift_rejected_without_value_read(self):
        owner = self.owner({'profile': {'other': 1}}, 2)
        owner.input_payload['tree']['object'][0][1] = {'object': []}
        with self.assertRaisesRegex(ValueError, 'manifest identity drift'):
            input_v3.component_absent(owner, 'input/profile/native_upload_audit')

    def test_duplicate_and_malformed_object_never_prove_absence(self):
        owner = self.owner({'profile': {}}, 2)
        for children in ([['profile', {'object': []}], ['profile', {'object': []}]],
                         [['profile']]):
            owner.input_payload['tree'] = {'object': deepcopy(children)}
            owner.input_manifest_digest = digest(owner.input_payload)
            with self.assertRaises(ValueError):
                input_v3.component_absent(owner, 'input/profile/native_upload_audit')

    def test_shared_owner_validation_failure_propagates(self):
        owner = NS(input_payload={'schema': input_v3.V3, 'tree': {'object': [
            ['profile', {'owner_reference': 'input/profile'}]]},
            'owner_references': {'input/profile': {}}})
        with patch.object(input_storage, 'read_input', return_value={}), \
                patch.object(input_v3, '_identity', return_value={}), \
                patch.object(input_v3, '_owner_manifest', side_effect=ValueError('foreign owner')):
            with self.assertRaisesRegex(ValueError, 'foreign owner'):
                input_v3.component_absent(owner, 'input/profile/native_upload_audit')
