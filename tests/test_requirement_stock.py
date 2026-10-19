"""Versioned raw stock feed retains SQL NULL/update semantics and typed capture."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('VF_SECRET_KEY','requirement-stock-contract-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()

from mta.application.requirement_stock import apply,validate
from mta.application.native_daily_contract import FEED_SCHEMA,STOCK_FEED_SCHEMA,STOCK_TABLE
from mta.application.production_csv_contract import feeds
from mta.application.production_csv import assemble
from mta.application.production_csv_files import load_binding
from mta.application.operational_inputs import encode_csv
from mta.runtime.production_daily import decode,input_table
from tests.test_production_csv_diagnostics import master_payload
from tools.create_daily_csv_example import create

DAY='2026-10-18'


def record(value=7):
    return dict(SKUCode='001',WhCode='W',StockForReqCalc=value,ReportDate=DAY)


class RequirementStockTests(unittest.TestCase):
    def test_only_v4_adds_one_feed_and_preserves_all_fourteen_existing_specs(self):
        old,new=feeds(FEED_SCHEMA),feeds(STOCK_FEED_SCHEMA)
        self.assertEqual(len(old),14)
        self.assertEqual({k:v for k,v in new.items() if k in old},old)
        self.assertEqual(set(new)-set(old),{'AdditionalDataStockForReqCalc.csv'})
        self.assertEqual(new['AdditionalDataStockForReqCalc.csv']['table'],STOCK_TABLE)

    def test_csv_decode_and_typed_capture_keep_null_duplicate_order_and_date(self):
        with tempfile.TemporaryDirectory() as td:
            root=create(Path(__file__).resolve().parents[1]/'examples/starter-data/vectorflow-starter-inputs-v1.zip',Path(td)/'csv')
            binding=load_binding(root/'binding-template.json')
            binding['intake_schema']=STOCK_FEED_SCHEMA
            batch=json.loads((root/DAY/'batch.json').read_bytes())
            payloads={name:(root/DAY/name).read_bytes() for name,status in batch['feeds'].items() if status=='PRESENT'}
            expected=[record(None),record(-7),record(-7)]
            extra={'MasterDataRaw.csv':master_payload()['raw_master'],
                'SOBDataRaw.csv':[],'MOQDataRaw1.csv':[],'MOQDataRaw2.csv':[],
                'AdditionalDataStockForReqCalc.csv':expected}
            for name,rows in extra.items():
                batch['feeds'][name]='PRESENT'
                payloads[name]=encode_csv(feeds(STOCK_FEED_SCHEMA)[name]['columns'],rows)
            raw,ordinals=assemble(batch,binding,payloads,first_day=True)
            value=decode(raw,hashlib.sha256(raw).hexdigest())
            self.assertEqual(value['day']['requirement_stock'],expected)
            self.assertEqual([r['record'] for r in ordinals['AdditionalDataStockForReqCalc.csv']],[1,2,3])
            fields={key:type(value).__name__ for key,value in record().items()}
            self.assertEqual(input_table(fields,'input/day/requirement_stock/values',expected),STOCK_TABLE)
            value['day']['requirement_stock'][0]['ReportDate']='2026-10-17'
            raw=json.dumps(value).encode()
            with self.assertRaisesRegex(ValueError,'date differs'):decode(raw,hashlib.sha256(raw).hexdigest())

    def test_null_is_current_stock_and_explicit_override_uses_existing_primitive(self):
        source={'stock_openings':[dict(sku_code='001',location_code='W',stock=12)]}
        rows=[record(None),record(12)]
        original=deepcopy(rows)
        result=apply(source,rows,DAY)
        self.assertEqual(result['stock_openings'][0]['stock'],12)
        self.assertIsNone(result['stock_openings'][0]['stock_for_requirement_override'])
        self.assertEqual(rows,original)
        apply(source,[record(-7),record(-7)],DAY)
        self.assertEqual(result['stock_openings'][0]['stock_for_requirement_override'],-7)
        from decimal import Decimal
        from mta.domain.r1_current_day import StockOpening,calculate_stock_balances
        row=result['stock_openings'][0]
        balances=calculate_stock_balances((StockOpening(row['sku_code'],row['location_code'],
            Decimal(row['stock']),Decimal(10),stock_for_requirement_override=Decimal(row['stock_for_requirement_override'])),),
            reservation_type=0,reservation_for_rationing_only=False)
        self.assertEqual(balances[0].stock_for_requirement,Decimal(-7))

    def test_ambiguous_update_unknown_stock_and_outside_master_are_not_repaired(self):
        for rows,stock in (([record(1),record(2)],12),([record(None),record(7)],12),([record(7)],None)):
            source={'stock_openings':[dict(sku_code='001',location_code='W',stock=stock)]}
            with self.subTest(rows=rows,stock=stock),self.assertRaises(ValueError):apply(source,rows,DAY)
        with self.assertRaisesRegex(ValueError,'outside consuming master'):apply({'stock_openings':[]},[record()],DAY)

    def test_sql_integer_roster_date_and_identity_guards(self):
        for field,bad in (('StockForReqCalc',True),('StockForReqCalc',2**31),('StockForReqCalc','7'),
                          ('SKUCode',''),('WhCode','nonascii\N{LATIN SMALL LETTER E WITH ACUTE}'),('ReportDate','2026-10-17')):
            row=record();row[field]=bad
            with self.subTest(field=field,bad=bad),self.assertRaises(ValueError):validate([row],DAY)

    def test_native_daily_chain_connects_raw_override_to_unchanged_calculation(self):
        from tests.test_h3_inactive_mode import inactive_frame,inactive_day
        from tests.test_production_daily_contract import encoded_day
        from tests.production_h3_fixture import CHILD
        from mta.runtime.production_daily import working_day
        from mta.temporal.chain import calculate_day
        from mta.planning.engine import calculate_current_day
        frame=inactive_frame();value=inactive_day('2037-04-10',root=True)
        # Complete v4 CSV decoding is proved above; exercise the same additional
        # population through the real connected daily producers here.
        day=working_day(decode(*encoded_day(value)),frame['profile'])
        day['requirement_stock']=[dict(SKUCode='SUPPLIED-Z9',WhCode=CHILD,
            StockForReqCalc=7,ReportDate='2037-04-10')]
        observed=[]
        def calculate(source,**owned):
            output=calculate_current_day(source,defer_pick=True,**owned)
            observed.extend(r for r in output['r1_stock_balance'] if
                (r['sku_code'],r['location_code'])==('SUPPLIED-Z9',CHILD))
            return output,'requirement-stock-component-only'
        calculate_day(deepcopy(frame['opening']['state']),'2037-04-09',day,
            frame['profile'],'requirement-stock-component-only',calculate,native_daily=True)
        self.assertEqual(len(observed),1)
        self.assertEqual(observed[0]['stock_for_requirement'],'7')

    def test_unknown_prior_stock_roundtrips_without_making_other_configuration_nullable(self):
        from tests.initialization_input_fixture import supplied_input,encoded
        from mta.mdm.initialization_contract import decode as initial_decode
        value=supplied_input();value['configuration']['calculation']['stock_openings'][0]['stock']=None
        raw,sha,args=encoded(value)
        frame=initial_decode(raw,sha,**args)[1]
        self.assertIsNone(frame['profile']['calculation']['stock_openings'][0]['stock'])
        value['configuration']['calculation']['stock_openings'][0]['utilized_stock']=None
        raw,sha,args=encoded(value)
        with self.assertRaisesRegex(ValueError,'NULL in required'):initial_decode(raw,sha,**args)


if __name__=='__main__':unittest.main()
