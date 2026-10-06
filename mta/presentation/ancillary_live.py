"""Explicit live remark ownership and retry-stable daily captures."""
from datetime import date, datetime, time, timedelta, timezone
import json
from django.conf import settings
from django.db import connection, transaction

from mta.presentation.context import PublicationUnavailable
from mta.runtime.relational_state import quote
from mta.serialization import digest


BPR = 'BPRReport_RemarkDetails'
BOR = 'BORReport_RemarkDetails'
BOROA = 'BORReport_OARemarkDetails'
PATHS = {
    BPR: 'sources/bpr/BPRReport_RemarkDetails',
    BOR: 'sources/bor/BORReport_RemarkDetails',
    BOROA: 'sources/boroa/BORReport_OARemarkDetails',
}


def serving_live(run):
    """True only for enabled daily serving, never the owned preparation transaction."""
    if (getattr(run, 'kind', None) != 'DAILY_CHAIN' or
            not getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False)):
        return False
    if connection.vendor == 'postgresql' and connection.in_atomic_block:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('fresh.daily_publication_build',true)")
            if cursor.fetchone()[0] == str(run.pk):
                return False
    return True


def _models(family):
    from mta.runtime.ancillary_models import (
        BprCapturedRemark, BprLiveRemark, BorCapturedRemark, BorLiveRemarkDaily,
        BorOaCapturedRemark, BorOaLiveRemarkDaily,
    )
    try:
        return {
            BPR: (BprLiveRemark, BprCapturedRemark,
                  ('SKUCode', 'WhCode', 'Remark', 'Username', 'RemarkDate')),
            BOR: (BorLiveRemarkDaily, BorCapturedRemark,
                  ('SKUCode', 'WhCode', 'Remark', 'Username', 'RemarkDate', 'SupplierCode')),
            BOROA: (BorOaLiveRemarkDaily, BorOaCapturedRemark,
                    ('SKUCode', 'WhCode', 'Remark', 'Username', 'RemarkDate', 'SupplierCode')),
        }[family]
    except KeyError as exc:
        raise ValueError('Unknown remark family: ' + str(family)) from exc


def family_for_path(path):
    matches = [family for family, value in PATHS.items() if value == path]
    if len(matches) != 1:
        raise PublicationUnavailable('daily_remark_source_path_unknown:' + str(path))
    return matches[0]


def initialize_owner(family, *, provenance_digest, provenance_receipt):
    """Explicitly establish an initially empty owner; never called by readers."""
    from mta.runtime.ancillary_models import RemarkOwner
    if not isinstance(provenance_digest, str) or len(provenance_digest) != 64:
        raise ValueError('Remark owner provenance digest invalid')
    if (not isinstance(provenance_receipt, dict) or not provenance_receipt or
            len(json.dumps(provenance_receipt, sort_keys=True, separators=(',', ':')).encode()) > 8192 or
            digest(provenance_receipt) != provenance_digest):
        raise ValueError('Remark owner provenance receipt invalid')
    _models(family)
    with transaction.atomic():
        owner = RemarkOwner.objects.select_for_update().filter(pk=family).first()
        if owner is None:
            return RemarkOwner.objects.create(
                family=family, provenance_digest=provenance_digest,
                provenance_receipt=provenance_receipt, next_ordinal=0)
        if (owner.provenance_digest != provenance_digest or
                owner.provenance_receipt != provenance_receipt):
            raise PublicationUnavailable('daily_remark_owner_provenance_changed:' + family)
        return owner


def owner(family, *, lock=False):
    from mta.runtime.ancillary_models import RemarkOwner
    query = RemarkOwner.objects.select_for_update() if lock else RemarkOwner.objects
    value = query.filter(pk=family).first()
    if value is None:
        raise PublicationUnavailable('daily_remark_owner_not_initialized:' + family)
    return value


def _wire(record, fields):
    return {field: getattr(record, field) for field in fields}


def _rows_digest(rows):
    return digest([{**row, 'RemarkDate': (row['RemarkDate'].isoformat()
                   if isinstance(row['RemarkDate'], datetime) else row['RemarkDate'])} for row in rows])


