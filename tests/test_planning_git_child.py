"""Corrected child route, distinct permissions and frozen location contract."""
import ast
import inspect
import json
import os
from decimal import Decimal
from types import SimpleNamespace as Obj
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'git-child-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.http import JsonResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from django.urls import resolve
from mta.presentation import planning_git_child as subject, planning_git_sql as original, planning_git_views as views
from mta.presentation.context import PublicationUnavailable


def item(name, value, operator='equalto'):
    return dict(attributeName=name, value=value, operator=operator)


class ChildGitTests(SimpleTestCase):
    def test_location_builder_is_frozen_except_obsolete_combined_child_refusal(self):
        expected = ast.parse(inspect.getsource(original.grid)).body[0]
        expected.name = 'location_grid'
        expected.body = [statement for statement in expected.body if not (
            isinstance(statement, ast.If) and any(isinstance(node, ast.Constant)
                and isinstance(node.value, str) and node.value.startswith('LEG-GIT-CHILD-TRANSPORTER-INVALID-SQL:')
                for node in ast.walk(statement)))]
        self.assertEqual(ast.dump(expected), ast.dump(ast.parse(inspect.getsource(subject.location_grid)).body[0]))

    def test_direct_ids_do_not_expand_roots_or_match_nulls_or_leading_spaces(self):
        records = [dict(id=1, level_1='A', level_2=None, level_3=None),
                   dict(id=2, level_1='A', level_2='B', level_3='C'),
                   dict(id=3, level_1='A', level_2='B', level_3='C')]
        catalogue = dict(products=dict(records=records), locations=dict(records=[
            dict(id=9, level_1='D', level_2='E', level_3='F')]))
        product = lambda code, first='A', third='C': dict(SKUCode=code, SL1=first, SL2='B', SL3=third)
        location = dict(WHCode='PARENT', LL1='D', LL2='E', LL3='F')
        attributes = dict(SkuAttributeData=[product('P1'), product('P1'), product('PAD','a '),
            product('LEADING',' A'), product('NULL',third=None)], LocationAttributeData=[location,dict(location)])
        with patch.object(subject, 'permission_catalogue', return_value=catalogue):
            products, locations = subject.direct_permissions(dict(product_permissions=[1], location_permissions=[9]), attributes)
            self.assertFalse(products)
            self.assertEqual(locations.multiplicities['PARENT'], 2)
            products, _ = subject.direct_permissions(dict(product_permissions=['2',2], location_permissions=[9]), attributes)
            self.assertEqual(products.multiplicities, {'P1':2,'PAD':1})
            products, _ = subject.direct_permissions(dict(product_permissions=[2,3], location_permissions=[9]), attributes)
            self.assertEqual(products.multiplicities['P1'], 4)

    def test_data_filter_uses_nms_hierarchy_and_retains_missing_ambiguous_owners(self):
        filters = subject.TransporterFilters({'filters': {'productFilter': {'filters':[item('p1','BUSINESS')]}}})
        self.assertIn('nms."SL1"', filters.compile())
        available = subject.TransporterFilters({'filters': {'productFilter': {'filters': []},
            'availabilityFilter': {'filters': [item('virtualnorm', '12')]}}})
        self.assertIn('vf."VirtualNorm"', available.compile())
        for spelling, field in [('git', 'GIT'), ('GIT', 'GIT'), ('stock', 'Stock'), ('STOCK', 'Stock')]:
            predicate = subject.TransporterFilters({'filters': {'availabilityFilter': {
                'filters': [item(spelling, '0', 'greaterthan')]}}})
            self.assertIn('vf."'+field+'"', predicate.compile())
        for spellings in (['Git'], ['Stock'], ['stock', 'Stock'], ['git', 'Git']):
            with self.subTest(spellings=spellings), self.assertRaises(PublicationUnavailable):
                subject.TransporterFilters({'filters': {'availabilityFilter': {
                    'filters': [item(spelling, '0', 'greaterthan') for spelling in spellings]}}}).compile()
        for group, row in (
            ('locationFilter', item('l1','ZONE')),
            ('supplyChainFilter', item('forlocation','DEPOT')),
            ('customAttributeFilter', item('skuattr1','X')),
            ('customAttributeFilter', item('skulocattr1','X')),
            ('availabilityFilter', item('norm','1'))):
            groups = {group:{'filters':[row]}, 'productFilter':{'filters':[]}}
            if group == 'productFilter': groups[group]={'filters':[row]}
            with self.subTest(group=group, row=row), self.assertRaises(PublicationUnavailable):
                subject.TransporterFilters({'filters':groups}).compile()
        valid = subject.TransporterFilters({'filters': {'productFilter': {'filters':[]},
            'customAttributeFilter':{'filters':[item('locattr1','X')]}}})
        self.assertIn('la."c1"', valid.compile())

    @override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity')
    def test_authentication_and_unchanged_parent_count_owners(self):
        for suffix in ('','Count'):
            match = resolve('/api/mta/GetPlanningDataGrid'+suffix)
            req = RequestFactory().post('/api/mta/GetPlanningDataGrid'+suffix, data='{}', content_type='application/json')
            self.assertEqual(match.func(req).status_code, 403)
        def retained(request, payload, *, count=False):
            return JsonResponse(dict(payload=payload, count=count))
        for count, kind in ((False,'parent'),(True,'child')):
            payload=dict(category='git',type=kind)
            req=RequestFactory().post('/api/mta/GetPlanningDataGrid',data=json.dumps(payload),
                content_type='application/json',HTTP_X_VECTORFLOW_IDENTITY='{"id":8}')
            with patch.object(views.views,'planning_grid',retained),patch.object(views,'selected_run') as selected:
                response=views.planning_grid(req,count=count)
            self.assertEqual(json.loads(response.content),dict(payload=payload,count=count))
            selected.assert_not_called()

    def test_scoped_dispatch_passes_its_own_binding_without_full_selection(self):
        from mta.presentation.scoped_api import _planning
        bound=Obj(run=Obj(pk='own-phase-run'),git=object())
        payload=dict(category='git',type='child',filters={})
        with patch.object(subject,'grid',return_value={'own':True}) as reader, \
                patch('mta.presentation.context.selected_run',side_effect=AssertionError('Full fallback')):
            response=_planning(bound,'planning_grid',payload)
        self.assertEqual(json.loads(response.content)['data'],{'own':True})
        reader.assert_called_once_with(bound.run,payload,count=False,read_binding=bound.git)

    def test_raw_cursor_jsonb_text_becomes_nested_numeric_rows(self):
        from django.db import connections
        names=('rn','tc','on','phy','_parent','_wh','_ambiguous_key','transit')
        for nested in ('[{"SKUCode":"P1","Price":7,"wt":1.25,"eoc":null}]',
                       [dict(SKUCode='P1',Price=7,wt=Decimal('1.25'),eoc=None)]):
            with patch.object(subject,'transporter_query',return_value=('SELECT 1',[])), \
                    patch.object(connections['default'],'cursor') as cursor:
                result=cursor.return_value.__enter__.return_value
                result.description=[(name,) for name in names]
                result.fetchall.return_value=[(1,'T','O',Decimal('20.9'),'P','D',False,nested)]
                rows=subject.transporter_grid(Obj(pk='own'),{},set(),set())
            self.assertEqual(rows,[dict(rn=1,tc='T',on='O',phy=20.9,
                transit=[dict(SKUCode='P1',Price=7,wt=1.25,eoc=None)])])

    def test_wrong_phase_owners_deny_before_any_full_source_lookup(self):
        from mta.presentation import daily_git_preparation
        run=Obj(pk='own')
        with patch.object(subject,'image_query',side_effect=AssertionError('Full query')):
            with self.assertRaises(PublicationUnavailable):
                subject.location_grid(run,dict(type='child'),read_binding=Obj())
            with patch.object(daily_git_preparation,'image_query',side_effect=AssertionError('Full source')):
                with self.assertRaises(PublicationUnavailable):
                    subject.transporter_query(run,{},set(),set(),read_binding=Obj(prepared=object()))
