"""Finite222 upgrade pins, ownership delta and historical-admission boundary."""
import hashlib
from copy import deepcopy
from pathlib import Path
from importlib import import_module
import unittest
from mta.runtime import scoped_action_transition as transition
from mta.serialization import digest


class ScopedActionTransitionTests(unittest.TestCase):
    def spec(self, bootstrap=False):
        return dict(previous_release=dict(source_commit=transition.PREVIOUS_COMMIT,
            manifest_sha256=transition.PREVIOUS_RELEASE),migration_pins=transition.migration_pins(),
            catalogue_delta=transition.catalogue_delta(bootstrap=bootstrap))

    def test_migration_bytes_and_only_exact_predecessor_function_replacement(self):
        path=Path(__file__).resolve().parents[1]/'mta/runtime/migrations'/(transition.MIGRATION_NAME+'.py')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),transition.MIGRATION_SHA256)
        migration=import_module('mta.runtime.migrations.'+transition.MIGRATION_NAME)
        self.assertIn('$expected$'+migration.OLD+'$expected$',migration.SQL)
        self.assertEqual(migration.SQL.count('CREATE OR REPLACE FUNCTION'),1)
        for forbidden in ('CREATE TABLE','GRANT ','DROP FUNCTION','UPDATE mta.', 'DELETE FROM'):
            self.assertNotIn(forbidden,migration.SQL)

    def test_specification_and_receipt_are_exact_for_both_registrar_states(self):
        for bootstrap in (False, True):
            spec=self.spec(bootstrap)
            transition.require_specification(spec)
            receipt=dict(migration_pins=spec['migration_pins'],
                previous_release=transition.PREVIOUS_RELEASE,before_schema_digest=transition.BEFORE_SCHEMA,
                before_guard_digest=transition.BEFORE_GUARD,catalogue_delta_digest=digest(spec['catalogue_delta']))
            self.assertTrue(transition.approved_receipt(receipt))
            for field in receipt:
                self.assertFalse(transition.approved_receipt(dict(receipt,**{field:'changed'})))
            changed=deepcopy(spec);changed['catalogue_delta']['arbitrary']={'before':None,'after':'DDL'}
            with self.assertRaises(ValueError):transition.require_specification(changed)
            changed=deepcopy(spec);changed['migration_pins'][0][0]='0223_arbitrary'
            with self.assertRaises(ValueError):transition.require_specification(changed)

    def test_bootstrap_only_adds_exact_registrar_relation(self):
        delta=transition.catalogue_delta(bootstrap=True)
        function=next(k for k in delta if k.startswith('functions:'))
        self.assertEqual(transition.catalogue_delta(),{function:delta[function]})
        for key,value in delta.items():
            if key!=function:
                self.assertIn('ingestion_schema_compatibility',key)
                self.assertIsNone(value['before'])
        self.assertEqual(delta[function]['before']['owner'], 'vftest_g2n_20261024_owner')
        table='fresh_control.ingestion_schema_compatibility'
        readers={value['after']['grantee'] for key,value in delta.items()
            if key.startswith('grants:') and value['after']['grantee']!='fresh_namespace_registrar'}
        self.assertEqual(readers,{'vftest_g2n_20261024_owner','vftest_g2n_20261024_runtime'})
        self.assertFalse(any('vectorflow_mta_' in key for key in delta))
        self.assertEqual(delta['column:'+table+'.body']['after'],[3,'jsonb',True,'','',None])
        self.assertEqual(delta['index:fresh_control.ingestion_schema_compatibility_pkey']['after'],
            ['CREATE UNIQUE INDEX ingestion_schema_compatibility_pkey ON '+table+
             ' USING btree (initialization_id, target_release)'])
        self.assertEqual(delta['trigger:'+table+'.ingestion_schema_transition_immutable']['after'],
            ['O','CREATE TRIGGER ingestion_schema_transition_immutable BEFORE DELETE OR UPDATE OR TRUNCATE ON '+
             table+' FOR EACH STATEMENT EXECUTE FUNCTION fresh_control.ingestion_transition_immutable()'])

    def test_authority_exception_names_only222(self):
        from mta.runtime import ingestion_authority as authority
        from uuid import uuid4
        body={key:'a'*64 for key in authority.SCHEMA_FIELDS}
        body.update(contract=authority.SCHEMA_CONTRACT,initialization_id=str(uuid4()),
            target_commit='b'*40,migration_pins=transition.migration_pins())
        self.assertEqual(authority.validate_schema_transition(body),body)
        for name in ('0222_arbitrary','0221_scoped_action_cache_writer','0223_recovered_scope_actions'):
            with self.assertRaises(ValueError):
                authority.validate_schema_transition(dict(body,migration_pins=[[name,'a'*64]]))
