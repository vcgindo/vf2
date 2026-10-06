"""Bounded production-serving tests for canonical GIT charts and custom grid."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()

from mta.presentation import daily_git_custom, daily_git_preparation, daily_git_read, git_read
from mta.presentation.context import PublicationUnavailable


class Codes(set):
    pass


def scopes():
    products = Codes(('A',)); products.multiplicities = {'A': 2}
    locations = Codes(('L', 'P')); locations.multiplicities = {'L': 1, 'P': 1}
    return products, locations


class DailyGitServingTests(unittest.TestCase):
    def test_retained_location_configuration_is_exact_and_missing_binding_denied(self):
        metadata = {'fields': [('c1', 'c1', 'text')]}
        visible = dict(ReportName='AdminBPR', Col_Code='LocAttr1', Header='Region/Group', Visible=True)
        with patch.object(daily_git_preparation, 'BPR_UI_CONFIG', [visible]), \
             patch.object(daily_git_preparation, 'image_metadata', return_value=metadata):
            self.assertEqual(daily_git_preparation.location_configuration(SimpleNamespace()),
                             ([('c1', 'c1')],
                              [dict(header='Region Group', colCode='c1', colPosition=0)]))
        with patch.object(daily_git_preparation, 'BPR_UI_CONFIG', [visible]), \
             patch.object(daily_git_preparation, 'image_metadata', return_value={'fields': []}), \
             self.assertRaisesRegex(PublicationUnavailable, 'binding_missing:c1'):
            daily_git_preparation.location_configuration(SimpleNamespace())

    def test_graph_executes_four_aggregate_queries_and_assembles_wire(self):
        products, locations = scopes()
        relations = {name: ('SELECT * FROM ' + name.replace('/', '_'), [name])
                     for name in (daily_git_preparation.TRANSPORTER_PATH,
                                  daily_git_preparation.TRANSIT_PATH, 'git_master',
                                  daily_git_preparation.DESCRIPTION_PATH,
                                  daily_git_preparation.LOCATION_PATH)}
        rows = [
            [dict(counts=4, WhCode='L', Details='Location', LogisticsLocation='LOG',
                  ll1='North', ll2=None, ll3=None, ll4=None, ll5=None, SKUStatus='Delay')],
            [dict(WhCode='L', LRCount=8, MinDelayDays=2, MaxDelayDays=4,
                  Mean=3, Median=3, Q1=2, Q3=4, Details='Location',
                  LogisticsLocation='LOG', ll1='North', ll2=None, ll3=None,
                  ll4=None, ll5=None)],
            [dict(counts=4, TransporterCode='T', TruckStatus='Delay',
                  TransporterName='Carrier')],
            [dict(TransporterCode='T', LRCount=8, MinDelayDays=2, MaxDelayDays=4,
                  Mean=3, Median=3, Q1=2, Q3=4, TransporterName='Carrier')],
        ]
        captured = []
        def fetch(sql, params):
            captured.append((sql, params))
            return rows[len(captured) - 1]
        with patch.object(daily_git_read, 'sources', return_value=(relations, [], [])), \
             patch.object(daily_git_read, '_fetch', side_effect=fetch):
            result = daily_git_read.graph(SimpleNamespace(), products, locations)
        self.assertEqual(len(captured), 4)
        self.assertIn('percentile_cont(0.25)', captured[1][0])
        self.assertIn('generate_series(1,P.weight*L.weight)', captured[0][0])
        self.assertIn('JOIN L ON', captured[2][0])
        self.assertEqual(result['data']['locationWise']['maxTechBlackRedColumn']['data'][0]['delay'], '4')
        self.assertEqual(result['data']['transporterWise']['delayDaysStatisticalBox']['data'][0]['Q3'], '4')

    def test_custom_keeps_inner_nms_join_pages_before_readback_and_omits_null_json(self):
        products, locations = scopes()
        names = (daily_git_preparation.TRANSPORTER_PATH, 'git_master',
                 daily_git_preparation.TRANSIT_PATH, daily_git_preparation.NMS_PATH,
                 daily_git_preparation.DESCRIPTION_PATH)
        relations = {name: ('SELECT * FROM ' + name.replace('/', '_'), [name]) for name in names}
        captured = {}
        class Cursor:
            calls = 0
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, sql, params):
                self.calls += 1
                captured.update(sql=sql, params=params)
                self.description = ([('key1',), ('key2',), ('count',), ('distinct',)]
                                    if self.calls == 1 else
                                    [('RN',), ('sc',), ('wc',), ('dd',), ('rmk',)])
            def fetchall(self):
                return [('a', 'l', 2, 1)] if self.calls == 1 else [(1, 'A', 'L', 3, None)]
        with patch.object(daily_git_custom, 'sources', return_value=(relations, [], [])), \
             patch.object(daily_git_custom.connection, 'cursor', return_value=Cursor()):
            result = daily_git_custom.custom(SimpleNamespace(), products, locations, (2, 5))
        self.assertIn(' JOIN C ON ', captured['sql'])
        self.assertIn('row_number() OVER (ORDER BY "sc","wc")', captured['sql'])
        self.assertIn('WHERE "RN" BETWEEN %s AND %s', captured['sql'])
        self.assertEqual(captured['params'][-2:], [6, 10])
        self.assertEqual(result['data'], [dict(RN=1, sc='A', wc='L', dd=3)])

    def test_daily_routes_dispatch_without_terminal_zero_fallback(self):
        run = SimpleNamespace(kind='DAILY_CHAIN')
        products, locations = scopes()
        resolved = ({}, None)
        with patch.object(git_read, 'selected_run', return_value=run), \
             patch('mta.presentation.daily_preparation.production_branch', return_value=True), \
             patch('mta.presentation.bpr_sql._projected_attributes', return_value=resolved), \
             patch.object(git_read, 'scope', return_value=(products, locations)), \
             patch('mta.presentation.daily_git_custom.custom', return_value={'custom': True}) as custom:
            self.assertEqual(git_read.custom({'paginationParameter': None}), {'custom': True})
            custom.assert_called_once_with(run, products, locations, None)
        with patch.object(git_read, 'selected_run', return_value=run), \
             patch('mta.presentation.daily_preparation.production_branch', return_value=True), \
             patch('mta.presentation.bpr_sql._projected_attributes', return_value=resolved), \
             patch.object(git_read, 'scope', return_value=(products, locations)), \
             patch('mta.presentation.daily_git_read.graph', return_value={'graph': True}) as graph:
            self.assertEqual(git_read.graph({'type': 'child'}), {'graph': True})
            graph.assert_called_once_with(run, products, locations)


if __name__ == '__main__':
    unittest.main()
