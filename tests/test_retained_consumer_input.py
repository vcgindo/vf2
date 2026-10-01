"""Streaming-reader protocol tests, not synthetic business acceptance cases."""
import gzip
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


@unittest.skipUnless(importlib.util.find_spec('ijson'), 'Oracle-only streaming dependency not installed')
class RetainedConsumerReaderTest(unittest.TestCase):
    def test_only_declared_terminal_tables_are_materialized(self):
        from parity.retained_consumer_input import selected_capture_tables, STATE_FIELDS
        closing = {'typed':[{'integer':7,'boolean':True,'null':None,'decimal_wire':'7.00'}]}
        late = {name:[dict(marker=name)] for name in STATE_FIELDS}
        record = dict(closing=closing,native_inputs={'vf_ReqCalculation':[{'SKUCode':'337','Norm':7}],
            'BPRMaster':[{'SKUCode':'337','ParentWhCode':'LDC001'}]},unrelated=[{'ignored':i} for i in range(10000)],
            output=dict(CalculationCheckpoints={'bifurcation':[{'band':'0'}],'routes':[{'order_id':'unit'}]},
                        BPRStages=[dict(stage='earlier',state={'vf_RationedReqReport':[{'wrong':True}]}),
                                   dict(stage='UpdateBPR.sql',state={**late,'IntermediateTables':{'unused':[1,2,3]}})]))
        with TemporaryDirectory() as directory:
            path = Path(directory)/'capture.json.gz'
            with gzip.open(path,'wt') as stream:
                json.dump(record,stream,sort_keys=True)
            self.assertEqual(selected_capture_tables(path),dict(closing=closing,bands=[{'band':'0'}],late=late))
            self.assertEqual(selected_capture_tables(path,include_routes=True),
                dict(closing=closing,bands=[{'band':'0'}],late=late,routes=[{'order_id':'unit'}]))
            self.assertEqual(selected_capture_tables(path,include_requirements=True),
                dict(closing=closing,bands=[{'band':'0'}],late=late,requirements=[{'SKUCode':'337','Norm':7}]))
            self.assertEqual(selected_capture_tables(path,include_master=True),
                dict(closing=closing,bands=[{'band':'0'}],late=late,bpr_master=[{'SKUCode':'337','ParentWhCode':'LDC001'}]))

    def test_incomplete_source_is_not_success(self):
        from parity.retained_consumer_input import selected_capture_tables
        with TemporaryDirectory() as directory:
            path = Path(directory)/'capture.json.gz'
            with gzip.open(path,'wt') as stream:
                json.dump({'closing':{},'output':{}},stream)
            with self.assertRaisesRegex(ValueError,'roster incomplete'):
                selected_capture_tables(path)


if __name__ == '__main__':
    unittest.main()
