"""Generation-bound current shipment edits and separately owned live histories.

Readers never initialize owners or mutate frozen shipment/request captures.
"""
import json
from datetime import datetime, time, timedelta, timezone
from django.db import connection, transaction
from django.conf import settings
from mta.presentation.context import PublicationUnavailable
from mta.presentation import daily_transit
from mta.runtime.models import (LogisticsHistoryOwner, TransitLiveGeneration,
    TransitAnnotation, TransitRemarkHistory, ExpediteRemarkHistory)
from mta.serialization import digest, storage

OWNER = 'LogisticsWorkflow'


def enabled():
    return getattr(settings,'VF_MTA_LOGISTICS_CURRENT',False)


def history_owner(*, lock=False):
    if not enabled():
        raise PublicationUnavailable('logistics_workflows_not_enabled')
    query = LogisticsHistoryOwner.objects.select_for_update() if lock else LogisticsHistoryOwner.objects
    owner = query.filter(pk=OWNER).first()
    if owner is None or digest(owner.provenance) != owner.provenance_digest:
        raise PublicationUnavailable('logistics_history_owner_missing_or_changed')
    return owner


@transaction.atomic
def initialize(run, *, provenance):
    """Explicit native source registration, including legitimately empty rows."""
    from mta.presentation.selective import image_metadata, image_rows
    item = image_metadata(run, daily_transit.PATH)
    image_rows(run, daily_transit.PATH)  # Validate the complete typed population.
    if (not isinstance(provenance, dict) or not provenance or
            len(json.dumps(provenance)) > 8192):
        raise ValueError('Bounded explicit logistics provenance required')
    owner = LogisticsHistoryOwner.objects.select_for_update().filter(pk=OWNER).first()
    if owner is None:
        owner = LogisticsHistoryOwner.objects.create(name=OWNER,
            provenance=provenance, provenance_digest=digest(provenance))
    if owner.provenance_digest != digest(provenance):
        raise PublicationUnavailable('logistics_owner_provenance_changed')
    generation, _ = TransitLiveGeneration.objects.get_or_create(run=run,
        defaults=dict(source_digest=item['digest']))
    if generation.source_digest != item['digest']:
        raise PublicationUnavailable('logistics_shipment_generation_changed')
    return generation


def generation(run, *, lock=False):
    from mta.presentation.selective import image_metadata
    query = TransitLiveGeneration.objects.select_for_update() if lock else TransitLiveGeneration.objects
    value = query.filter(run=run).first()
    if value is None or value.source_digest != image_metadata(run, daily_transit.PATH)['digest']:
        raise PublicationUnavailable('logistics_shipment_generation_missing_or_changed')
    return value


def transit_rows(run, *, include_live=True, native_rows=None):
    from mta.presentation.selective import image_rows
    rows = image_rows(run, daily_transit.PATH) if native_rows is None else native_rows
    if not include_live or not enabled():
        return rows
    # An untouched new generation is exactly its validated native source. Old
    # annotations cannot follow an order into a later shipment refresh.
    value = TransitLiveGeneration.objects.filter(run=run).first()
    if value is None:
        return rows
    generation(run)
    edits = {r.source_ordinal: r for r in TransitAnnotation.objects.filter(generation=value)}
    if any(ordinal >= len(rows) for ordinal in edits):
        raise PublicationUnavailable('logistics_annotation_source_ordinal_changed')
    result = []
    for ordinal, row in enumerate(rows):
        edit = edits.get(ordinal)
        result.append(row if edit is None else dict(row,
            CurrentLocationCode=edit.CurrentLocationCode,
            ETA=storage(edit.ETA), Remark=edit.Remark))
    return result


def serving_transit_rows(run, native_rows=None):
    from mta.presentation.ancillary_live import serving_live
    return transit_rows(run,include_live=enabled() and serving_live(run),native_rows=native_rows)


def current_requests(*, lock=False):
    """Explicit live choice; daily_requests.rows/query remain frozen-only."""
    from mta.presentation import daily_requests
    from mta.runtime.models import DailyRequestOwner, DailyOpenRequest
    query = DailyRequestOwner.objects.select_for_update() if lock else DailyRequestOwner.objects
    owner = query.filter(pk=daily_requests.OWNER).first()
    if owner is None or digest(owner.provenance) != owner.provenance_digest:
        raise PublicationUnavailable('logistics_request_owner_missing_or_changed')
    rows = DailyOpenRequest.objects.filter(owner=owner).order_by('ordinal')
    if lock:
        rows = rows.select_for_update()
    return owner, list(rows)


@transaction.atomic
def retain_history(*, business_date, horizon):
    """ClearHistoryData_BPR: both history dates <= midnight cutoff are removed."""
    if type(horizon) is not int:
        raise ValueError('Native BPR remark horizon required')
    owner = history_owner(lock=True)
    cutoff = datetime.combine(business_date, time.min, tzinfo=timezone.utc)-timedelta(days=horizon)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.logistics_retention_cutoff',%s,true)", [cutoff.isoformat()])
    counts = (TransitRemarkHistory.objects.filter(owner=owner, RemarksDate__lte=cutoff).delete()[0],
              ExpediteRemarkHistory.objects.filter(owner=owner, RemarkDate__lte=cutoff).delete()[0])
    owner.revision += 1
    owner.save(update_fields=['revision'])
    return counts
