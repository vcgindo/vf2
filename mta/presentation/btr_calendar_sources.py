"""Bounded source directory for a selected run's BTR date window.

The first cut can read its accepted BTR import as an anchor. Each successor
references only its own immutable daily report, and retains the prior sources
that can still contribute dates. The publication owner authenticates the
previous generation before passing its directory to advance().
"""
from datetime import date, timedelta
from itertools import groupby
from uuid import UUID

from django.db import connection
from mta.domain.sql_identity_keys import group_key
from mta.presentation.btr_calendar import daily_cells
from mta.runtime.relational_state import STORAGE_TABLES, quote, table_sql, wire_value


FORMAT = 'btr-dated-import-v1'
HISTORY = 'closing/btr/BPR'
DAILY = 'reports/bpr/vf_RationedReqReport'
OPERANDS = ('PhysicalInventoryPen', 'PhysicalInventoryColor', 'DispatchPen', 'DispatchColor',
            'TechPen', 'TechColor', 'EcoPen', 'EcoColor')
TRENDS = dict(zip(('BPPTrendPhysicalInv','BufferTrendPhysicalInv','BPPTrendDispatch','BufferTrendDispatch',
                   'BPPTrendTech','BufferTrendReport','BPPTrendEcon','BufferTrendReportEcon'), OPERANDS))


