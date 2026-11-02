from dataclasses import replace
from io import StringIO
import csv
import unittest
from types import SimpleNamespace

from mta.runtime.execution_setting_values import SettingCell
from mta.runtime.execution_setting_catalogue import extract, AUTO_DBM_CELL_PATH
from mta.runtime.execution_setting_owners import extract as owner_cells
from mta.runtime.execution_settings_csv import export_text, import_text, revision


class SettingsFileTests(unittest.TestCase):
    def setUp(self):
        self.version = SimpleNamespace(pk='installation-specific-version', revision=2)
        self.cells = extract({'delivery': {'batch': {'AutoDBMActive': 0}},
                              'daily': {'settings': [{'Parameter': 'Blank', 'Value': ''},
                                                     {'Parameter': 'Null', 'Value': None}]}})
        self.cells += owner_cells({'dbm': {'VFSettings': [
            {'Parameter': 'SuperDelayFactor', 'Value': '2', 'Description': None},
            {'Parameter': 'SuperDelayFactor', 'Value': '2', 'Description': None}]}})
        self.text = export_text(self.version, self.cells)

    def change(self, predicate, field, value):
        reader = csv.DictReader(StringIO(self.text))
        rows = list(reader)
        for row in rows:
            if predicate(row):
                row[field] = value
        out = StringIO(newline='')
        writer = csv.DictWriter(out, fieldnames=reader.fieldnames, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
        return out.getvalue()

    def test_complete_typed_duplicate_and_null_bag_round_trips_with_bom(self):
        self.assertEqual(import_text('\ufeff' + self.text, self.version, self.cells), self.cells)
        self.assertEqual(revision(self.text), 2)

    def test_only_qualified_auto_value_changes(self):
        text = self.change(lambda row: row['Path'] == AUTO_DBM_CELL_PATH, 'Value', '1')
        actual = import_text(text, self.version, self.cells)
        expected = tuple(replace(c, value_text='1') if c.path == AUTO_DBM_CELL_PATH else c for c in self.cells)
        self.assertEqual(actual, expected)

    def test_foreign_export_or_changed_metadata_refused(self):
        for field, value in [('Version', 'foreign'), ('Revision', '3'), ('Type', 'bool'),
                             ('State', 'NULL'), ('Path', '/foreign'), ('Effect', 'make editable'),
                             ('Activation', 'FUTURE_RUN'), ('Occurrence', '9')]:
            with self.subTest(field=field):
                text = self.change(lambda row: row['Path'].startswith('/owners/'), field, value)
                with self.assertRaises(ValueError):
                    import_text(text, self.version, self.cells)

    def test_missing_extra_or_reordered_rows_refused(self):
        lines = self.text.splitlines(keepends=True)
        for text in (''.join(lines[:-1]), self.text + lines[-1],
                     ''.join([lines[0], lines[2], lines[1], *lines[3:]])):
            with self.assertRaises(ValueError):
                import_text(text, self.version, self.cells)

    def test_locked_values_and_blank_null_distinction_refused(self):
        for path in ('/owners/', '/daily/settings/'):
            text = self.change(lambda row: row['Path'].startswith(path) and row['Path'].endswith('/Value'),
                               'Value', '1')
            with self.assertRaisesRegex(ValueError, 'locked'):
                import_text(text, self.version, self.cells)

    def test_auto_value_has_strict_integer_0_1_domain(self):
        for value in ('true', 'False', '01', '1.0', ' 1', '2', '', 'NULL'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                import_text(self.change(lambda row: row['Path'] == AUTO_DBM_CELL_PATH, 'Value', value),
                            self.version, self.cells)

    def test_mixed_or_noncanonical_revision_refused(self):
        for value in ('0', '02', '-1', '2.0', ' 2', '٢'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                revision(self.change(lambda row: True, 'Revision', value))


if __name__ == '__main__':
    unittest.main()
