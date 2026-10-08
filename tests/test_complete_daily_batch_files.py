from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mta.application.complete_daily_batch_files import (
    sqlcmd_bytes, write_pick_reports, reports_from_pick_state, PICK_NAMES, UnqualifiedBatchValue)
from mta.application.complete_daily_pick_files import project_reports


class BatchFileTests(unittest.TestCase):
    def test_persisted_state_reconstructs_exact_file_bytes_without_mutation(self):
        from mta.domain.remaining_capabilities import calculate_pick_list_state
        from mta.serialization import storage
        from tests.test_pick_stage_state import fixture
        state = calculate_pick_list_state(fixture())
        persisted = storage(state)
        before = deepcopy(persisted)
        expected, actual = reports_from_pick_state(state), reports_from_pick_state(persisted)
        for name in PICK_NAMES:
            self.assertEqual(sqlcmd_bytes(actual[name]['resultsets']), sqlcmd_bytes(expected[name]['resultsets']))
        self.assertEqual(persisted, before)
        del persisted['LogisticPickList'][0]['NewSRNo']
        with self.assertRaisesRegex(ValueError, 'column roster'):
            reports_from_pick_state(persisted)
        with self.assertRaises(KeyError):
            reports_from_pick_state({})

    def test_native_literal_resultset_format_is_not_csv_escaped(self):
        sets = [dict(fields=['']*5, types=['varchar(7)']*5,
                     rows=[['Text', 'Null', 'Decimal', 'Comma', 'Unicode']]),
            dict(fields=['']*5, types=['nvarchar(50)', 'int', 'decimal(13,3)', 'nvarchar(50)', 'nvarchar(50)'],
                 rows=[[' edge ', None, Decimal('-1.250'), 'a,b"c', 'é'],
                       ['  lead   ', 12, Decimal('0.000'), 'line\r\nnext', 'tail']])]
        self.assertEqual(sqlcmd_bytes(sets),
            b'Text,Null,Decimal,Comma,Unicode\r\n edge ,NULL,-1.250,a,b"c,\xe9\r\n  lead   ,12,.000,line\r\nnext,tail\r\n')

    def test_decimal_zero_fraction_and_null_empty_text_remain_distinct(self):
        sets = [dict(fields=['']*6, types=['decimal(13,3)']*3 + ['nvarchar(50)']*3,
            rows=[[Decimal('-0.000'), Decimal('.125'), Decimal('-.125'), '', '   ', None]])]
        self.assertEqual(sqlcmd_bytes(sets), b'.000,.125,-.125,,   ,NULL\r\n')

    def test_encoding_unknown_types_and_display_truncation_fail_explicitly(self):
        for kind, value in [('nvarchar(50)', '中'), ('nvarchar(50)', 'x\0y'),
                ('nvarchar(300)', 'x'*257), ('nvarchar(2)', 'long'),
                ('decimal(13,3)', Decimal('1.25')), ('int', True), ('float', 1.0)]:
            with self.subTest(kind=kind, value=str(value)[:10]), self.assertRaises(UnqualifiedBatchValue):
                sqlcmd_bytes([dict(fields=[''], types=[kind], rows=[[value]])])

    def test_four_file_lifecycle_replaces_both_old_files_and_copies_exact_bytes(self):
        reports = project_reports(logistic_pick_list=[], pick_list_data_for_truck_formation=[])
        before = deepcopy(reports)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output, download = root/'output', root/'download'
            output.mkdir(); download.mkdir()
            for name in PICK_NAMES.values():
                (output/name).write_bytes(b'old-output')
                (download/name).write_bytes(b'old-download')
            completed = write_pick_reports(reports, owned_root=root, output_folder=output, download_folder=download)
            self.assertEqual([r['report'] for r in completed], list(PICK_NAMES))
            for kind, name in PICK_NAMES.items():
                self.assertEqual((output/name).read_bytes(), sqlcmd_bytes(reports[kind]['resultsets']))
                self.assertEqual((output/name).read_bytes(), (download/name).read_bytes())
        self.assertEqual(reports, before)

    def test_failed_format_has_no_success_and_retains_canonical_delete_before_write(self):
        reports = project_reports(logistic_pick_list=[], pick_list_data_for_truck_formation=[])
        reports['logistic']['resultsets'][0]['rows'][0] = ('中',)*11
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output, download = root/'output', root/'download'
            output.mkdir(); download.mkdir()
            name = PICK_NAMES['logistic']
            (output/name).write_bytes(b'old'); (download/name).write_bytes(b'old')
            with self.assertRaises(UnqualifiedBatchValue):
                write_pick_reports(reports, owned_root=root, output_folder=output, download_folder=download)
            self.assertFalse((output/name).exists())
            self.assertFalse((download/name).exists())

    def test_ownership_and_roster_denial_precede_file_mutation(self):
        reports = project_reports(logistic_pick_list=[], pick_list_data_for_truck_formation=[])
        with TemporaryDirectory() as directory, TemporaryDirectory() as outside:
            root = Path(directory)
            with self.assertRaises(ValueError):
                write_pick_reports(reports, owned_root=root, output_folder=root, download_folder=outside)
            with self.assertRaises(ValueError):
                write_pick_reports(reports, owned_root=root, output_folder=root, download_folder=root)
            with self.assertRaises(ValueError):
                write_pick_reports({}, owned_root=root, output_folder=root, download_folder=outside)


if __name__ == '__main__':
    unittest.main()
