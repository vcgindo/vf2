"""Actual BPR live-out/readback contracts, without runtime publication."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import unittest

from mta.application import runtime_report_bpr_inputs as bridge
from mta.application import runtime_demand_reports as demand
from mta.application.native_output_contracts import native_assignments
from mta.application.runtime_report_projection import project
from mta.runtime import phase_state
from mta.runtime.relational_state import STORAGE_TABLES
from mta.serialization import storage
from tests.test_phase_state import native_bpr,MemoryImages


class BprInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with native_assignments(True):
            cls.phase,cls.sources,cls.refs=native_bpr('bpr-pure-report-bridge')
        cls.definitions={row['Id']:row for row in json.loads(
            (Path(__file__).parent/'fixtures/runtime_reports_retained_20261019.json').read_bytes())}

    def restored(self):
        memory=MemoryImages()
        image=phase_state.encode(deepcopy(self.phase),deepcopy(self.sources),
            row_writer=memory.rows,export_writer=memory.export)
        phase,_sources=phase_state.decode(image,**deepcopy(self.refs),
            row_reader=memory.read,export_reader=memory.read)
        return phase

    def test_full_and_actual_phase_codec_match_all_cells_of_both_real_queries(self):
        before=storage(self.phase)
        live=bridge.build(self.phase); restored=bridge.build(self.restored())
        for identity,width in ((7,12),(10,107)):
            with self.subTest(report=identity):
                definition=self.definitions[identity]
                a,refs=bridge.select(live,definition); b,_=bridge.select(restored,definition)
                self.assertEqual(set(a),set(refs))
                for logical in a:
                    self.assertEqual(list(a[logical]),list(b[logical]))
                left=project(definition,a);right=project(definition,b)
                self.assertEqual(left['columns'],right['columns'])
                left_rows=list(left['rows']);right_rows=list(right['rows'])
                self.assertTrue(left_rows)
                self.assertEqual(left_rows,right_rows)
                self.assertTrue(all(len(row)==width for row in left_rows))
        self.assertEqual(storage(self.phase),before)

    def test_exact_existing_adapter_fields_and_physical_lineage(self):
        bundle=bridge.build(self.phase)
        expected={
            'BPR/SpikeOrderData':demand.SPIKE_FIELDS,
            'BPR/vf_RationedReqReport':demand.RATIONED_FIELDS,
            'BPR/SupplierDispatchReq':('SKUCode','WHCode','SupplierCode','OriginalReq','DispatchReq',*demand.SUPPLIER_BANDS),
        }
        for table in ('SiteDescriptionTbl','SkuAttributeData','LocationAttributeData','SkuLocAttributeData'):
            expected['BPR/'+table]=tuple(name for name,_kind in STORAGE_TABLES['Importer/'+table])
        self.assertEqual(set(bundle['sources']),set(expected))
        for logical,fields in expected.items():
            self.assertEqual(bundle['descriptors'][logical]['fields'],list(fields))
            for row in bundle['sources'][logical]:self.assertEqual(tuple(row),fields)
        self.assertEqual(bundle['descriptors']['BPR/SupplierDispatchReq']['physical_table'],
                         'complete/BPR/SupplierDispatchReq')
        self.assertEqual(bundle['descriptors']['BPR/vf_RationedReqReport']['physical_path'],
                         'late/vf_RationedReqReport')
        self.assertFalse(bundle['descriptors']['BPR/SkuLocAttributeData']['persisted_bpr_partition'])
        self.assertEqual(set(bundle['copy_descriptors']),{'BPR/'+name for name in
            ('SkuAttributeData','SKUDescriptionTbl','LocationAttributeData','SiteDescriptionTbl')})

    def test_spike_dates_bits_nulls_and_duplicate_order_are_actual_source_cells(self):
        phase=deepcopy(self.phase)
        rows=phase.order_state['SpikeOrderData'];self.assertTrue(rows)
        first=deepcopy(rows[0]);first.update(OrderKey=83,DueDate=None,IntroDate='2037-04-08',
            FirstServicingWhCode=None,IsSpike='1',IsElephant='0')
        second=deepcopy(first);second['OrderKey']=84
        phase.order_state['SpikeOrderData']=[first,deepcopy(first),second]
        bundle=bridge.build(phase);logical,_=bridge.select(bundle,self.definitions[7])
        actual=list(project(self.definitions[7],logical)['rows'])
        self.assertEqual([row[0] for row in actual],[83,83,84])
        self.assertIs(actual[0][3],True);self.assertIs(actual[0][4],False)
        self.assertIsNone(actual[0][9]);self.assertIsNone(actual[0][10])
        self.assertEqual(actual[0][11],date(2037,4,8))

    def test_total_uses_complete_supplier_bands_and_preserves_copy_multiplicity(self):
        phase=deepcopy(self.phase)
        supplier=phase.complete['SupplierDispatchReq'];self.assertTrue(supplier)
        # Separate source owners: these fields never come from rationed A.
        for row in supplier:
            row.update(ReqTopOfRed=101,ReqTopOfYellow=202,ReqTopOfGreen=303)
        for row in phase.late['vf_RationedReqReport']:
            row.update(ReqTopOfRed=-1,ReqTopOfYellow=-2,ReqTopOfGreen=-3)
        for row in phase.importer['SkuLocAttributeData']:row['c1']=None
        baseline=bridge.build(phase)
        source,_=bridge.select(baseline,self.definitions[10])
        rows=list(project(self.definitions[10],source)['rows']);self.assertTrue(rows)
        bands={row[20:23] for row in rows}
        self.assertIn((101,202,303),bands)
        self.assertLessEqual(bands,{(101,202,303),(None,None,None)})
        self.assertTrue(all(type(row[7]) is Decimal for row in rows if row[7] is not None))
        phase.importer['SkuLocAttributeData']*=2
        duplicate=bridge.build(phase);source,_=bridge.select(duplicate,self.definitions[10])
        doubled=list(project(self.definitions[10],source)['rows'])
        self.assertEqual(len(doubled),2*len(rows))
        self.assertEqual(doubled,[row for row in rows for _ in (0,1)])
        self.assertTrue(all(row['c1'] is None for row in duplicate['sources']['BPR/SkuLocAttributeData']))

    def test_missing_population_and_late_missing_field_deny(self):
        for owner,name in (('order_state','SpikeOrderData'),('late','vf_RationedReqReport'),
                ('complete','SupplierDispatchReq'),('importer','SkuLocAttributeData'),
                ('importer','SkuAttributeData'),('importer','SKUDescriptionTbl'),
                ('importer','SiteDescriptionTbl'),('importer','LocationAttributeData')):
            phase=deepcopy(self.phase);del getattr(phase,owner)[name]
            with self.subTest(owner=owner,name=name),self.assertRaisesRegex(ValueError,'population missing'):
                bridge.build(phase)
        for owner,name,field in (('order_state','SpikeOrderData','DueDate'),
                ('complete','SupplierDispatchReq','ReqTopOfRed'),
                ('late','vf_RationedReqReport','Stock'),('importer','SkuLocAttributeData','c15')):
            phase=deepcopy(self.phase);rows=getattr(phase,owner)[name]
            self.assertTrue(rows);del rows[-1][field]
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'fields missing'):bridge.build(phase)

    def test_empty_sources_and_wrong_phase_do_not_fabricate_rows(self):
        phase=deepcopy(self.phase)
        phase.order_state['SpikeOrderData']=[]
        phase.complete['SupplierDispatchReq']=[]
        bundle=bridge.build(phase)
        logical,_=bridge.select(bundle,self.definitions[7])
        self.assertEqual(list(project(self.definitions[7],logical)['rows']),[])
        logical,_=bridge.select(bundle,self.definitions[10])
        rows=list(project(self.definitions[10],logical)['rows'])
        # SupplierDispatchReq is LEFT joined: absence preserves actual rationed
        # rows with NULL bands. Empty rationed owner really produces no rows.
        self.assertTrue(rows)
        self.assertTrue(all(row[20:23]==(None,None,None) for row in rows))
        phase.late['vf_RationedReqReport']=[]
        logical,_=bridge.select(bridge.build(phase),self.definitions[10])
        self.assertEqual(list(project(self.definitions[10],logical)['rows']),[])
        with self.assertRaisesRegex(ValueError,'Actual native BPR'):bridge.build(None)
        with self.assertRaisesRegex(ValueError,'PostBPR input'):bridge.select(bundle,self.definitions[2])


if __name__=='__main__':unittest.main()
