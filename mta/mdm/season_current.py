"""Seasonality consumers over the explicitly selected, owned publication."""
from datetime import date, timedelta
from decimal import Decimal
import re
from types import SimpleNamespace

from mta.application.r1_seasonality import SEASON_FIELDS
from mta.mdm.drafts import omit_nulls
from mta.mdm.force_reads import _scope_count
from mta.mdm.force_tasks import scopes
from mta.mdm.task_reads import TaskDenied, sql_key
from mta.presentation.context import PublicationUnavailable, selected_run
from mta.presentation.rrr_sql import like_pattern
from mta.presentation.selective import image_rows
from mta.mdm.target_fixture import consumer_rows as fixture_rows, SOURCE as TARGET_SOURCE
from mta.runtime.mdm_season_models import MdmSeasonCurrent

NUMERIC = {'tn', 'dnp', 'ulc', 'bd', 'r', 'nn', 'onm', 'tp', 'sts'}


def consumer_rows(source, run, path):
    if getattr(source, 'digest', None) == TARGET_SOURCE:
        return fixture_rows(source, run, path)
    return image_rows(run, path)

def publication(source):
    from mta.mdm.season_source import require_installed
    owner = require_installed(source)
    if owner.last_run_id is None:
        raise PublicationUnavailable('seasonality_has_no_committed_publication')
    run = selected_run()
    if run.pk != owner.last_run_id:
        raise PublicationUnavailable('seasonality_selected_run_owner_mismatch')
    return run


def live_rows(source):
    return list(MdmSeasonCurrent.objects.filter(source=source).order_by('ordinal').values(*SEASON_FIELDS))


def same(a, b):
    return all(a.get(n) is not None and b.get(n) is not None and
               sql_key(a[n]) == sql_key(b[n]) for n in ('SKUCode', 'WhCode'))


def _filter(row, item):
    alias, op = item['attributeName'], item['op']
    actual = row[alias]
    wanted = item.get('value')
    wanted = '' if wanted is None else wanted
    if op in ('hasValue', 'hasNoValue'):
        empty = actual is None or (actual == 0 if alias in NUMERIC else str(actual).strip(' ') == '')
        return not empty if op == 'hasValue' else empty
    if op in ('contains', 'startsWith', 'endsWith', 'Notcontains', 'NotstartsWith', 'NotendsWith'):
        if actual is None:
            return False
        pattern = ('%' if op.endswith(('contains', 'endsWith')) else '') + str(wanted)
        pattern += '%' if op.endswith(('contains', 'startsWith')) else ''
        matched = re.fullmatch(like_pattern(pattern), str(actual), re.IGNORECASE | re.DOTALL) is not None
        return not matched if op.startswith('Not') else matched
    if actual is None:
        return op == '<>'
    if alias in NUMERIC:
        a, b = Decimal(str(actual)), Decimal(str(wanted) or '0')
    elif alias in ('sd', 'ed'):
        a, b = str(actual), str(wanted) or '1900-01-01'
    else:
        a, b = sql_key(str(actual)), sql_key(str(wanted))
    return {'=': lambda: a == b, '!=': lambda: a != b, '<>': lambda: a != b,
            '>': lambda: a > b, '>=': lambda: a >= b, '<': lambda: a < b,
            '<=': lambda: a <= b}[op]()


def projected(source, run, seasons, *, payload=None, descriptions=None):
    master = consumer_rows(source, run, 'closing/dbm/DBMMaster')
    if descriptions is None:
        skus = consumer_rows(source, run, 'closing/dbm/SKUDescriptionTbl')
        locations = consumer_rows(source, run, 'closing/dbm/SiteDescriptionTbl')
    else:
        skus, locations = descriptions
    result = []
    for s in seasons:
        multiplicity = 1 if payload is None else _scope_count(source, SimpleNamespace(**s), payload)
        for m in master:
            if not same(s, m):
                continue
            descriptions = [r for r in skus if sql_key(r['SKUCode']) == sql_key(s['SKUCode'])] or [None]
            sites = [r for r in locations if sql_key(r['WHCode']) == sql_key(s['WhCode'])] or [None]
            for sku in descriptions:
                for loc in sites:
                    row = dict(sc=s['SKUCode'], wc=s['WhCode'], sd=s['StartDate'], ed=s['EndDate'],
                        tn=s['TargetNorm'], dnp=s['DeltaNormPercentage'], ulc=s['UpperLowerCap'],
                        bd=s['BuildupDuration'], skd=sku['SKUDescription'] if sku else None,
                        wd=loc['WHDescription'] if loc else None, r=m['RLT'],
                        nn=s['NewNorm'] if s['NewNorm'] is not None else m['Norm'],
                        onm=s['OrigNorm'], tp=s['Type'], sts=s['Status'], cmt=s['Comment'])
                    result.extend(dict(row) for _ in range(multiplicity))
    return result


