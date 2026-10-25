"""Focused read-binding proofs; no database, service or selection mutation."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'scoped-logistics-unit-only')
import django
django.setup()
from contextlib import ExitStack
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from mta.presentation import logistics_read as reader, scoped_logistics as scoped
from mta.presentation.context import PublicationUnavailable
from mta.presentation.permissions import PermissionCodes
from mta.presentation.scoped_view import ViewBinding


class ScopedLogisticsTests(unittest.TestCase):
    def view(self):
        sources = NS(run=NS(pk='run'), source_digest='sources', acceptance_id='phase',
                     acceptance_digest='phase-digest', snapshot_digest='snapshot')
        transit = Mock()
        transit.provenance.return_value = {'generation_id': 'transit'}
        transit.image_query.side_effect = lambda path: ('SELECT * FROM owned_transit', ['transit', path])
        transit.rows.return_value = [dict(OrderNo='Order', SKUCode='SKU', WhCode='WH')]
        bpr = NS(sources=sources, reports=NS(generation=NS(pk='report')), transit=transit)
        bpr.image_query = lambda path: ('SELECT * FROM owned_image', ['phase', path])
        requests = Mock()
        requests.query.return_value = ('SELECT * FROM captured_request', ['capture'])
        expedite = NS(sources=sources, core=NS(prepared=bpr), transit=transit, requests=requests,
                      attributes=lambda: {'SkuAttributeData': [], 'LocationAttributeData': []},
                      fact_query=lambda name: ('SELECT * FROM owned_fact', ['report', name]))
        return ViewBinding(NS(), bpr, None, None, expedite)

    def read_context(self, view):
        stack = ExitStack()
        stack.enter_context(patch.object(scoped, 'require_binding', side_effect=lambda run, bound: bound))
        stack.enter_context(patch.object(reader, 'scope', return_value=(PermissionCodes({'SKU': 2}), PermissionCodes({'WH': 3}))))
        for function in ('image_query', 'image_rows', '_projected_attributes', '_dispatch_relation', '_transit_relation'):
            stack.enter_context(patch.object(reader, function, side_effect=AssertionError('Full source reached')))
        for function in ('current_requests', 'history_owner', 'transit_rows'):
            stack.enter_context(patch.object(reader.logistics_live, function, side_effect=AssertionError('live owner reached')))
        return stack

    def test_grid_count_and_contacts_use_owned_sources_and_keep_shape(self):
        view = self.view()
        retained = dict(RN=1, OrderNo='Order', Qty=4, Action=None,
                        DispatchDate=datetime(2026, 10, 18, tzinfo=timezone.utc),
                        skuDetails=[dict(SKUCode='SKU', InTransitQty=4)])
        with self.read_context(view), patch.object(reader, '_fetch', return_value=[retained]) as fetch:
            rows = reader.transit_grid(view.run, {}, read_binding=view)
            self.assertEqual(rows, [dict(RN=1, OrderNo='Order', Qty=4, DispatchDate='2026-10-18T00:00:00',
                                       skuDetails=[dict(SKUCode='SKU', InTransitQty=4)])])
            sql, params = fetch.call_args.args
            self.assertIn('LEFT JOIN B', sql)
            self.assertIn('generate_series(1,P.weight*L.weight)', sql)
            self.assertIn(2, params); self.assertIn(3, params)
            fetch.return_value = [dict(n=6)]
            self.assertEqual(reader.transit_grid(view.run, {}, count=True, read_binding=view), 6)
            fetch.return_value = [dict(SKUCode='SKU', WhCode='WH', TransporterName='Carrier', TransporterContact=None)]
            self.assertEqual(reader.contacts(view.run, {'orderNo': 'Order'}, read_binding=view),
                             [dict(TransporterName='Carrier')])

    def test_owned_empty_requests_keeps_configuration_and_missing_owner_fails(self):
        view = self.view()
        with self.read_context(view), patch.object(reader, '_fetch', return_value=[]) as fetch:
            result = reader.open_requests(view.run, {}, read_binding=view)
            self.assertEqual(result['data'], [])
            self.assertEqual(len(result['uiConfig']), 9)
            view.expedite.requests.verify_rows.assert_called_once()
            self.assertIn('captured_request', fetch.call_args.args[0])
            self.assertIn('owned_fact', fetch.call_args.args[0])
            view.expedite.requests.verify_rows.side_effect = PublicationUnavailable('missing')
            with self.assertRaises(PublicationUnavailable):
                reader.open_requests(view.run, {}, read_binding=view)

    def test_order_scope_denies_hidden_sibling_and_null_target(self):
        view = self.view()
        with self.read_context(view):
            for denied in (dict(SKUCode='other', WhCode='WH'), dict(SKUCode=None, WhCode='WH')):
                view.bpr.transit.rows.return_value = [dict(OrderNo='Order', SKUCode='SKU', WhCode='WH'),
                                                     dict(OrderNo='Order', **denied)]
                with self.assertRaises(reader.TargetDenied):
                    reader.contacts(view.run, {'orderNo': 'Order'}, read_binding=view)

    def test_binding_rejects_wrong_run_transit_and_live_overlay(self):
        view = self.view()
        with patch('mta.presentation.scoped_expedite.require_binding', return_value=view.expedite), \
                patch.object(reader.logistics_live, 'enabled', return_value=False):
            self.assertIs(scoped.require_binding(view.run, view), view)
            with self.assertRaises(PublicationUnavailable): scoped.require_binding(NS(pk='other'), view)
            view.bpr.transit = None
            with self.assertRaises(PublicationUnavailable): scoped.require_binding(view.run, view)
        view = self.view()
        with patch('mta.presentation.scoped_expedite.require_binding', return_value=view.expedite), \
                patch.object(reader.logistics_live, 'enabled', return_value=True), \
                patch('mta.runtime.models.TransitLiveGeneration.objects.filter') as query:
            query.return_value.exists.return_value = True
            with self.assertRaises(PublicationUnavailable): scoped.require_binding(view.run, view)

    def test_history_empty_requires_exact_manifest_image_and_preserves_dates(self):
        view = self.view()
        name = 'OpenExpeditRequestRemarksHistory'
        table = 'complete/BPR/' + name
        image = 'phase/BPR/complete/' + name
        physical = 'phase/PRE_BPR/complete/' + name
        from mta.runtime import phase_state
        item = dict(image=physical, table=table, count=0, digest='0'*64, fields=[])
        manifest = dict(state=dict(complete={name: dict(image=image)}), images={image:item})
        phase = NS(snapshot=NS(state_digest='snapshot', manifest=manifest))
        with patch.object(scoped, 'require_binding', return_value=view), \
                patch('mta.presentation.scoped_sources._accepted_phase', return_value=phase), \
                patch.object(scoped, 'load_image', return_value=[]) as load:
            sql, params = scoped.history_query(view.run, view, name)
            self.assertEqual(params, ['run', physical])
            self.assertIn('"RemarkDate" AT TIME ZONE \'UTC\'', sql)
            load.assert_called_once_with(view.run, item, table_registry=phase_state.REGISTRY)
            del manifest['state']['complete'][name]
            with self.assertRaises(PublicationUnavailable): scoped.history_query(view.run, view, name)
            manifest['state']['complete'][name] = dict(image=image)
            item['image'] = 'phase/PRE_BPR/complete/unrelated'
            with self.assertRaises(PublicationUnavailable): scoped.history_query(view.run, view, name)
            item['image'] = physical
            item['table'] = 'complete/BPR/InTransitWhereAboutsRemarks'
            with self.assertRaises(PublicationUnavailable): scoped.history_query(view.run, view, name)

    def test_default_full_path_remains_default(self):
        with patch.object(reader, '_relation', return_value=(['A AS (SELECT 1)'], [], ' FROM A')) as relation, \
                patch.object(reader, '_fetch', return_value=[dict(n=2)]):
            self.assertEqual(reader.transit_grid('Full', {}, count=True), 2)
            relation.assert_called_once_with('Full', {}, transit=True, read_binding=None)

    def test_nonempty_inherited_history_uses_native_columns_without_null_defaults(self):
        view = self.view()
        name = 'InTransitWhereAboutsRemarks'
        table = 'complete/BPR/' + name
        logical = 'phase/BPR/complete/' + name
        physical = 'phase/PRE_BPR/complete/' + name
        from mta.runtime import phase_state
        fields = [(field, field, 'int' if kind == 'int' else 'str')
                  for field, kind in phase_state.REGISTRY[table]]
        item = dict(image=physical, table=table, count=1, digest='0'*64, fields=fields)
        phase = NS(snapshot=NS(state_digest='snapshot', manifest=dict(
            state=dict(complete={name: dict(image=logical)}), images={logical: item})))
        with patch.object(scoped, 'require_binding', return_value=view), \
                patch('mta.presentation.scoped_sources._accepted_phase', return_value=phase), \
                patch.object(scoped, 'load_image', return_value=[dict(ETA=None, Remarks=None)]) as load:
            sql, params = scoped.history_query(view.run, view, name)
            self.assertEqual(params, ['run', physical])
            self.assertIn('"ETA" AS "ETA"', sql)
            self.assertIn('"UserId" AS "UserId"', sql)
            self.assertIn('"RemarksDate" AT TIME ZONE \'UTC\' AS "RemarksDate"', sql)
            self.assertNotIn('COALESCE', sql)
            load.assert_called_once_with(view.run, item, table_registry=phase_state.REGISTRY)
