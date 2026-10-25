"""Finite native transition pins and exact old/new application capabilities."""
import hashlib
from pathlib import Path
from importlib import import_module
from unittest.mock import Mock
import unittest
from mta.runtime import scoped_dbm_transition as transition


class ScopedDbmTransitionTests(unittest.TestCase):
    def test_migration_pins_and_receipt_reject_every_identity_change(self):
        for name,pin in transition.PINS:
            path=Path(__file__).resolve().parents[1]/'mta/runtime/migrations'/(name+'.py')
            self.assertEqual(hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest(),pin)
        value=dict(initialization_id=transition.INITIALIZATION,migration_pins=transition.migration_pins(),
            previous_release=transition.PREVIOUS_RELEASE,before_schema_digest=transition.BEFORE_SCHEMA,
            before_guard_digest=transition.BEFORE_GUARD,schema_digest=transition.AFTER_SCHEMA,
            guard_digest=transition.AFTER_GUARD,catalogue_delta_digest=transition.DELTA)
        self.assertTrue(transition.approved_receipt(value))
        for name in value:
            with self.subTest(field=name):self.assertFalse(transition.approved_receipt(dict(value,**{name:'changed'})))

    def test_schema_authority_accepts_only_three_named_new_migrations(self):
        from mta.runtime.ingestion_authority import SCHEMA_FIELDS,SCHEMA_CONTRACT,validate_schema_transition
        value={key:'a'*64 for key in SCHEMA_FIELDS}
        value.update(contract=SCHEMA_CONTRACT,initialization_id=transition.INITIALIZATION,
            target_commit='b'*40,migration_pins=transition.migration_pins())
        self.assertEqual(validate_schema_transition(value),value)
        for name in ('0224_arbitrary','0226_any_guard','0227_scoped_dbm_action_dependencies'):
            with self.assertRaises(ValueError):validate_schema_transition(dict(value,migration_pins=[[name,'a'*64]]))

    def test_old_new_capability_rosters_never_accept_mixed_or_unknown_function_bodies(self):
        from mta.runtime import scoped_action_ownership as action,scoped_remark_ownership as remark
        names=('mta.stamp_scoped_action_transaction()','mta.guard_scoped_action_cache()',
               'mta.scope_cache_command(reference uuid, actor text)')
        def catalogue(module):
            return dict(functions=[dict(name=name,body=body,returns=result,security_definer=False,
                configuration=['search_path=pg_catalog, mta']) for name,body,result in zip(names,
                    (module.STAMP,module.CACHE,module.LEASE),('trigger','trigger','fresh_mta_runcommand'))])
        old=import_module('mta.runtime.migrations.0221_scoped_action_cache_writer')
        new=import_module('mta.runtime.migrations.0226_scoped_dbm_action_dependencies')
        for module in (old,new):
            data=catalogue(module)
            self.assertEqual(action.migration(catalogue=data),module)
            self.assertTrue(action.application_grants(data))
            data['functions'][1]['body']='unknown'
            with self.assertRaises(ValueError):action.application_grants(data)
        data=catalogue(old);data['functions'][1]['body']=new.CACHE
        with self.assertRaises(ValueError):action.application_grants(data)
        cursor=Mock();cursor.fetchone.return_value=(False,)
        self.assertEqual(action.migration(cursor),old)
        cursor.fetchone.return_value=(True,)
        self.assertEqual(action.migration(cursor),new)

    def test_arbitrary_delta_or_old_release_is_not_transition_authority(self):
        value=dict(initialization_id=transition.INITIALIZATION,migration_pins=transition.migration_pins(),
            previous_release=dict(source_commit=transition.PREVIOUS_COMMIT,manifest_sha256=transition.PREVIOUS_RELEASE),
            catalogue_delta={})
        with self.assertRaises(ValueError):transition.require_specification(value)
