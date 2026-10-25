"""MDM keeps its G1 source verification/lock lifetime in phase-selected mode."""
from contextlib import contextmanager
import json,os,unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','scoped-mdm-binding-unit-only')
import django;django.setup()
from django.http import JsonResponse
from django.test import RequestFactory
from mta.presentation import mdm_views
from mta.runtime.mdm_models import MdmSource


class ScopedMdmBindingTests(unittest.TestCase):
    def call(self, *, phase=True, captured_source=7):
        events=[]
        run=NS(pk='accepted-bpr' if phase else 'completed-full',
            mdm_input_capture=NS(source_id=captured_source))
        @contextmanager
        def verified(node):
            self.assertIs(node,run);events.append('verified-enter')
            yield
            events.append('verified-exit')
        @contextmanager
        def locked(source):
            self.assertEqual(source,7);events.append('source-enter')
            yield
            events.append('source-exit')
        def configuration(request,payload):
            events.append('existing-family-reader')
            return JsonResponse(dict(screen=payload['screenType']))
        configuration.__module__=mdm_views.__name__
        endpoint=mdm_views.endpoint('POST')(configuration)
        request=RequestFactory().post('/api/mta/GetMasterUIConfiguration',
            data=json.dumps(dict(screenType='View')),
            content_type='application/json',HTTP_X_VECTORFLOW_IDENTITY='{"id":"fixture"}')
        with patch.object(MdmSource.objects,'filter') as source, \
                patch('mta.presentation.scoped_selection.enabled',return_value=phase), \
                patch('mta.presentation.installation_metadata.publication_configured',return_value=True), \
                patch('mta.presentation.scoped_admission.binding',return_value=(run,'accepted')), \
                patch('mta.presentation.context.selected_run',return_value=run) as full, \
                patch('mta.presentation.report_verification.verification_scope',side_effect=verified), \
                patch('mta.mdm.supplier_revisions.source_lock',side_effect=locked):
            source.return_value.values_list.return_value.first.return_value=7
            response=endpoint(request)
            self.assertEqual(full.call_count,0 if phase else 1)
        return response,events

    def test_phase_dispatch_uses_existing_family_reader_and_verified_source_lifetime(self):
        response,events=self.call()
        self.assertEqual(response.status_code,200)
        self.assertEqual(json.loads(response.content),dict(screen='View'))
        self.assertEqual(events,['verified-enter','source-enter','existing-family-reader','source-exit','verified-exit'])

    def test_full_default_retains_the_same_verification_and_lock_order(self):
        response,events=self.call(phase=False)
        self.assertEqual(response.status_code,200)
        self.assertEqual(events,['verified-enter','source-enter','existing-family-reader','source-exit','verified-exit'])

    def test_phase_cannot_route_a_different_mdm_source(self):
        response,events=self.call(captured_source=99)
        self.assertEqual(response.status_code,503)
        self.assertEqual(json.loads(response.content)['error'],'phase_mdm_source_binding_differs')
        self.assertEqual(events,[])
