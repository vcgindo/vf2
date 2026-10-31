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
from django.conf import settings
from django.utils import timezone

from mta.presentation import btr, btr_display, btr_reporting, hierarchy
from mta.presentation.btr_copy import write_batch
from mta.presentation.btr_filters import BtrPredicate, unavailable
from mta.presentation.btr_snapshot_fields import (
    TEXT_FIELDS, DISPLAY_FIELDS, SCALAR_FIELDS, DAILY_FIELDS, FILTER_FIELDS,
    display_field, filter_field,
)
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query, image_rows
from mta.runtime.models import BtrPresentationRow, BtrReportingGeneration, BtrScopeDimension
from mta.runtime.relational_state import quote
from mta.serialization import digest

TABLE = 'mta.' + BtrPresentationRow._meta.db_table
ROW_FIELDS = tuple(f.attname for f in BtrPresentationRow._meta.fields if f.name not in ('id', 'generation'))
SCOPE_SOURCES = (
    ('sa', 'SkuAttributeData', 'SKUCode', 'SL', 'sa_ordinal'),
    ('la', 'LocationAttributeData', 'WHCode', 'LL', 'la_ordinal'),
)


def _collect_dimensions(dimensions, source_fields):
    for owner, _table, code, prefix, ordinal in SCOPE_SOURCES:
        if source_fields[ordinal] is not None:
            dimensions[owner].add((source_fields[ordinal], *(source_fields[filter_field(owner, name)]
                for name in (code, *(prefix + str(i) for i in (1, 2, 3))))))


def _save_dimensions(generation, dimensions):
    BtrScopeDimension.objects.bulk_create([
        BtrScopeDimension(generation=generation, owner=owner, source_ordinal=row[0],
            code=row[1], level_1=row[2], level_2=row[3], level_3=row[4])
        for owner, rows in dimensions.items() for row in sorted(rows, key=lambda row: row[0])
    ], batch_size=500)


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


def _source_operands(run, reference, generation):
    """Give fresh driving populations statistics in their owning transaction.

    Shared-table statistics cannot describe an uncommitted generation UUID.
    One-row estimates for a freshly inserted run/image can turn ordinal joins
    into repeated full run scans. Keep every occurrence, original id and typed
    source value; never change operational facts or durable reporting rows.
    """
    name = connection.ops.quote_name('vf_btr_snapshot_ref_' + generation.pk.hex)
    with connection.cursor() as cursor:
        cursor.execute('CREATE TEMP TABLE ' + name + ' ON COMMIT DROP AS '
            'SELECT * FROM ' + btr_reporting.REF_TABLE +
            ' WHERE generation_id=%s AND export=false', [reference.pk])
        cursor.execute('ANALYZE ' + name)
    operands = {'reference': 'pg_temp.' + name, 'sources': {}}
    for branch in ('tech', 'eco'):
        for alias in (*btr_reporting.ORDINALS, 'sd', 'ld'):
            path = btr_reporting.SOURCES[branch + '_' + alias if alias in ('A', 'btd') else alias]
            if path in operands['sources']:
                continue
            query, params = image_query(run, path)
            source = connection.ops.quote_name('vf_btr_snapshot_' + generation.pk.hex + '_' + str(len(operands['sources'])))
            with connection.cursor() as cursor:
                cursor.execute('CREATE TEMP TABLE ' + source + ' ON COMMIT DROP AS SELECT * FROM (' + query + ') source', params)
                cursor.execute('CREATE INDEX ON ' + source + ' (vf_ordinal)')
                cursor.execute('ANALYZE ' + source)
            operands['sources'][path] = 'pg_temp.' + source
    return operands


def _source_rows(run, reference, branch, *, operands=None):
    """Retained unique-source qualification makes each stored join occurrence exact."""
    ctes, params = [], []
    for alias in (*btr_reporting.ORDINALS, 'sd', 'ld'):
        path = btr_reporting.SOURCES[branch + '_' + alias if alias in ('A', 'btd') else alias]
        sql, values = (('SELECT * FROM ' + operands['sources'][path], []) if operands is not None
                       else image_query(run, path))
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
           for name, value in projection + display) + ' FROM ' + (operands['reference'] if operands else btr_reporting.REF_TABLE) + ' J' + joins +
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
    return _build(run,reference,admission=admission)


def build_run(run,reference):
    """Prepare one unselected committed native source, without serving admission."""
    if (run.kind!='DAILY_CHAIN' or run.status!='SUCCEEDED' or
            run.production_manifest.get('version')!=3 or not run.production_digest or
            str(run.pk)==str(settings.VF_MTA_PUBLISHED_RUN)):
        raise PublicationUnavailable('btr_snapshot_requires_unselected_committed_daily_run')
    return _build(run,reference,allow_outer=True)


