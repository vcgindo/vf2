"""Owner selection contracts; real retained typed-owner proof is separate."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from contextlib import ExitStack
from mta.serialization import digest
from mta.presentation import scoped_transit as module
from mta.presentation.context import PublicationUnavailable


class ScopedTransitOpeningSettingsTests(TestCase):
    def setUp(self):
        self.profile={'delivery':{'site_code':'ordinary'}}
        self.rows=[dict(Parameter='SuperDelayFactor',Value='2',Description='Retained')]
        self.item=dict(table='Importer/VFSettings',image='input/opening/state/dbm/VFSettings/values')
        self.owner=SimpleNamespace(pk='opening',source_id=3,opening_date=date(2026,10,17),
            source=SimpleNamespace(digest='source'),input_sha256='input',input_digest='content',
            configuration_digest='configuration',_meta=SimpleNamespace(model_name='productioninitialization'),
            input_payload={'images':{'settings':self.item}})
        self.binding=dict(id='opening',source_digest='source',input_sha256='input',
            content_digest='content',configuration_digest='configuration')
        self.run=SimpleNamespace(input_payload={'schema':'native'},predecessor_id=None,business_date=date(2026,10,18))
        self.phase=SimpleNamespace(run=self.run,source_id=3,
            snapshot=SimpleNamespace(manifest={'references':{'profile':digest(self.profile)}}))

    def resolve(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(module,'read_input',return_value={
                'profile':self.profile,'initialization_binding':self.binding}))
            node=stack.enter_context(patch('mta.presentation.scoped_inherited_btr._node',
                return_value=(self.owner,{'records':'settings'})))
            load=stack.enter_context(patch('mta.runtime.opening_storage.load_image',return_value=self.rows))
            locator=stack.enter_context(patch.object(module,'_settings_owner',return_value={'owner':'checked'}))
            result=module._opening_settings(self.phase)
            node.assert_called_once_with(self.run,'input/opening/state/dbm/VFSettings')
            load.assert_called_once_with(self.owner,self.item)
            locator.assert_called_once_with(self.run,self.rows,path='input/opening/state/dbm/VFSettings')
            return result

    def test_root_uses_exact_retained_typed_owner_without_profile_mutation(self):
        before=digest(self.profile)
        self.assertEqual(self.resolve(),(self.rows,{'owner':'checked'}))
        self.assertEqual(digest(self.profile),before)

    def test_foreign_initialization_source_date_or_binding_refuses(self):
        for name,value in [('source_id',4),('opening_date',date(2026,10,16)),('pk','foreign')]:
            original=getattr(self.owner,name);setattr(self.owner,name,value)
            with self.subTest(name=name),self.assertRaises(PublicationUnavailable):self.resolve()
            setattr(self.owner,name,original)

    def test_incorrect_table_is_not_accepted_as_settings(self):
        self.item['table']='other'
        with self.assertRaises(PublicationUnavailable):self.resolve()

    def test_undeclared_initialization_is_denied(self):
        self.binding.clear()
        with self.assertRaises(PublicationUnavailable):self.resolve()

    def test_successor_cannot_borrow_running_or_foreign_predecessor(self):
        self.run.predecessor_id='parent'
        parent=SimpleNamespace(kind='DAILY_CHAIN',status='RUNNING')
        with patch.object(module,'read_input',return_value={'profile':self.profile,
                'initialization_binding':self.binding,'lineage':{}}), \
                patch('mta.runtime.models.CalculationRun.objects.get',return_value=parent):
            with self.assertRaises(PublicationUnavailable):module._opening_settings(self.phase)

    def test_successor_uses_only_its_consumed_same_source_parent_image(self):
        self.run.predecessor_id='parent'
        path='closing/dbm/VFSettings'
        item=dict(image=path,table='Importer/VFSettings')
        parent=SimpleNamespace(pk='parent',kind='DAILY_CHAIN',status='SUCCEEDED',
            business_date=date(2026,10,17),output_digest='parent-output',
            input_manifest_digest='parent-input',
            mdm_input_capture=SimpleNamespace(source_id=3,status='CONSUMED'),
            production_manifest={'images':{path:item}})
        current={'profile':self.profile,'initialization_binding':self.binding,
            'lineage':dict(run_id='parent',output_digest='parent-output',commands=[])}
        previous={'profile':self.profile,'initialization_binding':self.binding}
        for source,status in ((3,'CONSUMED'),(4,'CONSUMED'),(3,'CAPTURED')):
            parent.mdm_input_capture=SimpleNamespace(source_id=source,status=status)
            with ExitStack() as stack:
                stack.enter_context(patch.object(module,'read_input',side_effect=[current,previous]))
                stack.enter_context(patch('mta.runtime.models.CalculationRun.objects.get',return_value=parent))
                verify=stack.enter_context(patch('mta.runtime.receipt_integrity.verify_root'))
                commands=stack.enter_context(patch('mta.runtime.models.RunCommand.objects.filter'))
                commands.return_value.order_by.return_value=[]
                stack.enter_context(patch('mta.presentation.scoped_inherited_btr._node',
                    return_value=(self.run,{'scalar':None})))
                load=stack.enter_context(patch('mta.runtime.relational_state.load_image',return_value=self.rows))
                if (source,status)!=(3,'CONSUMED'):
                    with self.assertRaises(PublicationUnavailable):module._opening_settings(self.phase)
                    load.assert_not_called()
                else:
                    rows,locator=module._opening_settings(self.phase)
                    self.assertEqual(rows,self.rows)
                    self.assertEqual(locator['owner_id'],'parent')
                    self.assertEqual(locator['output_digest'],'parent-output')
                    load.assert_called_once_with(parent,item)
                    verify.assert_called_once_with(parent)
