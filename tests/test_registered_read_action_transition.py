"""Finite guard correction and complete typed preservation; no native acceptance."""
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
import hashlib
import os
import unittest
from unittest.mock import Mock,patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','registered-read-action-transition-component')
import django
django.setup()
from mta.runtime import registered_read_action_transition as upgrade
from mta.runtime import ingestion_authority as authority,ingestion_admission as admission
from mta.serialization import digest


class RegisteredReadActionTransitionTests(unittest.TestCase):
    def spec(self,bootstrap=False):
        return dict(previous_release=dict(source_commit=upgrade.PREVIOUS_COMMIT,
            manifest_sha256=upgrade.PREVIOUS_RELEASE),migration_pins=upgrade.migration_pins(),
            catalogue_delta=upgrade.catalogue_delta(bootstrap=bootstrap))

    def test_only_exact_guard_and_optional_existing_bootstrap_are_admitted(self):
        for bootstrap in (False,True):
            spec=self.spec(bootstrap)
            upgrade.require_specification(spec)
            receipt=dict(migration_pins=spec['migration_pins'],previous_release=upgrade.PREVIOUS_RELEASE,
                catalogue_delta_digest=digest(spec['catalogue_delta']))
            self.assertTrue(upgrade.approved_receipt(receipt))
            for key in receipt:
                self.assertFalse(upgrade.approved_receipt(dict(receipt,**{key:'changed'})))
            for key in ('migration_pins','previous_release','catalogue_delta'):
                changed=deepcopy(spec)
                if key=='migration_pins':changed[key].append(['0237_intake_diagnostic_guards','0'*64])
                elif key=='previous_release':changed[key]['source_commit']='0'*40
                else:changed[key]['arbitrary']={'before':None,'after':'DDL'}
                with self.subTest(key=key),self.assertRaises(ValueError):upgrade.require_specification(changed)
        plain=upgrade.catalogue_delta();boot=upgrade.catalogue_delta(bootstrap=True)
        name='functions:mta.guard_scope_read_reference()'
        self.assertEqual(set(plain),{name})
        frozen=import_module('mta.runtime.migrations.'+upgrade.MIGRATION_NAME)
        self.assertEqual(plain[name]['before']['body'],frozen.OLD)
        self.assertEqual(plain[name]['after'],dict(plain[name]['before'],body=frozen.BODY))
        for key in set(boot)-set(plain):
            self.assertIn('ingestion_schema_compatibility',key)
            self.assertIsNone(boot[key]['before'])
        self.assertNotIn('actionable_scope_phase',str(boot))

    def test_authority_admits_exact238_name_only(self):
        body={key:'a'*64 for key in authority.SCHEMA_FIELDS}
        body.update(contract=authority.SCHEMA_CONTRACT,initialization_id=str(uuid4()),
            target_commit='b'*40,migration_pins=upgrade.migration_pins())
        self.assertEqual(authority.validate_schema_transition(body),body)
        for name in ('0238_arbitrary','0239_registered_read_action_cut'):
            with self.assertRaises(ValueError):
                authority.validate_schema_transition(dict(body,migration_pins=[[name,'a'*64]]))

    def start_answers(self):
        old=import_module('mta.runtime.migrations.0235_registered_scope_read_attachment')
        watch=import_module('mta.runtime.migrations.0237_intake_diagnostic_guards')
        return [('0237_intake_diagnostic_guards',),
            (old.BODY,False,['search_path=pg_catalog, mta'],upgrade.OWNER),
            (watch.NEW,True,['search_path=pg_catalog, mta'],upgrade.OWNER),(False,)]

    def start(self,answers,guard=True):
        cursor=Mock();cursor.fetchone.side_effect=answers
        with patch('mta.runtime.ingestion_ownership.migration_history_guard',return_value=guard):
            upgrade.require_start(cursor)
        return cursor

    def test_start_accepts_consumed_state_but_refuses_wrong_owner_guard_or_worker(self):
        self.start(self.start_answers())
        for index,value in ((0,('0236_intake_diagnostic_custody',)),
                (1,('wrong',False,['search_path=pg_catalog, mta'],upgrade.OWNER)),
                (2,('wrong',True,['search_path=pg_catalog, mta'],upgrade.OWNER)),(3,(True,))):
            answers=self.start_answers();answers[index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):self.start(answers)
        with self.assertRaisesRegex(ValueError,'history guard'):self.start(self.start_answers(),False)

    def test_effective_schema_accepts_finite_correction_once(self):
        cert=dict(schema_digest='s0',guard_digest='g0',receipt_digest='r',release_digest=upgrade.PREVIOUS_RELEASE)
        origin={key:'fixed' for key in authority.FIELDS}
        origin.update(initialization_id=str(uuid4()),target_commit=upgrade.PREVIOUS_COMMIT,
                      target_release=upgrade.PREVIOUS_RELEASE)
        target=dict(origin,target_commit='1'*40,target_release='1'*64)
        link=dict(contract=authority.SCHEMA_CONTRACT,previous_release=origin['target_release'],
            previous_authority_digest=digest(origin),certification_digest='r',target_commit=target['target_commit'],
            migration_pins=upgrade.migration_pins(),catalogue_delta_digest=digest(upgrade.catalogue_delta()),
            before_schema_digest='s0',before_guard_digest='g0',schema_digest='s1',guard_digest='g1')
        links={target['target_release']:link};bodies={origin['target_release']:origin,target['target_release']:target}
        def resolve(body):
            with patch.object(admission,'_activation_metadata',return_value=cert),\
                    patch.object(authority,'read',side_effect=lambda c,i,r:bodies[r]),\
                    patch.object(authority,'read_schema_transition',side_effect=lambda c,b:links.get(b['target_release'])):
                return admission.effective_schema(None,body)
        self.assertEqual(resolve(target)[2:4],('s1','g1'))
        link['catalogue_delta_digest']='tampered'
        with self.assertRaisesRegex(ValueError,'registered-read'):resolve(target)
        link['catalogue_delta_digest']=digest(upgrade.catalogue_delta())
        repeated=dict(target,target_commit='2'*40,target_release='2'*64)
        bodies[repeated['target_release']]=repeated
        links[repeated['target_release']]=dict(link,previous_release=target['target_release'],
            previous_authority_digest=digest(target),target_commit=repeated['target_commit'],
            before_schema_digest='s1',before_guard_digest='g1',schema_digest='s2',guard_digest='g2')
        with self.assertRaisesRegex(ValueError,'registered-read'):resolve(repeated)


