"""Bounded code/schema composition; original receipts and real DDL limit remain."""
import os
from copy import deepcopy
from uuid import uuid4
import unittest
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','code-schema-component')
import django
django.setup()
from mta.runtime import ingestion_authority as authority,ingestion_admission as admission
from mta.serialization import digest


class CodeSchemaContractTests(unittest.TestCase):
    def link(self):
        row={k:'a'*64 for k in authority.CODE_SCHEMA_FIELDS}
        row.update(contract=authority.CODE_SCHEMA_CONTRACT,initialization_id=str(uuid4()),
            target_commit='b'*40,target_release='c'*64,anchor_release='d'*64,
            migration_pins=[],catalogue_delta_digest=digest({}))
        return row

    def test_explicit_nonmigration_contract_and_no_self_anchor(self):
        row=self.link();self.assertEqual(authority.validate_code_schema(row),row)
        for delta in ({'migration_pins':[['0168_fake','e'*64]]},{'catalogue_delta_digest':'f'*64},
            {'anchor_release':row['target_release']},{'target_commit':'bad'},
            {'certification_digest':None},{'contract':authority.SCHEMA_CONTRACT},{'extra':True}):
            with self.subTest(delta=delta),self.assertRaises((ValueError,TypeError)):
                authority.validate_code_schema({**row,**delta})
        with self.assertRaisesRegex(ValueError,'Exact schema transition'):
            authority.validate_schema_transition(row)

    def test_original_no_schema_activation_stays_exact(self):
        body=dict(target_release='a'*64,initialization_id=str(uuid4()))
        cert=dict(schema_digest='b'*64,guard_digest='c'*64,receipt_digest='d'*64,
            release_digest=body['target_release'],authority_roles=['owner','installer','runtime'])
        with patch.object(admission,'_activation_metadata',return_value=cert), \
                patch.object(authority,'read_schema_transition',return_value=None), \
                patch.object(authority,'read',return_value=body), \
                patch('release.native_schema.schema_digest',return_value=cert['schema_digest']), \
                patch.object(admission,'security_digest',return_value=cert['guard_digest']):
            self.assertEqual(admission.validate_activation(None,body),cert)

    def test_direct_anchor_and_changed_live_security_fail_closed(self):
        cert=dict(schema_digest='a'*64,guard_digest='b'*64,receipt_digest='c'*64,
            release_digest='d'*64,authority_roles=['owner','installer','runtime'])
        anchor={k:'fixed' for k in authority.FIELDS};anchor.update(target_release=cert['release_digest'],target_commit='e'*40)
        body={**anchor,'target_release':'f'*64,'target_commit':'a'*40}
        link=dict(self.link(),target_release=body['target_release'],target_commit=body['target_commit'],
            anchor_release=anchor['target_release'],anchor_authority_digest=digest(anchor),
            anchor_schema_receipt_digest=cert['receipt_digest'],certification_digest=cert['receipt_digest'],
            schema_digest=cert['schema_digest'],guard_digest=cert['guard_digest'])
        with patch.object(admission,'_activation_metadata',return_value=cert), \
                patch.object(authority,'read',return_value=anchor), \
                patch.object(authority,'read_schema_transition',side_effect=lambda c,a:link if a is body else None), \
                patch('release.native_schema.schema_digest',return_value=cert['schema_digest']), \
                patch.object(admission,'security_digest',return_value=cert['guard_digest']) as security:
            self.assertEqual(admission.validate_activation(None,body),cert)
            security.return_value='0'*64
            with self.assertRaisesRegex(ValueError,'Current schema, grants, roles or guards differ'):
                admission.validate_activation(None,body)
            security.return_value=cert['guard_digest']
            for field in ('anchor_authority_digest','anchor_schema_receipt_digest','schema_digest','certification_digest'):
                original=link[field];link[field]='0'*64
                with self.subTest(field=field),self.assertRaisesRegex(ValueError,'Code-only'):
                    admission.validate_activation(None,body)
                link[field]=original


