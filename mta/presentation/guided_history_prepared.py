from mta.presentation.native_mode import removed_mode
"""Selective aggregates over sealed fixture history occurrence references."""
from django.conf import settings
from django.db import connection

from mta.presentation.context import PublicationUnavailable
from mta.presentation.guided_history_fields import (
    native_excess_schema_digest, schema_digest,
)
from mta.presentation.insight_filters import unavailable
from mta.presentation.rrr_sql import Filters, equal
from mta.presentation.selective import image_metadata, image_query
from mta.runtime.models import (
    ExcessInventoryRow, GuidedAvailabilityHistoryRow,
    GuidedAvailabilitySnapshotReference, GuidedExcessHistoryRow,
    GuidedHistoryPreparedProjection,
)
from mta.runtime.guided_history_schema import verify_guards
from mta.runtime.relational_state import quote


def refs(node, alias):
    if node[0] == 'or':
        return any(refs(child, alias) for child in node[1])
    return node[1][0] == alias


def fields_for(node, alias):
    if node[0] == 'or':
        result = set()
        for child in node[1]: result.update(fields_for(child, alias))
        return result
    return {node[1][1]} if node[1][0] == alias else set()


def read_prepared(run, cutoff, predicate, products, locations, kind, minimum_age=None, payload=None):
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if not daily:
        return None
    if daily:
        from mta.presentation.daily_preparation import source_digest
        source = source_digest(run)
    else:
        selected, source = removed_mode('historical_fixture')
        if selected.pk != run.pk:
            raise PublicationUnavailable('Guided history prepared run differs')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('Guided history prepared guards differ') from exc
    family = 'excess' if kind.startswith('excess-') else 'availability'
    expected_schema = schema_digest()
    if daily and family == 'excess':
        from mta.presentation import native_excess_history
        history_identity = native_excess_history.identity(run)
        native_excess_history.require_cutoff(history_identity, cutoff)
        source = native_excess_history.source_digest(source, history_identity)
        expected_schema = native_excess_schema_digest()
    receipt = GuidedHistoryPreparedProjection.objects.filter(run=run, family=family).first()
    if receipt is None or receipt.source_digest != source or receipt.schema_digest != expected_schema:
        raise PublicationUnavailable('Guided history prepared receipt differs')
    if payload is not None:
        from mta.presentation.guided_aggregates import read_aggregate
        aggregated = read_aggregate(run, cutoff, predicate, payload, kind, minimum_age)
        if aggregated is not None:
            return aggregated
    model = GuidedExcessHistoryRow if family == 'excess' else GuidedAvailabilityHistoryRow
    table = 'mta.' + quote(model._meta.db_table)
    ctes = ['H AS (SELECT * FROM ' + table + ' WHERE run_id=%s AND report_date>%s)']
    params = [run.pk, cutoff]
    wires = {'_a': {'SKUCode': 'str', 'WHCode': 'str', 'WhCode': 'str', 'ParentWhCode': 'str', 'ReportDate': 'str', 'PhysicalInventoryColor': 'str', 'Amount': 'int'}}
    aliases = {node[1][0] for node in predicate.sql_terms if node[0] != 'or'}
    for node in predicate.sql_terms:
        if node[0] == 'or':
            aliases.update((alias for alias in ('_a', '_sku', '_location', '_pair', '_snapshot') if refs(node, alias)))
    owner = 'closing/importer/' if family == 'excess' else 'closing/btr/'
    relations = {}
    for alias, name in (('_sku', 'SkuAttributeData'), ('_location', 'LocationAttributeData'), ('_pair', 'SkuLocAttributeData')):
        if alias in aliases:
            item = image_metadata(run, owner + name)
            query, values = image_query(run, owner + name)
            ctes.append(alias + ' AS (' + query + ')')
            params.extend(values)
            wires[alias] = {field: wire for field, _, wire in item['fields']}
            relations[alias] = True
    core = {'SKUCode', 'WHCode', 'WhCode', 'ParentWhCode', 'ReportDate', 'PhysicalInventoryColor', 'Amount'}
    fact_fields = set()
    for node in predicate.sql_terms:
        fact_fields.update(fields_for(node, '_a'))
    if any((field not in core for field in fact_fields)):
        if family == 'excess':
            fact_where = ' WHERE run_id IN (SELECT DISTINCT fact_run_id FROM H))' if daily else ' WHERE run_id=%s)'
            ctes.append('_fact AS (SELECT *,ordinal vf_ordinal FROM mta.' + quote(ExcessInventoryRow._meta.db_table) + fact_where)
            if not daily:
                params.append(run.pk)
                item = removed_mode('historical_fixture')
                wires['_a'] = dict(zip(item['fields'], item['wire']))
            else:
                wires['_a'] = {field.name: 'str' if field.get_internal_type() in ('CharField', 'TextField', 'DateField') else 'decimal' if field.get_internal_type() == 'DecimalField' else 'int' for field in ExcessInventoryRow._meta.fields if field.name not in ('id', 'run')}
        else:
            item = image_metadata(run, 'closing/btr/BPR')
            query, values = image_query(run, 'closing/btr/BPR')
            ctes.append('_fact AS (' + query + ')')
            params.extend(values)
            wires['_a'] = {field: wire for field, _, wire in item['fields']}
        relations['_fact'] = True
    if kind == 'availability-ageing':
        ref = 'mta.' + quote(GuidedAvailabilitySnapshotReference._meta.db_table)
        ctes.append('_snapshot_ref AS (SELECT * FROM ' + ref + ' WHERE run_id=%s)')
        params.append(run.pk)
        if '_snapshot' in aliases:
            item = image_metadata(run, 'closing/btr/BTRSnapshotForUI')
            query, values = image_query(run, 'closing/btr/BTRSnapshotForUI')
            ctes.append('_snapshot AS (' + query + ')')
            params.extend(values)
            wires['_snapshot'] = {field: wire for field, _, wire in item['fields']}

    class Compiler(Filters):

        def column(self, alias, field):
            wire = wires[alias][field]
            column = alias + '.' + quote(field)
            return (column + '::text', 'text') if wire == 'str' else (column, wire)
    compiler = Compiler({})

    def term(node):
        if node[0] == 'or':
            return '(' + ' OR '.join((term(child) for child in node[1])) + ')'
        if node[0] == 'in':
            column, _ = compiler.column(*node[1])
            compiler.params.extend(node[2])
            return '(' + ' OR '.join((equal(column, '%s') for _ in node[2])) + ')'
        return compiler.compare(*node[1], node[2], node[3])
    try:
        where = ' AND '.join((term(node) for node in predicate.sql_terms)) or 'TRUE'
    except PublicationUnavailable as exc:
        unavailable(str(exc).partition(':')[2])
    for alias, codes in (('P', products), ('L', locations)):
        values = 'VALUES ' + ','.join(['(%s,%s)'] * len(codes))
        params.extend((value for code in sorted(codes) for value in (code, codes.multiplicities[code])))
        fields = ('SKUCode',) if alias == 'P' else ('WHCode', 'WhCode')
        code_terms = [node for node in predicate.sql_terms if node[0] == 'in' and node[1][0] == '_a' and (node[1][1] in fields)]
        scope_where = []
        for node in code_terms:
            scope_where.append('(' + ' OR '.join((equal('allowed.code', '%s') for _ in node[2])) + ')')
            params.extend(node[2])
        query = 'SELECT * FROM (' + values + ') allowed(code,weight) WHERE ' + ' AND '.join(scope_where) if scope_where else values
        ctes.append(alias + '(code,weight) AS (' + query + ')')
    core_select = 'H.sku_code "SKUCode",H.location_code "WHCode",H.location_code "WhCode",H.parent_location_code "ParentWhCode",H.report_date "ReportDate",H.physical_inventory_color "PhysicalInventoryColor"' + (',H.amount "Amount"' if family == 'excess' else '')
    joins = ' FROM H '
    if '_fact' in relations:
        joins += 'JOIN _fact _a ON ' + ('H.fact_run_id=_a.run_id AND ' if daily and family == 'excess' else '') + 'H.fact_ordinal=_a.vf_ordinal '
    else:
        joins += 'CROSS JOIN LATERAL (SELECT ' + core_select + ') _a '
    for alias, column in (('_sku', 'sku_ordinal'), ('_location', 'location_ordinal'), ('_pair', 'pair_ordinal')):
        if alias in relations:
            joins += ('LEFT JOIN ' if alias == '_pair' else 'JOIN ') + alias + ' ON H.' + column + '=' + alias + '.vf_ordinal '
    joins += 'JOIN P ON H.sku_code=P.code JOIN L ON H.location_code=L.code '
    if predicate.children:
        item = image_metadata(run, owner + 'LocationAttributeData')
        query, values = image_query(run, owner + 'LocationAttributeData')
        ctes.append('_parent AS (' + query + ')')
        params.extend(values)
        joins += 'JOIN _parent parent ON ' + equal('H.parent_location_code', 'parent."WHCode"') + ' AND (' + ' OR '.join((equal('parent."LocationType"', '%s') for _ in predicate.children)) + ') '
        params.extend(predicate.children)
    if kind == 'availability-ageing':
        joins += 'JOIN _snapshot_ref SR ON H.snapshot_anchor_ordinal=SR.snapshot_anchor_ordinal AND SR.age_physical_inventory>=%s '
        params.append(int(minimum_age))
        if '_snapshot' in aliases:
            joins += 'JOIN _snapshot ON SR.snapshot_ordinal=_snapshot.vf_ordinal '
    weight = '(P.weight::bigint*L.weight::bigint)'
    day = 'H.report_date'
    colour = 'H.physical_inventory_color'
    if kind == 'availability-trend':
        selected = day + ',H.location_type,trunc(100::numeric*sum(CASE WHEN ' + colour + ' IS NOT NULL AND ' + colour + "<>'Black' THEN " + weight + ' ELSE 0 END)/nullif(sum(CASE WHEN ' + colour + ' IS NOT NULL THEN ' + weight + ' ELSE 0 END),0))'
        tail = ' GROUP BY ' + day + ',H.location_type HAVING count(' + colour + ')>0 ORDER BY ' + day + ',min(H.ordinal)'
    elif kind == 'availability-ageing':
        selected = day + ',' + ','.join(('sum(CASE WHEN ' + colour + "='" + c + "' THEN " + weight + ' ELSE 0 END)' for c in ('Black', 'Red', 'White')))
        tail = ' GROUP BY ' + day + ' ORDER BY ' + day
    else:
        if kind == 'excess-sku':
            where += ' AND ' + equal(colour, "'white'")
        selected = day + ',H.location_type,sum(' + ('H.amount::numeric*' + weight if kind == 'excess-value' else weight) + ')'
        tail = ' GROUP BY ' + day + ',H.location_type ORDER BY ' + day + ",coalesce(H.location_type,'-')"
    with connection.cursor() as cursor:
        cursor.execute('WITH ' + ','.join(ctes) + ' SELECT ' + selected + joins + 'WHERE ' + where + tail, params + compiler.params)
        return cursor.fetchall()
