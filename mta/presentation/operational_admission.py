"""Explicit verified operational qualification; never writes parity or business state."""
from copy import deepcopy
from datetime import timedelta
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.db import connection, transaction
from mta.serialization import digest, storage
from mta.presentation.context import PublicationUnavailable

POLICY = 'supported-synthetic-operational-v1'
QUALIFICATION = 'inactive-nms-critical-flags-remain-false'
BLOCKED_ROUTES = ('orderFulfillment-custom', 'git-child-GetPlanningDataGrid')


def reject(reason):
    raise PublicationUnavailable('operational_acceptance_' + reason)


def enabled():
    value = getattr(settings, 'VF_MTA_OPERATIONAL_POLICY', '')
    if value not in ('', POLICY):
        reject('unknown_policy')
    if not value:
        if getattr(settings, 'VF_MTA_OPERATIONAL_RECEIPT', ''):
            reject('receipt_without_policy')
        return False
    forbidden = ('VF_MTA_CONSUMPTION_POLICY', 'VF_MTA_FIXTURE_FILE', 'VF_MTA_FIXTURE_SHA256',
        'VF_MTA_TERMINAL_FILE', 'VF_MTA_TERMINAL_SHA256', 'VF_MTA_EXCESS_HISTORY_FILE',
        'VF_MTA_EXCESS_HISTORY_SHA256', 'VF_MTA_PLANNING_EXTENSION', 'VF_MTA_RRR_COLOUR_EXTENSION',
        'VF_MTA_GUIDED_EXCESS_DISPOSITION', 'VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY',
        'VF_MTA_ACTIONS_ENABLED')
    if (any(getattr(settings, key, '') for key in forbidden)
            or not settings.VF_MTA_DAILY_PUBLICATION
            or settings.VF_MTA_SYNTHETIC_ROSTER != 'core-without-bor-v1'):
        reject('configuration_outside_domain')
    return True


@lru_cache(maxsize=1)
def code_identity():
    """Immutable deployed code, not a caller-supplied revision assertion."""
    root = Path(__file__).resolve().parents[1]
    paths = sorted([*root.rglob('*.py'), *(root / 'config').glob('*.json')])
    return digest({p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in paths})


def actions(run):
    result = []
    for event in run.commands.order_by('id'):
        if digest(event.payload) != event.digest:
            reject('action_payload_changed')
        result.append(dict(id=event.pk, digest=event.digest, before=event.before_digest,
                           after=event.after_digest))
    return result


