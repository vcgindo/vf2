"""Finite upgrade authority and unused-owner boundary; native proof is separate."""
from copy import deepcopy
from importlib import import_module
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'registered-report-schema-component')
import django
django.setup()
from mta.runtime import registered_report_schema_transition as upgrade
from mta.runtime import ingestion_authority as authority
from mta.runtime import ingestion_admission as admission
from mta.serialization import digest


class RegisteredReportTransitionTests(unittest.TestCase):
    def delta(self, owner='test_owner', consumer='test_reader'):
        def grant(role):
            name='mta.fresh_mta_reportdefinitionregistration'
            return ('grants:'+name+':None:'+owner+':'+role+':SELECT',
                    dict(before=None,after=dict(owner=owner,grantee=role,privilege='SELECT')))
        return dict([('functions:mta.ingestion_watch()',
                      dict(before=dict(owner=owner,body='old'),after=dict(owner=owner,body='new'))),
                     grant(owner),grant(consumer),grant('fresh_operational_acceptor')])

    def test_normalization_preserves_acceptor_and_guard_semantics(self):
        delta=self.delta()
        self.assertEqual(upgrade.catalogue_contract(delta),
                         upgrade.catalogue_contract(self.delta('other_owner','other_reader')))
        changed=deepcopy(delta)
        changed['functions:mta.ingestion_watch()']['after']['body']='other'
        self.assertNotEqual(upgrade.catalogue_contract(delta),upgrade.catalogue_contract(changed))
        changed=deepcopy(delta)
        key=next(k for k in changed if ':fresh_operational_acceptor:' in k)
        changed[key]['after']['grantee']='unqualified_acceptor'
        with self.assertRaises(ValueError):upgrade.catalogue_contract(changed)

    def test_exact_delta_and_ordered_migration_bytes_required(self):
        spec=dict(migration_pins=upgrade.migration_pins(),catalogue_delta=self.delta())
        with self.assertRaises(ValueError):upgrade.require_specification(spec)
        with patch.object(upgrade,'CATALOGUE_DELTA_DIGEST',upgrade.catalogue_contract(spec['catalogue_delta'])):
            upgrade.require_specification(spec)
            for pins in (spec['migration_pins'][:-1],list(reversed(spec['migration_pins'])),
                         [[name,'0'*64] for name,_ in spec['migration_pins']]):
                with self.assertRaisesRegex(ValueError,'migration bytes'):
                    upgrade.require_specification(dict(spec,migration_pins=pins))
            changed=deepcopy(spec);changed['catalogue_delta']['functions:mta.ingestion_watch()']['after']['body']='tampered'
            with self.assertRaisesRegex(ValueError,'catalogue'):
                upgrade.require_specification(changed)

    def test_authority_only_adds_exact_names(self):
        value={key:'a'*64 for key in authority.SCHEMA_FIELDS}
        value.update(contract=authority.SCHEMA_CONTRACT,initialization_id=str(uuid4()),
                     target_commit='b'*40,migration_pins=upgrade.migration_pins())
        self.assertEqual(authority.validate_schema_transition(value),value)
        for name in ('0233_arbitrary','0238_intake_diagnostic_guards'):
            with self.assertRaises(ValueError):
                authority.validate_schema_transition(dict(value,migration_pins=[[name,'a'*64]]))

    def start_answers(self):
        placement=import_module('mta.runtime.migrations.0231_runtime_report_placement_guards')
        publication=import_module('mta.runtime.migrations.0230_runtime_report_publication_guards')
        return [('0232_runtime_report_consumer_read',),(None,),
                (placement.NEW,),(publication.READ_REFERENCE_BODY,),(placement.SOURCE,),
                (False,),(False,),(False,)]

    def require_start(self, answers, guard=True):
        from unittest.mock import Mock
        cursor=Mock();cursor.fetchone.side_effect=answers
        with patch('mta.runtime.ingestion_ownership.migration_history_guard',return_value=guard):
            upgrade.require_start(cursor)
        return cursor

    def test_start_refuses_existing_schema_extension_and_any_run_attempt_capture(self):
        answers=self.start_answers()
        self.require_start(answers)
        for index,replacement in ((0,('0231_runtime_report_placement_guards',)),
                (1,('fresh_control.ingestion_schema_compatibility',)),(2,('changed',)),
                (3,('changed',)),(4,('changed',)),(5,(True,)),(6,(True,)),(7,(True,))):
            changed=list(answers);changed[index]=replacement
            with self.subTest(index=index),self.assertRaises(ValueError):self.require_start(changed)
        with self.assertRaisesRegex(ValueError,'history guard'):self.require_start(answers,False)

    def test_schema_chain_accepts_once_and_refuses_repeated_or_partial_profile(self):
        cert=dict(schema_digest='s0',guard_digest='g0',receipt_digest='r',release_digest='0'*64)
        origin={k:'fixed' for k in authority.FIELDS}
        origin.update(initialization_id=str(uuid4()),target_commit='0'*40,target_release='0'*64)
        target=dict(origin,target_commit='1'*40,target_release='1'*64)
        link=dict(contract=authority.SCHEMA_CONTRACT,previous_release=origin['target_release'],
                  previous_authority_digest=digest(origin),certification_digest='r',
                  target_commit=target['target_commit'],migration_pins=upgrade.migration_pins(),
                  before_schema_digest='s0',before_guard_digest='g0',schema_digest='s1',guard_digest='g1')
        links={target['target_release']:link};bodies={origin['target_release']:origin,target['target_release']:target}
        def resolve(body):
            with patch.object(admission,'_activation_metadata',return_value=cert),\
                    patch.object(authority,'read',side_effect=lambda c,i,r:bodies[r]),\
                    patch.object(authority,'read_schema_transition',side_effect=lambda c,b:links.get(b['target_release'])):
                return admission.effective_schema(None,body)
        self.assertEqual(resolve(target)[2:4],('s1','g1'))
        link['migration_pins']=upgrade.migration_pins()[:-1]
        with self.assertRaisesRegex(ValueError,'registered report'):resolve(target)
        link['migration_pins']=upgrade.migration_pins()
        repeated=dict(target,target_commit='2'*40,target_release='2'*64)
        bodies[repeated['target_release']]=repeated
        links[repeated['target_release']]=dict(link,previous_release=target['target_release'],
            previous_authority_digest=digest(target),target_commit=repeated['target_commit'],
            before_schema_digest='s1',before_guard_digest='g1',schema_digest='s2',guard_digest='g2')
        with self.assertRaisesRegex(ValueError,'registered report'):resolve(repeated)
