"""Writable capability rejects escalation while v1 remains read-only."""
from copy import deepcopy
import json
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from mta.mdm import owned_namespace as owned
from mta.runtime import test_owned_namespace as v1_tests
from mta.serialization import digest


class ApplicationCapabilityTests(SimpleTestCase):
    def setUp(self):
        # These are receipt-join units; actual native identity is qualified by
        # the isolated registration tests, never by a worktree's missing pins.
        self.release = dict(schema='vectorflow-native-release-source-v1', source_commit='f'*40,
            manifest_sha256='1'*64, source_files_digest='2'*64, migrations_digest='3'*64,
            implementation_sha256='b'*64)
        self.enterContext(patch('release.native_identity.require_current',return_value=self.release))
        base=v1_tests.OwnedNamespaceTests();base.setUp()
        self.db=base.database;self.reg=base.registration;self.proof=base.evidence
        self.original=owned._receipt_identity(self.reg)
        self.catalogue=dict(objects=[],grants=[],functions=[])
        self.next_oid=100
        for name in owned.APPLICATION_GRANTS:
            self.object(name)
        for name in (owned.REGISTRY,owned.APPLICATION_REGISTRY):self.object(name,owner=14)
        for name,grant in owned.APPLICATION_GRANTS.items():
            if 'INSERT' in grant['table'] and name.startswith('mta.'):
                self.object(name+'_id_seq',kind='S',sequence_for=name+'.id')
        for obj in self.catalogue['objects']:
            if obj['kind']!='S':self.grant('table',obj['name'],'SELECT')
        for name,grant in owned.APPLICATION_GRANTS.items():
            for permission in grant['table']:
                if permission=='UPDATE' and grant['columns']:
                    for column in grant['columns']:self.grant('column',name,permission,column=column)
                else:self.grant('table',name,permission)
            if 'INSERT' in grant['table'] and name.startswith('mta.'):
                self.grant('sequence',name+'_id_seq','USAGE')
        for name in sorted(owned.APPLICATION_FUNCTIONS):
            self.next_oid+=1
            self.catalogue['functions'].append(dict(name=name,oid=self.next_oid,owner=10,
                security_definer=False,body='fixed helper source',configuration=None,language=14,returns='boolean'))
            self.grant('function',name,'EXECUTE')
        self.digests=owned._check_application_grants(self.catalogue,self.reg)
        self.binding=dict(policy=owned.APPLICATION_POLICY,original_registration=self.original,
            original_implementation_sha256='b'*64,implementation_sha256='c'*64,
            profile_digest=owned._application_profile_digest(),**self.digests)
        self.binding['receipt_digest']=digest(self.binding)

    def object(self,name,kind='r',owner=10,sequence_for=None):
        self.next_oid+=1
        self.catalogue['objects'].append(dict(name=name,oid=self.next_oid,kind=kind,
            owner=owner,sequence_for=sequence_for))

    def grant(self,scope,name,privilege,column=None,grantee=12):
        objects=self.catalogue['objects']+self.catalogue['functions']
        obj=next((o for o in objects if o['name']==name),dict(oid=999,owner=10))
        self.catalogue['grants'].append(dict(scope=scope,name=name,oid=obj['oid'],owner=obj['owner'],
            column=column,grantor=obj['owner'],grantee=grantee,privilege=privilege,grantable=False))

    def fresh_binding(self):
        value=dict(self.binding,policy=owned.PRODUCTION_APPLICATION_POLICY,
            implementation_sha256=self.original['adapter_sha256'],
            profile_digest=owned._production_application_profile_digest(),
            release_identity=self.release,schema_digest='f'*64)
        value['receipt_digest']=digest({k:v for k,v in value.items() if k!='receipt_digest'})
        return value

    def test_historical_profile_does_not_replace_current_native_identity(self):
        with self.assertRaisesRegex(ValueError,'fresh release identity differs'):
            owned._validate_application_binding(self.binding,self.original,'c'*64,self.digests)

    def test_v1_still_rejects_same_write_catalogue(self):
        evidence=deepcopy(self.proof);evidence['acl']['count']=1
        with self.assertRaisesRegex(ValueError,'grant catalogue differs'):
            owned._validate(self.db,self.reg,evidence,artifact_sha256='a'*64,adapter_sha256='b'*64)

    def test_table_column_sequence_default_public_and_grant_option_deny(self):
        changes=(
            lambda c:c['grants'].append(dict(next(g for g in c['grants'] if g['name']=='mta.fresh_mta_calculationrun'),privilege='DELETE')),
            lambda c:c['grants'].append(dict(c['grants'][0],scope='column',column='digest',privilege='UPDATE')),
            lambda c:c['grants'].append(dict(next(g for g in c['grants'] if g['scope']=='sequence'),privilege='UPDATE')),
            lambda c:c['grants'].append(dict(c['grants'][0],scope='default')),
            lambda c:c['grants'].append(dict(c['grants'][0],grantee=0)),
            lambda c:c['grants'].append(dict(next(g for g in c['grants'] if g['scope']=='function'),grantee=0)),
            lambda c:c['grants'].append(dict(c['grants'][0],grantable=True)),
            lambda c:c['grants'].append(dict(c['grants'][0],grantee=99)),
            lambda c:c['functions'][0].update(security_definer=True),
        )
        for i,change in enumerate(changes):
            catalogue=deepcopy(self.catalogue);change(catalogue)
            with self.subTest(change=i),self.assertRaises(ValueError):
                owned._check_application_grants(catalogue,self.reg)

    def test_missing_select_sequence_and_sequence_reownership_deny(self):
        for boundary in ('select','sequence','dependency'):
            catalogue=deepcopy(self.catalogue)
            if boundary=='select':catalogue['grants'].pop(0)
            elif boundary=='sequence':catalogue['objects']=[o for o in catalogue['objects'] if o['kind']!='S']
            else:next(o for o in catalogue['objects'] if o['kind']=='S')['sequence_for']='mta.unrelated.id'
            with self.subTest(boundary=boundary),self.assertRaises(ValueError):
                owned._check_application_grants(catalogue,self.reg)

    def test_no_full_command_or_identity_update(self):
        for name in ('mta.fresh_mta_runcommand','mta.fresh_mta_calculationrun','mta.fresh_mta_mdmsource'):
            catalogue=deepcopy(self.catalogue)
            catalogue['grants'].append(dict(next(g for g in catalogue['grants'] if g['name']==name),privilege='UPDATE'))
            with self.subTest(name=name),self.assertRaises(ValueError):owned._check_application_grants(catalogue,self.reg)

    def test_profile_registration_code_and_oid_drift_deny(self):
        changes=(lambda b:b.update(policy=owned.POLICY),lambda b:b.update(implementation_sha256='c'*64),
            lambda b:b['original_registration'].update(database_oid=99),
            lambda b:b.update(profile_digest='d'*64),lambda b:b.update(grants_digest='e'*64),
            lambda b:b.update(untrusted_allowlist=['ALL']))
        for i,change in enumerate(changes):
            binding=deepcopy(self.fresh_binding());change(binding)
            binding['receipt_digest']=digest({k:v for k,v in binding.items() if k!='receipt_digest'})
            with self.subTest(change=i),self.assertRaises(ValueError):
                owned._validate_application_binding(binding,self.original,self.original['adapter_sha256'],self.digests,production=True)
        catalogue=deepcopy(self.catalogue);catalogue['objects'][0]['oid']+=10000
        new_digests=owned._check_application_grants(catalogue,self.reg)
        with self.assertRaises(ValueError):owned._validate_application_binding(self.binding,self.original,'c'*64,new_digests)

    def test_role_membership_and_superuser_still_deny(self):
        for role in ('consumer','issuer','owner','registrar'):
            reg=deepcopy(self.reg);reg[role]['superuser']=True
            with self.subTest(role=role),self.assertRaises(ValueError):
                owned._validate_identity(self.db,reg,self.proof)
        proof=deepcopy(self.proof);proof['consumer_roles']=[10]
        with self.assertRaises(ValueError):owned._validate_identity(self.db,self.reg,proof)

    def test_capability_requires_registrar_and_exact_immutable_triggers(self):
        triggers=[('application_capability_immutable',27,'O',14,False,owned.CAPABILITY_GUARD_BODY),
                  ('application_capability_truncate',34,'O',14,False,owned.CAPABILITY_GUARD_BODY)]
        cursor=MagicMock();cursor.fetchone.side_effect=[(77,),(14,14,False,False)]
        cursor.fetchall.side_effect=[triggers,[(True,json.dumps(self.binding))]]
        self.assertEqual(owned._read_application_capability(cursor,self.reg),self.binding)
        for metadata in ((10,14,False,False),(14,10,False,False),(14,14,True,False)):
            cursor=MagicMock();cursor.fetchone.side_effect=[(77,),metadata]
            with self.assertRaises(ValueError):owned._read_application_capability(cursor,self.reg)
        for rows in ([],[(*triggers[0][:2],'D',*triggers[0][3:]),triggers[1]]):
            cursor=MagicMock();cursor.fetchone.side_effect=[(77,),(14,14,False,False)];cursor.fetchall.return_value=rows
            with self.assertRaises(ValueError):owned._read_application_capability(cursor,self.reg)

    def test_task_actor_columns_and_generation_direct_table_grants_deny(self):
        for name,column in (('mta.fresh_mta_mdmtask','UserId'),
                            ('mta.fresh_mta_mdmsubtask','ApproverId'),
                            ('mta.fresh_mta_mdmforceowner','receipt_digest')):
            catalogue=deepcopy(self.catalogue)
            catalogue['grants'].append(dict(next(g for g in catalogue['grants'] if g['name']==name),
                scope='column',column=column,privilege='UPDATE'))
            with self.subTest(name=name),self.assertRaises(ValueError):
                owned._check_application_grants(catalogue,self.reg)

    def test_routine_source_and_oid_change_invalidate_sealed_binding(self):
        for key,value in (('body','replaced helper'),('oid',999999),('configuration',['search_path=public'])):
            catalogue=deepcopy(self.catalogue);catalogue['functions'][0][key]=value
            changed=owned._check_application_grants(catalogue,self.reg)
            with self.subTest(key=key),self.assertRaises(ValueError):
                owned._validate_application_binding(self.fresh_binding(),self.original,self.original['adapter_sha256'],changed,production=True)

    def test_write_guards_require_exact_body_owner_enabled_targets(self):
        self.enterContext(patch('mta.runtime.scoped_action_ownership.available',return_value=False))
        rows=[(name,kind,'O',14,False,owned.APPLICATION_WRITE_GUARD_BODY)
              for name,kind in sorted(owned.APPLICATION_WRITE_GUARDS.items())]
        cursor=MagicMock();cursor.fetchall.return_value=rows;owned._check_application_write_guards(cursor,self.reg)
        for altered in (rows[:-1],[(rows[0][0],rows[0][1],'D',*rows[0][3:]),*rows[1:]],
                        [(*rows[0][:3],10,*rows[0][4:]),*rows[1:]],
                        [(*rows[0][:-1],'BEGIN RETURN NEW; END'),*rows[1:]]):
            cursor.fetchall.return_value=altered
            with self.assertRaises(ValueError):owned._check_application_write_guards(cursor,self.reg)


    def test_fresh_production_binding_requires_same_current_source_and_its_own_policy(self):
        binding = self.fresh_binding()
        actual = owned._validate_application_binding(binding, self.original,
            self.original['adapter_sha256'], self.digests, production=True)
        self.assertEqual(actual['original_registration'], self.original)
        for production in (False,):
            with self.assertRaises(ValueError):
                owned._validate_application_binding(binding, self.original,
                    self.original['adapter_sha256'], self.digests, production=production)
        # The historical extension never becomes a generic new-install waiver.
        with self.assertRaises(ValueError):
            owned._validate_application_binding(self.binding, self.original, 'c'*64,
                self.digests, production=True)

    def test_production_binding_rejects_profile_source_catalogue_and_receipt_drift(self):
        binding = self.fresh_binding()
        for key,value in [('profile_digest','f'*64),('implementation_sha256','c'*64),
                          ('objects_digest','f'*64),('receipt_digest','f'*64),('unexpected',True)]:
            changed=dict(binding,**{key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):
                owned._validate_application_binding(changed,self.original,
                    self.original['adapter_sha256'],self.digests,production=True)

    def test_fresh_ui_layout_access_is_exact_and_not_inherited_by_historical_profile(self):
        name = 'mta.fresh_mta_userreportlayout'
        self.object(name)
        self.object(name+'_id_seq', kind='S', sequence_for=name+'.id')
        self.grant('table', name, 'SELECT')
        readonly = deepcopy(self.catalogue)
        for permission in ('INSERT', 'DELETE'):
            self.grant('table', name, permission)
        self.grant('sequence', name+'_id_seq', 'USAGE')
        owned._check_application_grants(self.catalogue, self.reg, production=True)
        # Same actual catalogue cannot silently widen an already sealed profile.
        with self.assertRaises(ValueError):
            owned._check_application_grants(self.catalogue, self.reg)
        with self.assertRaises(ValueError):
            owned._check_application_grants(readonly, self.reg, production=True)
        for permission in ('UPDATE', 'TRUNCATE', 'REFERENCES', 'TRIGGER'):
            catalogue = deepcopy(self.catalogue)
            catalogue['grants'].append(dict(next(g for g in catalogue['grants']
                if g['name']==name), privilege=permission))
            with self.subTest(permission=permission), self.assertRaises(ValueError):
                owned._check_application_grants(catalogue, self.reg, production=True)
        for changed in ('missing_sequence', 'public', 'grant_option'):
            catalogue = deepcopy(self.catalogue)
            grant = next(g for g in catalogue['grants'] if g['name']==name and g['privilege']=='DELETE')
            if changed == 'missing_sequence':
                catalogue['grants'] = [g for g in catalogue['grants'] if g['name']!=name+'_id_seq']
            elif changed == 'public':
                grant['grantee'] = 0
            else:
                grant['grantable'] = True
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                owned._check_application_grants(catalogue, self.reg, production=True)