def operation_metadata(attempt, repair):
    from mta.runtime.operational_attempts import configuration_value
    configuration_value(attempt.configuration)
    def metadata(value):
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, dict):
            return {k: metadata(v) for k,v in value.items()}
        if isinstance(value, (list,tuple)):
            return [metadata(v) for v in value]
        return storage(value)
    def owner(value):
        from mta.runtime.models import (OperationalFile, OperationalArchiveMember,
            OperationalBackup, OperationalIntentEvaluation, OperationalPopulation)
        return dict(id=str(value.pk), run=str(value.run_id), status=value.status,
            predecessor=str(value.predecessor_id) if value.predecessor_id else None,
            repair_of=str(value.repair_of_id) if value.repair_of_id else None,
            retry_of=str(value.retry_of_id) if value.retry_of_id else None,
            configuration=value.configuration_id, output=value.run_output_digest,
            source=value.source_digest, actions=value.action_digest, date=str(value.business_date),
            operations=metadata(list(value.operations.order_by('ordinal').values())),
            repairs=metadata(list(value.repair_targets.order_by('ordinal').values())),
            files=metadata(list(OperationalFile.objects.filter(operation__attempt=value).order_by('pk').values())),
            members=metadata(list(OperationalArchiveMember.objects.filter(archive__operation__attempt=value).order_by('pk').values())),
            backups=metadata(list(OperationalBackup.objects.filter(operation__attempt=value).order_by('pk').values())),
            evaluations=metadata(list(OperationalIntentEvaluation.objects.filter(operation__attempt=value).order_by('pk').values())),
            populations=metadata(list(OperationalPopulation.objects.filter(attempt=value).order_by('pk').values())))
    lineage=[]
    leaf=attempt
    seen=set()
    while leaf.retry_of_id:
        if leaf.pk in seen:
            reject('retry_cycle')
        seen.add(leaf.pk)
        prior=leaf.retry_of
        if (prior.status!='FAILED' or prior.run_id!=attempt.run_id
                or prior.configuration_id!=attempt.configuration_id
                or prior.run_output_digest!=attempt.run_output_digest
                or prior.action_digest!=attempt.action_digest or prior.source_digest!=attempt.source_digest
                or prior.business_date!=attempt.business_date or prior.predecessor_id!=attempt.predecessor_id
                or prior.repair_of_id!=attempt.repair_of_id
                or set(prior.retries.values_list('pk',flat=True))!={leaf.pk}):
            reject('retry_lineage_changed')
        lineage.append(owner(prior));leaf=prior
    repairs=list(attempt.repairs.order_by('created_at','pk'))
    successful=[r for r in repairs if r.status=='SUCCEEDED']
    if (any(r.status not in ('FAILED','SUCCEEDED') for r in repairs)
            or (repair is None and repairs)
            or (repair is not None and (len(successful)!=1 or successful[0].pk!=repair.pk))):
        reject('explicit_complete_repair_lineage_required')
    repair_chain=set();leaf=repair
    while leaf is not None:
        if (leaf.pk in repair_chain or leaf.repair_of_id!=attempt.pk
                or leaf.run_id!=attempt.run_id or leaf.configuration_id!=attempt.configuration_id
                or leaf.business_date!=attempt.business_date or leaf.predecessor_id!=attempt.predecessor_id
                or leaf.run_output_digest!=attempt.run_output_digest or leaf.action_digest!=attempt.action_digest
                or leaf.source_digest!=attempt.source_digest
                or (leaf.pk!=repair.pk and leaf.status!='FAILED')):
            reject('repair_retry_graph_changed')
        repair_chain.add(leaf.pk)
        prior=leaf.retry_of
        if prior and set(prior.retries.values_list('pk',flat=True))!={leaf.pk}:
            reject('repair_retry_branch')
        leaf=prior
    if repair_chain!={r.pk for r in repairs}:
        reject('detached_repair_attempt')
    return digest(dict(attempt=owner(attempt), repair=owner(repair) if repair else None,
                       retries=lineage, repairs=[owner(r) for r in repairs]))


def owner_checks(run, attempt, repair):
    if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED'
            or not run.production_manifest or not run.execution_revision
            or run.input_payload.get('schema') != 'fresh-daily-input-manifest-v2'):
        reject('native_completed_typed_run_required')
    if (attempt.run_id != run.pk or attempt.status != 'SUCCEEDED' or attempt.repair_of_id
            or attempt.business_date != run.business_date or attempt.run_output_digest != run.output_digest
            or attempt.action_digest != digest(actions(run))):
        reject('operational_owner_changed')
    if repair and (repair.run_id != run.pk or repair.status != 'SUCCEEDED'
            or repair.repair_of_id != attempt.pk or repair.configuration_id != attempt.configuration_id
            or repair.predecessor_id != attempt.predecessor_id or repair.business_date != run.business_date
            or repair.run_output_digest != run.output_digest or repair.action_digest != attempt.action_digest
            or repair.source_digest != attempt.source_digest):
        reject('repair_owner_changed')
    if run.predecessor_id:
        if not attempt.predecessor_id or attempt.predecessor.run_id != run.predecessor_id:
            reject('own_operational_predecessor_required')
    elif attempt.predecessor_id:
        reject('unexpected_operational_predecessor')


