from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from mta.application import runtime_report_encoding as encoding
from mta.application import runtime_report_files as files

FIXTURE = Path(__file__).parent/'fixtures/runtime_reports_retained_20261019.json'


def definition(identity=7):
    return next(row for row in json.loads(FIXTURE.read_bytes()) if row['Id'] == identity)


class RuntimeReportEncodingTests(unittest.TestCase):
    def test_all_native_column_types_and_literal_headers(self):
        widths = {2:24,3:24,4:31,5:31,6:31,7:12,8:34,10:107}
        for row in json.loads(FIXTURE.read_bytes()):
            self.assertEqual(len(encoding.types(row)), widths[row['Id']])
            self.assertEqual(len(encoding.headers(row['HeaderList'])), widths[row['Id']])
        self.assertEqual(encoding.types(definition(10))[20:23], ('int',)*3)
        self.assertEqual(encoding.types(definition(10))[24], 'varchar(125)')
        self.assertEqual(encoding.types(definition(10))[41], 'bit')
        self.assertEqual(encoding.types(definition(8))[27], 'nvarchar(max)')

    def test_literal_header_parser_preserves_spaces_commas_quotes_and_null(self):
        self.assertEqual(encoding.headers(" ' a ', 'b,c', 'd''e' \r\n"), (' a ', 'b,c', "d'e"))
        self.assertIsNone(encoding.headers(None))
        for text in ('', ' ', "'a',", "'a' 'b'", "'a'+ 'b'", "N'a'", '1', "'a'; SELECT 1"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                encoding.headers(text)

    def test_native_scalar_forms_no_trimming_or_csv_quoting(self):
        row = (3, ' edge ', 4, True, False, 10, None, 'S,1', 'W"1', 'é', date(2026,10,25), None)
        report = dict(definition(), HeaderList="'one', ' two '")
        self.assertEqual(b''.join(encoding.chunks(report, [row])),
            b'one, two \r\n3, edge ,4,1,0,10,NULL,S,1,W"1,\xe9,2026-10-25,NULL\r\n')
        self.assertEqual(encoding.cell(Decimal('-0.00'), 'decimal(10,2)'), '.00')
        self.assertEqual(encoding.cell(Decimal('-.12'), 'decimal(10,2)'), '-.12')
        self.assertEqual(encoding.cell('', 'nvarchar(50)'), '')
        self.assertEqual(encoding.cell('NULL', 'nvarchar(50)'), 'NULL')
        self.assertEqual(encoding.cell('a\r\nb', 'nvarchar(50)'), 'a\r\nb')
        # BOR SQL adds literal wrapper quotes; the formatter must not escape
        # embedded quotes or commas as an RFC CSV library would.
        self.assertEqual(encoding.cell('"a,"quoted" value"', 'varchar(127)'), '"a,"quoted" value"')

    def test_header_only_and_no_header_empty_population(self):
        self.assertEqual(len(list(encoding.chunks(definition(), []))), 1)
        self.assertEqual(list(encoding.chunks(dict(definition(), HeaderList=None), [])), [])

    def test_streaming_consumes_one_row_at_a_time_and_late_error_has_no_success(self):
        seen = []
        def rows():
            for value in ('S', '中'):
                seen.append(value)
                yield (1, 'C', 2, False, False, 4, 4, value, 'W', 'P', date(2026,10,25), None)
        report = encoding.chunks(definition(), rows())
        next(report)  # independent header SELECT
        self.assertEqual(seen, [])
        next(report)
        self.assertEqual(seen, ['S'])
        with self.assertRaisesRegex(ValueError, 'encoding'):
            next(report)

    def test_invalid_types_widths_and_unsupported_configurations_deny(self):
        for value, kind in ((Decimal('1.2'), 'decimal(10,2)'), (True,'int'),
                ('x'*51,'nvarchar(50)'), ('x'*257,'nvarchar(max)'), (3,'nvarchar(max)')):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                encoding.cell(value, kind)
        self.assertEqual(encoding.cell('x'*256,'nvarchar(max)'), 'x'*256)
        for changed in ({'Extension':'xlsx'}, {'TemplateName':'T'}, {'Delimeter':';'}, {'Query':'select 1'}):
            with self.assertRaises(ValueError):
                encoding.chunks(dict(definition(), **changed), [])
        with self.assertRaisesRegex(ValueError, 'width'):
            list(encoding.chunks(definition(), [(1,2)]))

    def test_late_stream_failure_does_not_replace_prior_download(self):
        def chunks():
            yield b'header\r\n'
            raise ValueError('late cell failure')
        with tempfile.TemporaryDirectory() as root:
            Path(root,'download').mkdir()
            prior = Path(root,'download/TotalReqReport_2026-04-08.csv')
            prior.write_bytes(b'accepted')
            with self.assertRaisesRegex(ValueError,'late cell failure'):
                files.publish(root=root, definition=definition(10),
                    variables=dict(TotalReqReport='TotalReqReport_2026-04-08',ReportsDownloadLoc='download'),
                    report_chunks=chunks())
            self.assertEqual(prior.read_bytes(), b'accepted')
            self.assertEqual(Path(root,'output/TotalReqReport_2026-04-08.csv').read_bytes(), b'header\r\n')

    def test_streamed_file_equals_direct_encoder_without_materializing_rows(self):
        report = definition(10)
        row = tuple(None for _ in range(107))
        with tempfile.TemporaryDirectory() as root:
            result = files.publish(root=root, definition=report,
                variables=dict(TotalReqReport='TotalReqReport_2026-04-08',ReportsDownloadLoc='download'),
                report_chunks=encoding.chunks(report, iter([row, row])))
            self.assertEqual(Path(root,result['download']['relative_path']).read_bytes(),
                             b''.join(encoding.chunks(report,[row,row])))
