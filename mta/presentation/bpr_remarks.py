"""Canonical BPR remark append/history over the daily live owner."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import DatabaseError

from mta.presentation import ancillary_live
from mta.presentation.context import PublicationUnavailable, selected_run
from mta.presentation.rrr_sql import key


def _literal(value, *, nullable=False):
    if value is None and nullable:
        return ''
    if not isinstance(value, str):
        raise ValueError('native string dictionary required')
    if "'" in value:
        raise PublicationUnavailable('LEG-BPR-UNESCAPED-LITERAL: NOT_PARITY')
    return value


def _run():
    run = selected_run()
    from mta.presentation.daily_preparation import production_branch
    if not production_branch(run):
        raise PublicationUnavailable('daily_BPR_remark_owner_not_selected')
    ancillary_live.image_metadata(run, ancillary_live.PATHS[ancillary_live.BPR])
    return run


def append(payload, actor):
    _run()
    rows = payload.get('data')
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise ValueError('native BPR batch invalid')
    username = _literal(actor['name'])
    keys = list(rows[0])
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('native BPR row invalid')
        for field in keys:
            _literal(row[field])
    canonical = {name.casefold(): name for name in ('SKUCode', 'WhCode', 'Remark')}
    columns = [canonical.get(name.casefold()) for name in keys]
    if (None in columns or len(set(columns)) != len(columns) or
            not {'SKUCode', 'WhCode'} <= set(columns) or len(username) > 100):
        return ''
    values = [{column: _literal(row[field]) for column, field in zip(columns, keys)}
              for row in rows]
    if any(len(row[field]) > 50 for row in values for field in ('SKUCode', 'WhCode')):
        return ''
    now = datetime.now(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).replace(
        microsecond=0, tzinfo=timezone.utc)
    try:
        return ancillary_live.append(ancillary_live.BPR, [dict(
            SKUCode=row['SKUCode'], WhCode=row['WhCode'], Remark=row.get('Remark'),
            Username=username) for row in values], actor_id=actor['id'], timestamp=now)
    except DatabaseError:
        # GenericFunction.PostQuery returns an empty string on provider failure;
        # AddRemark's deployed OR condition still reports success.
        return ''


def history(payload):
    run = _run()
    sku = _literal(payload.get('skucode'), nullable=True)
    location = _literal(payload.get('whcode'), nullable=True)
    sql, params = ancillary_live.image_query(
        run, ancillary_live.PATHS[ancillary_live.BPR], include_live=True)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT "Remark","RemarkDate","Username" FROM (' + sql +
                       ') M WHERE ' + key('M."SKUCode"') + '=' + key('%s') +
                       ' AND ' + key('M."WhCode"') + '=' + key('%s') +
                       ' ORDER BY "RemarkDate" DESC', [*params, sku, location])
        rows = cursor.fetchall()
    return [{name: value for name, value in dict(
        r=remark,
        rd=stamp.astimezone(timezone.utc).replace(tzinfo=None).isoformat(
            timespec='milliseconds' if stamp.microsecond else 'seconds'),
        un=username).items() if value is not None}
        for remark, stamp, username in rows]
