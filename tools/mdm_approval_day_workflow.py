"""Finite authenticated thirteen-master exercise; never calculate a day."""
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

REQUEST_SHA = '0a075cdfb20fa90dee8ab3684b7838c615259453358d4c4ac5ead227b3b73de5'
REVIEW_TIME = datetime.fromisoformat('2026-06-06T13:00:00+05:30')

# Exact native typed owners for this fixed thirteen-request exercise.
MODELS = {
    1: ('MdmSkuRequested', 'MdmSkuHistory', 'MdmSkuApproved'),
    2: ('MdmLocationRequested', 'MdmLocationHistory', 'MdmLocationApproved'),
    3: ('MdmSkuLocModifyRequested', 'MdmSkuLocHistory', 'MdmSkuLocModifyApproved'),
    4: ('MdmSobRequested', 'MdmSobHistory', 'MdmSobApproved'),
    5: ('MdmMoqRequested', 'MdmMoqHistory', 'MdmMoqWithoutDestinationApproved'),
    6: ('MdmStopPipoRequested', 'MdmStopPipoHistory', 'MdmStopPipoQueue'),
    7: ('MdmPhaseOutRequested', 'MdmPhaseOutHistory', 'MdmPhaseOutQueue'),
    8: ('MdmPhaseOutRequested', 'MdmPhaseOutHistory', 'MdmPhaseOutQueue'),
    9: ('MdmPhaseInNormRequested', 'MdmPhaseInNormHistory', 'MdmPhaseInNormQueue'),
    10: ('MdmSeasonStatusRequested', 'MdmSeasonStatusHistory', 'MdmSeasonCurrent'),
    11: ('MdmSeasonRequested', 'MdmSeasonHistory', 'MdmSeasonQueue'),
    12: ('MdmSeasonRequested', 'MdmSeasonHistory', 'MdmSeasonQueue'),
    13: ('MdmForceRequested', 'MdmForceHistory', 'MdmForceQueue'),
}


def typed_rows(model, query):
    return [{f.name: getattr(obj, f.attname) for f in model._meta.concrete_fields}
            for obj in query.order_by('pk')]


def task_rows(source, mid, task_id):
    from django.apps import apps
    models = tuple(apps.get_model('fresh_mta', name) for name in MODELS[mid])
    requested, history, effect = models
    rows = typed_rows(requested, requested.objects.filter(source=source, TaskId=task_id))
    if len(rows) != 1:
        raise ValueError('Fixed request must persist exactly one complete typed occurrence')
    names = {f.name for f in effect._meta.concrete_fields}
    key = {name: rows[0][name] for name in ('SKUCode', 'WHCode', 'WhCode', 'SupplierCode')
           if name in names and name in rows[0]}
    if not key:
        raise ValueError('Effect identity unavailable')
    return (rows, typed_rows(history, history.objects.filter(source=source, TaskId=task_id)),
            typed_rows(effect, effect.objects.filter(source=source, **key)))


def complete_effect(source, mid):
    from django.apps import apps
    model = apps.get_model('fresh_mta', MODELS[mid][2])
    return typed_rows(model, model.objects.filter(source=source))