def _snapshot_digest(rows):
    return _rows_digest(rows)


def _capture_metadata(capture):
    _, captured_model, fields = _models(capture.family)
    path = PATHS[capture.family]
    return dict(image=path, table=captured_model._meta.db_table,
                count=capture.row_count, digest=capture.rows_digest,
                fields=[[field, field, 'str'] for field in fields],
                family=capture.family, provenance_digest=capture.provenance_digest,
                watermark=capture.watermark,
                cutoff=capture.cutoff.isoformat() if capture.cutoff is not None else None)


def snapshot_all(*, business_date, bpr_remark_horizon=None):
    """Return JSON-safe pre-run facts for every explicitly initialized owner."""
    from mta.runtime.ancillary_models import RemarkOwner
    if isinstance(business_date, str):
        try:
            business_date = date.fromisoformat(business_date)
        except ValueError as exc:
            raise ValueError('Daily remark business date invalid') from exc
    if not isinstance(business_date, date) or isinstance(business_date, datetime):
        raise ValueError('Daily remark business date invalid')
    snapshots = {}
    with transaction.atomic():
        owners = list(RemarkOwner.objects.select_for_update().filter(
            family__in=(BPR, BOR, BOROA)).order_by('family'))
        for current_owner in owners:
            family = current_owner.family
            if (not current_owner.provenance_receipt or
                    digest(current_owner.provenance_receipt) != current_owner.provenance_digest):
                raise PublicationUnavailable('daily_remark_owner_provenance_changed:' + family)
            live_model, _, fields = _models(family)
            live = list(live_model.objects.filter(
                owner=current_owner, ordinal__lt=current_owner.next_ordinal).order_by('ordinal'))
            if [row.ordinal for row in live] != list(range(current_owner.next_ordinal)):
                raise PublicationUnavailable('daily_remark_live_ordinal_changed:' + family)
            cutoff = None
            if family == BPR:
                if type(bpr_remark_horizon) is not int:
                    raise ValueError('BPR remark horizon required')
                cutoff = datetime.combine(business_date, time.min, tzinfo=timezone.utc) - \
                    timedelta(days=bpr_remark_horizon)
                live = [row for row in live if row.RemarkDate > cutoff]
            rows = [dict(source_ordinal=row.ordinal, **{
                field: (getattr(row, field).isoformat() if field == 'RemarkDate'
                        else getattr(row, field)) for field in fields}) for row in live]
            snapshots[family] = dict(
                provenance_digest=current_owner.provenance_digest,
                provenance_receipt=current_owner.provenance_receipt,
                watermark=current_owner.next_ordinal,
                cutoff=cutoff.isoformat() if cutoff is not None else None, rows=rows,
                rows_digest=_snapshot_digest(rows))
    return snapshots


