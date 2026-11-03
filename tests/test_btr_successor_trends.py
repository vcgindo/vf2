from datetime import date, timedelta
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from tests.test_operational_btr_boundary import btr
from mta.presentation import btr_incremental_xml as snapshot, btr_successor_trends as trends
from mta.runtime import btr_import_relation as imports
from mta.serialization import digest


class SuccessorTrendsTest(TestCase):
    def setUp(self):
        day = date(2026, 4, 9)
        self.parent = SimpleNamespace(pk='p', business_date=day - timedelta(days=3))
        image = dict(storage_format=imports.FORMAT,
                     fields=[(field, field, kind) for field, kind in zip(
                         trends.OPERANDS, ('str','float','int','str','str','str','str','str'), strict=True)])
        self.run = SimpleNamespace(predecessor_id='p', business_date=day,
                                   production_manifest={'images': {imports.HISTORY: image}})

        def observation(sku, days_ago):
            return dict(SKUCode=sku, WHCode='W', ReportDate=(day-timedelta(days=days_ago)).isoformat(),
                        Norm=10, VirtualNorm=11, ParentWhCode='P', TechPen='9.00', EcoPen=-0.0,
                        DispatchPen=3, PhysicalInventoryPen=None, TechColor='Red', EcoColor="x&'\t",
                        DispatchColor='Black', PhysicalInventoryColor='White')

        before = [observation(sku, offset) for offset in (92,89,60,30,7,3) for sku in ('A','B')]
        before.append(observation('B',3))
        today = [observation('A',0), observation('C',0)]
        self.facts = dict(DBMMaster=[], vf_RationedReqReport=today)
        self.state = dict(BPR=before[2:]+today, LocationAttributeData=[])
        old = btr._generate_trends(self.parent.business_date, dict(BPR=before, LocationAttributeData=[]),
                                   self.facts, _owned=True)
        self.groups = []
        for owner, sku in enumerate(('A','B')):
            values = tuple(snapshot.shifted(btr._xml_rows(row for row in old[name] if row['SKUCode']==sku), 3)
                           for name in snapshot.FAMILIES)
            self.groups.append(((sku,'W'),owner,values))

    def result(self):
        return trends.generate(self.run,self.parent,dict(count=2),self.state,self.facts)

    def test_duplicate_latest_absent_key_expiry_and_typed_xml(self):
        expected = btr._generate_trends(self.run.business_date,dict(self.state),self.facts,_owned=True)
        with patch.object(snapshot,'previous_groups',side_effect=lambda *args: (r for r in self.groups)), \
                patch.object(trends,'summary') as metric:
            actual = self.result()
        self.assertEqual(metric.call_args.args, ('btr_trend_window_advance',))
        self.assertEqual(metric.call_args.kwargs['latest_rows'],4)
        self.assertIs(actual['BPR'],self.state['BPR'])
        for family in snapshot.FAMILIES:
            self.assertEqual(digest(actual[family]),digest(expected[family]))
        self.assertEqual(actual['BPPTrendEcon'][0]['D87'].hex(),(-0.0).hex())
        self.assertIs(type(actual['BPPTrendDispatch'][0]['D87']),int)

    def test_unusable_prefix_recomputes_whole_window(self):
        expected = btr._generate_trends(self.run.business_date,dict(self.state),self.facts,_owned=True)
        key,owner,prefixes=self.groups[0]
        self.groups[0]=key,owner,(None,*prefixes[1:])
        with patch.object(snapshot,'previous_groups',side_effect=lambda *args: (r for r in self.groups)), \
                patch.object(trends,'summary') as metric:
            actual=self.result()
        self.assertEqual(metric.call_args.args,('btr_trend_window_full_fallback',))
        self.assertEqual(digest(actual),digest(expected))

    def test_short_history_avoids_predecessor_cursor_and_wrong_parent_is_refused(self):
        self.state['BPR']=self.state['BPR'][-2:]
        with patch.object(snapshot,'previous_groups',side_effect=AssertionError('unexpected cursor')):
            self.assertEqual(len(self.result()['BPPTrendTech']),2)
            self.run.predecessor_id='other'
            with self.assertRaisesRegex(ValueError,'predecessor'):
                self.result()

    def test_conflicting_spelling_keeps_canonical_source_failure(self):
        self.state['BPR'][0] = {**self.state['BPR'][0], 'SKUCode': 'a '}
        with patch.object(snapshot, 'previous_groups', side_effect=lambda *args: (row for row in ())), \
                self.assertRaisesRegex(ValueError, 'SOURCE_ORDER_AMBIGUITY'):
            self.result()