def snapshot(run, publication, attempt, repair, artifact_path, finalization_path, pick_config_path, shipment_path):
    """Bounded persisted metadata for before/after and request drift checks."""
    from mta.presentation import daily_activation, daily_sources, daily_publication
    from mta.runtime.receipt_integrity import source_receipts
    owner_checks(run, attempt, repair)
    source = daily_sources.receipt(run)
    access = daily_activation.values(run, publication)
    path = Path(artifact_path)
    if not path.is_absolute() or not path.is_file():
        reject('frozen_artifact_required')
    artifact_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    from mta.mdm.daily_source import ARTIFACT_SHA
    if artifact_sha != ARTIFACT_SHA:
        reject('unregistered_artifact')
    capture = run.mdm_input_capture
    if capture.status != 'CONSUMED' or capture.nms_active:
        reject('consumed_inactive_mdm_required')
    if (publication.status != 'READY' or publication.output_digest != run.output_digest
            or publication.source_digest != daily_publication.source_identity(run)
            or publication.recipe_digest != daily_publication.recipe_identity()
            or publication.seal_digest != daily_publication.seal_identity(publication)):
        reject('publication_changed')
    from mta.presentation.daily_preparation import required_layers
    if set(publication.layers) != set(required_layers()) or any(
            row.get('status') != 'READY' for row in publication.layers.values()):
        reject('required_layers_incomplete')
    return dict(policy=POLICY, qualification=QUALIFICATION, blocked_routes=BLOCKED_ROUTES,
        code=code_identity(), run=str(run.pk), date=str(run.business_date),
        input=run.input_digest, input_manifest=run.input_manifest_digest,
        input_metadata=digest(run.input_payload), revision=run.execution_revision,
        output=run.output_digest, production=run.production_digest,
        production_metadata=digest(run.production_manifest), parity=digest(run.parity_summary),
        artifact=artifact_sha, finalization=hashlib.sha256(Path(finalization_path).read_bytes()).hexdigest(),
        pick_config=hashlib.sha256(Path(pick_config_path).read_bytes()).hexdigest(),
        shipment=hashlib.sha256(Path(shipment_path).read_bytes()).hexdigest(),
        actions=digest(actions(run)),
        predecessor=str(run.predecessor_id) if run.predecessor_id else None,
        predecessor_receipt=(run.predecessor.operationalacceptance.receipt_digest if run.predecessor_id else ''),
        predecessor_output=(run.predecessor.output_digest if run.predecessor_id else ''),
        mdm=digest(dict(source=capture.source_id, source_digest=capture.source.digest,
            receipt=capture.source.receipt, revision=capture.revision_digest,
            sql=capture.sql_digest, request=capture.request_digest, status=capture.status)),
        sources=digest(dict(images=source.images_digest, recipe=source.recipe_digest,
                            receipts=source_receipts(run))),
        operations=operation_metadata(attempt, repair), access=access,
        generation=str(publication.layers['btr']['receipt']['generation']))


