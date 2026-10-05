"""SQL reads of sealed normal-grid occurrences; live scope/filter/page only."""
from collections import defaultdict

from django.db import connection
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.planning_grids import admitted_grids
from mta.presentation.rrr_sql import Filters, equal
from mta.presentation.selective import image_query
from mta.runtime.models import ExcessInventoryRow, FulfillmentSummaryRow, FulfillmentDetailRow
from mta.runtime.relational_state import quote
from mta.serialization import storage


class GridFilters(Filters):
    def __init__(self, payload, family, model):
        super().__init__(payload)
        self.family, self.model = family, model
        self.owners = set()

    def column(self, owner, name):
        self.owners.add(owner)
        if owner != 'A':
            return super().column(owner, name)
        fields = {f.name.lower(): f for f in self.model._meta.fields}
        field = fields.get(name.lower())
        if field is None:
            raise PublicationUnavailable('LEG-' + self.family.upper() + '-FILTER-INVALID-SQL:missing column ' + name)
        kind = field.get_internal_type()
        return 'A.' + quote(field.column), ('bigint' if 'Integer' in kind else 'decimal' if kind == 'DecimalField' else 'text')

    def compile(self):
        from mta.presentation.dbm_filters import STANDARD_GROUPS
        if not any(self.groups.get(group) is not None for group in STANDARD_GROUPS):
            return 'TRUE'
        supply = defaultdict(list)
        for item in self.items('supplyChainFilter'):
            supply[item['attributeName'].lower()].append(item['value'])
        for name, owner, field in (('forlocation', 'D', 'LocationType'),
                ('forlocationlocationcode', 'A', 'WhCode'), ('forchildrenlocationcode', 'A', 'ParentWhCode')):
            self.in_list(owner, field, supply[name])
        self.children = supply['forchildren']
        for group, special, code in (('productFilter', 'sku', 'SKUCode'), ('locationFilter', 'location', 'WhCode')):
            items = self.items(group)
            self.in_list('A', code, [i['value'] for i in items if i['attributeName'].lower() == special])
            self.grouped([i for i in items if i['attributeName'].lower() != special],
                lambda name, group=group: ('C', name.replace('p', 'sl')) if group == 'productFilter' else ('D', 'l' + name))
        availability = self.items('availabilityFilter')
        for item in availability:
            name = item['attributeName'].lower()
            if name in ('norm', 'stock', 'git', 'virtualnorm'):
                self.where.append(self.compare('A', name, item.get('operator'), item['value']))
        for name, field in (('pic', 'PipelineInventoryColor'), ('ohic', 'PhysicalInventoryColor'), ('pipo,seasonality', 'Tags')):
            self.in_list('A', field, [i['value'] for i in availability if i['attributeName'].lower() == name])
        if self.family == 'fulfillment':
            self.in_list('A', 'Coverage', [i['value'] for i in self.items('coverageFilter') if i['attributeName'].lower() == 'coverage'])
        def custom(name):
            for prefix, owner in (('skulocattr', 'B'), ('skuattr', 'C'), ('locattr', 'D')):
                if prefix in name.lower():
                    return owner, name.lower().replace(prefix, 'c')
        self.grouped([i for i in self.items('customAttributeFilter') if any(p in i['attributeName'].lower()
                     for p in ('skulocattr', 'skuattr', 'locattr'))], custom)
        return ' AND '.join(self.where) or 'TRUE'


