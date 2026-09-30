"""Validator unit stubs, not synthetic acceptance artifacts."""
from copy import deepcopy
from datetime import date, timedelta
import unittest

from mta.serialization import digest
from parity.temporal_ledger import validate


class LedgerValidationTest(unittest.TestCase):
    def payload(self):
        start = date(2026, 6, 5)
        shipments, checks, facts = [], [], []
        for i in range(4):
            day = start + timedelta(days=i)
            shipments.append(dict(SKUCode='337', WhCode='AG515802', shipment_id=str(i),
                                  quantity=1, dispatch_date=(day-timedelta(days=1)).isoformat(),
                                  receipt_date=day.isoformat(), git_duration_days=1))
            checks.append(dict(SKUCode='337', WhCode='AG515802', ReportDate=day.isoformat(),
                               opening_stock=2, closing_stock=2, receipts=1, consumption=1,
                               opening_git=1, closing_git=int(i<3), dispatches=int(i<3), git_receipts=1))
            facts.append(dict(SKUCode='337', WhCode='AG515802', ReportDate=day.isoformat(),
                              Stock=2, GIT=int(i<3), Receipts=1, Consumption=1))
        return {'case': dict(opening_date=start.isoformat(),
            static_day={'raw_master':[dict(SKUCode='337', WhCode='AG515802', RLT=1)]},
            opening={section:{'DailyConsumption':[deepcopy(facts[0])]} for section in ('bpr','dbm')},
            days=[dict(business_date=row['ReportDate'],raw_daily=[row]) for row in facts[1:]],
            external_fact_ledger=dict(shipments=shipments,daily_reconciliation=checks,
                shipments_sha256=digest(shipments),reconciliation_sha256=digest(checks),
                counts=dict(identities=1,fact_rows=4,shipments=4),
                git_duration_formula='max(1, (RLT + 1) // 2)'))}

    def test_balanced_facts_pass(self):
        self.assertEqual(validate(self.payload())['status'],'PASS')

    def test_rehashed_unbalanced_ledger_fails(self):
        value=self.payload(); ledger=value['case']['external_fact_ledger']
        ledger['daily_reconciliation'][2]['consumption']=0
        ledger['reconciliation_sha256']=digest(ledger['daily_reconciliation'])
        with self.assertRaisesRegex(ValueError,'balance does not reconcile'):validate(value)

    def test_engine_fact_cannot_differ_from_valid_ledger(self):
        value=self.payload(); value['case']['days'][0]['raw_daily'][0]['Stock']=3
        with self.assertRaisesRegex(ValueError,'differs from ledger'):validate(value)

    def test_rehashed_wrong_transit_fails(self):
        value=self.payload(); ledger=value['case']['external_fact_ledger']
        ledger['shipments'][0]['dispatch_date']='2026-06-03'
        ledger['shipments_sha256']=digest(ledger['shipments'])
        with self.assertRaisesRegex(ValueError,'half-RLT'):validate(value)
