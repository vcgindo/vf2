"""Exact additive privileges and unchanged sealed receipt; no database creation."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, MagicMock
from django.test import override_settings
from mta.runtime import test_application_capability as base
from mta.mdm import owned_namespace as owned
from mta.serialization import digest


class LogisticsCapabilityTests(TestCase):
    object=base.ApplicationCapabilityTests.object
    grant=base.ApplicationCapabilityTests.grant

    def setUp(self):
        base.ApplicationCapabilityTests.setUp(self)
        for name in ('mta.fresh_mta_dailyopenrequest','mta.fresh_mta_dailyrequestowner'):
            self.object(name);self.grant('table',name,'SELECT')
        self.object('mta.fresh_mta_dailyopenrequest_id_seq',kind='S',sequence_for='mta.fresh_mta_dailyopenrequest.id')
        self.original_catalogue=deepcopy(self.catalogue)
        self.digests=owned._check_application_grants(self.catalogue,self.reg)
        self.binding.update(self.digests)
        self.binding['receipt_digest']=digest({k:v for k,v in self.binding.items() if k!='receipt_digest'})
        for name in sorted(owned.LOGISTICS_TABLES):
            self.object(name);self.grant('table',name,'SELECT')
        for name in sorted(owned.LOGISTICS_SEQUENCES):
            self.object(name,kind='S',sequence_for=name.removesuffix('_id_seq')+'.id')
        for name in sorted(owned.LOGISTICS_FUNCTIONS):
            self.next_oid+=1
            self.catalogue['functions'].append(dict(name=name,oid=self.next_oid,owner=10,
                security_definer=False,body='schema checked separately',configuration=None,language=14,returns='trigger'))
        for name,grants in owned.LOGISTICS_APPLICATION_GRANTS.items():
            for privilege in grants['table']:
                if privilege=='UPDATE':
                    for column in grants['columns']:self.grant('column',name,privilege,column=column)
                else:self.grant('table',name,privilege)
            if 'INSERT' in grants['table']:self.grant('sequence',name+'_id_seq','USAGE')

    def test_additive_profile_preserves_complete_original_catalogue_and_binding(self):
        owned._check_application_grants(self.catalogue,self.reg,logistics=True)
        original=owned._original_application_catalogue(self.catalogue,self.reg)
        self.assertEqual(original,self.original_catalogue)
        digests=owned._check_application_grants(original,self.reg)
        self.assertEqual(digests,self.digests)
        actual=owned._validate_application_binding(self.binding,self.original,'c'*64,digests)
        self.assertEqual(actual,{**self.binding,'artifact_sha256':'a'*64})

    def test_extra_privilege_public_grant_option_default_owner_and_sequence_drift_deny(self):
        def change(kind):
            c=deepcopy(self.catalogue)
            row=next(g for g in c['grants'] if g['name']=='mta.fresh_mta_dailyopenrequest' and g['privilege']=='INSERT')
            if kind=='delete':c['grants'].append(dict(row,privilege='DELETE'))
            if kind=='wide-update':c['grants'].append(dict(row,privilege='UPDATE'))
            if kind=='wrong-column':c['grants'].append(dict(row,scope='column',column='ParentWhCode',privilege='UPDATE'))
            if kind=='public':c['grants'].append(dict(row,grantee=0))
            if kind=='default':c['grants'].append(dict(row,scope='default'))
            if kind=='grant-option':row['grantable']=True
            if kind=='wrong-owner':next(o for o in c['objects'] if o['name'] in owned.LOGISTICS_TABLES)['owner']=12
            if kind=='sequence-owner':next(o for o in c['objects'] if o['name'] in owned.LOGISTICS_SEQUENCES)['sequence_for']='mta.other.id'
            if kind=='security-definer':next(f for f in c['functions'] if f['name'] in owned.LOGISTICS_FUNCTIONS)['security_definer']=True
            return c
        for kind in ('delete','wide-update','wrong-column','public','default','grant-option','wrong-owner','sequence-owner','security-definer'):
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                owned._check_application_grants(change(kind),self.reg,logistics=True)

    def test_original_object_and_privilege_drift_is_not_discarded(self):
        for kind in ('object','function','privilege','unknown-object'):
            c=deepcopy(self.catalogue)
            if kind=='object':next(o for o in c['objects'] if o['name']==owned.REGISTRY)['oid']+=1
            if kind=='function':next(f for f in c['functions'] if f['name'] in owned.APPLICATION_FUNCTIONS)['body']='changed'
            if kind=='privilege':c['grants'][0]['grantor']+=1
            if kind=='unknown-object':c['objects'].append(dict(c['objects'][0],name='mta.unapproved',oid=9999));c['grants'].append(dict(c['grants'][0],name='mta.unapproved',oid=9999))
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                owned._check_application_grants(c,self.reg,logistics=True)
                d=owned._check_application_grants(owned._original_application_catalogue(c,self.reg),self.reg)
                owned._validate_application_binding(self.binding,self.original,'c'*64,d)

    def test_missing_additive_grant_and_unapproved_new_reader_deny(self):
        c=deepcopy(self.catalogue);c['grants'].pop()
        with self.assertRaises(ValueError):owned._check_application_grants(c,self.reg,logistics=True)
        self.grant('table','mta.fresh_mta_transitannotation','SELECT',grantee=13)
        with self.assertRaises(ValueError):owned._original_application_catalogue(self.catalogue,self.reg)

    @override_settings(VF_MTA_LOGISTICS_CURRENT=True)
    def test_verify_binding_returns_the_unchanged_existing_receipt(self):
        expected={**self.binding,'artifact_sha256':'a'*64}
        with patch.object(owned,'_database_identity',return_value=self.db), \
             patch.object(owned,'_registered_identity',return_value=self.reg), \
             patch.object(owned,'_catalogue_evidence',return_value=self.proof), \
             patch.object(owned,'_validate_identity',return_value=self.original), \
             patch.object(owned,'_read_application_capability',return_value=self.binding), \
             patch.object(owned,'_check_application_write_guards'), \
             patch.object(owned,'_application_catalogue',return_value=self.catalogue), \
             patch.object(owned,'_check_logistics_schema') as schema, \
             patch.object(owned.connection,'cursor',return_value=MagicMock()):
            receipt={'owned_namespace':expected}
            self.assertIs(owned.verify_binding(receipt),receipt)
            schema.assert_called_once()
            self.assertEqual(receipt['owned_namespace'],expected)

    def test_new_schema_missing_relation_or_rls_deny_before_use(self):
        c=deepcopy(self.catalogue);next(o for o in c['objects'] if o['name'] in owned.LOGISTICS_TABLES)['owner']=99
        with self.assertRaisesRegex(ValueError,'relation identity'):
            owned._check_logistics_schema(MagicMock(),c,self.reg)
        cursor=MagicMock();cursor.fetchone.return_value=(True,False,'p')
        with self.assertRaisesRegex(ValueError,'table security'):
            owned._check_logistics_schema(cursor,self.catalogue,self.reg)


    def test_fresh_production_capability_validates_full_catalogue_without_historical_subtraction(self):
        for name, grants in owned.PRODUCTION_UI_GRANTS.items():
            self.object(name)
            self.object(name+'_id_seq', kind='S', sequence_for=name+'.id')
            self.grant('table', name, 'SELECT')
            for privilege in grants['table']:
                self.grant('table', name, privilege)
            self.grant('sequence', name+'_id_seq', 'USAGE')
        full_digests=owned._check_application_grants(self.catalogue,self.reg,logistics=True,production=True)
        binding=dict(self.binding, policy=owned.PRODUCTION_APPLICATION_POLICY,
            implementation_sha256=self.original['adapter_sha256'],
            profile_digest=owned._production_application_profile_digest(),**full_digests)
        binding['receipt_digest']=digest({k:v for k,v in binding.items() if k!='receipt_digest'})
        expected={**binding,'artifact_sha256':'a'*64}
        with patch.object(owned,'_database_identity',return_value=self.db), \
             patch.object(owned,'_registered_identity',return_value=self.reg), \
             patch.object(owned,'_catalogue_evidence',return_value=self.proof), \
             patch.object(owned,'_validate_identity',return_value=self.original), \
             patch.object(owned,'_read_application_capability',return_value=binding), \
             patch.object(owned,'_check_application_write_guards'), \
             patch.object(owned,'_application_catalogue',return_value=self.catalogue), \
             patch.object(owned,'_check_logistics_schema') as schema, \
             patch.object(owned,'_original_application_catalogue') as historical, \
             patch.object(owned.connection,'cursor',return_value=MagicMock()):
            receipt={'owned_namespace':expected}
            self.assertIs(owned.verify_binding(receipt),receipt)
            schema.assert_called_once()
            historical.assert_not_called()
            self.assertEqual(receipt['owned_namespace'],expected)

    def test_sealed_layout_delta_preserves_old_catalogue_and_rejects_broader_grants(self):
        table='mta.fresh_mta_userreportlayout'
        self.object(table)
        self.object(table+'_id_seq',kind='S',sequence_for=table+'.id')
        self.grant('table',table,'SELECT')
        before=deepcopy(self.catalogue)
        old=owned._original_application_catalogue(before,self.reg)
        original_digests=owned._check_application_grants(old,self.reg)
        self.grant('table',table,'INSERT')
        self.grant('table',table,'DELETE')
        self.grant('sequence',table+'_id_seq','USAGE')
        owned._check_application_grants(self.catalogue,self.reg,logistics=True,production=True)
        retained=owned._original_user_preferences_catalogue(self.catalogue,self.reg)
        self.assertEqual(retained,before)
        self.assertEqual(owned._check_application_grants(
            owned._original_application_catalogue(retained,self.reg),self.reg),original_digests)
        binding=dict(self.binding,**original_digests)
        binding['receipt_digest']=digest({k:v for k,v in binding.items() if k!='receipt_digest'})
        receipt={'owned_namespace':{**binding,'artifact_sha256':'a'*64}}
        with override_settings(VF_MTA_LOGISTICS_CURRENT=True), \
             patch.dict('os.environ',{'VF_MDM_SEALED_EXPORT_LAYOUTS':'1'}), \
             patch.object(owned,'_database_identity',return_value=self.db), \
             patch.object(owned,'_registered_identity',return_value=self.reg), \
             patch.object(owned,'_catalogue_evidence',return_value=self.proof), \
             patch.object(owned,'_validate_identity',return_value=self.original), \
             patch.object(owned,'_read_application_capability',return_value=binding), \
             patch.object(owned,'_check_application_write_guards') as guards, \
             patch.object(owned,'_require_sealed_layout_scope') as scope, \
             patch.object(owned,'_application_catalogue',return_value=self.catalogue), \
             patch.object(owned,'_check_logistics_schema') as schema, \
             patch.object(owned.connection,'cursor',return_value=MagicMock()):
            self.assertIs(owned.verify_binding(receipt),receipt)
            self.assertEqual(receipt['owned_namespace'],{**binding,'artifact_sha256':'a'*64})
            guards.assert_called_once()
            scope.assert_called_once_with(self.db)
            schema.assert_called_once()
        for kind in ('missing','grantor','grant-option','public','wide-update','sequence-update','other-delete'):
            altered=deepcopy(self.catalogue)
            row=next(g for g in altered['grants'] if g['name']==table and g['privilege']=='INSERT')
            if kind=='missing':altered['grants'].remove(row)
            if kind=='grantor':row['grantor']=999
            if kind=='grant-option':row['grantable']=True
            if kind=='public':row['grantee']=0
            if kind=='wide-update':altered['grants'].append(dict(row,privilege='UPDATE'))
            if kind=='sequence-update':altered['grants'].append(dict(
                next(g for g in altered['grants'] if g['name']==table+'_id_seq'),privilege='UPDATE'))
            if kind=='other-delete':altered['grants'].append(dict(row,name='mta.fresh_mta_dailyopenrequest',privilege='DELETE'))
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                owned._check_application_grants(altered,self.reg,logistics=True,production=True)
                owned._original_user_preferences_catalogue(altered,self.reg)
        with self.assertRaises(ValueError):
            owned._check_application_grants(self.catalogue,self.reg,logistics=True)

    def test_sealed_layout_opt_in_rejects_missing_export_pin_and_other_database(self):
        from mta.mdm.native_report_compatibility import DATABASE
        from release.sealed_export import PIN_ENV
        database=dict(name=DATABASE[0],oid=DATABASE[1])
        with patch.dict('os.environ',{},clear=True),self.assertRaises(ValueError):
            owned._require_sealed_layout_scope(database)
        with patch.dict('os.environ',{PIN_ENV:'a'*64}):
            owned._require_sealed_layout_scope(database)
            for value in (dict(database,oid=DATABASE[1]+1),dict(database,name='another_database')):
                with self.subTest(database=value),self.assertRaises(ValueError):
                    owned._require_sealed_layout_scope(value)