class CodeSchemaCompositionTests(unittest.TestCase):
    def setUp(self):
        self.initialization=str(uuid4())
        self.cert=dict(schema_digest='s0',guard_digest='g0',receipt_digest='r',
            release_digest='0'*64,authority_roles=['owner','installer','runtime'])
        self.bodies={};self.links={}
        self.base=self.activation('0')
        self.latest=self.base
        for index in range(1,5):
            self.latest=self.schema(str(index),self.latest,index)

    def activation(self,key):
        body={k:'fixed' for k in authority.FIELDS}
        body.update(initialization_id=self.initialization,target_release=key*64,target_commit=key*40)
        self.bodies[body['target_release']]=body
        return body

    def schema(self,key,parent,index):
        body=self.activation(key)
        self.links[body['target_release']]=dict(contract=authority.SCHEMA_CONTRACT,
            previous_release=parent['target_release'],previous_authority_digest=digest(parent),
            certification_digest='r',target_commit=body['target_commit'],
            before_schema_digest='s'+str(index-1),before_guard_digest='g'+str(index-1),
            schema_digest='s'+str(index),guard_digest='g'+str(index))
        return body

    def code(self,key,anchor,index):
        body=self.activation(key)
        self.links[body['target_release']]=dict(contract=authority.CODE_SCHEMA_CONTRACT,
            anchor_release=anchor['target_release'],anchor_authority_digest=digest(anchor),
            anchor_schema_receipt_digest=digest(self.links[anchor['target_release']]) if anchor['target_release'] in self.links else 'r',
            certification_digest='r',target_commit=body['target_commit'],
            schema_digest='s'+str(index),guard_digest='g'+str(index))
        return body

    def resolve(self,body):
        with patch.object(admission,'_activation_metadata',return_value=self.cert), \
                patch.object(authority,'read',side_effect=lambda c,i,r:self.bodies[r]), \
                patch.object(authority,'read_schema_transition',side_effect=lambda c,a:self.links.get(a['target_release'])):
            return admission.effective_schema(None,body)

    def test_four_real_extensions_and_repeated_code_use_direct_anchor(self):
        first=self.code('a',self.latest,4)
        second=self.code('b',self.latest,4)
        for body in (self.latest,first,second):
            cert,anchor,schema,guard,receipt=self.resolve(body)
            self.assertEqual((cert,anchor,schema,guard,receipt),
                (self.cert,self.latest,'s4','g4',digest(self.links[self.latest['target_release']])))
        baseline_code=self.code('c',self.base,0)
        self.assertEqual(self.resolve(baseline_code)[1:4],(self.base,'s0','g0'))

    def test_real_schema_after_code_inheritance_keeps_real_transition_count(self):
        third=self.bodies['3'*64]
        code=self.code('a',third,3)
        fourth=self.schema('b',code,4)
        self.assertEqual(self.resolve(fourth)[1:4],(fourth,'s4','g4'))
        fifth=self.schema('c',fourth,5)
        with self.assertRaisesRegex(ValueError,'four-admission boundary'):
            self.resolve(fifth)

    def test_code_ladder_cycle_foreign_anchor_and_catalogue_tampering_denied(self):
        body=self.code('a',self.latest,4)
        good=deepcopy(self.links[body['target_release']])
        for field in ('anchor_authority_digest','anchor_schema_receipt_digest','schema_digest','guard_digest','certification_digest','target_commit'):
            self.links[body['target_release']]={**good,field:'tampered'}
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'Code-only'):
                self.resolve(body)
        self.links[body['target_release']]=good
        ladder=self.code('b',body,4)
        with self.assertRaisesRegex(ValueError,'another code-only release'):
            self.resolve(ladder)
        self.bodies[self.latest['target_release']]['database_oid']='foreign'
        with self.assertRaisesRegex(ValueError,'ownership differs'):
            self.resolve(body)
        self.bodies[self.latest['target_release']]['database_oid']='fixed'
        # Authenticated cyclic metadata still cannot increase traversal bounds.
        extension=self.links[self.latest['target_release']]
        extension.update(previous_release=body['target_release'],previous_authority_digest=digest(body))
        good['anchor_schema_receipt_digest']=digest(extension)
        with self.assertRaisesRegex(ValueError,'cycle'):
            self.resolve(body)

    def test_schema_predecessor_fingerprints_are_not_skipped(self):
        self.links[self.latest['target_release']]['before_schema_digest']='foreign'
        with self.assertRaisesRegex(ValueError,'predecessor catalogue differs'):
            self.resolve(self.latest)

    def test_no_schema_table_retains_original_code_promotion_path(self):
        from unittest.mock import MagicMock
        cursor=MagicMock();cursor.fetchone.return_value=(None,)
        with patch.object(authority,'_provisioner'),patch.object(authority,'validate'), \
                patch.object(admission,'effective_schema',return_value=(self.cert,self.base,'s0','g0','r')), \
                patch.object(admission,'validate_activation') as live,patch.object(authority,'_schema_contract') as contract:
            new=self.activation('a')
            self.assertIsNone(authority.inherit_code_schema(cursor,new,self.base))
            live.assert_called_once_with(cursor,self.base);contract.assert_not_called()
            self.assertFalse(any('INSERT' in str(call) for call in cursor.execute.call_args_list))

    def test_registrar_receipt_digest_and_row_identity_remain_required(self):
        from unittest.mock import MagicMock
        contract=CodeSchemaContractTests();link=contract.link()
        activation=dict(initialization_id=link['initialization_id'],target_release=link['target_release'])
        cursor=MagicMock()
        with patch.object(authority,'_schema_contract'):
            for altered,receipt in ((link,digest(link)),(link,'0'*64),
                    ({**link,'initialization_id':str(uuid4())},None),
                    ({**link,'target_release':'f'*64},None)):
                cursor.fetchone.side_effect=[(authority.SCHEMA_TABLE,),(altered,receipt or digest(altered))]
                if altered==link and receipt==digest(link):
                    self.assertEqual(authority.read_schema_transition(cursor,activation),link)
                else:
                    with self.assertRaisesRegex(ValueError,'row identity differs'):
                        authority.read_schema_transition(cursor,activation)
