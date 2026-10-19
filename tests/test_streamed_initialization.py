"""Full CSV/typed reconstruction with immutable histories; no engine acceptance claim."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','streamed-opening-focused-only')
import django
django.setup()
from mta.application.initialization_csv import create,read_streamed,MANIFEST
from mta.application.streamed_input import StreamedInput
from mta.mdm.initialization_contract import decode
from mta.runtime.input_storage import save_input,read_input
from mta.runtime.relational_state import describe_rows
from mta.row_sequences import RecordRows
from mta.serialization import canonical_parts,digest
from tests.initialization_input_fixture import supplied_input,encoded


class StreamedOpeningTests(unittest.TestCase):
    def test_large_csv_full_native_decode_and_typed_reconstruction(self):
        value=supplied_input()
        row=dict(SKUCode='00337',WHCode='L',Stock=None,Consumption=1,GIT=2,
            Receipts=3,PSO=4,BlueZone=5,ReportDate='2037-04-08')
        value['opening']['state']['bpr']['DailyConsumption']=[dict(row) for _ in range(10001)]
        value['opening']['state']['bpr']['DailyConsumption'][-1]['Consumption']=2
        raw,sha,args=encoded(value)
        expected=decode(raw,sha,**args)[1]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'opening'
            manifest,stream=create(value,root,streamed=True)
            pin=hashlib.sha256((root/MANIFEST).read_bytes()).hexdigest()
            actual=read_streamed(root,pin,**args)
            frame=decode(actual,actual.sha256,**args)[1]
            history=frame['opening']['state']['bpr']['DailyConsumption']
            self.assertIsInstance(history,RecordRows)
            self.assertEqual(digest(frame),digest(expected))
            self.assertEqual(history[-1]['Consumption'],2)
            filename=next(name for name,spec in manifest['populations'].items()
                if spec['path']=='input/opening/state/bpr/DailyConsumption')
            (root/filename).unlink()
            # No post-validation dependency on mutable external CSV files.
            self.assertEqual(digest(decode(actual,actual.sha256,**args)[1]),digest(expected))
            # All normal gates still reject wrong input identities.
            with self.assertRaisesRegex(ValueError,'bytes differ'):
                decode(actual,'0'*64,**args)
            images={}
            def writer(owner,path,binding,rows,*,table):
                columns={name.casefold():(name,kind) for name,kind in __import__(
                    'mta.runtime.opening_storage',fromlist=['STORAGE_TABLES']).STORAGE_TABLES[table]}
                metadata,fields,native=describe_rows(rows,columns,path)
                metadata['table']=table
                images[path]=[dict(row) for row in rows]
                return metadata
            from mta.mdm.initialization_rows import select
            owner=SimpleNamespace(input_digest=digest(frame))
            owner.input_payload=save_input(owner,frame,image_writer=writer,table_selector=select)
            owner.input_manifest_digest=digest(owner.input_payload)
            reconstructed=read_input(owner,image_reader=lambda owner,meta: RecordRows(
                len(images[meta['image']]),lambda:iter(images[meta['image']])))
            self.assertIsInstance(reconstructed['opening']['state']['bpr']['DailyConsumption'],RecordRows)
            self.assertEqual(digest(reconstructed),digest(expected))
            self.assertEqual(list(reconstructed['opening']['state']['bpr']['DailyConsumption']),
                expected['opening']['state']['bpr']['DailyConsumption'])

    def test_large_pg_load_certifies_tail_before_returning_rows(self):
        from contextlib import contextmanager
        from itertools import islice
        from mta.runtime import relational_state,opening_storage
        expected=[{'value':'00337'},{'value':None}]*5001
        class Cursor:
            def __init__(self):self.records=iter(enumerate(row['value'] for row in expected))
            def execute(self,*args):pass
            def fetchmany(self,size):return list(islice(self.records,size))
        @contextmanager
        def chunked():yield Cursor()
        connection=SimpleNamespace(chunked_cursor=chunked)
        metadata=dict(image='input/test/values',table='input/string_values',
            count=len(expected),digest=digest(expected),fields=[['value','value','str']])
        for module in (relational_state,opening_storage):
            with self.subTest(module=module.__name__),patch.object(module,'connection',connection):
                rows=module.load_image(SimpleNamespace(pk='owned'),metadata)
                self.assertIsInstance(rows,RecordRows)
                self.assertEqual(rows[-1],expected[-1])
                with tempfile.TemporaryDirectory() as work,patch.dict(os.environ,{'VF_WORK_ROOT':work}):
                    cached=module.load_image(SimpleNamespace(pk='owned'),metadata)
                    self.assertTrue(hasattr(cached,'_data'))
                    self.assertEqual(list(cached),expected)
                with self.assertRaisesRegex(ValueError,'drift'):
                    module.load_image(SimpleNamespace(pk='owned'),dict(metadata,digest='0'*64))
                with self.assertRaisesRegex(ValueError,'drift'):
                    module.load_image(SimpleNamespace(pk='owned'),dict(metadata,count=len(expected)+1))

    def test_historical_btr_preflight_matches_approved_decoder_admission(self):
        from tests.test_initialization_history import historical
        from mta.runtime.production_preflight import initialization
        value=supplied_input()
        for table in ('BPR','RationingHistory'):
            value['opening']['state']['btr'][table]=[historical(table)]*2
        raw,sha,args=encoded(value)
        report=initialization(raw,sha,**args)
        self.assertFalse([q for q in report['issues'] if q['code']=='CALCULATED_OPENING_FORBIDDEN'],report)
        value['opening']['state']['btr']['BPR'][0]['ReportDate']='2037-04-10'
        raw,sha,args=encoded(value)
        report=initialization(raw,sha,**args)
        self.assertTrue(any('exceeds' in q['message'] for q in report['issues']),report)

    def test_manifest_population_count_is_not_trusted(self):
        rows=RecordRows(2,lambda:iter([{'value':1}]))
        with self.assertRaisesRegex(ValueError,'population drift'):list(rows)
        rows=RecordRows.from_rows([{'x':None},{'x':1},{'x':1}])
        self.assertEqual(b''.join(canonical_parts(rows)),b'[{"x":null},{"x":1},{"x":1}]')


if __name__=='__main__':unittest.main()
