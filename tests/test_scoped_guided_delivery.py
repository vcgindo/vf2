"""All eleven Guided routes share phase-bound freshness and the existing cache."""
from copy import deepcopy
from datetime import date
import json
from types import SimpleNamespace as Obj
import unittest
from unittest.mock import MagicMock, patch

from tests.test_scoped_btr import fixture
from django.test import RequestFactory, override_settings
from mta.presentation import scoped_guided as subject, report_cache, views
from mta.presentation.context import PublicationUnavailable


def bundle():
    run=Obj(pk='current-run',business_date=date(2026,10,26))
    parent=Obj(pk='parent-run')
    generation=Obj(pk='current-excess',digest='e'*64)
    view=Obj(run=run,reference=Obj(metadata={}),read_identity=dict(id='reference',digest='a'*64),action_revision=0,
        bpr=Obj(read_identity=dict(generation='current-report',remark_highwater=0),reports=Obj(generation=generation)))
    suggestions=Obj(btr=Obj(predecessor=parent),images={'suggestions':{'digest':'b'*64}},
        context=Obj(dbm={'DBMMaster':[dict(SKUCode='S',Norm=12)]}),attributes=MagicMock(return_value={}))
    chronic={kind:Obj(images={kind:{'digest':'c'*64}}) for kind in subject.scoped_guided_chronic.KINDS}
    availability=Obj(btr=Obj(predecessor=parent),aggregate=None,receipt=Obj(source_digest='s'*64,schema_digest='r'*64,
        rows_digest='d'*64,row_count=3,reference_count=1))
    excess=Obj(history=dict(root_date='2026-10-23',digest='f'*64,lineage=['own-parent']))
    return subject.GuidedBinding(view,suggestions,chronic,availability,excess)


class ScopedGuidedDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.bound=bundle()
        self.catalogue={'products':{'records':[{'id':1}]},'locations':{'records':[{'id':2}]}}
        self.payload=dict(product_permissions=[1],location_permissions=[2])
        self.actor={'id':3,'name':'owned-user'}

    def identity(self,bound=None,payload=None,actor=None):
        return report_cache.read_identity((bound or self.bound).run,payload or self.payload,actor or self.actor,
            read_binding=bound or self.bound)

    def test_identity_tracks_every_mutable_cut_and_live_actor_permission_partition(self):
        with patch.object(subject,'permission_catalogue',return_value=self.catalogue), \
                patch('mta.presentation.registered_report_view.recipe_digest',return_value='recipe'), \
                patch.object(report_cache,'reader_recipe',return_value='reader'):
            original=self.identity()
            mutations=(
                lambda b:b.view.read_identity.update(digest='new-reference'),
                lambda b:setattr(b.view,'action_revision',4),
                lambda b:b.view.bpr.read_identity.update(remark_highwater=1),
                lambda b:b.suggestions.context.dbm['DBMMaster'][0].update(Norm=8),
                lambda b:b.suggestions.images['suggestions'].update(digest='new-image'),
                lambda b:b.chronic['chronic-grid'].images['chronic-grid'].update(digest='new-chronic'),
                lambda b:setattr(b.availability.receipt,'rows_digest','new-history'),
                lambda b:setattr(b.availability,'aggregate',dict(rows='new-rollup',members='scope-members')),
                lambda b:b.excess.history.update(digest='new-lineage'),
                lambda b:setattr(b.view.bpr.reports.generation,'digest','new-excess'))
            for mutate in mutations:
                bound=deepcopy(self.bound);mutate(bound)
                self.assertNotEqual(self.identity(bound),original)
            self.assertNotEqual(self.identity(payload=dict(self.payload,product_permissions=[])),original)
            self.assertNotEqual(self.identity(actor=dict(self.actor,id=4)),original)
            self.catalogue['products']['records'][0]['level_1']='changed'
            self.assertNotEqual(self.identity(),original)
            for invalid in ([True],['bad'],[99]):
                with self.assertRaises((ValueError,PublicationUnavailable)):
                    self.identity(payload=dict(self.payload,product_permissions=invalid))

    def test_all_eleven_response_shapes_and_explicit_reader_binding(self):
        with patch('mta.presentation.guided_dbm.read_guided_dbm',return_value=[]) as suggestions, \
                patch('mta.presentation.guided_chronic.read_guided_chronic',return_value=[]) as grid, \
                patch('mta.presentation.chronic_sql.read_chronic',return_value=[]) as charts, \
                patch('mta.presentation.insight_history_sql.read_history',return_value=[]) as history:
            self.assertEqual(len(subject.KINDS),11)
            for kind in subject.KINDS:
                response=self.bound.response({},kind)
                body=json.loads(response.content)
                self.assertEqual(body['status'],200)
                self.assertEqual(body['data'],[] if kind in ('chronic-loc','chronic-sku') else None)
            self.assertEqual(suggestions.call_count,4)
            self.assertIs(suggestions.call_args.kwargs['read_binding'],self.bound.suggestions)
            self.assertEqual(grid.call_count,1)
            self.assertEqual(charts.call_count,2)
            self.assertEqual(history.call_count,4)
            with self.assertRaises(ValueError):self.bound.response({},'unknown')
            history.side_effect=OverflowError('canonical limit')
            self.assertEqual(json.loads(self.bound.response({},'excess-value').content)['status'],500)
            with self.assertRaises(OverflowError):self.bound.response({},'availability-trend')

    @override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity',VF_MTA_PHASE_SELECTION_FILE='owned-selection')
    def test_existing_routes_use_one_cache_and_revalidate_before_hits(self):
        cache=report_cache.ReportReadCache()
        calls=[]
        def response(payload,kind):
            calls.append(kind)
            return views.envelope(data=[{'kind':kind}])
        def request(payload):
            return RequestFactory().post('/api/mta/AvailabilityTrend',data=json.dumps(payload),content_type='application/json',
                HTTP_X_VECTORFLOW_IDENTITY=json.dumps(self.actor))
        with patch('mta.presentation.scoped_selection.selected',return_value=self.bound.view), \
                patch.object(subject,'bind',return_value=self.bound) as bind, \
                patch.object(subject,'permission_catalogue',return_value=self.catalogue), \
                patch('mta.presentation.registered_report_view.recipe_digest',return_value='recipe'), \
                patch.object(report_cache,'reader_recipe',return_value='reader'), \
                patch.object(report_cache,'cache',cache), \
                patch.object(subject.GuidedBinding,'response',side_effect=response), \
                patch('mta.presentation.context.selected_run',side_effect=AssertionError('Full selector')):
            identity_response=views.report_read_identity(request(self.payload))
            token=json.loads(identity_response.content)['data']['identity']
            payload=dict(self.payload,_report_read_identity=token)
            for kind in sorted(subject.KINDS):
                for _ in range(2):
                    result=views.insight_data(request(payload),kind=kind)
                    self.assertEqual(result.status_code,200)
                    self.assertEqual(json.loads(result.content)['data'],[{'kind':kind}])
                    if kind.startswith('excess-'):
                        self.assertEqual(result['X-VectorFLOW-History-Known-From'],'2026-10-23')
                        self.assertEqual(result['X-VectorFLOW-History-Before-Root'],'unknown')
            self.assertEqual(len(calls),11)
            self.assertEqual(bind.call_count,23)  # identity + every read, including hits
            self.bound.view.action_revision=1
            stale=views.insight_data(request(payload),kind='availability-trend')
            self.assertEqual(stale.status_code,409)
            self.assertEqual(len(calls),11)
            fresh=views.insight_data(request(self.payload),kind='availability-trend')
            self.assertEqual(fresh.status_code,200);self.assertEqual(len(calls),12)
            bind.side_effect=PublicationUnavailable('source no longer available')
            refused=views.insight_data(request(self.payload),kind='availability-trend')
            self.assertEqual(refused.status_code,503);self.assertEqual(len(calls),12)

    @override_settings(MTA_TRUSTED_GATEWAY_HEADER='X-VectorFLOW-Identity',VF_MTA_PHASE_SELECTION_FILE='owned-selection',
                       VF_MTA_GUIDED_EXCESS_DISPOSITION='existing-disposition')
    def test_configured_excess_denial_is_preserved_before_cache(self):
        request=RequestFactory().post('/api/mta/ExcessInventoryValue',data='{}',content_type='application/json',
            HTTP_X_VECTORFLOW_IDENTITY=json.dumps(self.actor))
        with patch('mta.presentation.scoped_selection.selected',return_value=self.bound.view), \
                patch.object(subject,'bind',return_value=self.bound), \
                patch('mta.presentation.daily_history_disposition.guard',side_effect=PublicationUnavailable('configured-denial')) as guard, \
                patch.object(report_cache,'cached_response') as cache:
            response=views.insight_data(request,kind='excess-value')
            self.assertEqual(response.status_code,503)
            guard.assert_called_once_with(self.bound.run,'excess-value')
            cache.assert_not_called()
