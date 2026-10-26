"""Dispatch/source-namespace contracts; no native or phase-owner proof."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unittest

from mta.application import runtime_report_projection as projection
from mta.application.runtime_report_configuration import plan, SCHEMA
from tests.test_runtime_bor_report import sources as bor_sources
from tests.test_runtime_demand_reports import sources as demand_sources
from tests.test_runtime_history_reports import efficiency_sources, allocation_sources


ROWS = json.loads((Path(__file__).parent / 'fixtures/runtime_reports_retained_20261019.json').read_bytes())


def inputs(definition):
    identity = definition['Id']
    arguments = (bor_sources() if identity in (4, 5, 6) else
                 efficiency_sources() if identity in (2, 3) else
                 allocation_sources() if identity == 8 else
                 dict(spike_order_data=[]) if identity == 7 else demand_sources())
    spec = projection.describe(definition)
    result = {}
    for argument, name in spec['sources'].items():
        value = arguments[argument]
        result[name] = ([dict(LastRunDate=datetime.combine(value, datetime.min.time()))]
                        if argument == 'today' else value)
    return result


class RuntimeReportProjectionTests(unittest.TestCase):
    def test_all_retained_queries_are_registered_with_exact_database_and_column_roster(self):
        expected = {2: 24, 3: 24, 4: 31, 5: 31, 6: 31, 7: 12, 8: 34, 10: 107}
        for definition in ROWS:
            with self.subTest(identity=definition['Id']):
                spec = projection.describe(definition)
                self.assertEqual(spec['captured_source_id'], definition['Id'])
                self.assertEqual(len(spec['columns']), expected[definition['Id']])
                # Captured HeaderList consists of literal SQL string columns.
                literals = re.findall(r"'(?:[^']|'')*'", definition['HeaderList'])
                self.assertEqual(len(literals), expected[definition['Id']])
                result = projection.project(definition, inputs(definition))
                self.assertEqual(result['columns'], spec['columns'])
                for row in result['rows']:
                    self.assertEqual(len(row), expected[definition['Id']])
                self.assertEqual(projection.describe(dict(definition, Id=999)), spec)

    def test_full_and_split_plans_dispatch_same_reports_in_same_placement_order(self):
        value = dict(schema=SCHEMA, RuntimeReports=ROWS, DownloadableUIReportSettings=[])
        def selected(scope):
            return [(stage['placement'], projection.describe(row)['query_sha256'])
                    for stage in plan(value, scope) for row in stage['RuntimeReports']]
        self.assertEqual(selected('Full'), selected('UptoBPR') + selected('PostBPR'))
        self.assertEqual(selected('Full'), selected('UptoDBM') + selected('PostDBM'))
        self.assertEqual(len(selected('Full')), 8)

    def test_same_column_names_cannot_substitute_a_different_database_owner(self):
        definition = ROWS[0]
        source = inputs(definition)
        source['BPR/SkuLocAttributeData'] = source.pop('BTR/SkuLocAttributeData')
        with self.assertRaisesRegex(ValueError, 'logical'):
            projection.project(definition, source)
        with self.assertRaisesRegex(ValueError, 'BaseDB'):
            projection.describe(dict(definition, BaseDB='%BPRDatabase%'))
        for definition in ROWS:
            source = inputs(definition)
            del source[next(iter(source))]
            with self.subTest(identity=definition['Id']), self.assertRaises(ValueError):
                projection.project(definition, source)

    def test_date_is_from_exact_source_not_implicit_run_or_host_date(self):
        definition = ROWS[0]
        source = inputs(definition)
        for values in ([], [dict(LastRunDate=None)]):
            source['BTR/LastBatchRunTbl'] = values
            self.assertEqual(projection.project(definition, source)['rows'], [])
        for values in ([dict(LastRunDate='2026-06-17T00:00:00')] * 2,
                       [{}], [dict(LastRunDate=datetime.now(timezone.utc))],
                       [dict(LastRunDate='not-a-date')], None):
            source['BTR/LastBatchRunTbl'] = values
            with self.subTest(values=values), self.assertRaises(ValueError):
                projection.project(definition, source)
        source['BTR/LastBatchRunTbl'] = [dict(LastRunDate='2026-06-17T15:00:00')]
        self.assertEqual(len(projection.project(definition, source)['rows']), 1)

    def test_unknown_queries_and_unexpected_sources_deny(self):
        with self.assertRaisesRegex(ValueError, 'no implemented'):
            projection.describe(dict(ROWS[0], Query='SELECT 1'))
        source = inputs(ROWS[0]); source['unrelated'] = []
        with self.assertRaisesRegex(ValueError, 'logical'):
            projection.project(ROWS[0], source)