def _iso(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Canonical BTR business date required')
    return parsed


def _sha(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _block(run, path):
    images = run.production_manifest['images']
    source, history = images[path], images[HISTORY]
    if (source['image'] != path or source['table'] != ('BTR/BPR' if path == HISTORY else 'BPR/vf_RationedReqReport')
            or history['image'] != HISTORY or history['table'] != 'BTR/BPR'):
        raise ValueError('BTR calendar requires its exact accepted import and source')
    # The pivot operates on the BPR wire representation. A decimal column
    # whose historical representation is text keeps its original MAX rules.
    kinds = {physical: kind for _, physical, kind in history['fields']}
    wire = [kinds[name] for name in OPERANDS] if history['count'] else []
    return dict(run=str(run.pk), day=run.business_date.isoformat(), source=source['digest'], wire=wire)


def validate(run, value):
    if (run.status != 'SUCCEEDED' or run.kind != 'DAILY_CHAIN' or run.evidence_mode != 'production'
            or run.production_manifest.get('version') != 3 or type(value) is not dict
            or set(value) != {'format','run','day','production','anchor','daily'}
            or value['format'] != FORMAT or value['run'] != str(run.pk)
            or value['day'] != run.business_date.isoformat() or value['production'] != run.production_digest
            or not _sha(value['production'])):
        raise ValueError('BTR calendar publication identity differs')
    anchor, daily = value['anchor'], value['daily']
    if not isinstance(daily, list) or len(daily) + (anchor is not None) > 90:
        raise ValueError('BTR calendar source window exceeds 90 dates')
    blocks = ([anchor] if anchor is not None else []) + daily
    previous = run.business_date - timedelta(days=90)
    owners = set()
    for b in blocks:
        if (type(b) is not dict or set(b) != {'day','run','source','wire'} or not _sha(b['source'])
                or str(UUID(b['run'])) != b['run'] or b['run'] in owners
                or type(b['wire']) is not list or len(b['wire']) not in (0,len(OPERANDS))
                or any(kind not in ('str','float','int') for kind in b['wire'])):
            raise ValueError('Invalid BTR date source')
        stamp = _iso(b['day'])
        if not previous < stamp <= run.business_date:
            raise ValueError('BTR date source order differs')
        previous = stamp
        owners.add(b['run'])
    if not blocks or blocks[-1] != _block(run, DAILY if daily else HISTORY):
        raise ValueError('BTR directory must include the exact current source')
    return value


def advance(run, *, predecessor=None, directory=None):
    """Bootstrap once, then roll forward an authenticated predecessor window."""
    if run.status != 'SUCCEEDED' or (directory is None) != (predecessor is None):
        raise ValueError('Accepted BTR run and explicit predecessor source required')
    if directory is None:
        anchor, daily = _block(run, HISTORY), []
    else:
        if run.predecessor_id != predecessor.pk or not predecessor.business_date < run.business_date:
            raise ValueError('BTR calendar requires its own earlier predecessor')
        validate(predecessor, directory)
        cutoff = (run.business_date - timedelta(days=90)).isoformat()
        anchor = directory['anchor']
        if anchor is not None and anchor['day'] <= cutoff:
            anchor = None
        daily = [b for b in directory['daily'] if b['day'] > cutoff]
        daily.append(_block(run, DAILY))
    value = dict(format=FORMAT, run=str(run.pk), day=run.business_date.isoformat(),
                 production=run.production_digest, anchor=anchor, daily=daily)
    return validate(run, value)


def _page_cells(run, directory, pairs):
    """Read from a directory authenticated by the owning publication/registrar.

    The caller retains all selected occurrences and their ordering. Only the
    lookup keys are deduplicated. Source ordinals determine input order within
    each date, including equal-valued duplicate maxima.
    """
    if not connection.in_atomic_block:
        raise ValueError('BTR calendar reads require the publication transaction')
    validate(run, directory)
    keys = {}
    for sku, loc in pairs:
        if sku is None or loc is None:
            raise ValueError('Calendar lookup requires a matched grid key')
        keys[group_key(sku, loc)] = (sku, loc)
    if not keys:
        return
    skus, locations = zip(*keys.values())
    ctes = ['keys(sku,loc) AS (SELECT * FROM unnest(%s::text[],%s::text[]))']
    params = [list(skus), list(locations)]
    selects, bindings = [], []
    blocks = {}
    def relation(table, location, stamp, owner, clause):
        # PostgreSQL can otherwise flatten the page relation and scan every
        # source occurrence before applying the already selected keys.
        columns = ','.join('f.' + quote(n) for n in OPERANDS)
        return (f'SELECT {stamp} AS stamp,{owner} AS owner,f.vf_ordinal,f."SKUCode",f.{quote(location)},{columns} '
                + clause[0] + ' CROSS JOIN LATERAL (SELECT f.* FROM ' + table_sql(table) + ' f WHERE '
                + clause[1] + ' AND lower(rtrim(f."SKUCode",\' \'))=lower(rtrim(k.sku,\' \'))'
                + f" AND lower(rtrim(f.{quote(location)},' '))=lower(rtrim(k.loc,' ')) OFFSET 0) f")
    if directory['daily']:
        dates, owners = [], []
        for block in directory['daily']:
            dates.append(block['day'])
            owners.append(block['run'])
            blocks[block['run']] = block
        ctes.append('days(stamp,owner) AS (SELECT * FROM unnest(%s::date[],%s::uuid[]))')
        params.extend([dates, owners])
        selects.append(relation('BPR/vf_RationedReqReport', 'WhCode', 'd.stamp', 'd.owner',
            ('FROM days d CROSS JOIN keys k', 'f.vf_run_id=d.owner AND f.vf_image=%s')))
        bindings.append(DAILY)
    anchor = directory['anchor']
    if anchor is not None:
        blocks[anchor['run']] = anchor
        selects.append(relation('BTR/BPR', 'WHCode', 'f."ReportDate"', '%s::uuid',
            ('FROM keys k', 'f.vf_run_id=%s AND f.vf_image=%s AND f."ReportDate">%s AND f."ReportDate"<=%s')))
        bindings.extend([anchor['run'], anchor['run'], HISTORY, run.business_date-timedelta(days=90), anchor['day']])
    sql = 'WITH ' + ','.join(ctes) + ' ' + ' UNION ALL '.join(selects) + ' ORDER BY 1,3'
    with connection.chunked_cursor() as cursor:
        cursor.execute(sql, params + bindings)
        def records():
            while batch := cursor.fetchmany(256):
                for stamp, owner, _, sku, loc, *values in batch:
                    kinds = blocks[str(owner)]['wire']
                    yield {'ReportDate': stamp, 'SKUCode': sku, 'WHCode': loc,
                           **{name: wire_value(value, kind) for name, value, kind in zip(OPERANDS, values, kinds, strict=True)}}
        for stamp, rows in groupby(records(), key=lambda row: row['ReportDate']):
            yield from daily_cells(stamp, rows)


def _trend_query(run, directory, name):
    """Complete relational image for bulk preparation and old SQL consumers.

    The current table supplies the native roster, ordinals and scalar columns.
    D1..D90 come exclusively from the referenced dated source. Joining after
    reduction preserves duplicate current roster rows. Bounded page reads can
    use the separate key lookup instead of materializing this complete image.
    """
    validate(run, directory)
    operand = TRENDS[name]
    table = 'BTR/' + name
    path = 'closing/btr/' + name
    index = OPERANDS.index(operand)
    inputs, parameters = [], []
    field = 'f.' + quote(operand)
    columns = 'f."SKUCode" COLLATE "C" AS sku,'
    anchor = directory['anchor']
    if anchor and anchor['wire']:
        inputs.append(f'SELECT {columns}f."WHCode" COLLATE "C" AS loc,f."ReportDate" AS stamp,'
                      f'%s::text AS kind,{field} AS cell,f.vf_ordinal FROM ' + table_sql('BTR/BPR') +
                      ' f WHERE f.vf_run_id=%s AND f.vf_image=%s AND f."ReportDate">%s AND f."ReportDate"<=%s')
        parameters.extend([anchor['wire'][index],anchor['run'],HISTORY,run.business_date-timedelta(days=90),anchor['day']])
    daily = [block for block in directory['daily'] if block['wire']]
    if daily:
        inputs.append(f'SELECT {columns}f."WhCode" COLLATE "C" AS loc,d.stamp,d.kind,{field} AS cell,f.vf_ordinal '
                      'FROM unnest(%s::uuid[],%s::date[],%s::text[]) d(owner,stamp,kind) JOIN ' +
                      table_sql('BPR/vf_RationedReqReport') + ' f ON f.vf_run_id=d.owner AND f.vf_image=%s')
        parameters.extend([[b['run'] for b in daily],[b['day'] for b in daily],[b['wire'][index] for b in daily],DAILY])
    is_pen = operand.endswith('Pen')
    value_type = 'numeric' if is_pen else 'text'
    if not inputs:
        inputs = [f'SELECT NULL::text AS sku,NULL::text AS loc,NULL::date AS stamp,NULL::text AS kind,'
                  f'NULL::{value_type} AS cell,NULL::bigint AS vf_ordinal WHERE FALSE']
    # BPR may decode a numeric value as text; e.g. MAX("9.00","100.00")
    # then stores 9.00 in the numeric pivot. Preserve the original comparison.
    ordering = ("""CASE WHEN kind='str' THEN cell::text END COLLATE "C" DESC NULLS LAST,
                CASE WHEN kind='float' THEN cell::double precision END DESC NULLS LAST,
                CASE WHEN kind='int' THEN trunc(cell) END DESC NULLS LAST"""
                if is_pen else 'cell COLLATE "C" DESC NULLS LAST')
    pivot = ','.join(f'max(cell) FILTER (WHERE slot={i}) AS "D{i}"' for i in range(1,91))
    days = {f'D{i}' for i in range(1,91)}
    projected = ','.join(('p.' if n in days else 'k.') + quote(n) for n, _ in STORAGE_TABLES[table])
    sql = ('WITH observations AS (' + ' UNION ALL '.join(inputs) +
           '), dated AS (SELECT DISTINCT ON (sku,loc,stamp) sku,loc,stamp-%s::date+90 AS slot,cell '
           'FROM observations ORDER BY sku,loc,stamp,' + ordering +
           ',vf_ordinal), pivots AS (SELECT sku,loc,' + pivot + ' FROM dated GROUP BY sku,loc) '
           'SELECT k.vf_run_id,k.vf_image,k.vf_ordinal,' + projected + ' FROM ' + table_sql(table) +
           ' k LEFT JOIN pivots p ON (p.sku IS NULL)=(k."SKUCode" IS NULL) '
           'AND (p.loc IS NULL)=(k."WhCode" IS NULL) '
           """AND coalesce(p.sku,'')=coalesce(k."SKUCode",'') COLLATE "C"
              AND coalesce(p.loc,'')=coalesce(k."WhCode",'') COLLATE "C" """
           'WHERE k.vf_run_id=%s AND k.vf_image=%s')
    return sql, parameters + [run.business_date,run.pk,path]
