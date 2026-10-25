"""Existing DBM grid/count wire on the selected BPR component, not native UI."""
from copy import deepcopy
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_scoped_api_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class ScopedDbmApiTests(unittest.TestCase):
    for name in ('setUp', 'rollback', 'owner', 'accept', 'bpr', 'parents', 'fetch', 'positive',
                 'start', 'scopes', 'reads', 'prepare_dbm', 'finish', 'publication_opening',
                 'prepare', 'binding', 'no_build', 'selected'):
        locals()[name] = getattr(fixtures.ScopedApiTests, name)
    row = staticmethod(fixtures.ScopedApiTests.row)

    def select_suggestions(self):
        from tests import test_h3_daily_integration as supplied
        from tests.production_h3_fixture import SEASON, CHILD
        opening = supplied.frame()
        rows = [dict(SKUCode=SEASON, WhCode=CHILD, Type=1, NewNorm=24),
                dict(SKUCode=SEASON, WhCode=CHILD, Type=None, NewNorm=None)]
        opening['opening']['state']['dbm']['Suggestions'] = deepcopy(rows)
        opening['opening']['state']['controls']['suggestions'] = deepcopy(rows)
        # Explicit initial reference configuration, before capture/calculation.
        opening['opening']['state']['dbm']['ReasonCodes'] = [dict(Id=1, Reason='Declared component Rule 1')]
        with patch.object(supplied, 'frame', return_value=opening):
            self.selected()
        self.action_pair = [SEASON, CHILD]

    def http(self, payload=None, *, count=False, authenticated=True):
        from django.test import RequestFactory
        from mta.presentation import views
        headers = {'HTTP_X_VECTORFLOW_IDENTITY': json.dumps(dict(id='component-reader'))} if authenticated else {}
        request = RequestFactory().post('/api/' + ('DBMDataCount' if count else 'DBMData'),
            data=json.dumps(self.payload if payload is None else payload),
            content_type='application/json', **headers)
        response = views.dbm_data(request, count=count)
        status, result = response.status_code, json.loads(response.content)
        response.close()
        return status, result

    def expected(self):
        from mta.runtime.scoped_actions import restore, state_after
        from mta.presentation.scoped_dbm import ATTRIBUTES
        phase, _ = restore(self.run, self.receipt)
        state = state_after(self.run, self.receipt, phase, expected_revision=0)
        state['ReasonCodes'] = deepcopy(phase.context.prior['dbm']['ReasonCodes'])
        state.update({name: deepcopy(phase.importer[name]) for name in ATTRIBUTES})
        for row in state['SkuLocAttributeData']:
            if row['NonNMS'] is not None:
                row['NonNMS'] = bool(row['NonNMS'])
        return SimpleNamespace(run=self.run, business_date=self.run.business_date, dbm=state)

    def test_grid_count_paging_filters_scopes_and_wire_equal_canonical_consumer(self):
        from mta.presentation import views
        from django.db import connection
        self.select_suggestions()
        expected = views.dbm_filtered(self.expected(), self.payload)
        self.assertTrue(expected)
        expected_wire = views.scalar_json_rows([{k: v for k, v in row.items() if v is not None} for row in expected])
        before = list(self.run.phase_acceptances.values_list('id', 'digest'))
        def readonly(execute, sql, params, many, context):
            self.assertEqual(sql.lstrip().split(None, 1)[0].upper(), 'SELECT')
            return execute(sql, params, many, context)
        with self.no_build(), connection.execute_wrapper(readonly), \
                patch('mta.runtime.scoped_actions.restore', side_effect=AssertionError('UI restore')), \
                patch('mta.runtime.phase_state.read', side_effect=AssertionError('UI phase reconstruction')):
            status, grid = self.http()
            self.assertEqual(status, 200)
            self.assertEqual(grid['data'], expected_wire[:2])
            status, count = self.http(count=True)
            self.assertEqual((status, count['recordCount']), (200, str(len(expected))))
            body = dict(self.payload, paginationParameter=dict(pageNumber=2, recordsPerPage=1))
            self.assertEqual(self.http(body)[1]['data'], expected_wire[1:2] or None)
            body = dict(self.payload, filters=dict(productFilter=dict(filters=[
                dict(attributeName='sku', value='NOT-A-SUPPLIED-SKU')])))
            self.assertIsNone(self.http(body)[1]['data'])
            body = dict(self.payload, product_permissions=[])
            self.assertIsNone(self.http(body)[1]['data'])
            self.assertEqual(self.http(body, count=True)[1]['recordCount'], '0')
            self.assertEqual(self.http(authenticated=False)[0], 403)
        self.assertEqual(list(self.run.phase_acceptances.values_list('id', 'digest')), before)
        self.assertFalse(self.run.commands.exists())

    def test_action_cut_requires_new_read_reference_then_grid_uses_current_acceptance(self):
        from mta.runtime import scoped_actions
        from mta.runtime.scope_execution import _setting, _close_attempt
        self.select_suggestions()
        self.assertTrue(self.http()[1]['data'])
        with _setting('fresh.scope_worker', self.attempt.worker_token):
            _close_attempt(self.attempt, self.run, 'RELEASED', {})
        event = scoped_actions.record(self.run.pk, phase_id=self.receipt.pk,
            phase_digest=self.receipt.digest, expected_revision=0, operation='APPLY',
            selected=[self.action_pair], timestamp='2037-04-10T10:00:00', actor='component-reader',
            idempotency_key='dbm-grid-current-apply')
        self.assertEqual(self.http()[0], 503)
        fresh = self.prepare(revision=event.pk)
        self.assertNotEqual(fresh.read_identity, self.view.read_identity)
        self.assertEqual(self.http()[0], 200)
        self.assertIsNone(self.http()[1]['data'])
        self.assertEqual(self.http(count=True)[1]['recordCount'], '0')