class CopyCursor:
    def __init__(self,tables,payloads,isolation='repeatable read'):
        self.tables=tables;self.payloads=iter(payloads);self.isolation=isolation
        self.queries=[];self.copies=[]
    def execute(self,query,params=None):
        self.current=query if isinstance(query,str) else query.as_string()
        self.queries.append((self.current,params))
    def fetchone(self):return (self.isolation,) if self.current=='SHOW transaction_isolation' else (2,)
    def fetchall(self):return self.tables
    @contextmanager
    def copy(self,query):
        self.copies.append(query.as_string())
        yield iter(next(self.payloads))


class TypedPreservationTests(unittest.TestCase):
    def preserve(self,cursor,atomic=True):
        with patch('django.db.connection',Mock(in_atomic_block=atomic)):
            return upgrade.preservation(cursor,{'original':'certificate'})

    def test_every_lineage_and_typed_population_is_streamed_without_row_loading(self):
        names=[('mta','django_migrations',['id']),
            ('mta','fresh_mta_ingestionreleasecompatibility',['id']),
            ('mta','fresh_mta_calculationrun',['id']),
            ('mta','fresh_mta_mdmdailyinputcapture',['run_id']),
            ('mta','fresh_mta_runphaseacceptance',['id']),('mta','fresh_mta_runcommand',['id']),
            ('mta','fresh_mta_scopereadreference',['id']),('mta','fresh_mta_intakediagnostic',['id']),
            ('mta_opening','typed_opening',['initialization_id','ordinal']),
            ('mta_state','typed_state',['vf_run_id','vf_image','vf_ordinal'])]
        payloads=[(b'header',memoryview(b'\x00typed\x00NULL\xff'),b'end') for _ in names[:-1]]
        cursor=CopyCursor(names,payloads)
        result=self.preserve(cursor)
        self.assertEqual(result['original'],{'original':'certificate'})
        self.assertEqual(len(result['typed_tables']),len(names)-1)
        self.assertEqual({(row['schema'],row['table']) for row in result['typed_tables']},
            {(s,t) for s,t,_ in names if t!='fresh_mta_ingestionreleasecompatibility'})
        expected=hashlib.sha256(b'header\x00typed\x00NULL\xffend').hexdigest()
        self.assertTrue(all(row['binary_sha256']==expected and row['rows']==2 for row in result['typed_tables']))
        self.assertTrue(all('FORMAT BINARY' in query and 'ORDER BY' in query for query in cursor.copies))
        history=next(query for query in cursor.copies if 'django_migrations' in query)
        self.assertIn("WHERE NOT (app='fresh_mta' AND name='0238_registered_read_action_cut')",history)
        self.assertTrue(all('WHERE' not in query for query in cursor.copies if 'django_migrations' not in query))

    def test_changed_binary_cell_changes_proof_and_unkeyed_or_unfenced_snapshot_refuses(self):
        tables=[('mta_state','state',['vf_run_id','vf_ordinal'])]
        first=self.preserve(CopyCursor(tables,[(b'NULL',)]))
        second=self.preserve(CopyCursor(tables,[(b'',)]))
        self.assertNotEqual(first,second)
        for cursor,atomic in ((CopyCursor(tables,[],isolation='read committed'),True),
                              (CopyCursor(tables,[]),False),
                              (CopyCursor([('mta_state','state',[])],[]),True),
                              (CopyCursor([],[]),True)):
            with self.assertRaises(ValueError):self.preserve(cursor,atomic)


if __name__=='__main__':unittest.main()
