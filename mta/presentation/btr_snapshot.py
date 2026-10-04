"""One-time, typed BTR display preparation and direct prepared-grid reads.

Version 2 uses the existing generation selection and immutability boundary.
Counts, exports and raw clients keep the pinned version-1 reader. No activation,
calculation, source mutation or permission grant occurs in this module.
"""
import hashlib
import json
import logging
import math

from django.db import connection, transaction
from django.utils import timezone

from mta.presentation import btr, btr_display, btr_reporting, hierarchy
from mta.presentation.btr_filters import BtrPredicate, unavailable
from mta.presentation.btr_snapshot_fields import (
    TEXT_FIELDS, DISPLAY_FIELDS, SCALAR_FIELDS, DAILY_FIELDS, FILTER_FIELDS,
    display_field, filter_field,
)
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query, image_rows
from mta.runtime.models import BtrPresentationRow, BtrReportingGeneration
from mta.runtime.relational_state import quote
from mta.serialization import digest

TABLE = 'mta.' + BtrPresentationRow._meta.db_table
ROW_FIELDS = tuple(f.attname for f in BtrPresentationRow._meta.fields if f.name not in ('id', 'generation'))


def rows_identity(generation):
    checksum, count = hashlib.sha256(), 0
    for row in BtrPresentationRow.objects.filter(generation=generation).order_by('id').values_list(
            *ROW_FIELDS).iterator(chunk_size=128):
        checksum.update((json.dumps(row, ensure_ascii=False, separators=(',', ':'), default=str) + '\n').encode())
        count += 1
    return count, checksum.hexdigest()


def reference_generation(run, generation):
    reference = BtrReportingGeneration.objects.filter(
        pk=generation.qualification.get('reference_generation'), run=run, version=1,
        status='READY', eligible=True).first()
    if reference is None or reference.source_digest != digest(btr_reporting.source_identity(run)):
        raise PublicationUnavailable('btr_snapshot_reference_mismatch')
    return reference


def prepared_values(raw):
    """Build-time only: exact accepted string-to-JS display conversion."""
    converted = {name: btr_display._convert(name, '' if value is None else str(value))
                 for name, value in raw.items()}
    fields, tokens, result = [], [], {}
    for name in TEXT_FIELDS:
        result[display_field(name, 'text')] = converted[name]
    for name in DISPLAY_FIELDS:
        value = converted[name]
        if isinstance(value, float):
            if not math.isfinite(value):
                fields.append(name)
                tokens.append(btr_display._token(value))
                value = None
            result[display_field(name, 'number')] = value
            result[display_field(name, 'text')] = None
        else:
            result[display_field(name, 'number')] = None
            result[display_field(name, 'text')] = value
    available, empty = [0], [0]
    for name in DAILY_FIELDS:
        value = converted[name]
        available.append(available[-1] + int(value != '' and btr_display._parse_int_is_below_100(value)))
        empty.append(empty[-1] + int(value == ''))
    value = btr_display._availability(available[-1], 90 - empty[-1])
    result.update(availability=value if math.isfinite(value) else None,
                  available_prefix=available, empty_prefix=empty,
                  nonfinite_fields=fields, nonfinite_tokens=tokens)
    return result


