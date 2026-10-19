"""External CSV facts retain the native contract, values, NULLs and occurrence order."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import os
from unittest.mock import patch
os.environ.setdefault('VF_SECRET_KEY', 'unit-contract-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.application.production_csv import parse_csv, assemble, CsvIntakeError
from mta.runtime.production_daily import decode
from tools.create_daily_csv_example import create
from mta.application.production_csv_files import load_binding, regular, snapshot


class ProductionCsvTests(unittest.TestCase):
    def test_both_intake_modes_have_complete_exact_decimal_metadata(self):
        from mta.application.production_csv_contract import feeds
        from mta.application.native_daily_contract import SCHEMA, FEED_SCHEMA
        for mode in (SCHEMA,FEED_SCHEMA):
            for name,spec in feeds(mode).items():
                for column in spec['columns']:
                    if column['type'] in ('decimal','numeric'):
                        self.assertRegex(column['parameters'], r'^\d+,\s*\d+$', (name,column))

    def test_v2_csv_maps_external_master_supplier_rows_without_engine_execution(self):
        from mta.application.production_csv_contract import feeds
        from mta.application.native_daily_contract import FEED_SCHEMA
        from mta.application.operational_inputs import encode_csv
        from tests.test_production_csv_diagnostics import master_payload
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root=create(Path(__file__).resolve().parents[1]/'examples/starter-data/vectorflow-starter-inputs-v1.zip',Path(directory)/'csv')
            binding=load_binding(root/'binding-template.json');binding['intake_schema']=FEED_SCHEMA
            batch=json.loads((root/'2026-10-18/batch.json').read_bytes())
            payloads={name:(root/'2026-10-18'/name).read_bytes() for name,state in batch['feeds'].items() if state=='PRESENT'}
            expected={'MasterDataRaw.csv':master_payload()['raw_master'],
                'SOBDataRaw.csv':[dict(SKUCode='CSV-1',WHCode='CSV-W',SupplierCode='CSV-P',SupplierDescription='Parent',SOB=37.125)],
                'MOQDataRaw1.csv':[], 'MOQDataRaw2.csv':[]}
            for name,rows in expected.items():
                batch['feeds'][name]='PRESENT';payloads[name]=encode_csv(feeds(FEED_SCHEMA)[name]['columns'],rows)
            raw,_=assemble(batch,binding,payloads,first_day=True)
            value=decode(raw,hashlib.sha256(raw).hexdigest())
            self.assertEqual(value['day']['raw_master'],expected['MasterDataRaw.csv'])
            self.assertEqual(value['day']['supplier_feeds']['SOBDataRaw'],expected['SOBDataRaw.csv'])
    def test_normal_csv_syntax_and_exact_text_null_duplicates(self):
        columns = [dict(name='SKU', type='nvarchar', parameters='50', nullable=True),
                   dict(name='Qty', type='int', nullable=True)]
        rows, positions = parse_csv(b'\xef\xbb\xbfSKU,Qty\n00337,1\n00337,1\n"a,b",\\N\n,0\n', columns, 'x.csv')
        self.assertEqual(rows, [dict(SKU='00337', Qty=1), dict(SKU='00337', Qty=1),
                               dict(SKU='a,b', Qty=None), dict(SKU='', Qty=0)])
        self.assertEqual([v['record'] for v in positions], [1, 2, 3, 4])

    def test_invalid_numeric_is_not_zero_or_null(self):
        with self.assertRaises(CsvIntakeError) as failure:
            parse_csv(b'Qty\n\n1.5\n', [dict(name='Qty', type='int', nullable=True)], 'x.csv')
        self.assertEqual(failure.exception.issues[-1]['column'], 'Qty')

    def test_exact_decimal_multiline_text_and_nullable_width(self):
        columns = [dict(name='Text',type='nvarchar',parameters='12',nullable=False),
                   dict(name='Value',type='decimal',parameters='8,3',nullable=True)]
        rows, lines = parse_csv(b'Text,Value\r\n"a\nb",12.340\r\n', columns, 'x.csv')
        self.assertEqual(rows, [dict(Text='a\nb', Value='12.340')])
        self.assertEqual(lines, [dict(record=1,first_line=2,last_line=3)])
        for raw in (b'Text,Value\n\\N,1\n', b'Text,Value\na,1.0001\n',
                    b'Text,Value\na,NaN\n', b'Value,Text\n1,a\n'):
            with self.subTest(raw=raw), self.assertRaises(CsvIntakeError):
                parse_csv(raw, columns, 'x.csv')

    def test_path_escape_and_snapshot_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); root=base/'incoming'; root.mkdir()
            (base/'outside').write_text('protected')
            with self.assertRaisesRegex(ValueError,'outside'):
                regular(root/'..'/'outside',root)
            batch=root/'day';batch.mkdir()
            (batch/'READY').write_bytes(b'')
            (batch/'batch.json').write_text(json.dumps(dict(schema='vectorflow-daily-csv-v1',feeds={'x.csv':'PRESENT'})))
            original=b'x\r\n"a,b"\r\n';(batch/'x.csv').write_bytes(original)
            _, receipt=snapshot(batch,base/'archive',root)
            self.assertEqual((base/'archive'/'x.csv').read_bytes(),original)
            self.assertEqual(receipt['files']['x.csv']['bytes'],len(original))
            with self.assertRaises(FileExistsError):snapshot(batch,base/'archive',root)
            (batch/'unlisted.csv').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'roster'):snapshot(batch,base/'archive2',root)

    def test_missing_ready_and_changed_during_capture_never_complete_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'incoming';source.mkdir()
            (source/'batch.json').write_text(json.dumps(dict(schema='vectorflow-daily-csv-v1',feeds={'x.csv':'PRESENT'})))
            path=source/'x.csv';path.write_bytes(b'x\r\n1\r\n')
            with self.assertRaises(FileNotFoundError):snapshot(source,base/'absent',source)
            self.assertFalse((base/'absent').exists())
            (source/'READY').write_bytes(b'')
            real_open=Path.open
            class ChangingReader:
                changed=False
                def __init__(self,stream):self.stream=stream
                def __enter__(self):self.stream.__enter__();return self
                def __exit__(self,*args):return self.stream.__exit__(*args)
                def read(self,size):
                    value=self.stream.read(size)
                    if value and not self.changed:
                        with real_open(path,'ab') as writer:writer.write(b'!')
                        self.changed=True
                    return value
            def opening(candidate,*args,**kwargs):
                stream=real_open(candidate,*args,**kwargs)
                return ChangingReader(stream) if candidate==path and args==('rb',) else stream
            with patch.object(Path,'open',opening),self.assertRaisesRegex(ValueError,'changed during capture'):
                snapshot(source,base/'partial',source)
            self.assertTrue((base/'partial'/'x.csv').exists())
            self.assertFalse((base/'partial'/'snapshot.json').exists())

    def test_both_dated_examples_decode_and_preserve_all_external_business_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = create(Path(__file__).resolve().parents[1] /
                'examples/starter-data/vectorflow-starter-inputs-v1.zip', Path(directory) / 'csv')
            binding = load_binding(root / 'binding-template.json')
            with zipfile.ZipFile(Path(__file__).resolve().parents[1] /
                    'examples/starter-data/vectorflow-starter-inputs-v1.zip') as archive:
                for index, day in enumerate(('2026-10-18', '2026-10-19'), 1):
                    batch = json.loads((root / day / 'batch.json').read_bytes())
                    payloads = {name:(root / day / name).read_bytes() for name, status in batch['feeds'].items() if status == 'PRESENT'}
                    raw, positions = assemble(batch, binding, payloads, first_day=index == 1)
                    import hashlib
                    value = decode(raw, hashlib.sha256(raw).hexdigest())
                    expected = json.loads(archive.read(f'day-0{index}.json'))
                    for field in ('day', 'consumer_opening', 'intake_schema'):
                        self.assertEqual(value[field], expected[field])
                    for name in ('shipments', 'transporters'):
                        self.assertEqual(value['producer_sources'][name]['rows'], expected['producer_sources'][name]['rows'])
                    self.assertEqual(len(positions['DailyDataRaw.csv']), 16)


if __name__ == '__main__':
    unittest.main()