def verify_review(source, mid, task_id, prior_effect):
    """Do not mistake native caught SQL errors/HTTP200 for a successful effect."""
    from mta.runtime.mdm_models import MdmTask, MdmSubTask
    from mta.serialization import storage
    requested, history, effect = task_rows(source, mid, task_id)
    task = MdmTask.objects.get(source=source, TaskID=task_id, MasterId=str(mid))
    subtasks = typed_rows(MdmSubTask, MdmSubTask.objects.filter(source=source, TaskID=task_id))
    approved_by = 'ApproverBy' if mid == 10 else 'ApprovedBy'
    if (not history or any(r['Status'] != '3' or str(r[approved_by]) != '3'
            or {v.strip() for v in r['ApproverId'].split(',')} != {'3'} for r in history)
            or not requested[0]['Approved'] or requested[0]['Reverted']
            or task.TaskStatus != '1'):
        raise ValueError('Native request/history/header approval state differs')
    mine = [r for r in subtasks if r['ApproverId'] == '3']
    if (len(mine) != 1 or mine[0]['TaskStatus'] != ('4' if mid == 10 else '2')
            or mine[0]['ApprovedOrRejectedDate'] != REVIEW_TIME.strftime('%d/%m/%Y %I:%M %p')
            or any(r['TaskStatus'] != '8' for r in subtasks if r['ApproverId'] != '3')):
        raise ValueError('Reviewer completion was not persisted')
    if len(effect) != 1:
        raise ValueError('Expected native approval effect occurrence missing or duplicated')
    actual, expected = effect[0], requested[0]
    after = complete_effect(source, mid)
    old_target = [r for r in prior_effect if r['id'] == actual['id']]
    if [r for r in after if r['id'] != actual['id']] != [r for r in prior_effect if r['id'] != actual['id']]:
        raise ValueError('Approval changed an unrelated effect-table occurrence')
    if mid == 10:
        if (len(old_target) != 1 or actual['Status'] != expected['Status1']
                or actual['Status'] != 23 or actual['Comment'] != expected['Comment']
                or actual['revision'] != old_target[0]['revision'] + 1):
            raise ValueError('Season stop publication/revision differs')
        unchanged = set(actual) - {'Status', 'Comment', 'revision'}
        if any(actual[n] != old_target[0][n] for n in unchanged):
            raise ValueError('Season stop changed an unrelated value')
    else:
        shared = set(actual) & set(expected) - {'id', 'source', 'revision'}
        if mid in (11, 12):
            shared.discard('ActivateDBM')  # Native ADD explicitly publishes False.
            if actual['ActivateDBM'] is not False:
                raise ValueError('Season queue ActivateDBM differs')
        if not shared or any(actual[n] != expected[n] for n in shared):
            raise ValueError('Complete typed approval queue differs from request')
        if old_target:
            raise ValueError('Fixed new approval unexpectedly replaced an existing queue row')
        if mid >= 4 and actual['revision'] != (1 if mid in (4, 5, 11, 12, 13) else 0):
            raise ValueError('Native insert/update effect revision differs')
    return storage(dict(master_id=mid, task_id=task_id, requested=requested,
        history=history, effect=effect, full_effect_before=prior_effect,
        full_effect_after=after, subtasks=subtasks, header_status=task.TaskStatus))


def schedule():
    """Approved distinct seconds; actual actions still need execution release."""
    return [dict(master_id=i, submitted=REVIEW_TIME - timedelta(seconds=14-i),
                 reviewed=REVIEW_TIME) for i in range(1, 14)]