def _build(run,reference,*,admission=None,allow_outer=False):
    outer=not transaction.get_autocommit()
    if outer and not allow_outer:
        raise ValueError('BTR builder requires its own transaction boundary')
    if reference is not None and reference.version == 2:
        reference = reference_generation(run, reference)
    if (reference is None or reference.run_id!=run.pk or reference.version!=1 or
            reference.status!='READY' or not reference.eligible or
            reference.source_digest!=digest(btr_reporting.source_identity(run))):
        raise PublicationUnavailable('btr_snapshot_requires_qualified_reference')
    lineage = btr_reporting.source_identity(run, 2)
    source, generation = digest(lineage), None
    lock = int(source[:15], 16)
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_lock(%s)', [lock])
    try:
        existing = BtrReportingGeneration.objects.filter(run=run, version=2, source_digest=source, status='READY').first()
        if existing:
            return existing
        BtrReportingGeneration.objects.filter(run=run, version=2, source_digest=source, status='BUILDING').update(
            status='FAILED', failure='Interrupted snapshot build; never selected', completed_at=timezone.now())
        generation = BtrReportingGeneration.objects.create(run=run, version=2, source_kind=run.kind,
            business_date=run.business_date, source_digest=source, lineage=lineage)
        with transaction.atomic():
            with connection.cursor() as cursor:
                if not outer:
                    cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                cursor.execute("SET LOCAL statement_timeout='60s'")
                cursor.execute("SET LOCAL work_mem='32MB'")
            counts = {}
            dimensions = {owner: set() for owner, *_ in SCOPE_SOURCES}
            operands = _source_operands(run, reference, generation)
            for branch in ('tech', 'eco'):
                count, batch = 0, []
                for source_fields, raw in _source_rows(run, reference, branch, operands=operands):
                    _collect_dimensions(dimensions, source_fields)
                    batch.append(BtrPresentationRow(generation=generation, branch=branch,
                                                   **source_fields, **prepared_values(raw)))
                    count += 1
                    if len(batch) == 64:
                        write_batch(batch)
                        batch.clear()
                if batch:
                    write_batch(batch)
                if count != reference.qualification['populations'][branch + '_grid']:
                    raise PublicationUnavailable('btr_snapshot_population_mismatch')
                counts[branch] = count
            _save_dimensions(generation, dimensions)
            generation.row_count, generation.rows_digest = rows_identity(generation)
            if admission is not None:
                from mta.presentation.admission import binding
                if binding()[1]!=admission:
                    raise PublicationUnavailable('btr_snapshot_source_changed')
            if btr_reporting.source_identity(run, 2) != lineage:
                raise PublicationUnavailable('btr_snapshot_source_changed')
            generation.qualification = dict(reference_generation=str(reference.pk), populations=counts,
                labels=image_rows(run, btr_reporting.SOURCES['dates']), mapper='retained-js-v1')
            generation.eligible, generation.status, generation.completed_at = True, 'READY', timezone.now()
            generation.save()
        if not outer:
            with connection.cursor() as cursor:
                # The fixture wrapper retains its targeted maintenance. Native
                # daily layers own an outer transaction and cannot VACUUM.
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
    sources = {owner: (table, (code, *(prefix + str(i) for i in (1, 2, 3))))
               for owner, table, code, prefix, _ in SCOPE_SOURCES}
    result = {table: [] for table, _ in sources.values()}
    for owner, *values in BtrScopeDimension.objects.filter(generation=generation).order_by(
            'owner', 'source_ordinal').values_list('owner', 'code', 'level_1', 'level_2', 'level_3'):
        table, fields = sources[owner]
        result[table].append(dict(zip(fields, values)))
    return result


def _display_projection(columns):
    fields, slots = [], []
    for name in (*TEXT_FIELDS, *SCALAR_FIELDS, *columns, *('C' + c for c in columns)):
        slots.append((name, len(fields), name in TEXT_FIELDS))
        if name in TEXT_FIELDS:
            fields.append(display_field(name, 'text'))
        else:
            fields.extend(display_field(name, kind) for kind in ('number', 'text'))
    return ','.join('S.' + quote(field) for field in fields), slots


def _display_row(values, slots, nonfinite):
    row = {}
    for name, index, text_only in slots:
        value = values[index]
        row[name] = value if text_only or value is not None else (
            None if name in nonfinite else values[index + 1] if values[index + 1] is not None else '')
    return row


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
    projection, slots = _display_projection(columns)
    for branch in ('tech', 'eco'):
        if selected_name not in (branch, 'both'):
            continue
        local = ctes + ['S AS NOT MATERIALIZED (SELECT * FROM ' + TABLE + ' WHERE generation_id=%s AND branch=%s)']
        # Preserve canonical key selection, then unfiltered key rejoin and second
        # LIMIT. Permission overlap multiplies selected keys, exactly as before.
        local.append('selected AS (SELECT S.sku_key,S.location_key FROM S' + auth + ' WHERE ' + where + parent +
                     ' ORDER BY ' + order + ' LIMIT %s OFFSET %s)')
        local.append('page AS (SELECT S.id,S.sku_key,S.location_key FROM selected T JOIN S ON S.sku_key=T.sku_key AND S.location_key=T.location_key'
                     ' WHERE TRUE' + parent + ' ORDER BY ' + order + ' LIMIT %s)')
        # Keep the ordered, bounded page as the outer relation. OFFSET 0 prevents
        # flattening this typed lookup into a wide join before page selection.
        sql = ('WITH ' + ','.join(local) + ' SELECT display.* FROM page CROSS JOIN LATERAL (SELECT ' + projection +
               ',S.availability,' + summary + ',S.nonfinite_fields,S.nonfinite_tokens'
               ' FROM S WHERE S.id=page.id OFFSET 0) display ORDER BY '
               'page.sku_key NULLS FIRST,page.location_key NULLS FIRST')
        values = params + [generation.pk, branch] + filters.params + filters.children + [paging[1], (paging[0]-1)*paging[1]] + filters.children + [paging[1]]
        with connection.cursor() as cursor:
            cursor.execute(sql, values)
            for index, values in enumerate(cursor.fetchall()):
                default, available, empty, fields, tokens = values[-5:]
                row = _display_row(values, slots, fields)
                availability = default if default_range else btr_display._availability(available, horizon - empty)
                row['Availability'] = availability if availability is not None and math.isfinite(availability) else None
                if row['Availability'] is None:
                    result['displayNonFinite'].append([branch, index, 'Availability', 'NaN'])
                result['displayNonFinite'].extend([branch, index, field, token] for field, token in zip(fields, tokens) if field in row)
                result[branch].append(row)
    logging.getLogger(__name__).info('BTR reader=presentation generation=%s', generation.pk)
    return result
