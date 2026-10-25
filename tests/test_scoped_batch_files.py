"""Finite phase-derived file bytes and exclusive-root behavior; no database writes."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','scoped-batch-unit-only')
import django
django.setup()
from copy import deepcopy
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import json
import unittest
from unittest.mock import patch
import zipfile
from mta.presentation import scoped_batch_files as batch
from mta.presentation.context import PublicationUnavailable
from mta.runtime import phase_state
from mta.serialization import digest
from test_operational_bor import bor_row
from test_operational_exceptions import master, daily, processed


class ScopedBatchFilesTests(unittest.TestCase):
    def fixture(self, nonempty=False):
        manifest=dict(state=dict(importer={},control_final={},diagnostics={},late={}),
                      consumers=dict(production_reports={}),images={})
        run=NS(pk='run', business_date=date(2026,10,24))
        phase=NS(pk='phase',run_id='run',run=run,phase='BPR',digest='phase-digest',
                 snapshot=NS(state_digest='snapshot',manifest=manifest))
        bags={}
        def add(node, suffix, table, rows):
            logical='phase/BPR/'+suffix
            physical='phase/PRE_BPR/'+suffix
            cursor=manifest
            for part in node[:-1]:cursor=cursor[part]
            cursor[node[-1]]=dict(image=logical)
            registry=dict(phase_state.REGISTRY[table])
            fields=[[field,field,'int' if type(value) is int else 'str'] for field,value in rows[0].items()] if rows else []
            self.assertTrue(all(field in registry for field,_,_ in fields))
            item=dict(image=physical,table=table,count=len(rows),digest=digest(rows),fields=fields)
            manifest['images'][logical]=item
            bags[physical]=rows
        add(('state','importer','SKUDescriptionTbl'),'importer/SKUDescriptionTbl','Importer/SKUDescriptionTbl',
            [dict(SKUCode='S',SKUDescription='S, Name')])
        add(('state','importer','SiteDescriptionTbl'),'importer/SiteDescriptionTbl','Importer/SiteDescriptionTbl',
            [dict(WHCode='W',WHDescription='Warehouse'),dict(WHCode='P',WHDescription='Parent')])
        add(('consumers','production_reports','BORWithOrderAllocation'),'sources/production/BORWithOrderAllocation',
            'production/BORWithOrderAllocation',[bor_row(),bor_row()])
        add(('consumers','production_reports','BOROARequirement'),'sources/production/BOROARequirement',
            'production/BOROARequirement',[dict(SKUCode='S',WhCode='W',AdvAllocDone=2)])
        add(('state','diagnostics','failed_force'),'diagnostics/failed_force','Projection/FailedForce',[])
        add(('state','importer','MasterData'),'importer/MasterData','Importer/MasterData',
            [processed(),processed(WhCode='P',Norm=0,ParentWhCode=None)] if nonempty else [processed()])
        add(('state','control_final','phase_out'),'controls/phase_out','DBM/PhaseOutTbl',[])
        add(('state','bpr_master'),'bpr_master','BPR/BPRMaster',[master()])
        add(('state','late','BPRDailyConsumption'),'late/BPRDailyConsumption','BPR/DailyConsumption',
            [daily(ReportDate='2026-10-24')] if nonempty else [])
        return phase,bags

    def context(self,phase,bags):
        stack=ExitStack()
        stack.enter_context(patch('mta.runtime.scope_runtime_reports.require_test_database'))
        stack.enter_context(patch.object(batch.scoped_sources,'_accepted_phase',return_value=phase))
        loader=stack.enter_context(patch.object(batch,'load_image',side_effect=lambda run,item,**kwargs:deepcopy(bags[item['image']])) )
        stack.enter_context(patch.object(batch.bor,'collect_bor_order_allocation',side_effect=AssertionError('allocation replay')))
        stack.enter_context(patch.object(batch.bor,'collect_bor_order_allocation_history',side_effect=AssertionError('history replay')))
        stack.loader=loader
        return stack

    def test_payload_is_source_bound_retains_duplicate_rows_and_canonical_empty_branches(self):
        phase,bags=self.fixture()
        before=deepcopy(bags)
        with self.context(phase,bags) as context:
            metadata,data=batch.payload('phase',expected_digest='phase-digest',declaration=deepcopy(batch.TEST_DECLARATION))
            self.assertEqual(metadata['counts']['BOR_OrderAllocation'],2)
            self.assertEqual(data['BOR_OrderAllocation'].count(b'"S, Name"'),2)
            self.assertEqual(data['FailedForceNormChanges'],b'SKUCode,WHCode,VectorFlowNorm,Reason\r\n')
            self.assertEqual(data['NoNormParentReport'],b'')
            self.assertIsNone(data['BPRExceptionReport'])
            self.assertEqual(len(metadata['sources']),9)
            self.assertTrue(all(v['physical_image'].startswith('phase/PRE_BPR/') for v in metadata['sources'].values()))
            self.assertTrue(all(call.args[0] is phase.run for call in context.loader.call_args_list))
            self.assertEqual(metadata['digest'],digest({k:v for k,v in metadata.items() if k!='digest'}))
        self.assertEqual(bags,before)

    def test_missing_source_wrong_alias_and_changed_rows_deny_instead_of_empty(self):
        for defect in ('missing','alias','rows','phase'):
            phase,bags=self.fixture()
            with self.subTest(defect=defect),self.context(phase,bags):
                node=phase.snapshot.manifest['state']['diagnostics']
                item=phase.snapshot.manifest['images'][node['failed_force']['image']]
                if defect=='missing':del node['failed_force']
                elif defect=='alias':item['image']='phase/PRE_BPR/diagnostics/unrelated'
                elif defect=='rows':
                    bags[item['image']]=[dict(SKUCode='S')]
                else:phase.phase='PRE_BPR'
                with self.assertRaises(PublicationUnavailable):
                    batch.payload('phase',expected_digest='phase-digest',declaration=deepcopy(batch.TEST_DECLARATION))

    def test_explicit_test_settings_are_required(self):
        for changes in ({'IsMTOEnvironment':1},{'IsMTOEnvironment':False}, {'allocation_history':'continue'},
                        {'excluded_optional_branches':[]}):
            declaration=dict(batch.TEST_DECLARATION,**changes)
            with self.assertRaises(PublicationUnavailable):batch.payload('phase',expected_digest='digest',declaration=declaration)

    def test_native_serializer_rejects_boolean_quantity_without_coercion(self):
        phase,bags=self.fixture()
        image=phase.snapshot.manifest['consumers']['production_reports']['BORWithOrderAllocation']['image']
        physical=phase.snapshot.manifest['images'][image]['image']
        bags[physical][0]['Norm']=True
        with self.context(phase,bags),self.assertRaises(ValueError):
            batch.payload('phase',expected_digest='phase-digest',declaration=deepcopy(batch.TEST_DECLARATION))

    def test_prepare_empty_branch_uses_actual_business_day_and_retains_existing_root(self):
        phase,bags=self.fixture()
        with TemporaryDirectory() as parent,self.context(phase,bags):
            root=Path(parent)/'exclusive'
            metadata,paths=batch.prepare('phase',expected_digest='phase-digest',declaration=deepcopy(batch.TEST_DECLARATION),root=root)
            self.assertEqual(set(paths['files']),{'output/BOR_OrderAllocation.csv','download/BOR_OrderAllocation.csv',
                'output/24-FailedForceNormChanges.csv','output/NoNormParentReport.csv'})
            self.assertEqual((root/'output/NoNormParentReport.csv').read_bytes(),b'')
            self.assertFalse(list(root.rglob('*.zip')))
            self.assertEqual(json.loads(Path(paths['manifest']).read_text())['digest'],metadata['digest'])
            retained=(root/'download/BOR_OrderAllocation.csv').read_bytes()
            with self.assertRaises(ValueError):
                batch.prepare('phase',expected_digest='phase-digest',declaration=deepcopy(batch.TEST_DECLARATION),root=root)
            self.assertEqual((root/'download/BOR_OrderAllocation.csv').read_bytes(),retained)
            self.assertFalse(list(root.rglob('*Pick*')))
            self.assertFalse(list(root.rglob('*InputData*')))

    def test_nonempty_native_branches_require_writer_before_mutation_then_use_existing_wrappers(self):
        phase,bags=self.fixture(nonempty=True)
        def archive(*,root,staging,members,destination):
            target=Path(root)/destination
            target.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(target,'x') as output:
                for name in members:output.write(Path(root)/staging/name,name)
            return dict(test_writer=True)
        with TemporaryDirectory() as parent,self.context(phase,bags):
            root=Path(parent)/'exclusive'
            with self.assertRaises(ValueError):
                batch.prepare('phase',expected_digest='phase-digest',declaration=deepcopy(batch.TEST_DECLARATION),root=root)
            self.assertFalse(root.exists())
            metadata,paths=batch.prepare('phase',expected_digest='phase-digest',declaration=deepcopy(batch.TEST_DECLARATION),root=root,archive_writer=archive)
            self.assertGreater(metadata['counts']['NoNormParentReport'],0)
            self.assertGreater(metadata['counts']['BPRExceptionReport'],0)
            self.assertFalse((root/'output/NoNormParentReport.csv').exists())
            self.assertTrue((root/'output/BPRExceptionReport.csv').exists())
            with zipfile.ZipFile(root/'download/BPRExceptionReport.zip') as zipped:
                self.assertEqual(zipped.read('BPRExceptionReport.csv'),(root/'output/BPRExceptionReport.csv').read_bytes())
