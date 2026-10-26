"""Actual bridge -> typed wire -> report projection, without authority claims."""
from copy import deepcopy
from unittest.mock import patch
import unittest

from mta.application import runtime_report_postbtr_inputs as bridge
from mta.application.runtime_report_projection import project
from mta.runtime import runtime_report_stage_storage as images
from mta.runtime.phase_state import REGISTRY,recipe_digest
from mta.serialization import digest,storage
from tests import test_runtime_report_postbtr_inputs as fixture_module

OWNER='10000000-0000-4000-8000-000000000001'


class ReportStageStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.PostBtrInputTests.setUpClass()
        fixture=fixture_module.PostBtrInputTests()
        boundary,sources=fixture.boundary(True)
        cls.bundle=fixture.build(boundary,sources,[dict(SKUCode='sku',WhCode='wh',
            SupplierCode=None,Remark='quotes, " and\nnewline',RemarkDate='2037-04-10T00:30:00+05:30')])

    def capture(self):
        rows={}
        def writer(logical,values):
            meta,wire,_,_=images.describe(OWNER,logical,values)
            rows[meta['image']]=list(wire)
            return meta
        manifest=images.capture(None,candidate_id=OWNER,placement='PostBTR',
            sources=self.bundle['sources'],row_writer=writer)
        return manifest,rows

    def test_real_bridge_roundtrip_all_six_queries_and_native_types(self):
        manifest,wire=self.capture()
        def load(_run,meta,**_options):return deepcopy(wire[meta['image']])
        for definition in fixture_module.PostBtrInputTests.definitions:
            expected,descriptors=bridge.select(self.bundle,definition)
            fields={name:value['fields'] for name,value in descriptors.items()}
            with self.subTest(report=definition['Id']),patch.object(images.typed,'load_image',load):
                actual=images.read(None,manifest,candidate_id=OWNER,placement='PostBTR',fields=fields)
                self.assertEqual(storage(expected),storage(actual))
                self.assertEqual(storage(project(definition,expected)),storage(project(definition,actual)))
        self.assertEqual(set(manifest['images']),set(self.bundle['sources']))
        self.assertNotIn('quotes',str(manifest))

    def test_shared_phase_registry_and_recipe_unchanged(self):
        before=recipe_digest();registry=deepcopy(REGISTRY)
        self.capture()
        self.assertEqual(recipe_digest(),before)
        self.assertEqual(REGISTRY,registry)
        self.assertFalse(set(images.TABLES)&REGISTRY.keys())
        self.assertEqual(len(set(map(images.typed.table_name,images.TABLES))),len(images.TABLES))

    def test_metadata_cannot_move_to_foreign_owner_stage_or_table(self):
        original,_=self.capture()
        for mutation in ('owner','placement','image','table','missing-field','ordinal','unknown-source'):
            value=deepcopy(original);name=next(iter(value['images']));meta=value['images'][name]
            if mutation=='owner':value['candidate_id']='20000000-0000-4000-8000-000000000001'
            elif mutation=='placement':value['placement']='Final'
            elif mutation=='image':meta['image']=meta['image'].replace('10000000','20000000')
            elif mutation=='table':meta['table']='BTR/RationingHistory'
            elif mutation=='missing-field':meta['fields']=[['invented','invented','str']]
            elif mutation=='ordinal':meta['count']=-1
            else:value['images']['invented']=value['images'].pop(name)
            value['digest']=digest({k:v for k,v in value.items() if k!='digest'})
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                images.validate_images(value,candidate_id=OWNER,placement='PostBTR')

    def test_missing_source_and_nonempty_column_omission_deny(self):
        manifest,wire=self.capture()
        with self.assertRaisesRegex(ValueError,'absent'):
            images.read(None,manifest,candidate_id=OWNER,placement='PostBTR',fields={'missing':['SKUCode']})
        logical='BPR/BORReport_OARemarkDetails'
        value=deepcopy(manifest);value['images'][logical]['fields']=[]
        value['digest']=digest({k:v for k,v in value.items() if k!='digest'})
        with self.assertRaisesRegex(ValueError,'no columns'):
            images.validate_images(value,candidate_id=OWNER,placement='PostBTR')

    def test_unknown_source_shape_fails_before_any_write(self):
        called=[]
        with self.assertRaises(ValueError):
            images.capture(None,candidate_id=OWNER,placement='PostBTR',sources={
                'BPR/ColorSequence':[dict(Color='Red',SequenceNo=2)],
                'BPR/BORWithOrderAllocation':[dict(invented=1)]},
                row_writer=lambda *args:called.append(args))
        self.assertEqual(called,[])
        for row in (dict(color='Red',SequenceNo=2),dict(Color='Red',color='Blue',SequenceNo=2)):
            with self.subTest(row=row),self.assertRaisesRegex(ValueError,'canonical column'):
                images.capture(None,candidate_id=OWNER,placement='PostBTR',
                    sources={'BPR/ColorSequence':[row]},row_writer=lambda *args:called.append(args))
            self.assertEqual(called,[])

    def test_explicit_empty_is_readable_but_absence_is_not(self):
        manifest=images.capture(None,candidate_id=OWNER,placement='PostBTR',
            sources={'BPR/BORWithOrderAllocation':[]},
            row_writer=lambda name,values:images.describe(OWNER,name,values)[0])
        with patch.object(images.typed,'load_image',return_value=[]):
            rows=images.read(None,manifest,candidate_id=OWNER,placement='PostBTR',
                fields={'BPR/BORWithOrderAllocation':['SKUCode','WhCode']})
            self.assertEqual(list(rows['BPR/BORWithOrderAllocation']),[])
