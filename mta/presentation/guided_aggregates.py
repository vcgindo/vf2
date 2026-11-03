"""Exact unfiltered history rollups over permission-equivalent scope classes.

Raw-owner predicates deliberately use the existing occurrence reader. Scope
classes retain each permission's multiplicity, not just boolean membership.
"""
import hashlib
from pathlib import Path

from django.db import connection

from mta.presentation.context import permission_catalogue, PublicationUnavailable
from mta.presentation.permissions import expand_permission_ids, materialize_permission_memberships
from mta.runtime.models import ReportAggregateReceipt
from mta.serialization import digest

AGGREGATE_TABLE = 'mta.fresh_mta_guidedhistoryaggregate'
MEMBER_TABLE = 'mta.fresh_mta_reportscopemember'


def source_binding(run):
    """Bind the existing rollups to immutable prepared history and its scopes."""
    from mta.presentation import native_publication
    native_publication.require_mode()
    native_publication.require_publication(run)
    from mta.presentation.daily_preparation import source_digest
    from mta.presentation import native_excess_history
    from mta.presentation.guided_history_fields import schema_digest, native_excess_schema_digest
    from mta.runtime.models import GuidedHistoryPreparedProjection
    from mta.runtime.guided_history_schema import verify_guards
    verify_guards(connection)
    daily = source_digest(run)
    history = native_excess_history.identity(run)
    expected = {'availability': (daily, schema_digest()), 'excess': (native_excess_history.source_digest(daily, history), native_excess_schema_digest())}
    rows = list(GuidedHistoryPreparedProjection.objects.filter(run=run).order_by('family'))
    if {row.family for row in rows} != set(expected) or any(((row.source_digest, row.schema_digest) != expected[row.family] for row in rows)):
        raise PublicationUnavailable('Guided_aggregate_prepared_source_changed')
    fields = [field.attname for field in GuidedHistoryPreparedProjection._meta.fields if field.name not in ('id', 'run', 'created_at')]
    return digest(dict(version=1, daily=daily, permissions=permission_catalogue(), history=[{field: getattr(row, field) for field in fields} for row in rows]))


def recipe_digest():
    root = Path(__file__).resolve().parents[1]
    paths = ('presentation/guided_aggregates.py', 'presentation/permissions.py',
             'runtime/management/commands/prepare_guided_aggregates.py',
             'runtime/report_aggregate_schema.py', 'runtime/guided_statistics.py')
    return digest({path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths})


def compatible_recipe(observed):
    # The predecessor wrote the same rows before statistics moved into the
    # command. Keep its sealed identity and authenticate source and rows as usual.
    return observed in (recipe_digest(), '93abcba6aa62fe70060ec1ff6a96ea8ce1a737f2040e0a824888e90549bab55d')


def permission_classes(records, attributes, code, prefix):
    memberships = materialize_permission_memberships(records, [dict(code=row[code],
        **{f'level_{i}': row[f'{prefix}{i}'] for i in (1, 2, 3)}) for row in attributes])
    codes = {row[code] for row in attributes if row[code] is not None}
    maps, classes = {}, {}
    for value in codes:
        vector = tuple((identifier, members[value]) for identifier, members in sorted(memberships.items())
                       if members.get(value, 0))
        key = digest(vector)
        maps[value] = key
        classes[key] = vector
    return maps, classes


