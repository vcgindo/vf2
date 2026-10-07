from copy import deepcopy
import json
from pathlib import Path
import unittest
from tools.generate_temporal_scenario import physical_ledger, ROOT
from parity.temporal_ledger import validate
from mta.serialization import digest


class SyntheticLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = json.loads((ROOT/'baseline/synthetic-temporal-business-v1.json').read_text())
        masters = [dict(SKUCode='a',WhCode='root',ParentWhCode='external',RLT=4,Norm=80,PackSize=1),
                   dict(SKUCode='a',WhCode='child',ParentWhCode='root',RLT=7,Norm=100,PackSize=10)]
        ledger, facts, events = physical_ledger(masters,spec)
        history = [row for i,rows in facts.items() if i<0 for row in rows]
        cls.payload = {'case':dict(external_fact_ledger=ledger,static_day={'raw_master':masters},
            opening_date='2026-06-05',opening={'bpr':{'DailyConsumption':history},'dbm':{'DailyConsumption':history}},
            days=[dict(business_date=rows[0]['ReportDate'],raw_daily=rows) for i,rows in facts.items() if i>=0])}
        cls.events = events

    def test_shared_horizon_and_parent_shipments_are_conserved(self):
        self.assertEqual(validate(self.payload)['computed_days'],21)
        ledger = self.payload['case']['external_fact_ledger']
        shipments = ledger['shipments']
        for event in self.events:
            expected = sum(row['quantity'] for row in shipments if row['WhCode']=='child'
                           and row['dispatch_date']==event['ReportDate']) if event['WhCode']=='root' else 0
            self.assertEqual(event['parent_outbound'],expected)
        self.assertTrue(all(row['git_duration_days']==4 for row in shipments if row['WhCode']=='child'))

    def test_missing_duplicate_or_individual_short_horizon_is_rejected(self):
        for mutation in ('missing','duplicate','per-pair','ninety'):
            payload=deepcopy(self.payload);days=payload['case']['days']
            if mutation=='missing':days.pop()
            elif mutation=='duplicate':days[1]=deepcopy(days[0])
            elif mutation=='per-pair':days[12]['raw_daily']=[days[12]['raw_daily'][1]]
            else:days.extend(deepcopy(days[0]) for _ in range(69))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):validate(payload)

    def test_rehashed_wrong_receipt_or_balance_is_still_rejected(self):
        for kind in ('receipt','balance','catalogue'):
            payload=deepcopy(self.payload);case=payload['case'];ledger=case['external_fact_ledger']
            if kind=='receipt':
                ledger['shipments'][0]['receipt_date']='2026-06-26'
                ledger['shipments_sha256']=digest(ledger['shipments'])
            elif kind=='balance':
                ledger['daily_reconciliation'][0]['closing_stock']+=1
                ledger['reconciliation_sha256']=digest(ledger['daily_reconciliation'])
            else:case['static_day']['raw_master'][0]['SKUCode']='unknown'
            with self.subTest(kind=kind), self.assertRaises(ValueError):validate(payload)
