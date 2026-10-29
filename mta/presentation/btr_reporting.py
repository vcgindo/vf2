"""Opt-in, publication-bound BTR join references over unchanged typed sources.

Only stable joins are prepared. Permissions, filters, descriptions, daily values
and the canonical two-pass paging remain read-time operations. Ambiguous tied
bags use the accepted reader; no source ordinal becomes a business tie-break.
"""
import hashlib
import json
import re
from uuid import UUID

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from mta.presentation.context import PublicationUnavailable, selected_run
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_metadata, image_query
from mta.runtime.models import BtrJoinReference, BtrReportingGeneration
from mta.serialization import digest

VERSION = 1
SOURCES = {
    'sa': 'closing/btr/SkuAttributeData',
    'la': 'closing/btr/LocationAttributeData',
    'sla': 'closing/btr/SkuLocAttributeData',
    'B': 'closing/dbm/SKULocStandardAttributes',
    'E': 'reports/bpr/vf_RationedReqReport',
    'sd': 'closing/importer/SKUDescriptionTbl',
    'ld': 'closing/importer/SiteDescriptionTbl',
    'categories': 'closing/consumer_context/CategoryColDescription',
    'dates': 'closing/btr/BufferTrendDates',
}
for _branch, _trend in (('tech', 'PhysicalInv'), ('eco', 'Dispatch')):
    SOURCES[_branch + '_A'] = 'closing/btr/BPPTrend' + _trend
    SOURCES[_branch + '_btd'] = 'closing/btr/BufferTrend' + _trend
REF_TABLE = 'mta.' + BtrJoinReference._meta.db_table
ORDINALS = {'A': 'a_ordinal', 'btd': 'btd_ordinal', 'E': 'e_ordinal',
            'sla': 'sla_ordinal', 'sa': 'sa_ordinal', 'la': 'la_ordinal', 'B': 'b_ordinal'}
ROW_FIELDS = ('branch', 'export', 'sku_code', 'location_code', 'sku_key', 'location_key', *ORDINALS.values())


def source_identity(run, version=VERSION):
    return dict(version=version, run=str(run.pk), kind=run.kind, date=str(run.business_date),
                input_digest=run.input_digest, output_digest=run.output_digest,
                production_digest=run.production_digest,
                images={role: image_metadata(run, path) for role, path in SOURCES.items()})


def selected_generation(run):
    identifier = getattr(settings, 'VF_BTR_REPORTING_GENERATION', '')
    if not identifier:
        return None
    try:
        generation = BtrReportingGeneration.objects.get(pk=UUID(identifier), status='READY')
    except (ValueError, BtrReportingGeneration.DoesNotExist) as exc:
        raise PublicationUnavailable('btr_reporting_generation_not_ready') from exc
    if (generation.run_id != run.pk or generation.version not in (VERSION, 2) or
            generation.source_kind != run.kind or generation.business_date != run.business_date or
            generation.source_digest != digest(source_identity(run, generation.version))):
        raise PublicationUnavailable('btr_reporting_generation_source_mismatch')
    return generation


def admission_identity(run):
    generation = selected_generation(run)
    if generation is None:
        return None
    return dict(id=str(generation.pk), source=generation.source_digest, rows=generation.rows_digest,
                count=generation.row_count, eligible=generation.eligible,
                qualification=generation.qualification)