def read_aggregate(run, cutoff, predicate, payload, kind, minimum_age=None):

    def eligible(node):
        return all((eligible(child) for child in node[1])) if node[0] == 'or' else node[1] == ('_location', 'LocationType')
    if predicate.children or not all((eligible(node) for node in predicate.sql_terms)):
        return None
    from mta.presentation.native_publication import enabled
    if not (enabled() and run.kind == 'DAILY_CHAIN'):
        return None
    receipt = ReportAggregateReceipt.objects.filter(run=run).first()
    if receipt is None:
        return None
    if receipt.source_digest != source_binding(run) or not compatible_recipe(receipt.recipe_digest):
        raise PublicationUnavailable('Guided_aggregate_receipt_changed')
    from mta.runtime.report_aggregate_schema import verify_guards
    verify_guards(connection)
    catalogue = permission_catalogue()
    permissions = []
    for key, dimension in (('product_permissions', 'products'), ('location_permissions', 'locations')):
        assigned = payload.get(key, [])
        records = catalogue[dimension]['records']
        if not isinstance(assigned, list) or any((isinstance(v, bool) or not str(v).isdigit() for v in assigned)):
            raise ValueError('invalid_permission_scope_id')
        assigned = {int(value) for value in assigned}
        if assigned - {row['id'] for row in records}:
            raise PublicationUnavailable('permission_hierarchy_unavailable')
        permissions.append(sorted(expand_permission_ids(records, assigned)))
    if not all(permissions):
        return []
    source_family = 'excess' if kind.startswith('excess-') else 'availability'
    family = 'ageing' if kind == 'availability-ageing' else source_family
    params = [run.pk, source_family, permissions[0], run.pk, source_family, permissions[1], run.pk, family, cutoff]
    weight = '(P.weight::numeric*L.weight::numeric)'
    sql = 'WITH P AS (SELECT class_key,sum(weight) weight FROM ' + MEMBER_TABLE + " WHERE run_id=%s AND family=%s AND dimension='product' AND permission_id=ANY(%s) GROUP BY class_key)," + 'L AS (SELECT class_key,sum(weight) weight FROM ' + MEMBER_TABLE + " WHERE run_id=%s AND family=%s AND dimension='location' AND permission_id=ANY(%s) GROUP BY class_key) "
    where = 'R.run_id=%s AND R.family=%s AND R.report_date>%s'
    from mta.presentation.rrr_sql import Filters, equal

    class Compiler(Filters):

        def column(self, owner, name):
            return ('R.location_type::text', 'text')
    compiler = Compiler({})

    def term(node):
        if node[0] == 'or':
            return '(' + ' OR '.join((term(child) for child in node[1])) + ')'
        if node[0] == 'in':
            compiler.params.extend(node[2])
            return '(' + ' OR '.join((equal('R.location_type', '%s') for _ in node[2])) + ')'
        return compiler.compare(*node[1], node[2], node[3])
    if predicate.sql_terms:
        where += ' AND ' + ' AND '.join((term(node) for node in predicate.sql_terms))
    if kind == 'availability-trend':
        select = 'R.report_date,R.location_type,trunc(100::numeric*sum(R.nonblack_count*' + weight + ')/nullif(sum(R.nonnull_count*' + weight + '),0))'
        tail = ' GROUP BY R.report_date,R.location_type HAVING sum(R.nonnull_count)>0 ORDER BY R.report_date,min(R.first_ordinal)'
    elif kind == 'availability-ageing':
        where += ' AND R.snapshot_age>=%s'
        params.append(int(minimum_age))
        select = 'R.report_date,' + ','.join(('sum(R.' + colour + '_count*' + weight + ')' for colour in ('black', 'red', 'white')))
        tail = ' GROUP BY R.report_date ORDER BY R.report_date'
    else:
        value = 'R.amount' if kind == 'excess-value' else 'R.excess_white_count'
        select = 'R.report_date,R.location_type,sum(' + value + '*' + weight + ')'
        tail = ' GROUP BY R.report_date,R.location_type'
        if kind == 'excess-sku':
            tail += ' HAVING sum(R.excess_white_count)>0'
        tail += " ORDER BY R.report_date,coalesce(R.location_type,'-')"
    with connection.cursor() as cursor:
        cursor.execute(sql + ' SELECT ' + select + ' FROM ' + AGGREGATE_TABLE + ' R JOIN P ON R.product_class=P.class_key JOIN L ON R.location_class=L.class_key WHERE ' + where + tail, params[:9] + compiler.params + params[9:])
        return cursor.fetchall()
