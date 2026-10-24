"""Accepted BPR transit sources/producers; rollback-only supplied components.

No native registration, selected UI, legacy oracle or scale acceptance implied.
Explicit positive overrides use retained H3 identities and external facts only.
"""
from copy import deepcopy
from datetime import date,datetime
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_pick_files_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedTransitTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr'):
        locals()[_name]=fixtures.ScopedPickFileTests.__dict__[_name]

    def owner(self,**options):
        from tests import production_h3_fixture as h3,test_h3_daily_integration as supplied
        from tests.test_production_source_inputs import source_day
        sources=deepcopy(getattr(self,'transit_sources',source_day()['producer_sources']))
        original=h3.supplied_day
        def day(*args,**kwargs):
            result=original(*args,**kwargs)
            for source,target in (('shipments','shipment_input'),('transporters','transporter_input'),
                    ('report_policy','production_report_policy'),('report_opening','production_report_opening')):
                if source in sources:result['day'][target]=deepcopy(sources[source])
            result['day']['production_report_schema']=sources['schema']
            return result
        opening=supplied.frame()
        # This existing captured profile path explicitly owns Importer/VFSettings,
        # distinct from ImporterSettingsTbl and opening DBM/VFSettings.
        if getattr(self,'include_factor',True):
            opening['profile']['delivery']['btr_history']['importer_vf_settings'].extend(
                [dict(Parameter=getattr(self,'factor_parameter','SuperDelayFactor'),Value='2',
                    Description='Declared scoped transit component setting')]*getattr(self,'factor_count',1))
        if getattr(self,'conflicting_factor',False):
            opening['profile']['delivery']['conditional_dbm']['importer_vf_settings'].append(
                dict(Parameter='SuperDelayFactor',Value='9',Description='Conflicting separate projection'))
        if getattr(self,'wrong_table_factor',False):
            opening['opening']['state']['dbm']['VFSettings'].append(
                dict(Parameter='SuperDelayFactor',Value='2',Description='Different canonical owner'))
            opening['opening']['state']['importer_settings'].append(dict(Parameter='SuperDelayFactor',Value='2'))
        with patch.object(h3,'supplied_day',side_effect=day),patch.object(supplied,'frame',return_value=opening):
            fixtures.ScopedPickFileTests.owner(self,**options)

    def positive(self,*,duplicates=False,quantity=4):
        from tests.test_production_source_inputs import source_day
        from tests.production_h3_fixture import CHILD,PARENT
        self.transit_sources=source_day()['producer_sources']
        row=self.transit_sources['shipments']['rows'][0]
        row.update(ToLocationCode=CHILD,FromLocationCode=PARENT,InTransitQty=quantity)
        if duplicates:
            self.transit_sources['shipments']['rows'].append(deepcopy(row))
            self.transit_sources['transporters']['rows']*=2

    def produce(self,**changes):
        from mta.presentation.scoped_transit import produce
        return produce(**dict(dict(phase_id=self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0),**changes))

    def expected_transit(self,*,positive=False,quantity=7):
        from tests.production_h3_fixture import CHILD,PARENT
        return dict(SKUCode='SUPPLIED-Z9',WhCode=CHILD if positive else 'OWN-PARENT',
            ParentWhCode=PARENT if positive else 'SUPPLIER',CurrentLocationCode=None,LRCode='L-1',
            OrderNo='O-1',CreationDate=date(2037,4,8),GateOutDate=date(2037,4,9),InTransitQty=quantity,
            TransporterCode='T-1',Ageing=2,ETA=None,TLT=1,SLT=None,Remark=None,ReportDate=date(2037,4,10))

    def test_original_source_retains_null_standards_and_does_not_invent_a_match(self):
        from mta.serialization import digest
        from mta.presentation import scoped_sources
        self.bpr();metadata,rows=self.produce()
        self.assertEqual(rows['InTransitData'],[self.expected_transit()])
        self.assertEqual(rows['GoodsInTransitTransporterMaster'],[])
        self.assertEqual(rows['TransitRejectedMaster'],[])
        bound=scoped_sources.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        standard=next(row for row in bound.rows('closing/dbm/SKULocStandardAttributes')
            if (row['SKUCode'],row['WhCode'])==('SUPPLIED-Z9','OWN-PARENT'))
        self.assertIsNone(standard['SLT']);self.assertIsNone(standard['Price'])
        report=next(row for row in bound.rows('reports/bpr/vf_RationedReqReport')
            if (row['SKUCode'],row['WhCode'])==('SUPPLIED-Z9','OWN-PARENT'))
        self.assertEqual((report['ParentWhCode'],report['GIT']),('OWN-ROOT7',0))
        self.assertEqual(metadata['phase_digest'],self.receipt.digest)
        self.assertEqual(metadata['images']['InTransitData'],dict(count=1,digest=digest(rows['InTransitData'])))

    def test_positive_external_override_exact_rows_and_duplicate_join_occurrences(self):
        from mta.serialization import storage
        from mta.presentation import scoped_sources
        from tests.production_h3_fixture import CHILD,PARENT
        self.positive(duplicates=True);self.bpr();metadata,rows=self.produce()
        self.assertEqual(rows['InTransitData'],[self.expected_transit(positive=True,quantity=4)]*2)
        bound=scoped_sources.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        report=next(row for row in bound.rows('reports/bpr/vf_RationedReqReport')
            if (row['SKUCode'],row['WhCode'],row['ParentWhCode'])==('SUPPLIED-Z9',CHILD,PARENT))
        self.assertEqual(report['GIT'],4)
        expected=dict(Status='',OrderNo='O-1',SKUCode='SUPPLIED-Z9',WhCode=CHILD,ParentWhCode=PARENT,
            CurrentLocation=None,TransporterCode='T-1',TransporterName='Carrier',TransporterContact=None,
            LRCode='L-1',InTransitQty=4,PhysicalInventoryPen=report['PhysicalInventoryPen'],
            PhysicalInventoryColor=report['PhysicalInventoryColor'],PipelineInventoryColor=report['DispatchColor'],
            Price=None,SLT=None,Ageing=2,ETA=None,Remark=None,CreationDate=date(2037,4,8),
            TruckStatus=None,SKUStatus=None,IsParent=False,IsReceiving=True)
        self.assertEqual(storage(rows['GoodsInTransitTransporterMaster']),storage([expected]*4))
        self.assertEqual([row['InTransitQty'] for row in rows['InTransitDataRaw']],[4,4])
        self.assertEqual(metadata['images']['GoodsInTransitTransporterMaster']['count'],4)
        self.assertEqual(metadata['super_delay_factor'],'2')
        self.assertEqual(metadata['settings_owner']['path'],
            'input/profile/delivery/btr_history/importer_vf_settings')
        self.assertEqual(metadata['settings_owner']['image']['table'],'Importer/VFSettings')

    def test_empty_sources_are_owned_but_missing_and_stale_sources_deny(self):
        from django.db import transaction
        from tests.test_production_source_inputs import source_day
        from mta.presentation.context import PublicationUnavailable
        for case in ('empty','missing','stale','wrong_schema','missing_rows'):
            with self.subTest(case=case),transaction.atomic():
                self.transit_sources=source_day()['producer_sources']
                if case=='empty':
                    self.transit_sources['shipments']['rows']=[];self.transit_sources['transporters']['rows']=[]
                elif case=='missing':self.transit_sources.pop('transporters')
                elif case=='stale':self.transit_sources['shipments']['business_date']='2037-04-09'
                elif case=='wrong_schema':self.transit_sources['transporters']['schema']='unknown'
                else:self.transit_sources['shipments'].pop('rows')
                self.bpr()
                if case=='empty':self.assertTrue(all(bag==[] for bag in self.produce()[1].values()))
                elif case=='missing':
                    with self.assertRaisesRegex(PublicationUnavailable,'captured_sources_unavailable'):self.produce()
                else:
                    with self.assertRaisesRegex(ValueError,'Explicit dated production source'):self.produce()
                transaction.set_rollback(True)

    def test_missing_and_duplicate_scalar_settings_deny_even_owned_empty(self):
        from django.db import transaction
        from tests.test_production_source_inputs import source_day
        for number in (0,2):
            with self.subTest(number=number),transaction.atomic():
                self.include_factor=number!=0;self.factor_count=number
                self.transit_sources=source_day()['producer_sources']
                self.transit_sources['shipments']['rows']=[]
                self.bpr()
                with self.assertRaisesRegex(ValueError,'Exactly one accepted SuperDelayFactor'):self.produce()
                transaction.set_rollback(True)

    def test_negative_quantity_retains_native_diagnostic_and_transporter_row(self):
        self.positive(quantity=-3);self.bpr();_metadata,rows=self.produce()
        self.assertEqual(rows['InTransitData'],[self.expected_transit(positive=True,quantity=-3)])
        self.assertEqual(rows['TransitRejectedMaster'],[dict(SKUCode='SUPPLIED-Z9',WhCode='OWN-WH8',
            RejectionDate=datetime(2037,4,10),ReasonCode=-166,
            ReasonDescription='negative Qty in GoodsInTransit Data file/table')])
        self.assertEqual([row['InTransitQty'] for row in rows['GoodsInTransitTransporterMaster']],[-3])

    def test_factor_table_identity_conflicting_projections_and_sql_name_equality(self):
        from django.db import transaction
        from mta.runtime import production_daily
        for case in ('wrong_table','conflicting_projection','wrong_physical_image','case_spaces'):
            with self.subTest(case=case),transaction.atomic():
                self.include_factor=case!='wrong_table';self.wrong_table_factor=case=='wrong_table'
                self.conflicting_factor=case=='conflicting_projection'
                self.factor_parameter='superdelayfactor   ' if case=='case_spaces' else 'SuperDelayFactor'
                original=production_daily.input_table
                def table(fields,path,records):
                    if case=='wrong_physical_image' and path==(
                            'input/profile/delivery/btr_history/importer_vf_settings/values'):
                        return 'DBM/VFSettings'
                    return original(fields,path,records)
                if case=='wrong_physical_image':
                    # No DBM/VFSettings physical table is declared: the typed
                    # writer rejects that invented image before phase capture.
                    with self.assertRaisesRegex(ValueError,'Unknown typed image table'), \
                            patch.object(production_daily,'input_table',side_effect=table):self.bpr()
                    transaction.set_rollback(True)
                    continue
                self.bpr()
                if case=='case_spaces':self.assertEqual(self.produce()[0]['super_delay_factor'],'2')
                elif case=='wrong_table':
                    with self.assertRaisesRegex(ValueError,'Exactly one accepted'):self.produce()
                elif case=='conflicting_projection':
                    with self.assertRaisesRegex(ValueError,'factor declarations differ'):self.produce()
                transaction.set_rollback(True)

    def test_production_has_no_replay_write_or_counter_change_and_rejects_wrong_owner(self):
        from mta.runtime.models import RunPhaseAcceptance,DailySourceReceipt,DailyTransitRaw,DailyTransitRow
        from mta.runtime.scope_revisions import require_current
        from mta.presentation.context import PublicationUnavailable
        self.positive();self.bpr(counter=True)
        before=require_current(self.run)
        phases=list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest'))
        with patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('BPR replay')), \
                patch('mta.presentation.daily_transit.publish',side_effect=AssertionError('Full publication')):
            first=self.produce();self.assertEqual(self.produce(),first)
        self.assertEqual(require_current(self.run),before)
        self.assertEqual(list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest')),phases)
        for model in (DailySourceReceipt,DailyTransitRaw,DailyTransitRow):
            self.assertFalse(model.objects.filter(run=self.run).exists())
        for change in (dict(phase_id=self.pre_receipt.pk,expected_digest=self.pre_receipt.digest),
                dict(expected_digest='f'*64),dict(action_revision=1),dict(action_revision=True)):
            with self.subTest(change=change),self.assertRaises(PublicationUnavailable):self.produce(**change)
        self.run.refresh_from_db();self.assertEqual((self.run.status,self.run.output_digest),('RUNNING',''))
