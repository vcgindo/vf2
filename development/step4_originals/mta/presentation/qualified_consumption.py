"""Explicit two-owner qualified consumption; never a migration-parity waiver.

The approved file is a presentation supplement. It never backfills a calculation
input/source receipt, supplies a calculated row, or labels the native flag PASS.
"""
import hashlib
import inspect
import json
from pathlib import Path

from django.conf import settings
from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable

POLICY = 'cohort2-qualified-consumption-v1'
PIN_SHA = '164f203080d16f20dea24b8175beff934ac185b073f90ecad9d747a9f94d0604'
HIERARCHY_SHA = '03f37e4c809e70d6f6e2b5f65269021dbe30709bf6a2a6de6d0fb8cb2c469f3f'
REMARKS = 'sources/bpr/BPRReport_RemarkDetails'
REQUESTS = 'sources/planning/OpenExpediteRequests'


def enabled():
    value = getattr(settings, 'VF_MTA_CONSUMPTION_POLICY', '')
    if value not in ('', POLICY):
        raise PublicationUnavailable('unknown_consumption_policy')
    return value == POLICY


def pins():
    raw = (Path(__file__).resolve().parents[2] /
           'baseline/cohort3-consumption-v1.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != PIN_SHA:
        raise PublicationUnavailable('qualified_consumption_pins_changed')
    return json.loads(raw)


def owner(run):
    if not enabled():
        raise PublicationUnavailable('qualified_consumption_not_enabled')
    manifest = pins()
    matches = [row for row in manifest['runs'] if row['run_id'] == str(run.pk)]
    if len(matches) != 1:
        raise PublicationUnavailable('qualified_consumption_owner_not_approved')
    expected = matches[0]
    if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED'
            or str(run.business_date) != expected['date']
            or (str(run.predecessor_id) if run.predecessor_id else None) != expected['predecessor']
            or any(getattr(run, field) != expected[field] for field in
                   ('input_digest', 'output_digest', 'production_digest'))
            or run.parity_summary != {}):
        raise PublicationUnavailable('qualified_consumption_owner_changed')
    if (not getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False)
            or getattr(settings, 'VF_MTA_SYNTHETIC_ROSTER', '') != 'core-without-bor-v1'
            or getattr(settings, 'VF_MTA_ACTIONS_ENABLED', False)):
        raise PublicationUnavailable('qualified_consumption_configuration_denied')
    for key, allowed in (('VF_MTA_PERMISSIONS_SHA256', manifest['catalogue_sha256']),
                         ('VF_MTA_HIERARCHY_SHA256', HIERARCHY_SHA)):
        if getattr(settings, key, '') not in ('', allowed):
            raise PublicationUnavailable('qualified_consumption_access_changed')
    return expected


def identity(run):
    """Check bounded owner/operation/action metadata on every admission binding."""
    expected = owner(run)
    from mta.presentation.daily_sources import receipt
    source = receipt(run)
    if (source.images_digest != expected['daily_source_images_digest']
            or source.recipe_digest != expected['daily_source_recipe']):
        raise PublicationUnavailable('qualified_consumption_sources_changed')
    from mta.runtime.operational_models import OperationalAttempt
    from mta.runtime.operational_attempts import configuration_value
    attempt = OperationalAttempt.objects.select_related('configuration').get(
        pk=expected['operational_attempt'], run=run, status='SUCCEEDED')
    if (attempt.configuration_id != expected['operational_configuration']
            or attempt.action_digest != expected['action_digest']
            or attempt.source_digest != expected['source_digest']
            or attempt.run_output_digest != run.output_digest
            or attempt.business_date != run.business_date):
        raise PublicationUnavailable('qualified_consumption_operations_changed')
    configuration_value(attempt.configuration)
    predecessor = next((row['operational_attempt'] for row in pins()['runs']
                        if row['run_id'] == expected['predecessor']), None)
    if (str(attempt.predecessor_id) if attempt.predecessor_id else None) != predecessor:
        raise PublicationUnavailable('qualified_consumption_predecessor_changed')
    actions = []
    for event in run.commands.order_by('id'):
        if digest(event.payload) != event.digest:
            raise PublicationUnavailable('qualified_consumption_action_changed')
        actions.append(dict(id=event.pk, digest=event.digest,
                            before=event.before_digest, after=event.after_digest))
    if digest(actions) != expected['action_digest']:
        raise PublicationUnavailable('qualified_consumption_action_roster_changed')
    operations = list(attempt.operations.order_by('ordinal').values())
    if not operations or any(row['status'] != 'SUCCEEDED' for row in operations):
        raise PublicationUnavailable('qualified_consumption_operation_incomplete')
    # All operation fields, including bounded result/provenance receipts, bind
    # startup and request identities. Full file/state verification remains below.
    metadata = json.loads(json.dumps(operations, default=str))
    return digest(dict(policy=POLICY, pins=PIN_SHA, owner=expected,
                       operations=metadata, actions=actions))


