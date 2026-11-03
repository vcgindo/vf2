from datetime import date, timedelta
from decimal import Decimal
import unittest

from mta.domain import btr_finalization as btr
from mta.presentation.btr_calendar import daily_cells
from mta.row_sequences import RecordRows


TODAY = date(2026, 4, 9)


def observation(day=TODAY, **changes):
    return dict({'SKUCode': 'S', 'WHCode': 'W', 'ReportDate': day.isoformat(),
                 'Norm': 10, 'VirtualNorm': 11, 'ParentWhCode': 'P',
                 'PhysicalInventoryPen': Decimal('22.00'), 'PhysicalInventoryColor': 'Green',
                 'DispatchPen': Decimal('102.00'), 'DispatchColor': 'Black',
                 'TechPen': 17, 'TechColor': 'White', 'EcoPen': 18, 'EcoColor': 'Blue'}, **changes)


class BtrDatedCellTests(unittest.TestCase):
    def test_each_date_can_be_valid_while_combined_live_window_refuses_alias(self):
        older = observation(TODAY - timedelta(days=89))
        newer = observation(SKUCode='s ', WHCode='w')
        for r in (older, newer):
            cell, = daily_cells(date.fromisoformat(r['ReportDate']), [r])
            self.assertEqual((cell.sku, cell.location), (r['SKUCode'], r['WHCode']))
        with self.assertRaisesRegex(ValueError, 'identity spelling'):
            btr._pivot_cells([older, newer], TODAY, 'DispatchPen')
        cells, keys, _ = btr._pivot_cells([older, newer], TODAY + timedelta(days=1), 'DispatchPen')
        key, = keys
        self.assertEqual((key[0], key[1]), ('s ', 'w'))
        self.assertEqual(cells[key, TODAY], newer['DispatchPen'])

    def test_consumes_current_date_once_and_preserves_duplicate_maxima_and_nulls(self):
        inputs = [observation(DispatchPen=None), observation(PhysicalInventoryPen=Decimal('23.50')),
                  observation(SKUCode=None, PhysicalInventoryPen=None, PhysicalInventoryColor=None)]
        reads = []
        def records():
            reads.append(True)
            yield from inputs
        values = list(daily_cells(TODAY, RecordRows(3, records)))
        self.assertEqual(len(reads), 1)
        self.assertEqual(len(values), 2)
        self.assertEqual((values[0].observations, values[0].physical_pen, values[0].dispatch_pen),
                         (2, Decimal('23.50'), Decimal('102.00')))
        self.assertEqual((values[1].sku, values[1].observations, values[1].physical_pen), (None, 1, None))
        self.assertEqual(list(daily_cells(TODAY, [])), [])
        with self.assertRaisesRegex(ValueError, 'identity spelling'):
            list(daily_cells(TODAY, [observation(), observation(SKUCode='s ')]))
        with self.assertRaisesRegex(ValueError, 'different date'):
            list(daily_cells(TODAY, [observation(TODAY-timedelta(days=1))]))

    def test_dates_reconstruct_pivots_with_latest_multiplicity_and_master_override(self):
        # The oldest included date expires on the successor. There is a gap
        # longer than the one-day fill tolerance immediately before yesterday.
        history = [observation(TODAY-timedelta(days=89), DispatchColor='Red'),
                   observation(TODAY-timedelta(days=4), DispatchColor='Red'),
                   observation(TODAY-timedelta(days=1), DispatchColor='Red'),
                   observation(), observation(PhysicalInventoryPen=Decimal('23.50'))]
        facts = {'DBMMaster': [{'SKUCode': 'S', 'WHCode': 'W', 'Norm': 12, 'ParentWhCode': 'P2'}],
                 'ExpediteDispatches': []}
        cells = {}
        for stamp in sorted({r['ReportDate'] for r in history}):
            day = date.fromisoformat(stamp)
            cells[day], = daily_cells(day, [r for r in history if r['ReportDate'] == stamp])
        for offset in (0, 1):
            day = TODAY + timedelta(days=offset)
            if offset:
                rows = [observation(day, PhysicalInventoryColor='Yellow', DispatchColor='Green')]
                history.extend(rows)
                cells[day], = daily_cells(day, rows)
            state = btr._generate_trends(day, {'BPR': history, 'LocationAttributeData': []}, facts)
            self.assertEqual(len(state['BPPTrendPhysicalInv']), 2 if not offset else 1)
            self.assertEqual(len(state['BufferTrendPhysicalInv']), 1)
            for table, attribute in (('BPPTrendPhysicalInv','physical_pen'), ('BufferTrendPhysicalInv','physical_colour'),
                                     ('BPPTrendDispatch','dispatch_pen'), ('BufferTrendDispatch','dispatch_colour'),
                                     ('BPPTrendTech','tech_pen'), ('BufferTrendReport','tech_colour'),
                                     ('BPPTrendEcon','eco_pen'), ('BufferTrendReportEcon','eco_colour')):
                for r in state[table]:
                    for slot in btr.DAYS:
                        stamp = date.fromisoformat(state['BufferTrendDates'][0][slot])
                        self.assertEqual(r[slot], getattr(cells.get(stamp), attribute, None))
            self.assertEqual((state['BufferTrendPhysicalInv'][0]['Norm'], state['BufferTrendPhysicalInv'][0]['ParentWhCode']),
                             (12, 'P2'))
            if not offset:
                aged = btr._update_br_age(state, facts, 'BufferTrendDispatch', 1)
                self.assertEqual(aged['BufferTrendDispatch'][0]['BRAge'], 2)
                availability = btr._availability(state)['BufferTrendPhysicalInv'][0]
                self.assertEqual([availability[f'Availability_{s}'] for s in ('01_30','31_60','61_90')],
                                 [Decimal('100.00'), Decimal('0.00'), Decimal('100.00')])
