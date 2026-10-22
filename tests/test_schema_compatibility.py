"""Exact schema-extension shape and non-mutating catalogue delta contracts.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import os
import unittest
from copy import deepcopy
from uuid import uuid4
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','schema-contract-unit-only')
import django
django.setup()
from mta.runtime import ingestion_authority as authority
from release.advance_ingestion import catalogue_delta


class SchemaCompatibilityTests(unittest.TestCase):
    def body(self):
        body={k:'a'*64 for k in authority.SCHEMA_FIELDS}
        body.update(contract=authority.SCHEMA_CONTRACT,initialization_id=str(uuid4()),
                    target_commit='b'*40,migration_pins=[['0154_daily_report_generation','c'*64]])
        return body

    def test_exact_shape_and_typed_pins(self):
        body=self.body();self.assertEqual(authority.validate_schema_transition(body),body)
        for change in ({'extra':1},{'contract':'other'},{'initialization_id':'bad'},
                       {'target_commit':'b'*39},{'guard_digest':None},{'migration_pins':[]},
                       {'migration_pins':[['../0154_bad','c'*64]]},
                       {'migration_pins':body['migration_pins']*2},
                       {'migration_pins':[['0154_name','short']]}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                authority.validate_schema_transition(dict(body,**change))

    def test_delta_preserves_complete_before_after_and_inputs(self):
        before={'same':{'value':None},'changed':[None,1,1],'removed':False}
        after={'same':{'value':None},'changed':[1,None,1],'new':{'value':0}}
        saved=deepcopy((before,after))
        self.assertEqual(catalogue_delta(before,after),{
            'changed':{'before':[None,1,1],'after':[1,None,1]},
            'new':{'before':None,'after':{'value':0}},
            'removed':{'before':False,'after':None}})
        self.assertEqual((before,after),saved)

    def test_fifth_schema_admission_remains_denied(self):
        from mta.runtime import ingestion_admission as admission
        from mta.serialization import digest
        bodies=[dict.fromkeys(authority.FIELDS,'fixed') for _ in range(6)]
        for index,body in enumerate(bodies):
            body.update(target_release=str(index)*64,target_commit=str(index)*40)
        cert=dict(schema_digest='s',guard_digest='g',receipt_digest='r')
        extensions=[dict(previous_release=bodies[i+1]['target_release'],
            previous_authority_digest=digest(bodies[i+1]),certification_digest='r',
            target_commit=bodies[i]['target_commit']) for i in range(5)]
        with patch.object(admission,'_activation_metadata',return_value=cert), \
                patch.object(authority,'read_schema_transition',side_effect=extensions), \
                patch.object(authority,'read',side_effect=bodies[1:]), \
                self.assertRaisesRegex(ValueError,'four-admission boundary'):
            admission.validate_activation(None,bodies[0])
