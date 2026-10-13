from copy import deepcopy
from datetime import date, datetime
import unittest

from tests.test_production_daily_contract import encoded_day
from tests.production_daily_fixture import day_input, initialized_input
from mta.application.production_source_inputs import SCHEMA, validate
from mta.runtime.production_daily import decode, working_day, SOURCE_SCHEMA


def source_day():
    value = day_input('2037-04-10', root=True)
    value['intake_schema'] = value['schema']
    value['schema'] = SOURCE_SCHEMA
    value['producer_sources'] = dict(schema=SCHEMA,
        report_policy=dict(bor_history_horizon=90,rrr_history_horizon=90),
        report_opening=dict(BOR_OrderAllocationHistory=[],RRR_OrderAllocationHistory=[]),
        shipments=dict(schema='daily-transit-raw-v1', business_date='2037-04-10',
            provenance={'source':'declared external shipment ledger'}, rows=[dict(
                SKUCode='SUPPLIED-Z9', ToLocationCode='OWN-PARENT', FromLocationCode='SUPPLIER',
                CurrentLocationCode=None, LRCode='L-1',OrderNo='O-1',CreationDate='2037-04-08',
                GateOutDate='2037-04-09',InTransitQty=7,TransporterCode='T-1',Remark=None,
                ReportDate='2037-04-10')]),
        transporters=dict(schema='daily-transporter-raw-v1',business_date='2037-04-10',
            provenance={'source':'operator directory'}, rows=[dict(TransporterCode='T-1',
                TransporterName='Carrier',TransporterContact=None)]))
    value['consumer_opening']['remarks']['bor'] = [dict(SKUCode='SUPPLIED-Z9',WhCode='OWN-PARENT',
        SupplierCode='SUPPLIER',Remark=None,Username=None,RemarkDate='2037-04-09T09:10:11+00:00')]*2
    return value