def _source_rows(run, reference, branch):
    """Retained unique-source qualification makes each stored join occurrence exact."""
    ctes, params = [], []
    for alias in (*btr_reporting.ORDINALS, 'sd', 'ld'):
        path = btr_reporting.SOURCES[branch + '_' + alias if alias in ('A', 'btd') else alias]
        sql, values = image_query(run, path)
        ctes.append(alias + ' AS NOT MATERIALIZED (' + sql + ')')
        params.extend(values)
    query, values = image_query(run, btr_reporting.SOURCES['B'])
    with connection.cursor() as cursor:
        cursor.execute('SELECT "Category" FROM (' + query + ') s GROUP BY "Category" ORDER BY min(vf_ordinal)', values)
        categories = image_rows(run, btr_reporting.SOURCES['categories'])
        aliases = [(r[0], btr.category_alias_text(r[0], categories)) for r in cursor.fetchall()]
    ctes.append('cd AS (VALUES ' + ','.join(['(%s::text,%s::text)'] * len(aliases)) + ')'
                if aliases else 'cd AS (SELECT NULL::text AS column1,NULL::text AS column2 WHERE FALSE)')
    params.extend(v for pair in aliases for v in pair)
    projection = [(name, 'J.' + name) for name in ('sku_key', 'location_key', *btr_reporting.ORDINALS.values())]
    projection.append(('parent_location_type', 'parent."LocationType"'))
    projection.extend((filter_field(owner, field), owner + '.' + quote(field))
                      for owner, fields in FILTER_FIELDS.items() for field in fields)
    display = [('Source', "'" + branch + "'"), ('Category', 'cd.column2'), ('Tags', 'B."Tags"'),
               ('SKUCode', 'A."SKUCode"'), ('SKUDescription', 'sd."SKUDescription"'),
               ('WhCode', 'A."WhCode"'), ('LocationName', 'ld."WHDescription"'),
               ('Norm', 'E."Norm"'), ('VirtualNorm', 'E."VirtualNorm"'),
               ('pc', 'btd."ParentWhCode"'), ('pn', 'pld."WHDescription"')]
    display += [(day, 'A.' + quote(day)) for day in DAILY_FIELDS]
    display += [('C' + day, 'btd.' + quote(day)) for day in DAILY_FIELDS]
    display += [(name, 'btd.' + quote(field)) for name, field in (
        ('age', 'Age'), ('bc', 'BlackCount'), ('rc', 'RedCount'), ('yc', 'YellowCount'),
        ('gc', 'GreenCount'), ('blc', 'BlueCount'), ('wc', 'WhiteCount'))]
    joins = ''.join((' JOIN ' if alias == 'A' else ' LEFT JOIN ') + alias + ' ON ' + alias +
                    '.vf_ordinal=J.' + ordinal for alias, ordinal in btr_reporting.ORDINALS.items())
    joins += ' LEFT JOIN sd ON ' + equal('A."SKUCode"', 'sd."SKUCode"')
    joins += ' LEFT JOIN ld ON ' + equal('A."WhCode"', 'ld."WHCode"')
    joins += ' LEFT JOIN ld pld ON ' + equal('E."ParentWhCode"', 'pld."WHCode"')
    joins += ' LEFT JOIN la parent ON ' + equal('E."ParentWhCode"', 'parent."WHCode"')
    joins += ' LEFT JOIN cd ON ' + equal('B."Category"', 'cd.column1')
    sql = ('WITH ' + ','.join(ctes) + ' SELECT ' + ','.join(value + ' AS ' + quote(name)
           for name, value in projection + display) + ' FROM ' + btr_reporting.REF_TABLE + ' J' + joins +
           ' WHERE J.generation_id=%s AND J.branch=%s AND J.export=false ORDER BY J.id')
    # A named cursor keeps the wide build bounded; inserts use a separate cursor.
    with connection.chunked_cursor() as cursor:
        cursor.execute(sql, params + [reference.pk, branch])
        while rows := cursor.fetchmany(128):
            for values in rows:
                yield dict(zip((n for n, _ in projection), values[:len(projection)])), dict(
                    zip((n for n, _ in display), values[len(projection):]))


