"""Focused changes to the prepared snapshot boundary, without engine execution."""
import os
import math
import unittest
from copy import deepcopy

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()

from mta.presentation.btr_display import prepare_display
from mta.presentation.btr_snapshot import prepared_values, range_availability, _display_projection, _display_row
from mta.presentation.btr_snapshot_fields import TEXT_FIELDS, DISPLAY_FIELDS, DAILY_FIELDS, display_field


class SnapshotSummaryTests(unittest.TestCase):
    def test_prepared_cells_and_range_summary_match_accepted_mapper(self):
        values = ['', '0', '100', '-99999999.00', '99.999', '1e22', '1e-8',
                  'Infinity', '-Infinity', 'NaN', 'green', '12 tail', '00017']
        raw = {name: values[i % len(values)] for i, name in enumerate(DISPLAY_FIELDS)}
        raw.update({name: '00017' for name in TEXT_FIELDS})
        prepared = prepared_values(raw)
        for first, last, horizon in ((1, 90, 90), (84, 90, 7), (40, 60, 50), (1, 10, 7)):
            columns = DAILY_FIELDS[first-1:last]
            selected = {name: value for name, value in raw.items()
                        if name not in DAILY_FIELDS and not name.startswith('CD') or
                        name in columns or name in tuple('C' + c for c in columns)}
            expected = prepare_display({'tech': [deepcopy(selected)], 'eco': []}, horizon)
            row = expected['tech'][0]
            projection, slots = _display_projection(columns)
            stored_fields = [part.removeprefix('S.').strip('"') for part in projection.split(',')]
            actual_row = _display_row(tuple(prepared[f] for f in stored_fields), slots, prepared['nonfinite_fields'])
            self.assertEqual(actual_row, {name: row[name] for name in selected})
            self.assertNotIn('json', projection.lower())
            for name in selected:
                text = prepared[display_field(name, 'text')]
                number = prepared.get(display_field(name, 'number'))
                actual = None if name in prepared['nonfinite_fields'] else number if number is not None else text or ''
                self.assertEqual(actual, row[name], name)
                self.assertIs(type(actual), type(row[name]), name)
            actual = range_availability(prepared['available_prefix'], prepared['empty_prefix'], horizon, columns)
            self.assertEqual(None if math.isnan(actual) else actual, row['Availability'])

    def test_all_empty_and_source_nulls_keep_nan_and_empty_meanings(self):
        raw = dict.fromkeys((*TEXT_FIELDS, *DISPLAY_FIELDS), None)
        prepared = prepared_values(raw)
        self.assertIsNone(prepared['availability'])
        self.assertTrue(math.isnan(range_availability(prepared['available_prefix'], prepared['empty_prefix'], 7, DAILY_FIELDS)))
        # Missing server columns do not count as empty frontend cells.
        self.assertEqual(range_availability(prepared['available_prefix'], prepared['empty_prefix'], 7, DAILY_FIELDS[:7]), 0)


if __name__ == '__main__':
    unittest.main()
