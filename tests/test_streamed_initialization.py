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
    def test_large_current_open_orders_retain_order_validator_list_contract(self):
        from mta.mdm.initialization import read_initialized_input
        from mta.mdm.initialization_rows import select
        from mta.runtime import opening_storage
        from mta.application.r1_order_input import validate_order_input
        value=supplied_input()
        expected=[dict(OrderKey=i+1,CustomerOrderId='ORDER-'+str(i),PartId=1,IsSpike=0,IsElephant=0,
            OriginalQty=1,Qty=1,SKUCode='SUPPLIED-Z9',WhCode='OWN-WH8',CustomerExpectedDate=None,
            FirstServicingWhCode=None,DueDate=None,IntroDate='2037-04-08') for i in range(10001)]
        value['opening']['state']['orders']['SpikeOrderData']=expected
        value['opening']['state']['orders']['OrderIdentity']=[dict(Seed=1,Increment=1,LastValue=10001)]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'opening'
            manifest,native=create(value,root,streamed=True)
            args=dict(expected_configuration=manifest['configuration_digest'],expected_recipe=manifest['recipe_digest'])
            frame=decode(native,native.sha256,**args)[1]
            images={}
            def writer(owner,path,binding,rows,*,table):
                columns={name.casefold():(name,kind) for name,kind in opening_storage.STORAGE_TABLES[table]}
                metadata,_,_=describe_rows(rows,columns,path);metadata['table']=table
                images[path]=[dict(row) for row in rows]
                return metadata
            owner=SimpleNamespace(input_digest=digest(frame))
            owner.input_payload=save_input(owner,frame,image_writer=writer,table_selector=select)
            owner.input_manifest_digest=digest(owner.input_payload)
            with patch.object(opening_storage,'load_image',lambda owner,meta:RecordRows(
                    len(images[meta['image']]),lambda:iter(images[meta['image']]))):
                actual=read_initialized_input(owner)
            orders=actual['opening']['state']['orders']['SpikeOrderData']
            self.assertIs(type(orders),list)
            self.assertEqual(orders,expected)
            self.assertEqual(digest(actual),digest(frame))
            validate_order_input(dict(opening_date='2037-04-08',opening_identity='supplied',feed_status='PRESENT',
                feed_rows=[],opening_orders=orders,closure_history=[],identity_last_value=10001),'2037-04-09')

    def test_all_large_current_owners_survive_csv_and_typed_roundtrip(self):
        from copy import deepcopy
        from mta.mdm.initialization_contract import MASTER_TABLES, CURRENT_MASTER_PATHS
        from mta.mdm.master_owners import owner_batches
        from mta.mdm.initialization import read_initialized_input
        from mta.mdm.initialization_rows import select
        from mta.runtime import opening_storage
        value=supplied_input()
        for section,tables in MASTER_TABLES.items():
            for table in tables:
                rows=value['masters'][section][table]
                value['masters'][section][table]=[deepcopy(rows[i%len(rows)]) for i in range(10001)]
        rows=value['opening']['state']['consumer_context']['NMSAllItems']
        value['opening']['state']['consumer_context']['NMSAllItems']=[deepcopy(rows[i%len(rows)]) for i in range(10001)]
        history=dict(SKUCode='00337',WHCode='L',Stock=None,Consumption=1,GIT=2,
            Receipts=3,PSO=4,BlueZone=5,ReportDate='2037-04-08')
        value['opening']['state']['bpr']['DailyConsumption']=[dict(history) for _ in range(10001)]
        value['opening']['state']['bpr']['DailyConsumption'][-1]['Consumption']=2
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'opening'
            manifest,native=create(value,root,streamed=True)
            args=dict(expected_configuration=manifest['configuration_digest'],expected_recipe=manifest['recipe_digest'])
            stream=read_streamed(root,hashlib.sha256((root/MANIFEST).read_bytes()).hexdigest(),**args)
            frame=decode(stream,native.sha256,**args)[1]
            expected_batches=owner_batches(frame['opening']['state'],strict=True)
            actual_paths={'input'+path for _,_,_,_,path in expected_batches if ':' not in path}
            self.assertEqual(actual_paths,CURRENT_MASTER_PATHS)
            images={}
            def writer(owner,path,binding,rows,*,table):
                columns={name.casefold():(name,kind) for name,kind in opening_storage.STORAGE_TABLES[table]}
                metadata,_,_=describe_rows(rows,columns,path)
                metadata['table']=table
                images[path]=[dict(row) for row in rows]
                return metadata
            owner=SimpleNamespace(input_digest=digest(frame))
            owner.input_payload=save_input(owner,frame,image_writer=writer,table_selector=select)
            owner.input_manifest_digest=digest(owner.input_payload)
            def reader(owner,metadata):
                return RecordRows(len(images[metadata['image']]),lambda:iter(images[metadata['image']]))
            with patch.object(opening_storage,'load_image',reader):
                actual=read_initialized_input(owner)
            self.assertEqual(digest(actual),digest(frame))
            actual_batches=owner_batches(actual['opening']['state'],strict=True)
            self.assertEqual(actual_batches,expected_batches)  # All fields/NULLs/duplicate ordinals.
            for path in CURRENT_MASTER_PATHS:
                target=actual
                for part in path.split('/')[1:]:target=target[part]
                self.assertIs(type(target),list,path)
                self.assertEqual(len(target),10001,path)
            self.assertIsInstance(actual['opening']['state']['bpr']['DailyConsumption'],RecordRows)
            self.assertEqual(actual['opening']['state']['bpr']['DailyConsumption'][-1]['Consumption'],2)
            # Generic daily readers retain their original streaming default.
            generic=read_input(owner,image_reader=reader)
            self.assertIsInstance(generic['opening']['state']['importer']['SkuLocAttributeData'],RecordRows)

    def test_current_configuration_and_exclusions_preserve_large_list_contract(self):
        from mta.mdm.initialization import read_initialized_input
        from mta.runtime import opening_storage
        from mta.mdm.initialization_rows import select
        value=supplied_input();raw,sha,args=encoded(value)
        frame=decode(raw,sha,**args)[1]
        row=frame['profile']['calculation']['stock_openings'][0]
        frame['profile']['calculation']['stock_openings']=[dict(row) for _ in range(10001)]
        frame['pair_exclusions']=[dict(SKUCode='00337',WhCode=None) for _ in range(10001)]
        images={}
        def writer(owner,path,binding,rows,*,table):
            columns={name.casefold():(name,kind) for name,kind in opening_storage.STORAGE_TABLES[table]}
            metadata,_,_=describe_rows(rows,columns,path);metadata['table']=table
            images[path]=[dict(row) for row in rows]
            return metadata
        owner=SimpleNamespace(input_digest=digest(frame))
        owner.input_payload=save_input(owner,frame,image_writer=writer,table_selector=select)
        owner.input_manifest_digest=digest(owner.input_payload)
        with patch.object(opening_storage,'load_image',lambda owner,meta:RecordRows(
                len(images[meta['image']]),lambda:iter(images[meta['image']]))):
            actual=read_initialized_input(owner)
        self.assertIs(type(actual['profile']['calculation']['stock_openings']),list)
        self.assertIs(type(actual['pair_exclusions']),list)
        self.assertEqual(digest(actual),digest(frame))

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