def verify_input_domain(run, raw, output, artifact_path, finalization_path, pick_config_path, shipment_path):
    """Native inputs, frozen facts, exact finalization and own predecessor chain."""
    from mta.mdm.daily_source_install import registered
    from mta.mdm.daily_source import ARTIFACT_SHA, require_binding
    from mta.mdm.daily_input import compose
    from mta.application import daily_finalization as final
    from mta.runtime.validation_storage import read_input
    from mta.runtime.services import read_outputs
    from mta.runtime.temporal import command_state
    artifact = registered(Path(artifact_path).read_bytes(), ARTIFACT_SHA)
    case = artifact['case']
    capture = run.mdm_input_capture
    require_binding(capture.source, artifact_sha256=ARTIFACT_SHA, artifact_schema=artifact['schema'])
    from mta.presentation.operational_mdm import verify_consumed
    verify_consumed(run, raw, artifact)
    if digest(raw) != run.input_digest or raw.get('schema') != 'fresh-daily-chain-v1':
        reject('input_changed')
    profile = raw['profile']
    expected_profile = deepcopy(case['profile'])
    content=Path(finalization_path).read_bytes()
    supplement=json.loads(content)
    if (set(supplement)!={'schema','artifact_sha256','configuration','opening_complete'}
            or supplement['schema']!='generic-finalization-input-v1'
            or supplement['artifact_sha256']!=ARTIFACT_SHA or 'complete' in case['opening']):
        reject('finalization_supplement_scope')
    expected_profile.update(complete_daily=supplement['configuration'],
        complete_daily_config_sha256=hashlib.sha256(content).hexdigest(),
        complete_daily_artifact_sha256=ARTIFACT_SHA)
    from mta.application.operational_capture import CAPTURE_POLICY
    if profile.get('operational_sources') != CAPTURE_POLICY:
        reject('explicit_operational_capture_profile_required')
    from mta.runtime.daily_bindings import apply_pick, apply_operational_sources, verify_sha256
    from mta.application.operational_input_capture import INPUT_CAPTURE_POLICY
    from mta.application.timeline_controls import FORCE_CAPTURE_POLICY
    expected_profile=apply_operational_sources(expected_profile,CAPTURE_POLICY,INPUT_CAPTURE_POLICY,FORCE_CAPTURE_POLICY)
    pick_bytes=Path(pick_config_path).read_bytes()
    verify_sha256(pick_bytes,raw.get('pick_config_sha256'),'Complete Pick configuration')
    if not isinstance(raw.get('pick_output_root'),str) or not Path(raw['pick_output_root']).is_absolute():
        reject('explicit_pick_output_root_required')
    expected_profile=apply_pick(expected_profile,pick_bytes,'canonical-tied-order-v1')
    expected_opening={**case['opening'],'complete':supplement['opening_complete']}
    final.begin(deepcopy(expected_opening), case['days'][0]['business_date'])
    expected_profile['daily_publication'] = True
    # run_daily permits an explicit remark horizon; it is bound in the full profile.
    config = expected_profile.setdefault('daily_publication_config', {})
    horizon = profile.get('daily_publication_config', {}).get('bpr_remark_horizon')
    if (type(horizon) is not int or horizon != supplement['configuration']['remark_days']
            or config.get('bpr_remark_horizon', horizon) != horizon):
        reject('remark_horizon_changed')
    config['bpr_remark_horizon'] = horizon
    if profile != expected_profile or final.configuration(profile) is None:
        reject('frozen_profile_changed_or_incomplete')
    if raw.get('report_exceptions'):
        reject('undeclared_report_exceptions')
    final.verify_successor(output, profile, str(run.business_date))
    closing = output['ClosingState'][0]
    if (profile.get('force_flags',{}).get('nms_active') is not False
            or raw['day'].get('new_force_requests') != []
            or closing.get('controls',{}).get('upload_log') != []):
        reject('unsupported_upload_log_source')
    if any(closing['complete'][name] != [] for name in final.EMPTY_APPROVAL_QUEUES):
        reject('populated_approval_queue')
    matches = [(i, row) for i, row in enumerate(case['days']) if row['business_date'] == str(run.business_date)]
    if len(matches) != 1:
        reject('artifact_date')
    index, day = matches[0]
    expected_day = {**deepcopy(day), **deepcopy(case['static_day'])}
    from mta.runtime.daily_bindings import shipment_day
    if 'shipment_input' in expected_day:reject('shipment_cannot_replace_artifact')
    shipment_bytes=Path(shipment_path).read_bytes()
    verify_sha256(shipment_bytes,raw.get('shipment_sha256'),'Shipment supplement')
    expected_day['shipment_input']=shipment_day(shipment_path,raw['shipment_sha256'],
        artifact_sha256=ARTIFACT_SHA,business_date=str(run.business_date))
    if bool(index) != bool(run.predecessor_id):
        reject('artifact_predecessor')
    mdm = raw.get('mdm_input')
    if not mdm or mdm.get('revision_digest') != capture.revision_digest or mdm.get('nms_active') is not False:
        reject('mdm_capture_changed')
    if run.predecessor_id:
        parent = run.predecessor
        if (parent.business_date + timedelta(days=1) != run.business_date
                or str(parent.business_date) != case['days'][index-1]['business_date']
                or parent.mdm_input_capture.source_id != capture.source_id):
            reject('predecessor_date_or_source')
        parent_raw = read_input(parent)
        if parent_raw['profile'] != profile:
            reject('predecessor_profile')
        parent_output = read_outputs(parent)
        final.verify_successor(parent_output, profile, str(parent.business_date))
        _, commands = command_state(parent, parent_output['ClosingState'][0]['dbm'], through_date=run.business_date)
        if raw['opening'] is not None or raw['lineage'] != dict(run_id=str(parent.pk), output_digest=parent.output_digest, commands=commands):
            reject('predecessor_lineage')
        opening_date = str(parent.business_date)
    else:
        opening = raw['opening']
        from parity.temporal_policy import policy_for_case
        identities={case['case']+'-'+ARTIFACT_SHA+'-'+suffix for suffix in
                    ('daily','retained-fixed-actions',policy_for_case(case))}
        if (not isinstance(opening, dict) or opening.get('state') != expected_opening
                or opening.get('opening_date') != case['opening_date']
                or opening.get('identity') not in identities
                or run.opening_key != digest(dict(identity=opening['identity'], revision=run.execution_revision))
                or raw['lineage'] != dict(opening_identity=opening['identity'], opening_digest=digest(opening))):
            reject('opening_lineage')
        opening_date = opening['opening_date']
    expected_day['raw_master'] = storage(compose(mdm, expected_day['raw_master'], last_run_date=opening_date))
    expected_day['exclusions'] = deepcopy(mdm['pair_exclusions'])
    if raw['day'] != expected_day:
        reject('frozen_daily_facts_changed')
    finalization = final.validate_supplement(Path(finalization_path).read_bytes(), profile, raw['opening'])
    if finalization != raw.get('finalization_binding') or finalization['artifact_sha256'] != ARTIFACT_SHA:
        reject('finalization_binding')
    _, events = command_state(run, output['DBMFinal'][0])
    if events != actions(run):
        reject('action_chain')
    return digest(profile)


