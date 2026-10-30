"""PostgreSQL regression oracle for narrow BTR reference-source projections."""
from collections import Counter
from contextlib import ExitStack
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'btr-reference-projection-unit-only')
import django
django.setup()
from django.db import connection, transaction
from mta.presentation import btr_reporting as service
from mta.presentation.rrr_sql import equal, key


def legacy_populate(run, generation, target):
    """Frozen 66260758 join SQL, before the projection correction."""
    for branch in ('tech', 'eco'):
        for export in (False, True):
            paths = {alias: service.SOURCES[branch + '_' + alias] if alias in ('A', 'btd') else service.SOURCES[alias]
                     for alias in service.ORDINALS if not (export and alias == 'sla')}
            ctes, values = [], []
            for alias, path in paths.items():
                query, bound = service.image_query(run, path)
                ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
                values.extend(bound)
            joins = ''
            for alias in paths:
                if alias == 'A':
                    continue
                condition = (equal('A."WhCode"', alias + '."WHCode"') if alias == 'la' else
                             equal('A."SKUCode"', alias + '."SKUCode"'))
                if alias not in ('sa', 'la'):
                    condition += ' AND ' + equal('A."WhCode"', alias + ('."LocCode"' if alias == 'sla' else '."WhCode"'))
                joins += ' LEFT JOIN ' + alias + ' ON ' + condition
            expressions = ['%s', '%s', 'A."SKUCode"', 'A."WhCode"', key('A."SKUCode"'), key('A."WhCode"')]
            expressions += ['NULL::bigint' if export and alias == 'sla' else alias + '.vf_ordinal' for alias in service.ORDINALS]
            with connection.cursor() as cursor:
                cursor.execute('WITH ' + ','.join(ctes) + ' INSERT INTO ' + target +
                    ' (generation_id,' + ','.join('"' + f + '"' for f in service.ROW_FIELDS) + ') SELECT %s,' +
                    ','.join(expressions) + ' FROM A' + joins, values + [generation.pk, branch, export])


@unittest.skipUnless(os.environ.get('VF_BTR_KEY_POSTGRES_PROOF') == '1', 'Owned PostgreSQL proof only')
class BtrReferenceProjectionTests(unittest.TestCase):
    def test_all_reference_occurrences_match_legacy_and_independent_null_duplicate_join(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            self.assertEqual(cursor.fetchone()[0], 'vftest_fresh_capture_lifetime3_20261030')
        # Only temporary fixture tables are written. Preserve the accepted small
        # component database and roll back even a successful test.
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout='60s'")
                cursor.execute("SET LOCAL work_mem='32MB'")
            rows = {
                'tech_A': [(0, 'Ab', 'L1'), (1, 'Ab ', 'L1 '), (2, None, 'L1'),
                           (3, 'Ab', None), (4, 'Missing', 'Unknown'), (5, '', '')],
                'eco_A': [(10, 'b', 'L2'), (11, 'AB', 'l1')],
                'tech_btd': [(20, 'AB', 'l1'), (21, 'aB ', 'L1 '), (22, None, 'L1'), (23, 'Ab', None), (24, '', '')],
                'eco_btd': [(30, 'B ', 'l2'), (31, 'AB', 'L1')],
                'E': [(40, 'ab', 'L1'), (41, 'AB ', 'l1 '), (42, 'b', 'L2'), (43, None, 'L1'), (44, '', '')],
                'sla': [(50, 'ab ', 'l1'), (51, 'AB', 'L1 '), (52, 'b', 'L2'), (53, '', '')],
                'sa': [(60, 'AB', None), (61, 'ab ', None), (62, 'B', None), (63, None, None), (64, '', None)],
                'la': [(70, None, 'L1'), (71, None, 'l1 '), (72, None, 'L2'), (73, None, None), (74, None, '')],
                'B': [(80, 'AB', 'l1'), (81, 'ab ', 'L1 '), (82, 'b', 'L2'), (83, None, 'L1'), (84, '', '')],
            }
            names = {}
            with connection.cursor() as cursor:
                for index, (role, values) in enumerate(rows.items()):
                    name = 'btr_fixture_source_' + str(index)
                    names[service.SOURCES[role]] = name
                    cursor.execute('CREATE TEMP TABLE ' + name +
                        ' (vf_ordinal bigint,"SKUCode" text,"WhCode" text,"WHCode" text,"LocCode" text) ON COMMIT DROP')
                    cursor.executemany('INSERT INTO ' + name + ' VALUES (%s,%s,%s,%s,%s)',
                        [(ordinal, sku, location, location, location) for ordinal, sku, location in values])
                fields = ['generation_id uuid'] + ['"' + field + '" ' +
                    ('boolean' if field == 'export' else 'bigint' if field.endswith('_ordinal') else 'text')
                    for field in service.ROW_FIELDS]
                for name in ('btr_fixture_old', 'btr_fixture_new'):
                    cursor.execute('CREATE TEMP TABLE ' + name + ' (' + ','.join(fields) + ') ON COMMIT DROP')
            def query(run, path):
                return 'SELECT * FROM ' + names[path], []
            generation = SimpleNamespace(pk=uuid4())
            with patch.object(service, 'image_query', side_effect=query), patch.object(service, 'REF_TABLE', 'pg_temp.btr_fixture_new'):
                legacy_populate(None, generation, 'pg_temp.btr_fixture_old')
                service._populate(None, generation)
            def normalized(value):
                return None if value is None else value.rstrip(' ').lower()
            expected = []
            for branch in ('tech', 'eco'):
                for export in (False, True):
                    for a in rows[branch + '_A']:
                        bags = [{}]
                        for alias in service.ORDINALS:
                            if alias == 'A':
                                matches = [a]
                            elif export and alias == 'sla':
                                matches = [None]
                            else:
                                fields = (2,) if alias == 'la' else (1,) if alias == 'sa' else (1, 2)
                                population = rows[branch + '_btd' if alias == 'btd' else alias]
                                matches = [row for row in population if all(
                                    normalized(a[field]) is not None and normalized(a[field]) == normalized(row[field])
                                    for field in fields)] or [None]
                            bags = [dict(bag, **{alias: row}) for bag in bags for row in matches]
                        expected += [(branch, export, a[1], a[2], normalized(a[1]), normalized(a[2]),
                                      *(None if bag[alias] is None else bag[alias][0] for alias in service.ORDINALS))
                                     for bag in bags]
            actual = {}
            with connection.cursor() as cursor:
                for version in ('old', 'new'):
                    cursor.execute('SELECT ' + ','.join('"' + field + '"' for field in service.ROW_FIELDS) +
                                   ' FROM btr_fixture_' + version)
                    actual[version] = Counter(cursor.fetchall())
            self.assertGreater(len(expected), len(rows['tech_A']) + len(rows['eco_A']))
            self.assertEqual(actual['old'], Counter(expected))
            self.assertEqual(actual['new'], Counter(expected))
            self.assertTrue(any(row[2] == 'Ab ' and row[3] == 'L1 ' for row in actual['new']))
            self.assertTrue(all(row[9] is None for row in actual['new'] if row[1]))  # Export omits sla.
            transaction.set_rollback(True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_class WHERE relnamespace=pg_my_temp_schema() AND relname LIKE 'vf_btr_join_%'")
            self.assertEqual(cursor.fetchone()[0], 0)
