"""Dated page reconstruction against the existing prepared-row mapper."""
from datetime import date, timedelta
from decimal import Decimal
import math
import os
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation.btr_calendar import DayCell
from mta.presentation.btr_page_dates import date_slots, display_dates
from mta.presentation import btr_snapshot as original
from mta.presentation.btr_snapshot_fields import DAILY_FIELDS, DISPLAY_FIELDS, TEXT_FIELDS, display_field


class BtrPageDatesTests(unittest.TestCase):
    def test_sparse_dates_match_stored_numbers_text_prefixes_and_markers(self):
        start = date(2026, 1, 10)
        labels = {slot:(start+timedelta(days=i)).isoformat() for i,slot in enumerate(DAILY_FIELDS)}
        observations = {}
        for i in range(1,90,2):
            day = start + timedelta(days=i)
            observations[day] = DayCell(day, 'S', 'W', 2,
                [Decimal('100.00'), '99.99', None, 'Infinity', '1e21'][i%5], 'Red',
                ['99.1', '', Decimal('100.01')][i%3], '3Blue', 0, 'wrong', 0, 'wrong')
        for branch in ('tech','eco'):
            for present in (False,True):
                raw = dict.fromkeys((*TEXT_FIELDS,*DISPLAY_FIELDS), None)
                for i,slot in enumerate(DAILY_FIELDS):
                    day = start+timedelta(days=i)
                    if day in observations:
                        c = observations[day]
                        raw[slot] = c.physical_pen if branch=='tech' else c.dispatch_pen
                        if present:
                            raw['C'+slot] = c.physical_colour if branch=='tech' else c.dispatch_colour
                prepared = original.prepared_values(raw)
                for columns, horizon in ((DAILY_FIELDS,90),(DAILY_FIELDS[-30:],60),
                                         (DAILY_FIELDS[12:23],30),(DAILY_FIELDS[-1:],1),
                                         (DAILY_FIELDS[:1],90)):
                    slots = date_slots(labels, columns)
                    row, tokens = display_dates(branch, 4, observations, slots, horizon, has_colour_row=present)
                    expected_tokens = dict(zip(prepared['nonfinite_fields'],prepared['nonfinite_tokens'],strict=True))
                    for field in (*columns,*('C'+slot for slot in columns)):
                        num = prepared[display_field(field,'number')]
                        text = prepared[display_field(field,'text')]
                        value = num if num is not None else text
                        self.assertEqual((row[field],type(row[field])),(value,type(value)))
                        if field in expected_tokens:
                            self.assertEqual(tokens[field],[branch,4,field,expected_tokens[field]])
                    availability = original.range_availability(prepared['available_prefix'],prepared['empty_prefix'],
                                                               horizon,columns)
                    self.assertEqual(row['Availability'],availability if math.isfinite(availability) else None)
                    self.assertEqual('Availability' in tokens,not math.isfinite(availability))