def verify_operational_opening(attempt):
    """Re-read explicit root populations or the same accepted predecessor's rows."""
    from mta.runtime.operational_attempts import configuration_value, verify_attempt
    from mta.runtime.operational_native import read_population
    from mta.runtime.operational_opening import OPENING_TABLES, OPENING_POLICY, ACTION_TYPES
    from mta.runtime.operational_alert_sources import ABORT_OPENING_POLICY
    bindings = configuration_value(attempt.configuration)['bindings']
    if attempt.predecessor_id:
        previous = attempt.predecessor
        if (previous.run_id != attempt.run.predecessor_id or previous.status != 'SUCCEEDED'
                or previous.configuration_id != attempt.configuration_id):
            reject('operational_opening_predecessor')
        verify_attempt(previous)
        for name in (*OPENING_TABLES, 'RunAbortReasons'):
            read_population(previous, 'closing/' + name)
        return
    populations = {name: read_population(attempt, 'opening/' + name) for name in OPENING_TABLES}
    if (bindings.get('opening_policy') != OPENING_POLICY
            or bindings.get('opening_input_digest') != attempt.run.input_digest
            or bindings.get('opening_digest') != digest(populations)
            or populations['UIUploadLogActionType'] != ACTION_TYPES
            or any(rows != [] for name, rows in populations.items() if name != 'UIUploadLogActionType')
            or bindings.get('abort_opening_policy') != ABORT_OPENING_POLICY
            or bindings.get('abort_opening_digest') != digest([])
            or read_population(attempt, 'opening/RunAbortReasons') != []):
        reject('explicit_operational_opening_changed')


