"""Only the pure publication predicate may acquire consumer EXECUTE."""
from copy import deepcopy
from importlib import import_module
import unittest
from mta.runtime import runtime_report_read_transition as transition


class ConsumerReadTransitionTests(unittest.TestCase):
    def spec(self):
        delta={}
        for name in transition.CATALOGUE_NAMES:
            row=dict(scope='function',name=name,column=None,owner='namespace_owner',
                grantor='namespace_owner',grantee='namespace_runtime',privilege='EXECUTE',grantable=False)
            delta['grants:'+name+':None:namespace_owner:namespace_runtime:EXECUTE']=dict(before=None,after=row)
        return dict(migration_pins=transition.migration_pins(),catalogue_delta=delta)

    def test_exact_pair_and_no_other_acl_or_body_change(self):
        spec=self.spec();transition.require_specification(spec)
        for field,value in (('grantable',True),('grantee','PUBLIC'),('privilege','INSERT'),('grantor','other')):
            wrong=deepcopy(spec);next(iter(wrong['catalogue_delta'].values()))['after'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):transition.require_specification(wrong)
        wrong=deepcopy(spec);wrong['catalogue_delta']['unrelated']={'before':None,'after':{}}
        with self.assertRaises(ValueError):transition.require_specification(wrong)
        wrong=deepcopy(spec);next(iter(wrong['catalogue_delta'].values()))['before']={}
        with self.assertRaises(ValueError):transition.require_specification(wrong)

    def test_install_profile_requires_exact_invoker_bodies(self):
        rows=[dict(name=name,body=body,security_definer=False,returns='boolean',language=14,
            configuration=['search_path=pg_catalog, mta']) for name,body in zip(transition.CATALOGUE_NAMES,transition.bodies())]
        self.assertEqual(transition.application_functions({'functions':rows}),set(transition.CATALOGUE_NAMES))
        for field,value in (('security_definer',True),('returns','text'),('body','SELECT true')):
            wrong=deepcopy(rows);wrong[0][field]=value
            if field=='body':
                self.assertEqual(transition.application_functions({'functions':wrong}),set())
            else:
                with self.subTest(field=field),self.assertRaises(ValueError):transition.application_functions({'functions':wrong})
        self.assertEqual(transition.application_functions({'functions':[]}),set())

    def test_existing_object_acl_preservation_allows_only_reviewed_addition(self):
        base=dict(scope='function',name=transition.CATALOGUE_NAMES[0],oid=32,owner=5,
            column=None,grantor=5,grantee=5,privilege='EXECUTE',grantable=False)
        unrelated=dict(base,name='mta.other()',oid=31)
        before=[unrelated,base];added=dict(base,grantee=6)
        transition.require_preserved_acl(before,[unrelated,base,added],owner_oid=5,consumer_oid=6)
        for wrong in ([base,added],[unrelated,base], [unrelated,base,dict(added,grantee=7)],
                      [unrelated,base,dict(added,grantable=True)], [unrelated,base,added,dict(unrelated,grantee=6)],
                      [unrelated,base,added,added]):
            with self.subTest(after=wrong),self.assertRaises(ValueError):
                transition.require_preserved_acl(before,wrong,owner_oid=5,consumer_oid=6)

    def test_migration_has_no_new_writer_or_definer_and_prior_bodies_unchanged(self):
        migration=import_module('mta.runtime.migrations.0232_runtime_report_consumer_read')
        self.assertEqual(migration.Migration.dependencies,[('fresh_mta','0231_runtime_report_placement_guards')])
        self.assertNotIn('CREATE FUNCTION',migration.SQL)
        self.assertNotIn('SECURITY DEFINER',migration.SQL)
        self.assertIn('GRANT EXECUTE ON FUNCTION',migration.SQL)
        self.assertIn('REVOKE EXECUTE ON FUNCTION',migration.REVERSE)
        for name in transition.EXECUTE:self.assertIn(name,migration.SQL)
