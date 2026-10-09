"""Authenticated adapters for the already-ported canonical DBM commands."""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction

from mta.presentation.context import publication, scope
from mta.runtime.models import CalculationRun
from mta.runtime.temporal import record_command
from mta.temporal.actions import key


class ActionDenied(Exception):
    pass


@dataclass(frozen=True)
class PreacceptanceActionContext:
    """Internal action facts already verified by the explicit offline phase."""
    run: object
    output: dict
    dbm: dict
    action_timestamp: str
    idempotency_key: str


def timestamp():
    # Explicit selected legacy server civil date, not the Linux container's UTC.
    return datetime.now(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).isoformat()


def selected_pairs(payload):
    records = payload.get('data')
    if not isinstance(records, list) or not records:
        raise ValueError('nonempty_data_required')
    result = []
    for row in records:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k]
                                          for k in ('SKUCode','WHCode')):
            raise ValueError('SKUCode_and_WHCode_required')
        result.append((row['SKUCode'], row['WHCode']))
    # Source WHERE (... OR ...) treats repeated selected keys as membership,
    # never multiplying the Suggestions/DBMMaster population.
    return sorted(set(result))


@transaction.atomic
def submit(payload, actor, operation, *, preacceptance=None):
    from mta.presentation import fixture
    if preacceptance is None:
        if fixture.enabled():
            raise ActionDenied('demo_read_only')
        if not settings.VF_MTA_ACTIONS_ENABLED:
            raise ActionDenied('demo_read_only')
    elif not isinstance(preacceptance, PreacceptanceActionContext):
        raise ActionDenied('invalid_preacceptance_context')
    selected = selected_pairs(payload)
    # Lock before read/authorization/message calculation so it sees the same
    # command overlay that record_command will consume. No second state writer.
    if preacceptance is None:
        CalculationRun.objects.select_for_update().get(pk=settings.VF_MTA_PUBLISHED_RUN)
        context = publication()
        action_timestamp = timestamp()
        idempotency_key = 'http-'+str(uuid4())
    else:
        CalculationRun.objects.select_for_update().get(pk=preacceptance.run.pk)
        context = preacceptance
        action_timestamp = preacceptance.action_timestamp
        idempotency_key = preacceptance.idempotency_key
    from mta.runtime.models import OperationalAcceptance
    if OperationalAcceptance.objects.filter(run_id=context.run.pk).exists():
        raise ActionDenied('operational_acceptance_sealed')
    products, locations = scope(payload, attributes=context.output['ClosingState'][0]['importer'])
    if any(sku not in products or location not in locations for sku,location in selected):
        raise ActionDenied('selected_pair_outside_authenticated_scope')
    chosen = set(selected)
    suggestions = [row for row in context.dbm['Suggestions'] if key(row) in chosen]
    if operation == 'APPLY':
        keys = {key(row) for row in suggestions}
        masters = Counter(key(row) for row in context.dbm['DBMMaster'])
        affected = sum(key(row) in keys for row in context.dbm['NormAcceptanceTbl'])
        affected += sum(masters[key(row)] for row in suggestions)
    else:
        affected = 2*len(suggestions)  # insert sleep + delete suggestions
    event = record_command(context.run, operation=operation, selected=[list(pair) for pair in selected],
        timestamp=action_timestamp, actor=str(actor), idempotency_key=idempotency_key)
    return event, dict(data='' if operation=='APPLY' else None,
                       message='Saved Succesfully' if affected else None)