def read_grid(run, payload, *, family, paging, count=False, resolved_scope=None):
    relation, relation_params = admitted_grids(run)[family]
    importer, manifest = _projected_attributes(run) if resolved_scope is None else resolved_scope[:2]
    if manifest:
        raise PublicationUnavailable('planning_grid_native_hierarchy_required')
    if family == 'excess':
        from mta.presentation.excess_filters import predicate
        model = ExcessInventoryRow
    elif family == 'fulfillment':
        from mta.presentation.fulfillment_filters import predicate
        model = FulfillmentSummaryRow
    else:
        raise ValueError('Unknown Planning normal-grid family')
    predicate(payload, importer)  # Preserve structural and inherited-invalid branches.
    filters = GridFilters(payload, family, model)
    try:
        where = filters.compile()
    except PublicationUnavailable as exc:
        raise PublicationUnavailable('LEG-' + family.upper() + '-FILTER-INVALID-SQL:' + str(exc).partition(':')[2]) from exc
    products, locations = scope(payload, attributes=importer) if resolved_scope is None else resolved_scope[2:]
    if not products or not locations:
        return 0 if count else []
    ctes, params = ['H AS (' + relation + ')'], list(relation_params)
    for alias, codes in (('P', products), ('L', locations)):
        members = sorted(codes)
        ctes.append(alias + '(code,weight) AS (VALUES ' + ','.join(['(%s::text,%s::bigint)'] * len(members)) + ')')
        params.extend(v for code in members for v in (code, codes.multiplicities[code]))
    joins = (' FROM H JOIN mta.' + quote(model._meta.db_table) + ' A ON A.run_id=H.run_id AND A.ordinal=H.fact_ordinal'
             ' JOIN P ON A."SKUCode"=P.code JOIN L ON A."WhCode"=L.code')
    for alias, table, ordinal in (('B', 'SkuLocAttributeData', 'pair_ordinal'),
            ('C', 'SkuAttributeData', 'sku_ordinal'), ('D', 'LocationAttributeData', 'location_ordinal')):
        if alias not in filters.owners and not (alias == 'D' and filters.children):
            continue
        query, values = image_query(run, 'closing/importer/' + table)
        ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)
        if alias in filters.owners:
            joins += ' JOIN ' + alias + ' ON ' + alias + '.vf_ordinal=H.' + ordinal
    if filters.children:
        joins += ' JOIN D parent ON ' + equal('A."ParentWhCode"', 'parent."WHCode"') + ' AND (' + ' OR '.join(
            equal('parent."LocationType"', '%s') for _ in filters.children) + ')'
        params.extend(filters.children)
    params.extend(filters.params)
    if count:
        sql = 'WITH ' + ','.join(ctes) + ' SELECT COALESCE(sum(P.weight*L.weight),0)' + joins + ' WHERE ' + where
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return int(cursor.fetchone()[0])
    order = ('H.location_key DESC,H.sku_key ASC' if family == 'excess' else
             'A."Gap" DESC NULLS LAST,H.sku_key DESC,H.location_key DESC')
    # The occurrence ordinal preserves the existing selector's stable source
    # order inside SQL ties, not a new claim of legacy deterministic tie order.
    order += ',H.ordinal,copies.n'
    fields = [f.name for f in model._meta.local_fields if f.name not in ('id', 'run', 'ordinal')]
    selected = ','.join('A.' + quote(name) for name in fields)
    selected += ',H.sku_description AS "SKUName",H.location_description AS "WHName"'
    selected += ',' + ','.join('H.' + prefix + str(i) for prefix in ('sl', 'll') for i in range(1, 6))
    if family == 'excess':
        selected += ',H.parent_description AS "ParentWHName"'
    ctes.append('selected AS (SELECT row_number() OVER (ORDER BY ' + order + ') AS rn,' + selected
                + joins + ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) copies(n) WHERE ' + where + ')')
    sql = 'WITH ' + ','.join(ctes) + ' SELECT * FROM selected'
    if paging is not None:
        page, size = paging
        sql += ' WHERE rn BETWEEN %s AND %s'
        params.extend(((page-1)*size+1, page*size))
    sql += ' ORDER BY rn'
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [d[0] for d in cursor.description]
        rows = storage([dict(zip(names, values)) for values in cursor.fetchall()])
    for row in rows:
        row.update(WHCode=row['WhCode'], Requirement=row['RequiredQty' if family == 'excess' else 'TotalReq'],
                   PhysicalColor=row['PhysicalInventoryColor'], PipelineColor=row['PipelineInventoryColor'],
                   PhysicalPen=None if row['PhysicalInventoryPen'] is None else float(row['PhysicalInventoryPen']),
                   PipelinePen=None if row['PipelineInventoryPen'] is None else float(row['PipelineInventoryPen']))
    if family == 'excess':
        from mta.presentation.excess_grid import EXCESS_ALIASES
        return [dict(rn=row['rn'], **{alias: row.get(field) for alias, field in EXCESS_ALIASES.items()}) for row in rows]
    from mta.presentation.fulfillment_grid import fulfillment_grid_rows
    from mta.presentation.fulfillment_views import detail_aliases
    details = selected_details(run, rows)
    projected = fulfillment_grid_rows(rows, detail_aliases(details))
    for result, row in zip(projected, rows):
        result['rn'] = row['rn']
    return projected


def selected_details(run, rows):
    if not rows:
        return []
    pairs = sorted({(row['SKUCode'], row['WhCode']) for row in rows})
    fields = [f.name for f in FulfillmentDetailRow._meta.local_fields if f.name not in ('id', 'run', 'ordinal')]
    sql = ('WITH pairs(sku,location) AS (VALUES ' + ','.join(['(%s::text,%s::text)'] * len(pairs)) + ') SELECT '
           + ','.join('A.' + quote(name) for name in fields) + ' FROM mta.' + quote(FulfillmentDetailRow._meta.db_table)
           + ' A WHERE A.run_id=%s AND EXISTS (SELECT 1 FROM pairs P WHERE ' + equal('A."SKUCode"', 'P.sku')
           + ' AND ' + equal('A."WhCode"', 'P.location') + ') ORDER BY A.ordinal')
    with connection.cursor() as cursor:
        cursor.execute(sql, [*[value for pair in pairs for value in pair], run.pk])
        return storage([dict(zip(fields, row)) for row in cursor.fetchall()])
