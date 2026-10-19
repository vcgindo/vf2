import unittest

from tools.large_data_benchmark import next_row


class SyntheticBenchmarkFactsTest(unittest.TestCase):
    def row(self, **changes):
        return dict(SKUCode='000337',WhCode='DP01',Stock=30,Consumption=9,
                    Receipts=5,GIT=None,PSO=0,ReportDate='2026-04-07',**changes)

    def test_conservation_without_changing_source(self):
        source=self.row()
        actual=next_row(source)
        self.assertEqual(actual['Stock'],26)
        self.assertEqual(actual['ReportDate'],'2026-04-08')
        self.assertEqual(source['Stock'],30)
        self.assertEqual(actual['SKUCode'],'000337')
        self.assertIsNone(actual['GIT'])

    def test_consumption_cannot_exceed_available_stock(self):
        source=self.row();source.update(Stock=3,Consumption=100,Receipts=2)
        actual=next_row(source)
        self.assertEqual((actual['Consumption'],actual['Stock']),(5,0))

    def test_unknown_stock_and_absent_flows_stay_null(self):
        source=self.row();source.update(Stock=None,Consumption=None,Receipts=None)
        actual=next_row(source)
        for name in ('Stock','Consumption','Receipts','GIT'):
            self.assertIsNone(actual[name])

    def test_missing_flow_cells_are_preserved_in_known_stock_balance(self):
        source=self.row();source.update(Consumption=None,Receipts=None)
        actual=next_row(source)
        self.assertEqual(actual['Stock'],30)
        self.assertIsNone(actual['Consumption'])
        self.assertIsNone(actual['Receipts'])


if __name__=='__main__':
    unittest.main()