def _validate_snapshot(family, snapshot):
    _, _, fields = _models(family)
    if not isinstance(snapshot, dict) or set(snapshot) != {
            'provenance_digest', 'provenance_receipt', 'watermark', 'cutoff', 'rows', 'rows_digest'}:
        raise PublicationUnavailable('daily_remark_input_invalid:' + family)
    rows = snapshot['rows']
    try:
        cutoff = (datetime.fromisoformat(snapshot['cutoff'])
                  if snapshot['cutoff'] is not None else None)
    except (TypeError, ValueError) as exc:
        raise PublicationUnavailable('daily_remark_input_cutoff_invalid:' + family) from exc
    source_ordinals = [row.get('source_ordinal') for row in rows] if isinstance(rows, list) else []
    if (not isinstance(snapshot['provenance_digest'], str) or
            len(snapshot['provenance_digest']) != 64 or
            not isinstance(snapshot['provenance_receipt'], dict) or
            not snapshot['provenance_receipt'] or
            digest(snapshot['provenance_receipt']) != snapshot['provenance_digest'] or
            not isinstance(snapshot['rows_digest'], str) or len(snapshot['rows_digest']) != 64 or
            not isinstance(rows, list) or type(snapshot['watermark']) is not int or
            snapshot['watermark'] < 0 or
            (family == BPR) != (cutoff is not None) or
            (cutoff is not None and cutoff.tzinfo is None) or
            any(type(value) is not int for value in source_ordinals) or
            source_ordinals != sorted(source_ordinals) or
            len(set(source_ordinals)) != len(rows) or
            any(value < 0 or value >= snapshot['watermark'] for value in source_ordinals) or
            any(set(row) != {'source_ordinal', *fields} for row in rows) or
            _snapshot_digest(rows) != snapshot['rows_digest']):
        raise PublicationUnavailable('daily_remark_input_changed:' + family)
    for row in rows:
        try:
            stamp = datetime.fromisoformat(row['RemarkDate'])
        except (TypeError, ValueError) as exc:
            raise PublicationUnavailable('daily_remark_input_timestamp_invalid:' + family) from exc
        if stamp.tzinfo is None:
            raise PublicationUnavailable('daily_remark_input_timestamp_invalid:' + family)
        if cutoff is not None and stamp <= cutoff:
            raise PublicationUnavailable('daily_remark_input_retention_changed:' + family)
        required = ('SKUCode', 'WhCode') + (() if family == BPR else ('SupplierCode',))
        if any(not isinstance(row[field], str) or len(row[field]) > 50 for field in required):
            raise PublicationUnavailable('daily_remark_input_key_invalid:' + family)
        if row['Remark'] is not None and not isinstance(row['Remark'], str):
            raise PublicationUnavailable('daily_remark_input_remark_invalid:' + family)
        username_limit = 50 if family == BOROA else 100
        if (row['Username'] is not None and
                (not isinstance(row['Username'], str) or len(row['Username']) > username_limit)):
            raise PublicationUnavailable('daily_remark_input_username_invalid:' + family)
    return rows


def bind_snapshot(run, family, snapshot):
    """Bind raw pre-run facts to typed rows; retries verify the same raw bag."""
    from mta.runtime.ancillary_models import RemarkCapture
    live_model, captured_model, fields = _models(family)
    rows = _validate_snapshot(family, snapshot)
    cutoff = (datetime.fromisoformat(snapshot['cutoff'])
              if snapshot['cutoff'] is not None else None)
    with transaction.atomic():
        capture = RemarkCapture.objects.select_for_update().filter(run=run, family=family).first()
        if capture is not None:
            records = list(captured_model.objects.filter(capture=capture).order_by('ordinal'))
            stored = [dict(source_ordinal=row.source_ordinal, **_wire(row, fields)) for row in records]
            ordinals = [row.ordinal for row in records]
            if (capture.provenance_digest != snapshot['provenance_digest'] or
                    capture.watermark != snapshot['watermark'] or
                    capture.cutoff != cutoff or
                    capture.rows_digest != snapshot['rows_digest'] or
                    ordinals != list(range(capture.row_count)) or
                    _rows_digest(stored) != capture.rows_digest):
                raise PublicationUnavailable('daily_remark_capture_changed:' + family)
            return _capture_metadata(capture)
        capture = RemarkCapture.objects.create(
            run=run, family=family, provenance_digest=snapshot['provenance_digest'],
            watermark=snapshot['watermark'], cutoff=cutoff, row_count=len(rows),
            rows_digest=snapshot['rows_digest'])
        captured_model.objects.bulk_create([
            captured_model(capture=capture, ordinal=index,
                source_ordinal=row['source_ordinal'], **{
                    field: (datetime.fromisoformat(row[field]) if field == 'RemarkDate'
                            else row[field]) for field in fields})
            for index, row in enumerate(rows)
        ])
        stored = list(captured_model.objects.filter(capture=capture).order_by('ordinal'))
        if ([row.ordinal for row in stored] != list(range(len(rows))) or
                [row.source_ordinal for row in stored] !=
                    [row['source_ordinal'] for row in rows] or
                _rows_digest([dict(source_ordinal=row.source_ordinal, **_wire(row, fields))
                              for row in stored]) != capture.rows_digest):
            raise PublicationUnavailable('daily_remark_capture_write_changed:' + family)
        return _capture_metadata(capture)