def verify_candidate(run, publication, attempt, repair, artifact_path, finalization_path, pick_config_path, shipment_path):
    from mta.runtime.services import read_outputs
    from mta.runtime.validation_storage import read_input
    from mta.runtime.operational_runner import validate_configuration
    from mta.runtime.operational_attempts import verify_attempt
    from mta.presentation import daily_activation, daily_requests, ancillary_live, daily_sources
    from mta.presentation.daily_preparation import required_layers, verify_layer
    from mta.presentation.admission import verify_native
    before = snapshot(run, publication, attempt, repair, artifact_path, finalization_path, pick_config_path, shipment_path)
    profile = verify_input_domain(run, read_input(run), read_outputs(run), artifact_path, finalization_path, pick_config_path, shipment_path)
    validate_configuration(attempt.configuration)
    verify_attempt(attempt)
    verify_operational_opening(attempt)
    if repair:
        verify_attempt(repair)
    source = daily_sources.receipt(run)
    remark_path = 'sources/bpr/BPRReport_RemarkDetails'
    request_path = daily_requests.PATH
    if not {remark_path, request_path} <= set(source.images):
        reject('native_remark_request_sources_required')
    if (source.images[request_path] != daily_requests.metadata(run)
            or source.images[remark_path] != ancillary_live.image_metadata(run, remark_path)):
        reject('native_capture_metadata_changed')
    ancillary_live.image_rows(run, remark_path)
    daily_activation.access_manifest(run, verify_attributes=True)
    for name in required_layers():
        verify_layer(run, name, publication.layers[name]['receipt'])
    verify_native(run)
    if snapshot(run, publication, attempt, repair, artifact_path, finalization_path, pick_config_path, shipment_path) != before:
        reject('changed_during_verification')
    return before, profile


def receipt_values(run, attempt, repair, artifact_path, finalization_path, state, profile, pick_config_path, shipment_path):
    access = state['access']
    result = dict(policy=POLICY, qualification=QUALIFICATION, code_digest=state['code'],
        artifact_path=str(Path(artifact_path).resolve()), finalization_path=str(Path(finalization_path).resolve()),
        pick_config_path=str(Path(pick_config_path).resolve()), pick_config_digest=state['pick_config'],
        shipment_path=str(Path(shipment_path).resolve()), shipment_digest=state['shipment'],
        artifact_digest=state['artifact'],
        input_digest=run.input_digest, input_manifest_digest=run.input_manifest_digest,
        profile_digest=profile, execution_revision=run.execution_revision,
        output_digest=run.output_digest, production_digest=run.production_digest,
        action_digest=state['actions'], source_digest=state['sources'],
        operations_digest=state['operations'], operational_configuration_digest=attempt.configuration_id,
        operational_source_digest=attempt.source_digest,
        predecessor_receipt_digest=state.get('predecessor_receipt',''),
        predecessor_output_digest=state.get('predecessor_output',''),
        publication_seal=access['publication_seal'], layers_digest=access['layers_digest'],
        configuration_digest=access['configuration_digest'], permissions_digest=access['permissions_digest'],
        hierarchy_digest=access['hierarchy_digest'], activation_digest=access['activation_digest'],
        btr_generation=state['generation'], binding_digest=digest(state))
    result['receipt_digest'] = digest(dict(run=str(run.pk), attempt=str(attempt.pk),
        repair=str(repair.pk) if repair else None,
        predecessor=str(run.predecessor_id) if run.predecessor_id else None, **result))
    return result