def build_selected():
    from mta.presentation.admission import binding, verify
    if not transaction.get_autocommit():
        raise ValueError('BTR builder requires its own transaction boundary')
    run, admission = binding()
    verify(run)
    if run.kind != 'LEGACY_UI_FIXTURE' or hierarchy.selected_manifest(run):
        raise PublicationUnavailable('btr_snapshot_requires_native_retained_fixture')
    reference = btr_reporting.selected_generation(run)
    if reference is not None and reference.version == 2:
        reference = reference_generation(run, reference)
    if reference is None or not reference.eligible:
        raise PublicationUnavailable('btr_snapshot_requires_qualified_reference')
    btr_reporting.verify_generation(reference)
    lineage = btr_reporting.source_identity(run, 2)
    source, generation = digest(lineage), None
    lock = int(source[:15], 16)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_lock(%s)', [lock])
    try:
        existing = BtrReportingGeneration.objects.filter(run=run, version=2, source_digest=source, status='READY').first()
        if existing:
            btr_reporting.verify_generation(existing)
            return existing
        BtrReportingGeneration.objects.filter(run=run, version=2, source_digest=source, status='BUILDING').update(
            status='FAILED', failure='Interrupted snapshot build; never selected', completed_at=timezone.now())
        generation = BtrReportingGeneration.objects.create(run=run, version=2, source_kind=run.kind,
            business_date=run.business_date, source_digest=source, lineage=lineage)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                cursor.execute("SET LOCAL statement_timeout='60s'")
                cursor.execute("SET LOCAL work_mem='32MB'")
            counts = {}
            for branch in ('tech', 'eco'):
                count, batch = 0, []
                for source_fields, raw in _source_rows(run, reference, branch):
                    batch.append(BtrPresentationRow(generation=generation, branch=branch,
                                                   **source_fields, **prepared_values(raw)))
                    count += 1
                    if len(batch) == 64:
                        BtrPresentationRow.objects.bulk_create(batch, batch_size=64)
                        batch.clear()
                if batch:
                    BtrPresentationRow.objects.bulk_create(batch, batch_size=64)
                if count != reference.qualification['populations'][branch + '_grid']:
                    raise PublicationUnavailable('btr_snapshot_population_mismatch')
                counts[branch] = count
            generation.row_count, generation.rows_digest = rows_identity(generation)
            if binding()[1] != admission or btr_reporting.source_identity(run, 2) != lineage:
                raise PublicationUnavailable('btr_snapshot_source_changed')
            generation.qualification = dict(reference_generation=str(reference.pk), populations=counts,
                labels=image_rows(run, btr_reporting.SOURCES['dates']), mapper='retained-js-v1')
            generation.eligible, generation.status, generation.completed_at = True, 'READY', timezone.now()
            generation.save()
        with connection.cursor() as cursor:
            # Complete visibility for the narrow permission covering indexes.
            # Serial maintenance fits the existing PostgreSQL shared-memory cap.
            cursor.execute('VACUUM (ANALYZE, PARALLEL 0) ' + TABLE)
        return generation
    except BaseException as exc:
        if generation:
            BtrReportingGeneration.objects.filter(pk=generation.pk, status='BUILDING').update(status='FAILED',
                failure=type(exc).__name__ + ': ' + str(exc), completed_at=timezone.now())
        raise
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_unlock(%s)', [lock])


def _attributes(generation):
    result = {}
    for owner, table, code, prefix, ordinal in (
        ('sa', 'SkuAttributeData', 'SKUCode', 'SL', 'sa_ordinal'),
        ('la', 'LocationAttributeData', 'WHCode', 'LL', 'la_ordinal')):
        fields = (code, *(prefix + str(i) for i in (1, 2, 3)))
        # Retain distinct source ordinals, not distinct values; never deduplicate
        # permission multiplicity. Rows absent from this grid cannot admit keys.
        sql = ('SELECT DISTINCT ' + ordinal + ',' + ','.join(quote(filter_field(owner, f)) for f in fields) +
               ' FROM ' + TABLE + ' WHERE generation_id=%s AND ' + ordinal + ' IS NOT NULL')
        with connection.cursor() as cursor:
            cursor.execute(sql, [generation.pk])
            result[table] = [dict(zip(fields, row[1:])) for row in cursor.fetchall()]
    return result


def _display_sql(columns):
    pairs = []
    for name in (*TEXT_FIELDS, *SCALAR_FIELDS, *columns, *('C' + c for c in columns)):
        if name in TEXT_FIELDS:
            value = 'S.' + quote(display_field(name, 'text'))
        else:
            number, text = ('S.' + quote(display_field(name, kind)) for kind in ('number', 'text'))
            value = ('CASE WHEN ' + number + ' IS NOT NULL THEN to_jsonb(' + number + ') WHEN ' +
                     '%s=ANY(S.nonfinite_fields) THEN \'null\'::jsonb ELSE to_jsonb(coalesce(' + text + ",'')) END")
            # Fixed internal field names only; no request text enters SQL here.
            value = value.replace('%s', "'" + name + "'")
        pairs.append("'" + name + "'," + value)
    return ' || '.join('jsonb_build_object(' + ','.join(pairs[i:i+40]) + ')' for i in range(0, len(pairs), 40))


def range_availability(available, empty, horizon, columns):
    left = max(91 - horizon, int(columns[0][1:])) if columns else 1
    right = min(90, int(columns[-1][1:])) if columns else 0
    a = available[right] - available[left - 1] if left <= right else 0
    e = empty[right] - empty[left - 1] if left <= right else 0
    return btr_display._availability(a, horizon - e)