def read(source, payload, *, count=False):
    if int(payload['id']) != 10:
        return '' if count else None  # ADD-only masters have no current branch.
    if not payload.get('product_permissions') or not payload.get('location_permissions'):
        return '' if count else None
    run = publication(source)
    rows = [r for r in projected(source, run, live_rows(source), payload=payload)
            if all(_filter(r, f) for f in payload.get('filters') or [])]
    if count:
        return str(len(rows))
    rows.sort(key=lambda r: (sql_key(r['sc']), sql_key(r['wc'])))
    paging = payload.get('paginationParameter')
    if paging:
        page, size = int(paging['pageNumber']), int(paging['recordsPerPage'])
        rows = rows[(page - 1) * size:page * size]
    return [{f['key']: row[f['key']] for f in payload['fields']} for row in rows]


def _date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def graph(source, payload):
    sku, wh = payload['sc'], payload['wc']
    if sku is None or wh is None or sku == '' or wh == '':
        raise ValueError('Invalid SkuCode or Whcode')
    sku_scope, location_scope = scopes(source, payload)
    if sql_key(sku) not in sku_scope or sql_key(wh) not in location_scope:
        raise TaskDenied('sku_location_scope_required')
    run = publication(source)
    target = dict(SKUCode=sku, WhCode=wh)
    seasons = [r for r in live_rows(source) if same(r, target)]
    masters = [r for r in consumer_rows(source, run, 'closing/dbm/DBMMaster') if same(r, target)]
    logs = [r for r in consumer_rows(source, run, 'closing/dbm/NormChangeLogTbl') if same(r, target)]
    batches = consumer_rows(source, run, 'closing/dbm/LastBatchRunTbl')
    reasons = consumer_rows(source, run, 'closing/dbm/ReasonCodes')
    norms = []
    for s in seasons:
        for m in masters:
            duration = s['BuildupDuration'] if s['BuildupDuration'] is not None else m['RLT']
            if duration is None:
                continue
            start = _date(s['StartDate']) - timedelta(days=int(duration))
            for batch in batches:
                if batch['LastRunDate'] is None:
                    cutoff = start
                else:
                    cutoff = min(_date(batch['LastRunDate']), start)
                for row in logs:
                    if row['NormChangeDate'] is None or _date(row['NormChangeDate']) < cutoff:
                        continue
                    for reason in reasons:
                        if row['NormChangeReason'] is not None and row['NormChangeReason'] == reason['Id']:
                            norms.append(omit_nulls(dict(date=row['NormChangeDate'], old_norm=row['OldNorm'],
                                new_norm=row['NewNorm'], change_reason=reason['Reason'])))
    norms.sort(key=lambda r: r['date'], reverse=True)
    if getattr(source, 'digest', None) == TARGET_SOURCE:
        from mta.mdm.target_fixture import daily_pair_rows
        daily = daily_pair_rows(source, run, sku, wh)
    else:
        daily = [r for r in consumer_rows(source, run, 'closing/dbm/DailyConsumption') if same(r, target)]
    daily.sort(key=lambda r: (r['ReportDate'] is not None, str(r['ReportDate'] or '')), reverse=True)
    result = dict(norm=norms)
    if daily:
        result['dailyData'] = [omit_nulls(dict(date=r['ReportDate'], stock=r['Stock'], git=r['GIT']))
                               for r in daily[:180]]
    return [result]