def verify(run):
    """Actual native readback/files/intents/backup checks, without calculation."""
    before = identity(run)
    from mta.runtime.operational_models import OperationalAttempt
    from mta.runtime.operational_attempts import verify_attempt
    expected = owner(run)
    attempt = OperationalAttempt.objects.get(pk=expected['operational_attempt'])
    verify_attempt(attempt)
    repair = OperationalAttempt.objects.get(pk=pins()['repairs'][str(run.pk)],
        run=run, repair_of=attempt, status='SUCCEEDED')
    verify_attempt(repair)
    for path in (REMARKS, REQUESTS):
        empty_metadata(run, path)
    if identity(run) != before:
        raise PublicationUnavailable('qualified_consumption_changed_during_verification')
    return before


def recipe():
    return digest(dict(policy=POLICY, pins=PIN_SHA,
                       implementation=inspect.getsource(inspect.getmodule(recipe))))


def _empty_source(run, path):
    owner(run)
    from mta.runtime.models import DailySourceReceipt
    if path in DailySourceReceipt.objects.get(run=run).images:
        raise PublicationUnavailable('qualified_empty_conflicts_with_native_source')
    if path == REMARKS:
        from mta.runtime.ancillary_models import BprCapturedRemark, RemarkCapture
        from mta.presentation.ancillary_live import _models, BPR
        if RemarkCapture.objects.filter(run=run, family=BPR).exists():
            raise PublicationUnavailable('qualified_empty_remark_capture_conflict')
        model, fields = BprCapturedRemark, _models(BPR)[2]
    elif path == REQUESTS:
        from mta.runtime.daily_request_models import DailyCapturedRequest, DailyRequestCapture
        from mta.presentation.daily_requests import FIELDS
        if DailyRequestCapture.objects.filter(run=run).exists():
            raise PublicationUnavailable('qualified_empty_request_capture_conflict')
        model, fields = DailyCapturedRequest, FIELDS
    else:
        raise PublicationUnavailable('qualified_empty_path_not_approved')
    if model.objects.filter(capture__run=run).exists():
        raise PublicationUnavailable('qualified_empty_rows_not_empty')
    return model, fields


def empty_metadata(run, path):
    """None retains the strict reader; no catch-and-default for missing sources."""
    if not enabled() or path not in (REMARKS, REQUESTS):
        return None
    model, fields = _empty_source(run, path)
    return dict(image=path, table=model._meta.db_table, count=0, digest=digest([]),
                fields=[[field, field, 'str'] for field in fields],
                presentation_supplement=PIN_SHA, policy=POLICY)


def empty_query(run, path):
    item = empty_metadata(run, path)
    if item is None:
        return None
    model, fields = _empty_source(run, path)
    # Read the existing typed relation, scoped through its run-owned capture.
    # Never manufacture a SELECT of constants that could conceal actual rows.
    from mta.runtime.relational_state import quote
    capture = model._meta.get_field('capture').remote_field.model
    return ('SELECT r.ordinal AS vf_ordinal,' +
            ','.join('r.' + quote(field) for field in fields) +
            ' FROM mta.' + quote(model._meta.db_table) + ' r JOIN mta.' +
            quote(capture._meta.db_table) + ' c ON r.capture_id=c.' +
            quote(capture._meta.pk.column) + ' WHERE c.run_id=%s'), [run.pk]