def read_snapshot(run, generation, payload, paging):
    from mta.presentation.btr_sql import BtrFilters
    class SnapshotFilters(BtrFilters):
        def column(self, owner, name):
            _, kind = super().column(owner, name)
            field = next((f for f in FILTER_FIELDS.get(owner, {}) if f.lower() == name.lower()), None)
            if field is None:
                unavailable('missing column ' + name)
            return 'S.' + quote(filter_field(owner, field)), kind

    horizon = btr_display.display_horizon(payload)
    columns = btr.horizon_columns(run.business_date.isoformat(), payload)
    BtrPredicate(payload, [], count=False)
    products, locations = scope(payload, attributes=_attributes(generation))
    result = dict(tech=[], eco=[], labels=[{c: row[c] for c in columns}
                  for row in generation.qualification['labels']], displayPrepared=True, displayNonFinite=[])
    if not products or not locations:
        return result
    filters = SnapshotFilters(payload)
    try:
        where = filters.compile().replace('B."Category"', 'S.' + quote(filter_field('B', 'Category'))).replace(
            'btd."D90"', 'S.' + quote(filter_field('btd', 'D90')))
    except PublicationUnavailable as exc:
        unavailable(str(exc).partition(':')[2])
    parent = ' AND (' + ' OR '.join(equal('S.parent_location_type', '%s') for _ in filters.children) + ')' if filters.children else ''
    ctes, params = [], []
    for alias, codes in (('P', products), ('L', locations)):
        members = [code for code in sorted(codes) for _ in range(codes.multiplicities[code])]
        ctes.append(alias + ' AS (VALUES ' + ','.join(['(%s)'] * len(members)) + ')')
        params.extend(members)
    order = 'S.sku_key NULLS FIRST,S.location_key NULLS FIRST'
    auth = ' JOIN P ON S.sku_key=' + key('P.column1') + ' JOIN L ON S.location_key=' + key('L.column1')
    selected_name = str(payload.get('name', 'both')).lower()
    default_range = horizon == 90 and len(columns) == 90
    left, right = max(91 - horizon, int(columns[0][1:])), int(columns[-1][1:])
    # PostgreSQL arrays are one-based; element1 is our zero-day prefix. Fetch
    # only two summary differences, never decode 182 prefix cells per grid row.
    summary = ','.join('0' if default_range or left > right else
        f'S.{field}[{right + 1}]-S.{field}[{left}]' for field in ('available_prefix', 'empty_prefix'))
    for branch in ('tech', 'eco'):
        if selected_name not in (branch, 'both'):
            continue
        local = ctes + ['S AS NOT MATERIALIZED (SELECT * FROM ' + TABLE + ' WHERE generation_id=%s AND branch=%s)']
        # Preserve canonical key selection, then unfiltered key rejoin and second
        # LIMIT. Permission overlap multiplies selected keys, exactly as before.
        local.append('selected AS (SELECT S.sku_key,S.location_key FROM S' + auth + ' WHERE ' + where + parent +
                     ' ORDER BY ' + order + ' LIMIT %s OFFSET %s)')
        local.append('page AS (SELECT S.id FROM selected T JOIN S ON S.sku_key=T.sku_key AND S.location_key=T.location_key'
                     ' WHERE TRUE' + parent + ' ORDER BY ' + order + ' LIMIT %s)')
        sql = ('WITH ' + ','.join(local) + ' SELECT ' + _display_sql(columns) +
               ',S.availability,' + summary + ',S.nonfinite_fields,S.nonfinite_tokens'
               ' FROM page JOIN S ON S.id=page.id ORDER BY ' + order)
        values = params + [generation.pk, branch] + filters.params + filters.children + [paging[1], (paging[0]-1)*paging[1]] + filters.children + [paging[1]]
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            for index, (row, default, available, empty, fields, tokens) in enumerate(cursor.fetchall()):
                if isinstance(row, str):
                    row = json.loads(row)
                availability = default if default_range else btr_display._availability(available, horizon - empty)
                row['Availability'] = availability if availability is not None and math.isfinite(availability) else None
                if row['Availability'] is None:
                    result['displayNonFinite'].append([branch, index, 'Availability', 'NaN'])
                result['displayNonFinite'].extend([branch, index, field, token] for field, token in zip(fields, tokens) if field in row)
                result[branch].append(row)
    logging.getLogger(__name__).info('BTR reader=presentation generation=%s', generation.pk)
    return result
