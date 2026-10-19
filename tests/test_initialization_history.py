"""Historical BTR carry admission does not admit new-day output seeds."""
import copy
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('VF_SECRET_KEY','offline-history-contract-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()

from mta.mdm.initialization_contract import decode
from mta.mdm.initialization_rows import schema
from mta.application.initialization_csv import create
from tests.initialization_input_fixture import supplied_input,encoded


def historical(table):
    _,fields=schema('input/opening/state/btr/'+table+'/values',[])
    return {name:('2037-04-08' if kind=='date' else '2037-04-08T00:00:00' if kind=='datetime'
        else False if kind=='bit' else 0 if kind in ('int','bigint') else 0.0 if kind in ('float','real')
        else '0' if kind in ('decimal','numeric') else 'HISTORY') for name,kind in fields.items()}


class HistoricalOpeningTest(unittest.TestCase):
    def test_complete_dated_history_duplicates_and_csv_roundtrip(self):
        for table in ('BPR','RationingHistory'):
            with self.subTest(table=table):
                value=supplied_input();row=historical(table)
                value['opening']['state']['btr'][table]=[row,copy.deepcopy(row)]
                raw,sha,args=encoded(value);frame=decode(raw,sha,**args)[1]
                self.assertEqual(frame['opening']['state']['btr'][table],[row,row])
                with tempfile.TemporaryDirectory() as td:
                    _,assembled=create(value,Path(td)/'opening')
                    self.assertEqual(decode(assembled,__import__('hashlib').sha256(assembled).hexdigest(),**args)[1],frame)

    def test_missing_future_and_malformed_dates_are_denied(self):
        for table in ('BPR','RationingHistory'):
            for bad in (None,'2037-04-10','invalid'):
                value=supplied_input();row=historical(table);row['ReportDate']=bad
                value['opening']['state']['btr'][table]=[row]
                raw,sha,args=encoded(value)
                with self.subTest(table=table,date=bad),self.assertRaises(ValueError):decode(raw,sha,**args)

    def test_calculated_snapshot_is_still_forbidden(self):
        value=supplied_input();value['opening']['state']['btr']['BTRSnapshotForUI']=[historical('BTRSnapshotForUI')]
        raw,sha,args=encoded(value)
        with self.assertRaisesRegex(ValueError,'calculated output'):decode(raw,sha,**args)


if __name__=='__main__':unittest.main()