def requests(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != REQUEST_SHA:
        raise ValueError('Exact approved thirteen requests required')
    rows = json.loads(raw)['families']
    if [r['master_id'] for r in rows] != list(range(1, 14)):
        raise ValueError('Exact ordered master roster required')
    return rows


@contextmanager
def historical_clock(stamp):
    """Bind only imported MDM API/SQL clock helpers in this offline process."""
    from mta.mdm import clock, drafts
    originals = (clock.database_now, drafts.now)
    with ExitStack() as stack:
        for name, module in tuple(sys.modules.items()):
            if name.startswith('mta.mdm.') and module is not None:
                for attribute in ('database_now', 'now'):
                    if getattr(module, attribute, None) in originals:
                        stack.enter_context(patch.object(module, attribute, lambda: stamp))
        yield


class GatewaySession:
    def __init__(self, label):
        from rest_framework.test import APIRequestFactory
        from api.view.auth import UserLoginView
        from tools.cohort6_actions import _encrypted_password, _secret
        self.factory = APIRequestFactory()
        response = UserLoginView.as_view()(self.factory.post('/api/user/login/', {
            'email': _secret('NMS_' + label + '_EMAIL'),
            'password': _encrypted_password(_secret('NMS_' + label + '_PASSWORD')),
        }, format='json'))
        cookie = response.cookies.get('access_token')
        if response.status_code != 200 or cookie is None or not cookie.value:
            raise ValueError('Existing fixture password login failed')
        self.cookie = cookie.value
        self.actor = 2 if label == 'REQUESTER' else 3

    def post(self, route, payload):
        from api_gateway.views import API_GATEWAY_VIEW
        from api_gateway.interceptors.mta_interceptor import MTA_INTERCEPTOR
        raw = self.factory.post('/api/mta/' + route, payload, format='json')
        raw.COOKIES['access_token'] = self.cookie
        view = API_GATEWAY_VIEW()
        request = view.initialize_request(raw)
        view.request, view.args, view.kwargs = request, (), {}
        view.perform_authentication(request)
        view.check_permissions(request)
        if request.user.id != self.actor:
            raise ValueError('Authenticated fixture actor differs')
        response = MTA_INTERCEPTOR().forward(request, {
            'mta': {'base_url': 'http://mdm-day.invalid', 'application_id': 2}})
        raw.COOKIES.clear()
        return response.status_code, json.loads(response.content)


def submission(source, scenario):
    """Preserve current base fields; overlay only the approved scenario fields."""
    from mta.mdm import families
    from mta.runtime.mdm_models import (
        MdmSkuAttributes, MdmSkuDescription, MdmLocationAttributes,
        MdmLocationDescription)
    from mta.runtime.mdm_skuloc_models import MdmSkuLocCurrent
    mid, changes = scenario['master_id'], dict(scenario['request'])
    if mid == 4:
        changes['WhCode'] = changes.pop('WHCode')
    if mid == 7:
        if changes.pop('PhaseInSKUCode') is not None:
            raise ValueError('Master7 has no PhaseIn field; approved NULL required')
    current = {}
    if mid == 1:
        objects = (MdmSkuAttributes.objects.get(source=source, owner='Importer', SKUCode=changes['SKUCode']),
                   MdmSkuDescription.objects.get(source=source, owner='Importer', SKUCode=changes['SKUCode']))
    elif mid == 2:
        objects = (MdmLocationAttributes.objects.get(source=source, owner='Importer', WHCode=changes['WHCode']),
                   MdmLocationDescription.objects.get(source=source, owner='Importer', WHCode=changes['WHCode']))
    elif mid == 3:
        objects = (MdmSkuLocCurrent.objects.get(source=source, owner='Importer',
                   SKUCode=changes['SKUCode'], WhCode=changes['WhCode']),)
    else:
        objects = ()
    for obj in objects:
        current.update({f.name: getattr(obj, f.attname) for f in obj._meta.concrete_fields})
    current.update(changes)
    if mid in (4, 5):
        from mta.mdm.supplier import CONFIG
        aliases = {r['Col_Code']: r['TableField'] for r in CONFIG[mid]['UI_MDMConfig']}
    elif mid in (7, 8, 9):
        from mta.mdm.phase_controls_configuration import ALIASES
        aliases = ALIASES[mid]
    elif mid in (10, 11, 12):
        from mta.mdm.season_configuration import aliases as get_aliases
        aliases = get_aliases(mid)
    elif mid == 6:
        aliases = {'sc': 'SKUCode', 'wc': 'WhCode'}
    else:
        aliases = families.module(mid).ALIASES
    row = {alias: current[field] for alias, field in aliases.items()
           if field in current and (current[field] is not None or mid in (7, 8, 9, 10, 11, 12))}
    unbound = set(changes) - set(aliases.values()) - {'action'}
    if unbound:
        raise ValueError('Unmapped approved request fields: ' + repr(sorted(unbound)))
    action = 1 if mid in (4, 5, 7, 8, 9, 11, 12) else 2
    payload = dict(id=mid, taskId='', data=[row], isOverwrite=False)
    if mid == 10:
        payload['action'] = 'stop'
    return ('AddMasterData' if action == 1 else 'ModifyMasterData'), payload


def execute(source, run, request_path, evidence_path):
    from django.conf import settings
    from django.core.wsgi import get_wsgi_application
    from django.test import override_settings
    from api_gateway.inprocess_mta import owned_mdm_workflow_application
    from mta.mdm import families, integration_source
    from mta.presentation.operational_admission import verify
    from mta.runtime.mdm_models import MdmTask
    from tools.mdm_approval_day_identity import DATABASE
    scenarios = requests(request_path)
    if (source.database_name != DATABASE or str(run.business_date) != '2026-06-06'
            or run.mdm_input_capture.source_id != source.pk
            or str(settings.VF_MTA_PUBLISHED_RUN) != str(run.pk)
            or settings.VF_MTA_PUBLISHED_DIGEST != run.output_digest):
        raise ValueError('Exact own accepted D0 required')
    verify(run, selected=False)
    if MdmTask.objects.filter(source=source).exists():
        raise ValueError('Workflow tasks already exist; do not replay requests')
    # Import every relevant clock consumer before applying the test clock.
    for mid in range(1, 14):
        families.module(mid)
        families.module(mid, 'tasks')
        families.module(mid, 'reads')
    integration_source.installed_binding(source)
    if set(families.installed_ids(source)) != set(range(1, 14)):
        raise ValueError('All thirteen masters must be bound before requests')
    target = Path(evidence_path)
    if target.exists():
        raise ValueError('Workflow evidence exists; overwrite prohibited')
    sessions = {name: GatewaySession(name) for name in ('REQUESTER', 'REVIEWER')}
    try:
        with target.open('x', encoding='utf-8') as log, override_settings(
                MTA_INPROCESS_WSGI_APPLICATION=owned_mdm_workflow_application(
                    get_wsgi_application(), run_id=run.pk, output_digest=run.output_digest),
                VF_MDM_SOURCE_DIGEST=source.digest):
            pending = []
            for scenario, timing in zip(scenarios, schedule()):
                mid = scenario['master_id']
                route, payload = submission(source, scenario)
                with historical_clock(timing['submitted']):
                    code, submitted = sessions['REQUESTER'].post(route, payload)
                log.write(json.dumps(dict(master_id=mid, phase='submit', http=code,
                    response=submitted), default=str) + '\n'); log.flush()
                if code != 200 or submitted.get('status') != 200 or int(submitted.get('errorCount') or 0) or int(submitted.get('conflictErrorCount') or 0):
                    raise ValueError('Native submission failed for master ' + str(mid))
                task_id = submitted['taskId']
                expected = '2_' + timing['submitted'].strftime('%Y%m%d%H%M%S')
                if task_id != expected or MdmTask.objects.filter(source=source, TaskID=task_id, MasterId=str(mid)).count() != 1:
                    raise ValueError('Native task identity/roster differs')
                pending.append((mid, timing, task_id, payload))
            for mid, timing, task_id, payload in pending:
                row = {k: v for k, v in payload['data'][0].items() if k in ('sc', 'wc', 'spc', 'nn')}
                row.update(status='3', comments='MDM approval-to-day fixed request')
                decision = dict(taskId=task_id, data=[row])
                prior_effect = complete_effect(source, mid)
                with historical_clock(timing['reviewed']):
                    denied, _ = sessions['REQUESTER'].post('PostMasterAfterApproved', decision)
                    if denied != 403:
                        raise ValueError('Requester was not denied reviewer action')
                    code, approved = sessions['REVIEWER'].post('PostMasterAfterApproved', decision)
                log.write(json.dumps(dict(master_id=mid, phase='approve', task_id=task_id,
                    http=code, response=approved, requester_denied=True), default=str) + '\n'); log.flush()
                if code != 200 or approved.get('status', 200) != 200:
                    raise ValueError('Native approval failed for master ' + str(mid))
                proof = verify_review(source, mid, task_id, prior_effect)
                log.write(json.dumps(dict(phase='typed_review_proof', **proof)) + '\n'); log.flush()
    finally:
        for session in sessions.values():
            session.cookie = ''
    return dict(tasks=13, evidence=str(target), business_day_calls=0)


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    release = Path('/request/execution-request.json').read_bytes()
    approved = os.environ.get('MDM_DAY_EXECUTION_APPROVAL_SHA256', '')
    if len(approved) != 64 or hashlib.sha256(release).hexdigest() != approved:
        raise ValueError('Exact execution approval required before workflow binding')
    if args.evidence.exists():
        raise ValueError('Workflow attempt already exists; no replay')
    import django
    django.setup()
    from mta.runtime.models import CalculationRun
    from mta.runtime.mdm_models import MdmSource
    from mta.mdm.integration_source import bind_complete
    from mta.presentation.operational_admission import verify
    run = CalculationRun.objects.get(pk=args.run)
    source = MdmSource.objects.get(pk=1,
        digest='39f76f9c718a28e014737e8c856af7d29f1ab5dbdfd2370321a6cb539d010f8e')
    from django.conf import settings
    from tools.mdm_approval_day_identity import DATABASE
    if (source.database_name != DATABASE or str(run.business_date) != '2026-06-06'
            or run.mdm_input_capture.source_id != source.pk
            or str(settings.VF_MTA_PUBLISHED_RUN) != str(run.pk)
            or settings.VF_MTA_PUBLISHED_DIGEST != run.output_digest):
        raise ValueError('Exact own accepted D0 selection required before binding')
    # Validate the fixed request file before adding the optional family owners.
    requests('/request/workflow-requests.json')
    verify(run, selected=False)
    seal = bind_complete(source, run)
    result = execute(source, run, '/request/workflow-requests.json', args.evidence)
    result['integration_digest'] = seal.digest
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
