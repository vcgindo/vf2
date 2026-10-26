"""Pure actual-phase bridges; no custody, hook or native parity claim."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, date
from decimal import Decimal
import json
from pathlib import Path
import unittest

from mta.application import runtime_report_postbtr_inputs as bridge
from mta.application.native_output_contracts import native_assignments
from mta.application.runtime_report_btr_stage import prepare_btr_boundary
from mta.application.runtime_report_projection import project
from mta.runtime import phase_state
from mta.runtime.scope_bpr_histories import project as histories
from mta.application.production_output_policy import SOURCE_SCHEMA, contract
from mta.serialization import storage
from mta.temporal import chain
from tests.test_phase_state import native_bpr, MemoryImages


class PostBtrInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with native_assignments(True):
            bpr, sources, cls.refs = native_bpr('postbtr-source-bridge')
            policy=dict(bor_history_horizon=90,rrr_history_horizon=90,output_contract=contract())
            values=histories(sources.production_reports,
                dict(BOR_OrderAllocationHistory=[],RRR_OrderAllocationHistory=[]),
                business_date=bpr.context.today,policy=policy,source_schema=SOURCE_SCHEMA)
            cls.sources=replace(sources,production_reports=values)
            cls.phase=chain.produce_dbm(bpr)
        cls.definitions=[row for row in json.loads((Path(__file__).parent/'fixtures/runtime_reports_retained_20261019.json').read_bytes())
                         if row['Id'] in bridge.IDS]

    def boundary(self, scoped=False):
        phase=deepcopy(self.phase); sources=deepcopy(self.sources)
        if scoped:
            memory=MemoryImages()
            image=phase_state.encode(phase,sources,row_writer=memory.rows,export_writer=memory.export)
            phase,sources=phase_state.decode(image,**deepcopy(self.refs),
                row_reader=memory.read,export_reader=memory.read)
        with native_assignments(True):
            boundary=prepare_btr_boundary(phase,sources=sources if scoped else None,
                pick_source_digests=phase.pick_source_digests)
        return boundary,sources

    def build(self,boundary,sources,remarks=()):
        return bridge.build(boundary,sources=sources,frozen_remarks=list(remarks),
                            color_sequence=bridge.native_colours())

    def test_all_six_real_queries_full_and_restored_sources_match(self):
        full,full_sources=self.boundary()
        scoped,scoped_sources=self.boundary(True)
        a=self.build(full,full_sources); b=self.build(scoped,scoped_sources)
        self.assertEqual(set(a['sources']),set(a['descriptors']))
        for definition in self.definitions:
            with self.subTest(report=definition['Id']):
                left,refs=bridge.select(a,definition); right,_=bridge.select(b,definition)
                actual=project(definition,left); restored=project(definition,right)
                self.assertEqual(storage(actual),storage(restored))
                self.assertEqual(len(actual['columns']),24 if definition['Id'] in (2,3)
                                 else 34 if definition['Id']==8 else 31)
                self.assertEqual(set(left),set(refs))
        for name in ('BTR/LastBatchRunTbl','BPR/LastBatchRunTbl'):
            self.assertIs(type(a['sources'][name][0]['LastRunDate']),datetime)
        self.assertEqual(a['descriptors']['BPR/LastBatchRunTbl']['physical_table'],'DBM/LastBatchRunTbl')
        self.assertEqual(a['descriptors']['BPR/BORWithOrderAllocation']['physical_table'],
                         'production/BORWithOrderAllocation')
        self.assertFalse(a['descriptors']['BPR/SkuLocAttributeData']['persisted_bpr_partition'])

    def test_source_date_null_order_and_duplicates_are_independent(self):
        boundary,sources=self.boundary()
        history=deepcopy(boundary.trend_state['RationingHistory'])
        self.assertTrue(history)
        row=history[0]; row['ParentWhName']=None; row['DispatchPen']='12.30'
        row['ReportDate']='2037-04-08'
        boundary.trend_state['RationingHistory']=[row,deepcopy(row)]
        boundary.trend_state['LastBatchRunTbl']=[dict(LastRunDate='2037-04-10T00:00:00')]
        remarks=[dict(SKUCode='sku',WhCode='wh',SupplierCode='sup',Remark=None,
                      RemarkDate='2037-04-09T12:34:56.123')]*2
        bundle=self.build(boundary,sources,remarks)
        decoded=list(bundle['sources']['BTR/RationingHistory'])
        self.assertEqual(len(decoded),2)
        self.assertEqual(decoded[0],decoded[1])
        self.assertIsNone(decoded[0]['ParentWhName'])
        self.assertEqual(decoded[0]['DispatchPen'],Decimal('12.30'))
        self.assertEqual(decoded[0]['ReportDate'],date(2037,4,8))
        self.assertEqual(bundle['sources']['BTR/LastBatchRunTbl'][0]['LastRunDate'],datetime(2037,4,10))
        frozen=list(bundle['sources']['BPR/BORReport_OARemarkDetails'])
        self.assertEqual(len(frozen),2); self.assertIsNone(frozen[0]['Remark'])
        self.assertEqual(frozen[0]['RemarkDate'],datetime(2037,4,9,12,34,56,123000))
        self.assertEqual(len(bundle['sources']['BPR/BORWithOrderAllocation']),
                         len(sources.production_reports['BORWithOrderAllocation']))
        offset=[dict(remarks[0],RemarkDate='2037-04-10T00:30:00+05:30')]
        actual=self.build(boundary,sources,offset)['sources']['BPR/BORReport_OARemarkDetails'][0]
        self.assertEqual(actual['RemarkDate'],datetime(2037,4,9,19))

    def test_no_partial_complete_table_or_missing_history_fallback(self):
        boundary,sources=self.boundary()
        for name in ('BORWithOrderAllocation','BOR_OrderAllocationHistory','BOROARequirement'):
            reports=deepcopy(sources.production_reports); del reports[name]
            with self.subTest(missing=name),self.assertRaisesRegex(ValueError,'population missing'):
                self.build(boundary,replace(sources,production_reports=reports))
        reports=deepcopy(sources.production_reports)
        reports['BORWithOrderAllocation']=[dict(SKUCode='s',WhCode='w',DispatchColor='Red')]
        with self.assertRaisesRegex(ValueError,'fields missing'):
            self.build(boundary,replace(sources,production_reports=reports))
        for name in ('RationingHistory','LastBatchRunTbl','SkuLocAttributeData'):
            changed=replace(boundary,trend_state=deepcopy(boundary.trend_state))
            del changed.trend_state[name]
            with self.subTest(missing=name),self.assertRaisesRegex(ValueError,'population missing'):
                self.build(changed,sources)

    def test_site_filters_and_source_bag_multiplicity_use_complete_production(self):
        boundary,sources=self.boundary()
        reports=deepcopy(sources.production_reports)
        self.assertTrue(reports['BORWithOrderAllocation'])
        row=deepcopy(reports['BORWithOrderAllocation'][0])
        row.update(WhCode='P041',SupplierCode='supplier',Stock=123)
        other=deepcopy(row); other.update(WhCode='P001',Stock=456)
        reports['BORWithOrderAllocation']=[row,deepcopy(row),other]
        # Deliberately contradictory partial state must never become this input.
        boundary.phase.complete['BORWithOrderAllocation']=[dict(SKUCode='wrong',WhCode='wrong',DispatchColor='Red')]
        bundle=self.build(boundary,replace(sources,production_reports=reports))
        for identity,expected in ((4,[123,123,456]),(5,[123,123]),(6,[456])):
            definition=next(row for row in self.definitions if row['Id']==identity)
            logical,_=bridge.select(bundle,definition)
            actual=project(definition,logical)
            # Stock is SELECT position8, independent of helper-generated labels.
            self.assertEqual([cells[7] for cells in actual['rows']],expected)
            self.assertEqual([cells[2] for cells in actual['rows']],
                ['P041','P041','P001'] if identity==4 else ['P041','P041'] if identity==5 else ['P001'])
            self.assertEqual(len(actual['rows'][0]),31)

    def test_explicit_empty_capture_is_distinct_from_missing(self):
        boundary,sources=self.boundary()
        self.assertEqual(len(self.build(boundary,sources)['sources']['BPR/BORReport_OARemarkDetails']),0)
        with self.assertRaisesRegex(ValueError,'population required'):
            bridge.build(boundary,sources=sources,frozen_remarks=None,color_sequence=bridge.native_colours())
        with self.assertRaisesRegex(ValueError,'ColorSequence'):
            bridge.build(boundary,sources=sources,frozen_remarks=[],color_sequence=[])
        changed=deepcopy(bridge.native_colours()); changed[0]['SequenceNo']=True
        # bool==1 must not authenticate an int reference (checked below).
        with self.assertRaises(ValueError):
            bridge.build(boundary,sources=sources,frozen_remarks=[],color_sequence=changed)

    def test_scoped_wrong_sources_and_late_field_omission_deny(self):
        boundary,sources=self.boundary(True)
        with self.assertRaisesRegex(ValueError,'owner differs'):
            self.build(boundary,deepcopy(sources))
        boundary.phase.importer['SkuAttributeData']=[dict(SKUCode='s')]
        with self.assertRaisesRegex(ValueError,'fields missing'):
            self.build(boundary,sources)


if __name__=='__main__':unittest.main()
