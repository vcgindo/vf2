"""Static admission has one action lifetime; ordinary readers stay independent."""
import os,unittest
from types import SimpleNamespace
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django;django.setup()
from mta.presentation import schema_reuse
from mta.runtime import scoped_action_ownership,scoped_remark_ownership
from mta.presentation.registered_read_compatibility import compatible_guard_recipe,GUARD_ADMISSION_RECIPES

class ActionAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.db=SimpleNamespace(connection=SimpleNamespace(closed=False),in_atomic_block=True,atomic_blocks=[object()])
        self.alias=patch.object(schema_reuse,'connections',{'default':self.db});self.alias.start();self.addCleanup(self.alias.stop)
        self.state=dict(physical=self.db.connection,pid=os.getpid(),transaction=self.db.atomic_blocks[0],guards=set(),migrations=frozenset())
        self.token=schema_reuse._action.set(self.state);self.addCleanup(schema_reuse._action.reset,self.token)
    def test_only_successfully_admitted_contract_can_be_reused(self):
        for module,key in ((scoped_action_ownership,'action'),(scoped_remark_ownership,'remark')):
            with patch.object(module,'_verify_guards') as verify:
                module.verify_guards();self.assertEqual(verify.call_count,1)
                self.state['guards'].add(key)
                module.verify_guards();self.assertEqual(verify.call_count,1)
                # An independently supplied database never borrows this proof.
                module.verify_guards(SimpleNamespace(db=object()));self.assertEqual(verify.call_count,2)
    def test_changed_transaction_or_connection_refuses_reuse(self):
        self.state['guards'].add('action')
        self.db.atomic_blocks=[object()]
        with self.assertRaisesRegex(ValueError,'lifetime changed'):schema_reuse.action_guard('action')
        self.db.atomic_blocks=[self.state['transaction']]
        self.db.connection=SimpleNamespace(closed=False)
        with self.assertRaisesRegex(ValueError,'lifetime changed'):schema_reuse.action_guard('action')
    def test_outside_action_no_static_admission_is_inherited(self):
        token=schema_reuse._action.set(None)
        try:
            with patch.object(scoped_action_ownership,'_verify_guards') as verify:
                scoped_action_ownership.verify_guards();scoped_action_ownership.verify_guards()
                self.assertEqual(verify.call_count,2)
        finally:schema_reuse._action.reset(token)
    def test_old_reader_contract_does_not_alias_new_producer_or_unknown_recipe(self):
        for family,old in GUARD_ADMISSION_RECIPES.items():
            self.assertTrue(compatible_guard_recipe(family,old,'f'*64))
            self.assertTrue(compatible_guard_recipe(family,'f'*64,'f'*64))
            self.assertFalse(compatible_guard_recipe(family,'0'*64,'f'*64))
            self.assertEqual(GUARD_ADMISSION_RECIPES[family],old)
        with self.assertRaises(ValueError):compatible_guard_recipe('unknown','x','x')

    def test_borrowed_namespace_facts_cannot_be_mutated_by_the_consumer(self):
        from mta.mdm import owned_namespace
        self.state.update(database={'name':'qualified','owner':{'oid':10}},
            registration={'consumer_oid':11},namespace_evidence={'owner_roles':[]})
        cursor=SimpleNamespace(db=self.db)
        database=owned_namespace._database_identity(cursor)
        database['owner']['oid']=99
        self.assertEqual(owned_namespace._database_identity(cursor)['owner']['oid'],10)
        registration=owned_namespace._registered_identity(cursor)
        registration['consumer_oid']=99
        self.assertEqual(owned_namespace._registered_identity(cursor)['consumer_oid'],11)
        evidence=owned_namespace._catalogue_evidence(cursor,self.state['database'],self.state['registration'])
        evidence['owner_roles'].append(99)
        self.assertEqual(owned_namespace._catalogue_evidence(
            cursor,self.state['database'],self.state['registration'])['owner_roles'],[])

    def test_certificate_revocation_remains_live_inside_an_admitted_action(self):
        from uuid import uuid4
        from unittest.mock import Mock
        from mta.runtime import input_v3
        from mta.runtime.ingestion_models import InitializationCertification
        identifier=str(uuid4());source='a'*64
        class Run:pass
        Run.objects=Mock()
        owner=Run();owner.pk=uuid4();owner.production_manifest={'ingestion_preparation':{'initialization_id':identifier}}
        current=SimpleNamespace(mdm_input_capture=SimpleNamespace(source=SimpleNamespace(
            production_initialization=SimpleNamespace(pk=identifier),digest=source)),csv_attempt=None)
        Run.objects.select_related.return_value.get.return_value=current
        self.state['guards'].update(('accepted','action','ingestion'))
        with patch.object(InitializationCertification.objects,'filter') as query:
            query.return_value.exists.return_value=True
            self.assertEqual(input_v3._run_initialization_id(owner,None),identifier)
            query.return_value.exists.return_value=False
            with self.assertRaisesRegex(ValueError,'not currently certified'):
                input_v3._run_initialization_id(owner,None)
            self.assertEqual(query.call_count,2)
            current.mdm_input_capture.source.production_initialization.pk=str(uuid4())
            with self.assertRaisesRegex(ValueError,'differs from MDM capture'):
                input_v3._run_initialization_id(owner,None)


class ReadSnapshotAdmissionTests(unittest.TestCase):
    def test_only_a_successful_check_in_the_same_read_snapshot_is_reused(self):
        from mta.presentation import publication_binding, request_scope

        foreign_cursor = SimpleNamespace(db=object())
        with (patch.object(publication_binding, 'snapshot_identity') as snapshot,
              patch.object(scoped_action_ownership, '_verify_guards') as verify,
              request_scope.read_request('/api/mta/GetResearchInsightData')):
            snapshot.return_value = (object(), object())
            verify.side_effect = [ValueError('guard changed'), None, None, None, None]
            with self.assertRaisesRegex(ValueError, 'guard changed'):
                scoped_action_ownership.verify_guards()
            scoped_action_ownership.verify_guards()
            scoped_action_ownership.verify_guards()
            self.assertEqual(verify.call_count, 2)

            scoped_action_ownership.verify_guards(foreign_cursor)
            verify.assert_called_with(foreign_cursor)
            snapshot.return_value = (object(), object())
            scoped_action_ownership.verify_guards()
            self.assertEqual(verify.call_count, 4)
            snapshot.return_value = None
            scoped_action_ownership.verify_guards()
            self.assertEqual(verify.call_count, 5)