def bind_snapshots(run, snapshots):
    if not isinstance(snapshots, dict) or set(snapshots) - {BPR, BOR, BOROA}:
        raise PublicationUnavailable('daily_remark_inputs_invalid')
    return {PATHS[family]: bind_snapshot(run, family, snapshot)
            for family, snapshot in snapshots.items()}


def _capture(run, family):
    from mta.runtime.ancillary_models import RemarkCapture
    value = RemarkCapture.objects.filter(run=run, family=family).first()
    if value is None:
        raise PublicationUnavailable('daily_remark_capture_missing:' + family)
    return value


def image_metadata(run, path):
    return _capture_metadata(_capture(run, family_for_path(path)))


def image_rows(run, path, *, include_live=False):
    family = family_for_path(path)
    live_model, captured_model, fields = _models(family)
    capture = _capture(run, family)
    records = list(captured_model.objects.filter(capture=capture).order_by('ordinal'))
    rows = [_wire(row, fields) for row in records]
    stored = [dict(source_ordinal=row.source_ordinal, **values)
              for row, values in zip(records, rows)]
    if (len(rows) != capture.row_count or [row.ordinal for row in records] != list(range(len(rows))) or
            _rows_digest(stored) != capture.rows_digest):
        raise PublicationUnavailable('daily_remark_capture_changed:' + family)
    if include_live:
        current_owner = owner(family)
        if current_owner.provenance_digest != capture.provenance_digest:
            raise PublicationUnavailable('daily_remark_owner_provenance_changed:' + family)
        live = live_model.objects.filter(
            owner=current_owner, ordinal__gte=capture.watermark)
        if capture.cutoff is not None:
            live = live.filter(RemarkDate__gt=capture.cutoff)
        rows.extend(_wire(row, fields) for row in live.order_by('ordinal'))
    return [{field: (value.isoformat() if field == 'RemarkDate' else value)
             for field, value in row.items()} for row in rows]


def image_query(run, path, *, include_live=False):
    family = family_for_path(path)
    live_model, captured_model, fields = _models(family)
    capture = _capture(run, family)
    selected = ','.join(quote(field) for field in fields)
    captured = ('SELECT ordinal AS vf_ordinal,' + selected + ' FROM mta.' +
                quote(captured_model._meta.db_table) + ' WHERE capture_id=%s')
    params = [capture.pk]
    if not include_live:
        return captured, params
    current_owner = owner(family)
    if current_owner.provenance_digest != capture.provenance_digest:
        raise PublicationUnavailable('daily_remark_owner_provenance_changed:' + family)
    live = ('SELECT (%s + ordinal - %s) AS vf_ordinal,' + selected + ' FROM mta.' +
            quote(live_model._meta.db_table) + ' WHERE owner_id=%s AND ordinal>=%s')
    live_params = [capture.row_count, capture.watermark, family, capture.watermark]
    if capture.cutoff is not None:
        live += ' AND "RemarkDate">%s'
        live_params.append(capture.cutoff)
    return captured + ' UNION ALL ' + live, [*params, *live_params]


def publication_rows(run):
    """Typed named-image payloads for the daily source publisher."""
    from mta.runtime.ancillary_models import RemarkCapture
    families = RemarkCapture.objects.filter(run=run).values_list('family', flat=True)
    return {PATHS[family]: image_rows(run, PATHS[family]) for family in families}


def publication_metadata(run):
    from mta.runtime.ancillary_models import RemarkCapture
    captures = RemarkCapture.objects.filter(run=run).order_by('family')
    return {PATHS[capture.family]: _capture_metadata(capture) for capture in captures}


def append(family, values, *, actor_id, timestamp):
    """Append a canonical batch under one owner lock and ordinal allocation."""
    live_model, _, _ = _models(family)
    with transaction.atomic():
        current_owner = owner(family, lock=True)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.daily_remark_actor',%s,true)",
                           [str(actor_id)])
        first = current_owner.next_ordinal
        live_model.objects.bulk_create([
            live_model(owner=current_owner, ordinal=first + index,
                       actor_id=str(actor_id), RemarkDate=timestamp, **row)
            for index, row in enumerate(values)
        ])
        current_owner.next_ordinal = first + len(values)
        current_owner.save(update_fields=['next_ordinal'])
    return str(len(values))