def identity(run, *, selected=True):
    from mta.runtime.models import OperationalAcceptance, DailyUiPublication
    from mta.presentation.daily_activation import require_activation
    if not enabled():
        reject('policy_required')
    row = OperationalAcceptance.objects.select_related('attempt__configuration', 'repair').get(run=run)
    publication = DailyUiPublication.objects.get(run=run)
    state = snapshot(run, publication, row.attempt, row.repair, row.artifact_path, row.finalization_path, row.pick_config_path, row.shipment_path)
    expected = receipt_values(run, row.attempt, row.repair, row.artifact_path, row.finalization_path, state, row.profile_digest, row.pick_config_path, row.shipment_path)
    if any(str(getattr(row, key)) != str(value) for key, value in expected.items()):
        reject('receipt_identity_changed')
    if row.predecessor_id != run.predecessor_id:
        reject('receipt_predecessor_changed')
    require_activation(run, publication)
    if selected and (getattr(settings, 'VF_MTA_OPERATIONAL_RECEIPT', '') != row.receipt_digest
            or str(settings.VF_BTR_REPORTING_GENERATION) != str(row.btr_generation)):
        reject('selected_receipt_or_generation_changed')
    return row


def verify(run, *, selected=True):
    row = identity(run, selected=selected)
    if run.predecessor_id:
        parent = identity(run.predecessor, selected=False)
        if row.attempt.predecessor_id != parent.attempt_id:
            reject('receipt_operational_predecessor_changed')
    from mta.runtime.models import DailyUiPublication
    state, profile = verify_candidate(run, DailyUiPublication.objects.get(run=run),
        row.attempt, row.repair, row.artifact_path, row.finalization_path, row.pick_config_path, row.shipment_path)
    if receipt_values(run, row.attempt, row.repair, row.artifact_path, row.finalization_path, state, profile, row.pick_config_path, row.shipment_path)['receipt_digest'] != row.receipt_digest:
        reject('verified_receipt_changed')
    return row


@transaction.atomic
def issue(run_id, *, output_digest, attempt_id, artifact_path, finalization_path, pick_config_path, shipment_path, repair_id=None):
    from mta.runtime.models import CalculationRun, DailyUiPublication, DailyUiActivation, OperationalAcceptance, OperationalAttempt
    if not enabled():
        reject('policy_required')
    # Offline issuer credentials must be allowed to assume this role. Serving
    # credentials must not be a member; a caller-set custom GUC is insufficient.
    with connection.cursor() as cursor:
        cursor.execute('SET LOCAL ROLE fresh_operational_acceptor')
    run = CalculationRun.objects.select_for_update().get(pk=run_id)
    if run.output_digest != output_digest or str(run.pk) == settings.VF_MTA_PUBLISHED_RUN:
        reject('explicit_unselected_output_required')
    publication = DailyUiPublication.objects.select_for_update().get(run=run)
    attempt = OperationalAttempt.objects.select_for_update().get(pk=attempt_id)
    repair = OperationalAttempt.objects.select_for_update().get(pk=repair_id) if repair_id else None
    if run.predecessor_id:
        parent = verify(run.predecessor, selected=False)
        if attempt.predecessor_id != parent.attempt_id:
            reject('own_accepted_operational_predecessor_required')
    state, profile = verify_candidate(run, publication, attempt, repair, artifact_path, finalization_path, pick_config_path, shipment_path)
    values = receipt_values(run, attempt, repair, artifact_path, finalization_path, state, profile, pick_config_path, shipment_path)
    prior = OperationalAcceptance.objects.filter(run=run).first()
    if prior:
        if prior.receipt_digest != values['receipt_digest']:
            reject('retry_tuple_changed')
        identity(run, selected=False)
        return prior
    if DailyUiActivation.objects.filter(publication=publication).exists():
        reject('preexisting_activation_not_operational')
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.operational_acceptance',%s,true)", [str(run.pk)])
        row = OperationalAcceptance.objects.create(run=run, attempt=attempt, repair=repair,
            predecessor_id=run.predecessor_id, **values)
        cursor.execute("SELECT set_config('fresh.daily_activation',%s,true)", [str(run.pk)])
        cursor.execute("SELECT set_config('fresh.operational_daily_activation',%s,true)", [row.receipt_digest])
        DailyUiActivation.objects.create(publication=publication, **state['access'])
    identity(run, selected=False)
    return row