def rows_identity(generation):
    if generation.version == 2:
        from mta.presentation.btr_snapshot import rows_identity as snapshot_identity
        return snapshot_identity(generation)
    checksum = hashlib.sha256()
    count = 0
    for row in BtrJoinReference.objects.filter(generation=generation).order_by('id').values_list(*ROW_FIELDS).iterator(chunk_size=2000):
        checksum.update((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode())
        count += 1
    return count, checksum.hexdigest()


def verify_generation(generation):
    if generation.status != 'READY' or rows_identity(generation) != (generation.row_count, generation.rows_digest):
        raise PublicationUnavailable('btr_reporting_rows_changed')
    if generation.version == 2:
        # Counts/exports still consume this immutable predecessor. Keep their
        # full startup readback proof when the prepared grid is selected.
        from mta.presentation.btr_snapshot import reference_generation
        verify_generation(reference_generation(generation.run, generation))


def _duplicates(run):
    """Fail acceleration closed on any normalized source ambiguity, including display."""
    problems = {}
    with connection.cursor() as cursor:
        for role, path in SOURCES.items():
            if role in ('categories', 'dates'):
                continue
            columns = ('SKUCode',) if role in ('sa', 'sd') else ('WHCode',) if role in ('la', 'ld') else (
                'SKUCode', 'LocCode' if role == 'sla' else 'WhCode')
            query, values = image_query(run, path)
            keys = ','.join(key('"' + column + '"') for column in columns)
            cursor.execute('SELECT count(*) FROM (SELECT 1 FROM (' + query + ') s GROUP BY ' +
                           keys + ' HAVING count(*)>1) d', values)
            count = cursor.fetchone()[0]
            if count:
                problems[role] = count
        query, values = image_query(run, SOURCES['B'])
        cursor.execute('SELECT count(*) FROM (SELECT 1 FROM (SELECT DISTINCT "Category" FROM (' +
                       query + ') s) c GROUP BY ' + key('"Category"') + ' HAVING count(*)>1) d', values)
        if count := cursor.fetchone()[0]:
            problems['category_alias_keys'] = count
    return problems


def _populate(run, generation):
    for branch in ('tech', 'eco'):
        for export in (False, True):
            paths = {alias: SOURCES[branch + '_' + alias] if alias in ('A', 'btd') else SOURCES[alias]
                     for alias in ORDINALS if not (export and alias == 'sla')}
            ctes, values = [], []
            for alias, path in paths.items():
                query, bound = image_query(run, path)
                ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
                values.extend(bound)
            joins = ''
            for alias in paths:
                if alias == 'A':
                    continue
                condition = (equal('A."WhCode"', alias + '."WHCode"') if alias == 'la' else
                             equal('A."SKUCode"', alias + '."SKUCode"'))
                if alias not in ('sa', 'la'):
                    condition += ' AND ' + equal('A."WhCode"', alias + ('."LocCode"' if alias == 'sla' else '."WhCode"'))
                joins += ' LEFT JOIN ' + alias + ' ON ' + condition
            expressions = ['%s', '%s', 'A."SKUCode"', 'A."WhCode"', key('A."SKUCode"'), key('A."WhCode"')]
            expressions += ['NULL::bigint' if export and alias == 'sla' else alias + '.vf_ordinal' for alias in ORDINALS]
            with connection.cursor() as cursor:
                cursor.execute('WITH ' + ','.join(ctes) + ' INSERT INTO ' + REF_TABLE +
                    ' (generation_id,' + ','.join('"' + f + '"' for f in ROW_FIELDS) + ') SELECT %s,' +
                    ','.join(expressions) + ' FROM A' + joins, values + [generation.pk, branch, export])


def _build(run, *, admission=None, allow_outer=False):
    """Build one explicit immutable source identity; selection is the caller's concern."""
    outer = not transaction.get_autocommit()
    if outer and not allow_outer:
        raise ValueError('BTR builder requires its own transaction boundary')
    lineage = source_identity(run)
    source = digest(lineage)
    lock = int(source[:15], 16)
    generation = None
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_lock(%s)', [lock])
    try:
        existing = BtrReportingGeneration.objects.filter(run=run, version=VERSION, source_digest=source, status='READY').first()
        if existing:
            return existing
        # A released session lock proves a previous BUILDING worker is no longer the owner.
        BtrReportingGeneration.objects.filter(run=run, version=VERSION, source_digest=source, status='BUILDING').update(
            status='FAILED', failure='Interrupted reporting attempt; rows were never activated', completed_at=timezone.now())
        generation = BtrReportingGeneration.objects.create(run=run, version=VERSION, source_digest=source,
            source_kind=run.kind, business_date=run.business_date, lineage=lineage)
        with transaction.atomic():
            with connection.cursor() as cursor:
                if not outer:
                    cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
                cursor.execute("SET LOCAL statement_timeout='60s'")
                cursor.execute("SET LOCAL work_mem='32MB'")
            problems = _duplicates(run)
            _populate(run, generation)
            counts = {}
            with connection.cursor() as cursor:
                cursor.execute('SELECT branch,export,count(*) FROM ' + REF_TABLE +
                               ' WHERE generation_id=%s GROUP BY branch,export', [generation.pk])
                counts = {branch + ('_export' if export else '_grid'): count for branch, export, count in cursor.fetchall()}
            if not problems:
                expected = {branch + suffix: lineage['images'][branch + '_A']['count']
                            for branch in ('tech', 'eco') for suffix in ('_grid', '_export')}
                if any(counts.get(name, 0) != count for name, count in expected.items()):
                    raise PublicationUnavailable('btr_reporting_reference_population_mismatch')
            generation.row_count, generation.rows_digest = rows_identity(generation)
            if admission is not None:
                from mta.presentation.admission import binding
                if binding()[1] != admission:
                    raise PublicationUnavailable('btr_source_changed_during_build')
            if source_identity(run) != lineage:
                raise PublicationUnavailable('btr_source_changed_during_build')
            generation.eligible = not problems
            generation.qualification = dict(duplicate_groups=problems, populations=counts, ambiguous_reader='accepted')
            generation.status = 'READY'
            generation.completed_at = timezone.now()
            generation.save()
        return generation
    except BaseException as exc:
        if generation:
            BtrReportingGeneration.objects.filter(pk=generation.pk).update(status='FAILED',
                failure=type(exc).__name__ + ': ' + str(exc), completed_at=timezone.now())
        raise
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_unlock(%s)', [lock])


def build_run(run):
    """Prepare an unselected accepted daily run without consulting global selection."""
    if (getattr(run, 'kind', None) != 'DAILY_CHAIN' or
            getattr(run, 'status', None) != 'SUCCEEDED' or
            not getattr(run, 'production_digest', None)):
        raise PublicationUnavailable('btr_daily_source_run_not_accepted')
    return _build(run, allow_outer=True)


def build_selected():
    """Post-admission command, separate from execute_day; never rewrites accepted output."""
    from mta.presentation.admission import binding, verify
    run, admission = binding()
    # Fixture/selected behavior remains bound to the same serving admission.
    verify(run)
    return _build(run, admission=admission)


def eligible_request(generation, products, locations):
    return generation is not None and generation.version == VERSION and generation.eligible and all(
        count == 1 for codes in (products, locations) for count in codes.multiplicities.values())


def reference_from(expressions, *, parent_join=''):
    """Only retrieve owners actually used; their full join multiplicity is already in J."""
    used = set(re.findall(r'\b(A|btd|E|sla|sa|la|B)\.', expressions + parent_join))
    result = 'J'
    for alias, ordinal in ORDINALS.items():
        if alias in used:
            result += (' JOIN ' if alias == 'A' else ' LEFT JOIN ') + alias + ' ON ' + alias + '.vf_ordinal=J.' + ordinal
    return result + parent_join


def substitute_keys(expression):
    return expression.replace('A."SKUCode"', 'J.sku_code').replace('A."WhCode"', 'J.location_code')
