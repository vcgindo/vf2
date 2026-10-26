"""Mixed-owner Research contracts, with database access mocked explicitly."""
import json
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import MagicMock, patch

from tests.test_scoped_btr import fixture, Codes
from mta.presentation import scoped_research as owner, research_read as reader
from mta.presentation.context import PublicationUnavailable
from django.test import RequestFactory, override_settings


class ScopedResearchTests(unittest.TestCase):
    def setUp(self):
        self.btr = fixture()
        self.master = dict(table='BPR/vf_RationedReqReport', count=1,
            fields=[(name, name, 'str') for name in ('SKUCode', 'WhCode', 'ParentWhCode')])
        self.btr.sources.metadata = MagicMock(return_value=self.master)
        for path in owner.TRENDS:
            self.btr.images[path].update(count=4, fields=[(field, field,
                'int' if field in ('Age', 'BRAge') else 'str') for field in sorted(owner.REQUIRED[path])])
        self.bound = owner.ResearchBinding(self.btr)
        self.view = Obj(run_id=self.btr.run.pk, reference=Obj(metadata={
            'runtime_reports': {'schema':'fresh-registered-placement-read-configuration-v1'}}))

    def test_factory_preserves_authenticated_predecessor_and_current_master_owners(self):
        with patch.object(owner.scoped_btr, 'bind', return_value=self.btr) as bind:
            bound = owner.bind(self.view)
            bind.assert_called_once_with(self.view)
            self.assertEqual(bound.query(owner.MASTER)[1], ['CURRENT'])
            for path in owner.TRENDS:
                self.assertEqual(bound.query(path)[1], [self.btr.predecessor.pk, path])
            self.view.run_id = 'foreign'
            with self.assertRaisesRegex(PublicationUnavailable, 'run_differs'): owner.bind(self.view)
        with patch.object(owner.scoped_btr, 'bind', side_effect=PublicationUnavailable('missing-predecessor')):
            with self.assertRaisesRegex(PublicationUnavailable, 'missing-predecessor'): owner.bind(self.view)

    def test_missing_and_incomplete_sources_do_not_turn_into_empty_results(self):
        for change in ('missing', 'columns', 'nonempty-without-fields'):
            self.setUp(); path = owner.TRENDS[0]
            if change == 'missing': del self.btr.images[path]
            elif change == 'columns': self.btr.images[path]['fields'].pop()
            else: self.btr.images[path]['fields'] = []
            with self.subTest(change=change), patch.object(owner.scoped_btr, 'bind', return_value=self.btr), \
                    self.assertRaises(PublicationUnavailable): owner.bind(self.view)
        self.setUp()
        for path in owner.TRENDS: self.btr.images[path].update(count=0, fields=[])
        with patch.object(owner.scoped_btr, 'bind', return_value=self.btr), patch.object(reader.connection, 'cursor') as cursor:
            bound = owner.bind(self.view)
            self.assertEqual(reader.selected_rows(bound.run, owner.TRENDS[0], {('s', 'ch')}, read_binding=bound), [])
            cursor.assert_not_called()

    def test_selected_relation_uses_logical_aliases_and_exists_without_join_multiplication(self):
        self.master['fields'][0] = ('SKUCode', 'physical_sku', 'str')
        cursor = MagicMock(); cursor.__enter__.return_value = cursor
        cursor.fetchall.return_value = [('S', 'CH', 'P'), ('S', 'CH', 'P')]
        with patch.object(reader.connection, 'cursor', return_value=cursor):
            rows = reader.selected_rows(self.bound.run, owner.MASTER, {('s', 'ch')}, read_binding=self.bound)
        self.assertEqual(rows, [dict(SKUCode='S', WhCode='CH', ParentWhCode='P')]*2)
        sql, params = cursor.execute.call_args.args
        self.assertIn('WHERE EXISTS', sql)
        self.assertNotIn('physical_sku', sql)
        self.assertIn('A."SKUCode"', sql)
        self.assertEqual(params, ['s', 'ch', 'CURRENT'])

    def test_research_keeps_self_child_parent_nulls_and_distinct_union_from_old_trends(self):
        def trend(wh, parent):
            return dict(SKUCode='S', WhCode=wh, ParentWhCode=parent, Age=8, BRAge=None,
                        **{f'D{i}':'Red' if i==90 else 'Green' for i in range(1,91)})
        trends = [trend('CH', 'P'), trend('GRAND', 'CH'), trend('P', None), trend('CH', 'P')]
        population = {'SkuAttributeData':[{'SKUCode':'S'}], 'LocationAttributeData':[{'WHCode':'CH'}]}
        cursor = MagicMock(); cursor.__enter__.return_value = cursor
        master_rows = [('S', 'CH', 'P')]
        values = [[row[name] for name, _, _ in self.btr.images[owner.TRENDS[0]]['fields']] for row in trends]
        cursor.fetchall.side_effect = [master_rows, values, values]
        with patch.object(owner.scoped_btr.typed, 'load_image',
                side_effect=lambda _run, image: population[image['image'].rsplit('/',1)[1]]), \
                patch.object(reader.hierarchy, 'selected_manifest', return_value=None), \
                patch.object(reader, 'scope', return_value=(Codes(['S']), Codes(['CH']))), \
                patch('mta.presentation.history_prepared_sql.admitted', side_effect=AssertionError('Full admission')), \
                patch.object(reader.connection, 'cursor', return_value=cursor):
            result = reader.read_research(self.bound.run, {'data':[{'SKUCode':'S','WhCode':'CH'}]}, read_binding=self.bound)
        self.assertEqual(len(result), 6)
        self.assertEqual({(r['Type'],r['Pen']) for r in result},
                         {(kind,pen) for kind in ('Self','Child','Parent') for pen in ('Tech','Eco')})
        for row in result:
            self.assertEqual(row['Whcode'], 'CH'); self.assertEqual(row['Age'], 8)
            self.assertNotIn('BRAge', row)
            self.assertEqual(row['D90'], 'Red'); self.assertEqual(row['D1'], 'Green')
            if row['Type']=='Child': self.assertEqual(row['ChildCode'], 'GRAND')
            if row['Type']=='Parent': self.assertEqual(row['ParentWhCode'], 'P')
        calls = cursor.execute.call_args_list
        self.assertEqual(calls[0].args[1][-1], 'CURRENT')
        for call in calls[1:]:
            self.assertIn(self.btr.predecessor.pk, call.args[1])
            self.assertNotIn(self.btr.run.pk, call.args[1])
            self.assertEqual(call.args[1][:4], ['s','ch','s','p'])

    def test_availability_reuses_exact_bands_sql_and_permission_multiplicity(self):
        cursor = MagicMock(); cursor.__enter__.return_value = cursor
        cursor.fetchone.return_value = (2, 8, 0, 4, None, None)
        state = {'SkuAttributeData':[], 'LocationAttributeData':[]}
        with patch.object(reader, 'attributes', return_value=state), \
                patch.object(reader, 'scope', return_value=(Codes(['S']), Codes(['CH']))), \
                patch('mta.presentation.history_prepared_sql.admitted', side_effect=AssertionError('Full admission')), \
                patch.object(reader.connection, 'cursor', return_value=cursor):
            result = reader.read_historical_availability(self.bound.run, {}, read_binding=self.bound)
        self.assertEqual(result, [dict(availability_01_30=75, availability_31_60=100, availability_61_90=0)])
        sql, params = cursor.execute.call_args.args
        self.assertEqual(params.count(self.btr.predecessor.pk), 3)
        self.assertNotIn(self.btr.run.pk, params)
        self.assertEqual(params[-4:], ['S',2,'CH',2])
        self.assertEqual(sql.count('*P.column2*L.column2'), 6)
        self.assertEqual(sql.count(" IN ('Black')"), 90)
        self.assertNotIn('SkuLocAttributeData', sql)

    def test_denied_scope_and_hierarchy_supplement_do_not_invent_history(self):
        with patch.object(reader, 'attributes', return_value={}), \
                patch.object(reader, 'scope', return_value=(Codes(), Codes())), \
                patch.object(reader.connection, 'cursor') as cursor:
            result = reader.read_historical_availability(self.bound.run, {}, read_binding=self.bound)
            self.assertEqual(result, [dict(availability_01_30=0, availability_31_60=0, availability_61_90=0)])
            cursor.assert_not_called()
        with patch.object(owner.scoped_btr.typed, 'load_image', return_value=[]), \
                patch.object(reader.hierarchy, 'selected_manifest', return_value={'supplement':True}):
            with self.assertRaisesRegex(PublicationUnavailable, 'native_hierarchy_required'):
                reader.attributes(self.bound.run, read_binding=self.bound)

    @override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity', VF_MTA_PHASE_SELECTION_FILE='owned-selection')
    def test_original_routes_receive_bound_owner_and_keep_response_shape(self):
        from mta.presentation import views
        self.view.run = self.btr.run
        for function, method, implementation, value in (
                (views.research_insights, 'post', 'read_research', None),
                (views.historical_availability, 'get', 'read_historical_availability', [{'availability_01_30':0}])):
            request = getattr(RequestFactory(), method)('/api/mta/research-contract-test',
                **({'data':'{}', 'content_type':'application/json'} if method=='post' else {}),
                HTTP_X_VECTORFLOW_IDENTITY=json.dumps({'id':1,'name':'owned-user'}))
            with patch('mta.presentation.scoped_selection.selected', return_value=self.view), \
                    patch.object(owner, 'bind', return_value=self.bound), \
                    patch.object(reader, implementation, return_value=value) as read:
                response = function(request)
            self.assertEqual(response.status_code, 200)
            body = json.loads(response.content)
            self.assertEqual(body['data'], value); self.assertEqual(body['msg'], '')
            read.assert_called_once_with(self.btr.run, {}, read_binding=self.bound)
