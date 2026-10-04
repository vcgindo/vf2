"""Scoped/date-bounded aggregates over existing Guided history relations.

The existing predicate owns filter validation/grouping. Its internal terms are
compiled with the established SQL comparison implementation; no API changes or
additional historical rows are created.
"""
from datetime import timedelta
from django.db import connection

from mta.presentation import hierarchy
from mta.presentation.context import scope, permission_catalogue, PublicationUnavailable
from mta.presentation.insight_filters import InsightPredicate, unavailable
from mta.presentation.rrr_sql import Filters, equal
from mta.presentation.selective import image_metadata, image_query, image_rows
from mta.runtime.models import ExcessInventoryRow
from mta.runtime.relational_state import quote


def read_history(run, payload, kind):
    excess = kind.startswith('excess-')
    if excess and run.kind != 'LEGACY_UI_FIXTURE':
        raise ValueError('normal_excess_history_uses_its_admitted_chain')
    horizon = int(payload.get('horison', 0) if excess else
                  payload.get('horizon', payload.get('horison', 90 if kind == 'availability-trend' else 30)))
    if not excess and not 1 <= horizon <= 90:
        raise ValueError('horizon must be between 1 and 90 days')
    cutoff = run.business_date - timedelta(days=horizon)
    owner = 'closing/importer/' if excess else 'closing/btr/'
    attributes = {name: image_rows(run, owner + name) for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            attributes = hierarchy.project_attributes(attributes, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    predicate = InsightPredicate(payload, attributes['LocationAttributeData'], kind=kind)
    products, locations = scope(payload, attributes=attributes)
    if run.kind == 'LEGACY_UI_FIXTURE' and not manifest and products and locations:
        from mta.presentation.guided_history_prepared import read_prepared
        prepared_rows = read_prepared(
            run, cutoff, predicate, products, locations, kind,
            minimum_age=(int(payload.get('ageing', 1))
                         if kind == 'availability-ageing' else None))
        if prepared_rows is not None:
            return _result(prepared_rows, kind)
    ctes, params, wires = [], [], {}
    def add(alias, query, values, fields):
        ctes.append(alias + ' AS (' + query + ')'); params.extend(values)
        wires[alias] = {field: wire for field, _, wire in fields}
    def image(alias, path):
        item = image_metadata(run, path); query, values = image_query(run, path)
        add(alias, query, values, item['fields'])
    if excess:
        from mta.presentation.fixture import binding, receipt
        selected, _ = binding()
        if selected.pk != run.pk:
            raise PublicationUnavailable('fixture_history_run_mismatch')
        item = receipt(run, 'projection/ExcessInventoryRow')
        add('_a', 'SELECT *,ordinal AS vf_ordinal FROM mta.' + quote(ExcessInventoryRow._meta.db_table) +
            ' WHERE run_id=%s AND "ReportDate">%s', [run.pk, cutoff],
            [(field, field, wire) for field, wire in zip(item['fields'], item['wire'])])
    else:
        item = image_metadata(run, 'closing/btr/BPR'); query, values = image_query(run, 'closing/btr/BPR')
        add('_a', query + ' AND "ReportDate">%s', values + [cutoff], item['fields'])
    for alias, name, prefix in (('_sku', 'SkuAttributeData', 'SL'), ('_location', 'LocationAttributeData', 'LL'),
                                 ('_pair', 'SkuLocAttributeData', None)):
        if manifest and prefix:
            # Keep the existing approved read-time hierarchy, keyed by occurrence.
            image(alias + '_native', owner + name)
            rows = attributes[name]
            ctes.append(alias + '_hierarchy AS (VALUES ' + ','.join(['(%s,%s,%s,%s)'] * len(rows)) + ')')
            params.extend(v for i, row in enumerate(rows) for v in (i, *[row[prefix + str(n)] for n in (1,2,3)]))
            fields = image_metadata(run, owner + name)['fields']
            ctes.append(alias + ' AS (SELECT ' + ','.join('N.' + quote(f) for f, _, _ in fields
                if f not in [prefix + str(n) for n in (1,2,3)]) + ',' +
                ','.join('H.column' + str(n + 1) + ' AS ' + quote(prefix + str(n)) for n in (1,2,3)) +
                ',N.vf_ordinal FROM ' + alias + '_native N JOIN ' + alias + '_hierarchy H ON N.vf_ordinal=H.column1)')
            wires[alias] = wires[alias + '_native']
        else:
            image(alias, owner + name)
    if kind == 'availability-ageing':
        image('_snapshot', 'closing/btr/BTRSnapshotForUI')
    class HistoryFilters(Filters):
        def column(self, alias, field):
            column = alias + '.' + quote(field)
            wire = wires[alias][field]
            return (column + '::text', 'text') if wire == 'str' else (column, wire)
    compiler = HistoryFilters({})
    def term(node):
        if node[0] == 'or': return '(' + ' OR '.join(term(child) for child in node[1]) + ')'
        if node[0] == 'in':
            column, _ = compiler.column(*node[1]); compiler.params.extend(node[2])
            return '(' + ' OR '.join(equal(column, '%s') for _ in node[2]) + ')'
        return compiler.compare(*node[1], node[2], node[3])
    try:
        where = ' AND '.join(term(t) for t in predicate.sql_terms) or 'TRUE'
    except PublicationUnavailable as exc:
        unavailable(str(exc).partition(':')[2])

    def references(node, alias):
        if node[0] == 'or':
            return any(references(child, alias) for child in node[1])
        return node[1][0] == alias

    pair_predicate = any(references(node, '_pair') for node in predicate.sql_terms)
    snapshot_predicate = any(references(node, '_snapshot') for node in predicate.sql_terms)
    if not products or not locations:
        return []
    for alias, codes in (('P', products), ('L', locations)):
        ctes.append(alias + ' AS (VALUES ' + ','.join(['(%s,%s)'] * len(codes)) + ')')
        params.extend(v for code in sorted(codes) for v in (code, codes.multiplicities[code]))
    source_location = '_a.' + quote('WhCode' if excess else 'WHCode')
    joins = (' FROM _a JOIN _sku ON _a."SKUCode"=_sku."SKUCode"'
        ' JOIN _location ON _a."WhCode"=_location."WHCode"')
    pair_weight = ''
    if pair_predicate:
        joins += (' LEFT JOIN _pair ON _a."SKUCode"=_pair."SKUCode"'
                  ' AND _a."WhCode"=_pair."LocCode"')
    else:
        # A raw LEFT JOIN is one occurrence for a miss and one per matching
        # pair row.  Carry that exact bag weight without sorting every fact
        # occurrence against the complete pair relation.
        ctes.append('_pair_occurrence AS MATERIALIZED (SELECT "SKUCode","LocCode",count(*) AS vf_count'
                    ' FROM _pair GROUP BY "SKUCode","LocCode")')
        joins += (' LEFT JOIN _pair_occurrence ON _a."SKUCode"=_pair_occurrence."SKUCode"'
                  ' AND _a."WhCode"=_pair_occurrence."LocCode"')
        pair_weight = '*coalesce(_pair_occurrence.vf_count,1)'
    joins += (' JOIN P ON _a."SKUCode"=P.column1'
              ' JOIN L ON _a."WhCode"=L.column1')
    minimum_age = None
    snapshot_weight = ''
    if kind == 'availability-ageing':
        minimum_age = int(payload.get('ageing', 1))
    if minimum_age is not None and not snapshot_predicate:
        ctes.append('_snapshot_occurrence AS MATERIALIZED (SELECT "SKUCode","WhCode",count(*) AS vf_count'
                    ' FROM _snapshot WHERE "AgePhysicalInv">=%s'
                    ' GROUP BY "SKUCode","WhCode")')
        params.append(minimum_age)
        joins += (' JOIN _snapshot_occurrence ON _a."SKUCode"=_snapshot_occurrence."SKUCode"'
                  ' AND _a."WhCode"=_snapshot_occurrence."WhCode"')
        snapshot_weight = '*_snapshot_occurrence.vf_count'
    if predicate.children:
        # The native predicate returns parent-join multiplicity, not EXISTS.
        joins += (' JOIN _location parent ON ' + equal('_a."ParentWhCode"', 'parent."WHCode"') + ' AND (' +
            ' OR '.join(equal('parent."LocationType"', '%s') for _ in predicate.children) + ')')
        params.extend(predicate.children)
    joins = joins.replace('_a."WhCode"', source_location)
    weight = ('(P.column2::bigint*L.column2::bigint' + pair_weight +
              snapshot_weight + ')')
    day = '_a."ReportDate"'
    colour = '_a."PhysicalInventoryColor"'
    first_occurrence = "min(lpad(_a.vf_ordinal::text,20,'0')||lpad(_location.vf_ordinal::text,20,'0'))"
    if kind == 'availability-trend':
        selected = (day + ',_location."LocationType",trunc(100::numeric*sum(CASE WHEN ' + colour +
            " IS NOT NULL AND " + colour + "<>'Black' THEN " + weight + ' ELSE 0 END)/nullif(sum(CASE WHEN ' +
            colour + ' IS NOT NULL THEN ' + weight + ' ELSE 0 END),0))')
        group = ' GROUP BY ' + day + ',_location."LocationType" HAVING count(' + colour + ')>0 ORDER BY ' + day + ',' + first_occurrence
    elif kind == 'availability-ageing':
        if snapshot_predicate:
            joins += (' JOIN _snapshot ON _a."SKUCode"=_snapshot."SKUCode"'
                      ' AND _a."WhCode"=_snapshot."WhCode"'
                      ' AND _snapshot."AgePhysicalInv">=%s')
            params.append(minimum_age)
        selected = day + ',' + ','.join('sum(CASE WHEN ' + colour + "='" + c + "' THEN " + weight +
                                       ' ELSE 0 END)' for c in ('Black','Red','White'))
        group = ' GROUP BY ' + day + ' ORDER BY ' + day
    else:
        if kind == 'excess-sku':
            where += ' AND ' + equal(colour, "'white'")
        selected = day + ',_location."LocationType",sum(' + (
            '_a."Amount"::numeric*' + weight if kind == 'excess-value' else weight) + ')'
        group = ' GROUP BY ' + day + ',_location."LocationType" ORDER BY ' + day + ",coalesce(_location.\"LocationType\",'-')"
    with connection.cursor() as cursor:
        cursor.execute('WITH ' + ','.join(ctes) + ' SELECT ' + selected + joins.replace('_a."WhCode"', source_location) + ' WHERE ' + where + group,
                       params + compiler.params)
        rows = cursor.fetchall()
    return _result(rows, kind)


def _result(rows, kind):
    result = []
    for row in rows:
        if kind == 'availability-trend':
            item = dict(week=str(row[0]), percentage=int(row[2]))
            if row[1] is not None: item['locationtype'] = row[1]
        elif kind == 'availability-ageing':
            item = dict(date=str(row[0]), **dict(zip(('black','red','white'), map(int,row[1:]))))
        else:
            item = dict(date=str(row[0]), locationtype='-' if row[1] is None else row[1])
            if row[2] is not None:
                value = int(row[2])
                if not -(2**63) <= value < 2**63: raise OverflowError('Canonical BIGINT SUM overflow')
                item['value' if kind == 'excess-value' else 'countSku'] = value
        result.append(item)
    return result
