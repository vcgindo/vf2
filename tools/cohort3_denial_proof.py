"""Read-only Cohort3 denial proof over real ORM, authentication and WSGI paths."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tools.cohort3_settings')

import django
django.setup()

from django.test import Client, override_settings

from api.models import (
    User,
    User_Application_Location_Permission as LocationGrant,
    User_Application_Product_Permission as ProductGrant,
)
from mta.presentation import admission, qualified_consumption as policy
from mta.presentation.context import PublicationUnavailable
from mta.presentation.pick_downloads import PickDownloadDenied, REPORTS, open_report
from mta.presentation.qualified_session import selected
from mta.runtime.models import CalculationRun
from tools.cohort3_auth import issue_actor_tokens


REPOSITORY = Path(__file__).resolve().parents[1]


def response_content(response):
    if not response.streaming:
        return response.content
    if response.is_async:
        async def collect():
            return b''.join([chunk async for chunk in response.streaming_content])
        return asyncio.run(collect())
    return b''.join(response.streaming_content)


def actor_client(actor_id):
    client = Client()
    client.cookies['access_token'] = issue_actor_tokens(actor_id)['access']
    return client


def trusted_payload(actor_id):
    """Reproduce the gateway-owned actor and application-2 scope payload."""
    actor = User.all_objects.using('identity').get(
        pk=actor_id, is_active=True, is_admin=False, is_deleted=False)
    products = list(ProductGrant.objects.using('identity').filter(
        user_id=actor_id, application_id=2).order_by('productfilter_id').values_list(
            'productfilter_id', flat=True))
    locations = list(LocationGrant.objects.using('identity').filter(
        user_id=actor_id, application_id=2).order_by('locationfilter_id').values_list(
            'locationfilter_id', flat=True))
    return ({'product_permissions': products, 'location_permissions': locations,
             'user': {'id': actor.pk, 'name': actor.name}},
            {'id': actor.pk, 'name': actor.name, 'email': actor.email})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date-index', choices=(0, 1), type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(REPOSITORY):
        raise ValueError('Denial receipt must remain outside the Git checkout')
    if output.exists():
        raise ValueError('Proof receipt already exists; choose a new attempt path')
    if not output.parent.is_dir():
        raise ValueError('Proof receipt parent directory must already exist')

    pin = policy.pins()['runs'][args.date_index]
    candidate_pin = policy.pins()['runs'][1 - args.date_index]
    run = CalculationRun.objects.get(pk=pin['run_id'])
    candidate = CalculationRun.objects.get(pk=candidate_pin['run_id'])
    evidence = {
        'status': 'RUNNING',
        'run': pin['run_id'],
        'date': pin['date'],
        'output_digest': pin['output_digest'],
        'candidate_run': candidate_pin['run_id'],
        'calculation_calls': 0,
        'resource_writes': 0,
        'observations': [],
    }

    def observe_http(client, route, expected_status, label):
        response = client.get('/api/mta/' + route)
        raw = response_content(response)
        content_type = response.get('Content-Type', '')
        body = json.loads(raw) if 'json' in content_type else None
        item = {
            'label': label,
            'layer': 'actual_outer_gateway_http',
            'route': route,
            'status': response.status_code,
            'body': body,
            'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
        }
        evidence['observations'].append(item)
        response.close()
        if item['status'] != expected_status:
            raise AssertionError(item)
        return item

    def observe_direct(label, expected, function):
        try:
            function()
        except (PickDownloadDenied, PublicationUnavailable) as error:
            item = {'label': label, 'layer': 'direct_read_function',
                    'exception': type(error).__name__, 'denial': str(error)}
            evidence['observations'].append(item)
            if item['denial'] != expected:
                raise AssertionError(item)
            return item
        raise AssertionError(label + ' unexpectedly succeeded')

    try:
        with selected(run) as selection:
            evidence['selection'] = selection
            from tools.cohort3_wsgi import build_application
            build_application()

            invalid = Client()
            invalid.cookies['access_token'] = 'cohort3.invalid.jwt'
            item = observe_http(invalid, 'GetLastRunDate', 401, 'invalid-cookie-jwt')
            if not isinstance(item['body'], dict) or item['body'].get('code') != 'token_not_valid':
                raise AssertionError(item)

            broad = actor_client(2)
            restricted = actor_client(3)
            broad_payload, broad_identity = trusted_payload(2)
            restricted_payload, restricted_identity = trusted_payload(3)
            if 'entitlements' in restricted_identity:
                raise AssertionError('Restricted trusted identity unexpectedly has an entitlement')
            evidence['persisted_access'] = {
                'broad_actor': broad_identity['id'],
                'broad_product_permissions': broad_payload['product_permissions'],
                'broad_location_permissions': broad_payload['location_permissions'],
                'restricted_actor': restricted_identity['id'],
                'restricted_product_permissions': restricted_payload['product_permissions'],
                'restricted_location_permissions': restricted_payload['location_permissions'],
                'restricted_entitlements': [],
            }

            for report_name in REPORTS:
                item = observe_http(restricted, 'DownloadReports/' + report_name, 403,
                                    'restricted-entitlement-' + report_name)
                if item['body'] != {'error': 'mta_report_download_forbidden'}:
                    raise AssertionError(item)

                observe_direct('restricted-whole-file-scope-' + report_name,
                               'selected_run_pick_scope_denied',
                               lambda name=report_name: open_report(
                                   run, restricted_payload, name))

            # Removing only the approved read-time supplement preserves native
            # NULL hierarchy semantics. This is a direct read check because the
            # admitted HTTP application must retain its original immutable bind.
            with override_settings(VF_MTA_HIERARCHY_FILE='',
                                   VF_MTA_HIERARCHY_SHA256=''):
                for report_name in REPORTS:
                    observe_direct('native-null-hierarchy-' + report_name,
                                   'selected_run_pick_scope_denied',
                                   lambda name=report_name: open_report(
                                       run, broad_payload, name))

            for report_name in ('UnknownPickReport', '../LogisticPickListReport'):
                observe_direct('report-name-denied-' + report_name,
                               'unknown_pick_report',
                               lambda name=report_name: open_report(
                                   run, broad_payload, name))

            prior = admission.require_admission()
            try:
                # The candidate remains untouched. A deliberately invalid
                # terminal identity makes its real admission fail after the
                # selection scope has saved the prior valid admission.
                with override_settings(VF_MTA_TERMINAL_SHA256='0' * 64):
                    with selected(candidate):
                        raise AssertionError('Invalid candidate unexpectedly admitted')
            except PublicationUnavailable as error:
                candidate_denial = str(error)
                if candidate_denial not in {
                        'terminal_ancillary_supplement_not_configured',
                        'terminal_ancillary_supplement_hash_mismatch'}:
                    raise
                evidence['observations'].append({
                    'label': 'failed-candidate-preserves-prior',
                    'layer': 'qualified_selection_and_production_admission',
                    'candidate_run': str(candidate.pk),
                    'exception': type(error).__name__,
                    'denial': candidate_denial,
                    'prior_admission': prior,
                })
            if admission.require_admission() != prior:
                raise AssertionError('Failed candidate did not preserve prior admission')
            observe_http(broad, 'GetLastRunDate', 200,
                         'prior-admission-readable-after-candidate-denial')

        if admission._admitted is not None:
            raise AssertionError('Qualified selection did not restore the outer admission state')
        evidence['status'] = 'REAL_DENIAL_PROOF_PASS'
    except BaseException:
        evidence['status'] = 'FAILED'
        evidence['failure'] = traceback.format_exc()
        raise
    finally:
        with output.open('x', encoding='utf-8') as stream:
            json.dump(evidence, stream, indent=2, default=str)


if __name__ == '__main__':
    main()
