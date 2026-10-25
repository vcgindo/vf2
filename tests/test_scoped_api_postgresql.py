"""Owned component HTTP integration; native source admission stays mandatory."""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests import test_scoped_view_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class ScopedApiTests(unittest.TestCase):
    for name in ('setUp', 'rollback', 'accept', 'bpr', 'parents', 'fetch', 'positive', 'start',
                 'scopes', 'reads', 'prepare_dbm', 'finish', 'publication_opening', 'prepare', 'binding', 'no_build'):
        locals()[name] = getattr(fixtures.ScopedViewTests, name)
    row = staticmethod(fixtures.ScopedViewTests.row)

    def owner(self, **options):
        # Declared first-known dimension metadata for this small component,
        # before calculation/capture. No retained inputs/results are modified.
        from tests import test_h3_daily_integration as supplied
        original = supplied.frame
        def frame(*args, **kwargs):
            value = original(*args, **kwargs)
            for state in value['opening']['state'].values():
                if not isinstance(state, dict): continue
                for table, prefix in (('SkuAttributeData', 'SL'), ('LocationAttributeData', 'LL')):
                    for row in state.get(table, []):
                        row.update({prefix + str(i): 'Component hierarchy ' + str(i) for i in (1, 2, 3)})
            return value
        with patch.object(supplied, 'frame', side_effect=frame): fixtures.ScopedViewTests.owner(self, **options)

    def selected(self):
        from django.core.signals import request_finished
        from django.db import close_old_connections
        from django.test import override_settings
        from mta.presentation import scoped_selection as selection
        # RequestFactory responses still emit request_finished on close. That
        # receiver would close this fixture's outer rollback transaction. Keep
        # response/file/cursor closing real while isolating only that receiver.
        if request_finished.disconnect(close_old_connections):
            self.addCleanup(lambda: request_finished.connect(close_old_connections))
        self.start(); self.view = self.prepare()
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.selection_path = Path(directory.name) / 'selection.json'
        catalogue_path = Path(directory.name) / 'permissions.json'
        catalogue = dict(version='block1-permissions-v1', **{kind: dict(records=[dict(id=1,
            **{'level_' + str(i): 'Component hierarchy ' + str(i) for i in (1, 2, 3)})]) for kind in ('products', 'locations')})
        raw = json.dumps(catalogue).encode(); catalogue_path.write_bytes(raw)
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(override_settings(VF_MTA_PERMISSIONS_FILE=str(catalogue_path),
            VF_MTA_PERMISSIONS_SHA256=hashlib.sha256(raw).hexdigest(), VF_MTA_SELECTION_FILE='',
            VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST='', VF_MTA_NATIVE_PUBLICATION=True,
            VF_MTA_DAILY_PUBLICATION=True, VF_MTA_PHASE_SELECTION_FILE=str(self.selection_path)))
        self.real_native = selection.native_identity
        stack.enter_context(patch.object(selection, 'native_identity', return_value={'component_only': 'not-native-acceptance'}))
        self.anchor = selection.candidate(self.view); selection.write(self.selection_path, self.anchor)
        stack.enter_context(override_settings(VF_MTA_PHASE_SELECTION=self.anchor))
        self.payload = dict(product_permissions=[1], location_permissions=[1],
            paginationParameter=dict(pageNumber=1, recordsPerPage=2))

    def http(self, name, payload=None, *, authenticated=True, **kwargs):
        from time import perf_counter
        from django.test import RequestFactory
        from mta.presentation import views
        paths = dict(planning_overview='GetPlanningDataCount', planning_grid='GetPlanningDataGrid',
            planning_custom='GetPlanningDataCustom', planning_graph='GetPlanningDataGraph', rrr_data='RRRData',
            bpr_data='GetBPRData', export_data='GetExportDataAsync', last_run_date='GetLastRunDate')
        body = self.payload if payload is None else payload
        request = RequestFactory().generic('GET' if name == 'last_run_date' else 'POST',
            '/api/' + paths.get(name, name), data=json.dumps(body), content_type='application/json',
            **({'HTTP_X_VECTORFLOW_IDENTITY': json.dumps(dict(id='component-reader'))} if authenticated else {}))
        started = perf_counter()
        response = getattr(views, name)(request, **kwargs)
        print(json.dumps(dict(component_http=name,category=body.get('category'),count=kwargs.get('count',False),
            status=response.status_code,seconds=round(perf_counter()-started,3))),flush=True)
        return response

    def test_real_permissions_overview_matches_independent_ten_legacy_counts_and_http(self):
        from mta.presentation import scoped_overview, planning_overview
        from mta.presentation.context import scope
        self.selected(); view = self.view; sources = view.bpr.sources
        names = ('SkuAttributeData', 'LocationAttributeData', 'SkuLocAttributeData', 'SKUDescriptionTbl', 'SiteDescriptionTbl')
        attrs = {name: sources.rows('closing/importer/' + name) for name in names}
        products, locations = scope(self.payload, attributes=attrs)
        self.assertTrue(products); self.assertTrue(locations)
        reports = dict(git=sources.rows('reports/bpr/vf_RationedReqReport'),
            transporter=view.bpr.transit.rows('GoodsInTransitTransporterMaster'), transit=view.bpr.transit.rows('InTransitData'),
            expedite=view.bpr.reports.rows('ExpediteDispatches'), excess=view.bpr.reports.rows('ExcessInventoryDetails'),
            fulfillment=view.bpr.reports.rows('OrderFulfillmentSummary'))
        expected = planning_overview.counts(attrs, sources.rows('closing/dbm/SKULocStandardAttributes'), reports,
            view.run.business_date, products=products, locations=locations)
        with self.no_build(), patch('mta.presentation.context.configured_run', side_effect=AssertionError('Full selected')):
            actual, date = scoped_overview.read(view, self.payload)
            response = self.http('planning_overview')
        self.assertEqual(actual, expected)
        self.assertEqual(response.status_code, 200, response.content)
        value = json.loads(response.content); self.assertEqual(value['data'], expected); self.assertEqual(value['businessDate'], date)
        self.assertEqual(self.http('planning_overview', authenticated=False).status_code, 403)
        denied = dict(self.payload, product_permissions=[])
        zeros = json.loads(self.http('planning_overview', denied).content)['data']
        self.assertTrue(all(v == '0' for row in zeros for k, v in row.items() if k != 'category'))

    def test_one_request_binding_current_remark_refresh_missing_and_changed_anchor(self):
        from mta.presentation import scoped_selection as selection, scoped_view, ancillary_live
        from mta.presentation.request_scope import read_request
        from mta.presentation.context import PublicationUnavailable
        self.selected()
        with read_request('/api/GetPlanningDataCount'), self.no_build():
            old = selection.selected()
            value = self.row('new selected prefix', datetime(2037, 4, 11, tzinfo=timezone.utc))
            ancillary_live.append(ancillary_live.BPR, [{k: v for k, v in value.items() if k != 'RemarkDate'}],
                actor_id='selected-component', timestamp=value['RemarkDate'])
            self.assertIs(selection.selected(), old)
        with self.assertRaises(PublicationUnavailable): selection.selected()
        fresh = scoped_view.refresh_parent(old.reference.pk, expected_digest=old.reference.digest)
        with self.no_build(): self.assertEqual(selection.selected().read_identity, fresh.read_identity)
        selection.write(self.selection_path, dict(self.anchor, selection_digest=self.anchor['selection_digest']))
        self.assertEqual(selection.selected().read_identity, fresh.read_identity)
        from mta.serialization import digest
        changed = dict(self.anchor, business_date='2037-04-11')
        changed['selection_digest'] = digest({k: v for k, v in changed.items() if k != 'selection_digest'})
        selection.write(self.selection_path, changed)
        with self.assertRaisesRegex(PublicationUnavailable, 'changed_restart_required'): selection.selected()
        self.selection_path.write_text('{}')
        with self.assertRaises(PublicationUnavailable): selection.selected()

    def test_ambiguous_reference_and_concurrently_changed_cut_deny(self):
        from mta.presentation import scoped_selection as selection
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import ScopeReadReference
        self.selected()
        with patch.object(ScopeReadReference.objects, 'filter') as candidates:
            candidates.return_value.__getitem__.return_value = [self.view.reference, self.view.reference]
            with self.assertRaisesRegex(PublicationUnavailable, 'missing_or_ambiguous'): selection.selected()
        cut = selection._cut(self.run.pk)
        with patch.object(selection, '_cut', side_effect=[cut, (cut[0], cut[1] + 1)]):
            with self.assertRaisesRegex(PublicationUnavailable, 'current_reference_changed'): selection.selected()

    def test_http_existing_bpr_rrr_and_all_planning_read_families(self):
        self.selected()
        with self.no_build(), patch('mta.presentation.views.selected_run', side_effect=AssertionError('Full selected')):
            for family in ('excessInventory', 'orderFulfillment', 'git', 'expedite'):
                for name in ('planning_grid', 'planning_custom', 'planning_graph'):
                    payload = dict(self.payload, category=family, type='child' if family == 'git' and name == 'planning_graph' else 'parent')
                    if name == 'planning_graph' and family in ('excessInventory', 'orderFulfillment'): payload['type'] = 'sku'
                    response = self.http(name, payload)
                    self.assertEqual(response.status_code, 200, (family, name, response.content))
                response = self.http('planning_grid', dict(self.payload, category=family, type='child'), count=True)
                self.assertEqual(response.status_code, 200, (family, response.content))
            for name in ('bpr_data', 'rrr_data'):
                for count in (False, True):
                    response = self.http(name, count=count)
                    self.assertEqual(response.status_code, 200, (name, count, response.content))
            response = self.http('last_run_date')
            self.assertEqual(json.loads(response.content)['data'][0]['rawDate'], self.view.run.business_date.isoformat())
            invalid = self.http('planning_grid', dict(self.payload, category='git', type='child'))
            self.assertEqual(invalid.status_code, 503)
            self.assertIn(b'LEG-GIT-CHILD-TRANSPORTER-INVALID-SQL', invalid.content)
            denied = self.http('dbm_action', operation='APPLY')
            self.assertEqual(denied.status_code, 503)
        with patch('mta.presentation.views.ui_state.get_layout', return_value=None):
            for report in ('BPR', 'RRR'):
                response = self.http('export_data', dict(self.payload, reportName=report))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(b''.join(response.streaming_content))
                response.close()

    def test_component_is_denied_by_real_native_identity_and_full_mode_conflicts(self):
        from django.test import override_settings
        from mta.presentation import scoped_selection as selection
        from mta.presentation.context import PublicationUnavailable
        self.selected()
        with self.assertRaises(PublicationUnavailable): self.real_native(self.view)
        with patch.object(selection, 'native_identity', side_effect=self.real_native):
            response = self.http('planning_overview')
            self.assertEqual(response.status_code, 503)
        with override_settings(VF_MTA_SELECTION_FILE='full.json'):
            with self.assertRaisesRegex(PublicationUnavailable, 'full_selection_conflict'): selection.selected()

    def test_sleep_refreshes_current_reference_without_replacing_logical_anchor(self):
        from mta.presentation import scoped_selection as selection, scoped_view
        from mta.runtime.scope_execution import _setting, _close_attempt
        from mta.runtime.scoped_actions import record
        from mta.presentation.context import PublicationUnavailable
        from tests.production_h3_fixture import SEASON, CHILD
        self.action_case = True
        self.selected(); old = self.view; original_file = self.selection_path.read_bytes()
        with _setting('fresh.scope_worker', self.attempt.worker_token):
            _close_attempt(self.attempt, self.run, 'RELEASED', {})
        event = record(self.run.pk, phase_id=self.receipt.pk, phase_digest=self.receipt.digest,
            expected_revision=0, operation='SLEEP', selected=[[SEASON, CHILD]], timestamp='2037-04-10T10:00:00',
            actor='selected-component', idempotency_key='selected-sleep')
        with self.assertRaises(PublicationUnavailable): selection.selected()
        fresh = scoped_view.prepare(self.receipt.pk, expected_digest=self.receipt.digest, action_revision=event.pk)
        self.assertNotEqual(fresh.reference.metadata['source_digest'], old.reference.metadata['source_digest'])
        with self.no_build(): self.assertEqual(selection.selected().read_identity, fresh.read_identity)
        self.assertEqual(self.selection_path.read_bytes(), original_file)
        self.assertEqual(selection.candidate(fresh), self.anchor)

    def test_selected_metadata_profile(self):
        import cProfile, pstats
        from mta.presentation import scoped_selection as selection
        from mta.presentation.request_scope import read_request
        self.selected()
        profile = cProfile.Profile()
        with read_request('/api/GetPlanningDataCount'), profile:
            selection.selected()
        pstats.Stats(profile).strip_dirs().sort_stats('cumulative').print_stats(18)

    def test_matched_http_metadata_reuse_preserves_response(self):
        from mta.presentation import scoped_sources, scoped_prepared, scoped_report_storage
        from mta.runtime import ingestion_ownership
        from time import perf_counter
        def uncached(database, physical):
            with database.cursor() as cursor: return ingestion_ownership._verify_guard_coverage(cursor)
        self.selected()
        results = {}
        for cached in (True, False, False, True):
            with ExitStack() as stack:
                if not cached:
                    for module in (scoped_sources, scoped_prepared, scoped_report_storage):
                        stack.enter_context(patch.object(module, 'bind', module.bind.__wrapped__))
                    for helper in ('_accepted_phase', '_input_manifest_digest'):
                        stack.enter_context(patch.object(scoped_sources, helper, getattr(scoped_sources, helper).__wrapped__))
                    stack.enter_context(patch('mta.runtime.ingestion_ownership._request_guard_coverage',
                        side_effect=uncached))
                started = perf_counter()
                response = self.http('planning_overview')
                print(json.dumps(dict(matched_cache=cached,seconds=round(perf_counter()-started,3))),flush=True)
                self.assertEqual(response.status_code, 200)
                value = json.loads(response.content)
                if results: self.assertEqual(value, next(iter(results.values())))
                results[cached] = value


    def test_pick_download_entitlement_scope_and_exact_owned_file_bytes(self):
        from django.test import RequestFactory
        from mta.presentation import views
        from mta.presentation.pick_downloads import REPORTS
        from mta.runtime.scoped_pick_files import open_file
        self.selected()
        for report, filename in REPORTS.items():
            def request(entitlements, payload):
                return RequestFactory().generic('GET', '/api/DownloadReports/' + report,
                    data=json.dumps(payload), content_type='application/json',
                    HTTP_X_VECTORFLOW_IDENTITY=json.dumps(dict(id='component-reader', entitlements=entitlements)))
            denied = views.download_report(request([], self.payload), report_name=report)
            self.assertEqual(denied.status_code, 403)
            payload = dict(self.payload, product_permissions=[])
            denied = views.download_report(request(['mta-report-urls'], payload), report_name=report)
            self.assertEqual(denied.status_code, 403)
            with open_file(self.receipt.pk, filename, expected_digest=self.receipt.digest) as stream:
                expected = stream.read()
            response = views.download_report(request(['mta-report-urls'], self.payload), report_name=report)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), expected)
            response.close()