class ProductionSourceInputsTests(unittest.TestCase):
    def test_source_only_bor_version_requires_exact_amendment_and_keeps_external_facts(self):
        from mta.application import production_output_policy as policy
        value = source_day()
        original = deepcopy(value)
        sources = value['producer_sources']
        sources['schema'] = policy.SOURCE_SCHEMA
        sources['report_policy']['output_contract'] = policy.contract()
        decoded = decode(*encoded_day(value))
        working = working_day(decoded, initialized_input()['configuration'])
        self.assertEqual(working['production_report_schema'], policy.SOURCE_SCHEMA)
        self.assertEqual(working['production_report_policy']['output_contract'], policy.contract())
        for name in ('shipments', 'transporters', 'report_opening'):
            self.assertEqual(decoded['producer_sources'][name], original['producer_sources'][name])
        self.assertEqual(decoded['consumer_opening'], original['consumer_opening'])
        for change in (
            lambda s: s['report_policy'].pop('output_contract'),
            lambda s: s['report_policy']['output_contract'].update(normal_bor='legacy'),
            lambda s: s.update(schema=SCHEMA),
            lambda s: s.update(schema='fresh-production-source-inputs-v3'),
            lambda s: s.update(configuration={}),
            lambda s: s['report_opening'].update(GuidedExcessHistory=[]),
            lambda s: s['report_opening']['BOR_OrderAllocationHistory'].append({'Norm': 1}),
        ):
            invalid = deepcopy(value)
            change(invalid['producer_sources'])
            with self.subTest(change=change), self.assertRaises(ValueError):
                decode(*encoded_day(invalid))

    def test_versioned_facts_preserve_nulls_duplicates_and_supplied_dates(self):
        value = source_day()
        raw, sha = encoded_day(value)
        decoded = decode(raw,sha)
        self.assertEqual(decoded,value)
        day = working_day(decoded,initialized_input()['configuration'])
        self.assertEqual(day['shipment_input'],value['producer_sources']['shipments'])
        self.assertEqual(day['transporter_input'],value['producer_sources']['transporters'])
        self.assertNotIn('producer_sources',value['day'])

    def test_missing_stale_calculated_and_invalid_facts_deny(self):
        for change in (
            lambda v:v['producer_sources'].pop('transporters'),
            lambda v:v['producer_sources']['shipments'].update(business_date='2037-04-09'),
            lambda v:v['producer_sources']['shipments']['rows'][0].update(ETA='2037-04-12'),
            lambda v:v['producer_sources']['shipments']['rows'][0].update(InTransitQty=True),
            lambda v:v['consumer_opening']['remarks']['bor'][0].update(RemarkDate='2037-04-11T00:00:00Z'),
            lambda v:v.update(intake_schema='unknown')):
            value=source_day();change(value)
            with self.subTest(change=change),self.assertRaises(ValueError):
                decode(*encoded_day(value))

    def test_nonempty_consumer_capture_has_explicit_typed_input_and_timezone_roundtrip(self):
        from types import SimpleNamespace
        from mta.runtime.production_daily import input_table
        from mta.runtime.input_storage import save_input,read_input
        from mta.runtime.relational_state import db_value,wire_value
        from mta.serialization import digest
        from tests.production_h4_fixture import supplied_source_day
        opening=supplied_source_day('2037-04-10',root=True)['consumer_opening']
        raw=dict(profile={'delivery':{'site_code':'SUPPLIED'}},request_inputs=dict(rows=opening['requests']),remark_inputs={
            name:dict(rows=[dict(source_ordinal=i,**row) for i,row in enumerate(opening['remarks'][family])])
            for family,name in (('bpr','BPRReport_RemarkDetails'),('bor','BORReport_RemarkDetails'),('boroa','BORReport_OARemarkDetails'))})
        run=SimpleNamespace(input_digest=digest(raw));images={};tables={}
        def write(run,path,binding,rows,*,table):
            images[path]=list(rows);tables[path]=table
            return dict(image=path,table=table)
        run.input_payload=save_input(run,raw,image_writer=write,table_selector=input_table)
        run.input_manifest_digest=digest(run.input_payload)
        self.assertEqual(read_input(run,image_reader=lambda run,item:images[item['image']]),raw)
        self.assertEqual(tables['input/request_inputs/rows/values'],'input/production_request')
        for family in ('bpr','bor','boroa'):
            self.assertIn('input/production_remark_'+family,tables.values())
        stamp='2037-04-09T09:10:11+00:00'
        self.assertEqual(wire_value(db_value(stamp,'datetimetz'),'str'),stamp)

    def test_transit_uses_actual_directory_and_preserves_ledger_quantity(self):
        from mta.application.daily_transit import validate_goods_in_transit, transporter_master
        value=source_day()['producer_sources']
        raw=deepcopy(value['shipments']['rows'])
        for row in raw:
            for field in ('CreationDate','GateOutDate','ReportDate'):
                row[field]=date.fromisoformat(row[field])
        standards=[dict(SKUCode='SUPPLIED-Z9',WhCode='OWN-PARENT',SLT=3,Price=5)]
        transit=validate_goods_in_transit(raw,standards,date(2037,4,10),datetime(2037,4,10))['rows']
        self.assertEqual(transit[0]['InTransitQty'],7)
        self.assertEqual((transit[0]['Ageing'],transit[0]['ETA']),(2,date(2037,4,11)))
        reports=[dict(SKUCode='SUPPLIED-Z9',WhCode='OWN-PARENT',ParentWhCode='SUPPLIER',GIT=7,
            PhysicalInventoryPen=50,PhysicalInventoryColor='Red',DispatchColor='Yellow')]
        produced=transporter_master(transit,value['transporters']['rows'],reports,standards,2)
        self.assertTrue(produced)
        self.assertTrue(all(row['TransporterName']=='Carrier' and row['TransporterContact'] is None for row in produced))
