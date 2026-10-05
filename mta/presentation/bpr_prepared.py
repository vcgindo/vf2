"""Read the sealed native BPR candidate bag; request semantics remain live."""
from django.db import connection, transaction

from mta.presentation.bpr_filters import BprPredicate
from mta.presentation.bpr_sql import BprSqlFilters, _projected_attributes, _values_cte
from mta.presentation.bpr_prepared_fields import FIELDS, field_name, schema_digest
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query
from mta.runtime.models import BprPreparedProjection, BprPreparedRow
from mta.runtime.relational_state import quote


def column(owner, name):
    return 'R.' + quote(field_name(owner, name))


class PreparedFilters(BprSqlFilters):
    def column(self, owner, name):
        _, kind = super().column(owner, name)
        fields = {field.casefold(): field for field in FIELDS[owner]}
        if name.casefold() not in fields:
            raise PublicationUnavailable('BPR_prepared_filter_field_missing')
        return column(owner, fields[name.casefold()]), kind


def projection():
    c = column
    pen = lambda name: 'NULLIF(' + c('V', name) + ',-99999999.00)'
    result = [(name, c(owner, field)) for name, owner, field in (
        ('tags', 'S', 'Tags'), ('SKUCode', 'A', 'SKUCode'), ('SKUName', 'A', 'SKUName'),
        ('WHCode', 'A', 'WhCode'), ('WHName', 'A', 'WhName'),
        ('ParentWhCode', 'A', 'ParentWhCode'))]
    result += [('ParentName', "COALESCE(" + c('A', 'ParentName') + ",'-')")]
    result += [(name, c('A', name)) for name in ('Stock', 'Norm', 'GIT')]
    result += [('ts', c('A', 'TechColorSequence')), ('TechPen', pen('PhysicalInventoryPen')),
        ('es', c('A', 'EcoColorSequence')),
        ('PhysicalInventoryColorSequence', c('V', 'PhysicalInventoryColorSequence')),
        ('EcoPen', pen('DispatchPen')), ('TechColor', c('V', 'PhysicalInventoryColor')),
        ('EcoColor', c('V', 'DispatchColor'))]
    result += [(name, 'COALESCE(' + c('A', name) + ',0)')
               for name in ('Req', 'RationedQTY', 'LeftoverParentStock')]
    result += [('PhaseIn-Out', 'CASE ' + c('A', 'PhaseIn-Out') +
                " WHEN 1 THEN 'Phase Out' WHEN 2 THEN 'Phase In' ELSE '-' END")]
    result += [(name, c('A', name)) for name in ('ResidualSnP', 'NormReq', 'BlueReq')]
    result += [('vn', c('V', 'VirtualNorm'))]
    result += [(f'sl{i}', c('C', f'SL{i}')) for i in range(1, 6)]
    result += [(f'll{i}', c('D', f'LL{i}')) for i in range(1, 6)]
    for prefix, owner, field in (('SKULocAttr', 'A', 'SKULocAttr'),
                                  ('SKUAttr', 'C', 'c'), ('LocAttr', 'D', 'c')):
        result += [(f'{prefix}{i}', 'COALESCE(' + c(owner, f'{field}{i}') + ",'-')")
                   for i in range(1, 16)]
    result += [('Remark', 'RM."Remark"'), ('intransit', 'NULL')]
    result += [(name, 'T.' + quote(name)) for name in
               ('Availability_01_30', 'Availability_31_60', 'Availability_61_90')]
    return result


def _prepared_query(run):
    return ('SELECT * FROM ' + quote(BprPreparedRow._meta.db_table) +
            ' WHERE run_id=%s'), [run.pk]


def _build(run, payload, importer, ancillary, paging=None, *, count=False, analytics=False):
    ctes, params = [], []
    def add(alias, query, values):
        ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)

    query, values = _prepared_query(run)
    add('prepared', query, values)
    products, locations = scope(payload, attributes=importer)
    if not products or not locations:
        return None, []
    for alias, codes in (('P', products), ('L', locations)):
        query, values = _values_cte([{'code': code} for code in sorted(codes)
            for _ in range(codes.multiplicities[code])], ('code',))
        add(alias, query, values)

    filters = PreparedFilters(payload)
    where = filters.compile()
    parent = ''
    if filters.children:
        query, values = image_query(run, 'closing/importer/LocationAttributeData')
        add('D', query, values)
        parent = (' JOIN D parent ON ' + equal(column('A', 'ParentWhCode'), 'parent."WHCode"') +
                  ' AND (' + ' OR '.join(equal('parent."LocationType"', '%s')
                                         for _ in filters.children) + ')')
    auth = ' JOIN P ON R.sku_key=' + key('P.code') + ' JOIN L ON R.location_key=' + key('L.code')

    if not analytics:
        rows = [dict(ordinal=i, **{name: row[name] for name in
            ('SKUCode', 'WhCode', 'RemarkDate', 'Remark')})
            for i, row in enumerate(ancillary['BPRReport_RemarkDetails'])]
        query, values = _values_cte(rows, ('ordinal', 'SKUCode', 'WhCode', 'RemarkDate', 'Remark'),
                                    {'ordinal': '::bigint', 'RemarkDate': '::timestamp'})
        add('remarks', query, values)
        add('latest_dates', 'SELECT ' + key('"SKUCode"') + ' AS sku_key,' + key('"WhCode"') +
            ' AS loc_key,max("RemarkDate") AS latest FROM remarks GROUP BY 1,2', [])
        add('latest_remarks', 'SELECT M.* FROM remarks M JOIN latest_dates D ON ' +
            key('M."SKUCode"') + '=D.sku_key AND ' + key('M."WhCode"') +
            '=D.loc_key AND M."RemarkDate"=D.latest', [])
    remarks_join = (' LEFT JOIN latest_remarks RM ON R.sku_key=' + key('RM."SKUCode"') +
                    ' AND R.location_key=' + key('RM."WhCode"'))
    params.extend(filters.children)
    params.extend(filters.params)
    if count:
        return ('WITH ' + ','.join(ctes) + ' SELECT count(*) FROM prepared R' +
                remarks_join + auth + parent + ' WHERE R.s_ordinal IS NOT NULL AND (' + where + ')'), params
    if analytics:
        fields = []
        for prefix, field in (('OnHand', 'PhysicalInventoryColor'), ('Pipeline', 'DispatchColor')):
            for color in ('Black', 'Red', 'Yellow', 'Green', 'White', 'Blue', 'Grey'):
                fields.append('count(*) FILTER (WHERE ' + key(column('V', field)) + "='" +
                              color.lower() + "') AS " + quote(prefix + color))
        return ('WITH ' + ','.join(ctes) + ' SELECT ' + ','.join(fields) +
                ' FROM prepared R' + auth + parent + ' WHERE ' + where), params

    ordinals = ','.join('R.' + owner + '_ordinal' for owner in ('a', 'v', 's', 'c', 'd', 'b'))
    def ordering(projected):
        pen = lambda name: ('NULLIF(' + column('V', name) + ',-99999999.00)'
                            if projected else column('V', name))
        return (column('V', 'PhysicalInventoryColorSequence') + ' NULLS FIRST,' +
            pen('PhysicalInventoryPen') + ' DESC NULLS LAST,' + column('A', 'EcoColorSequence') +
            ' NULLS FIRST,' + pen('DispatchPen') + ' DESC NULLS LAST,' +
            'R.location_key DESC NULLS LAST,R.sku_key NULLS FIRST,' + ordinals)
    page, size = paging
    selected = ('SELECT R.sku_key,R.location_key FROM prepared R' + auth + parent +
                ' WHERE ' + where + ' ORDER BY ' + ordering(False) + ' LIMIT %s OFFSET %s')
    ctes.append('selected AS (' + selected + ')')
    params.extend((size, (page - 1) * size))
    ctes.append('selected_counts AS (SELECT sku_key,location_key,count(*)::bigint AS copies'
                ' FROM selected GROUP BY 1,2)')
    query, values = image_query(run, 'closing/btr/BufferTrendPhysicalInv')
    add('T', query, values)
    select = ','.join(value + ' AS ' + quote(name) for name, value in projection())
    # Reconstruct only selected keys through the existing normalized-key index.
    # OFFSET 0 keeps PostgreSQL from flattening this bounded lookup back into a
    # second whole-estate scan of the wide candidate relation. It does not limit
    # occurrences: every matching row and every selected-key copy is retained.
    joins = (' FROM selected_counts K CROSS JOIN LATERAL (SELECT * FROM prepared candidate'
        ' WHERE candidate.sku_key=K.sku_key AND candidate.location_key=K.location_key'
        ' OFFSET 0) R' + remarks_join +
        ' LEFT JOIN T ON R.sku_key=' + key('T."SKUCode"') + ' AND R.location_key=' +
        key('T."WhCode"') + ' CROSS JOIN LATERAL generate_series(1,K.copies) copy_ordinal')
    return ('WITH ' + ','.join(ctes) + ' SELECT ' + select + joins + ' ORDER BY ' +
            ordering(True) + ',RM.ordinal,T.vf_ordinal,copy_ordinal'), params


def read_bpr(run, payload, *, paging=None, count=False, analytics=False):
    from mta.presentation import fixture
    if getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE':
        raise ValueError('BPR prepared reader is fixture-only')
    if not count and not analytics and (not isinstance(paging, tuple) or len(paging) != 2 or
            any(type(value) is not int or value < 1 for value in paging)):
        raise ValueError('positive_BPR_pagination_required')
    importer, manifest = _projected_attributes(run)
    BprPredicate(payload, importer['LocationAttributeData'])
    if manifest:
        raise PublicationUnavailable('BPR_prepared_hierarchy_supplement_not_bound')
    selected, source_digest = fixture.binding()
    receipt = BprPreparedProjection.objects.filter(run_id=run.pk).first()
    if selected.pk != run.pk or receipt is None or receipt.source_digest != source_digest or \
            receipt.schema_digest != schema_digest():
        raise PublicationUnavailable('BPR_prepared_receipt_missing_or_changed')
    from mta.runtime.bpr_prepared_schema import verify_guards
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('BPR_prepared_guards_changed') from exc
    ancillary = fixture.bpr_ancillary(run)
    if ancillary['InTransitData']:
        raise PublicationUnavailable('nonempty_BPR_transit_wire_not_yet_validated')
    query, params = _build(run, payload, importer, ancillary, paging, count=count, analytics=analytics)
    if query is None:
        if analytics:
            return [{prefix + color: 0 for prefix in ('OnHand', 'Pipeline')
                     for color in ('Black', 'Red', 'Yellow', 'Green', 'White', 'Blue', 'Grey')}]
        return 0 if count else []
    # The finite fixture plan spent 3.25 of 3.38 seconds compiling JIT code.
    # Keep this choice local, including when a caller owns an outer transaction.
    # A failed query rolls back this savepoint and its SET LOCAL together.
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('jit')")
        previous_jit = cursor.fetchone()[0]
        cursor.execute("SET LOCAL jit=off")
        cursor.execute(query, params)
        if count:
            result = cursor.fetchone()[0]
        else:
            names = [field[0] for field in cursor.description]
            result = [dict(zip(names, row)) for row in cursor.fetchall()]
        cursor.execute("SELECT set_config('jit',%s,true)", [previous_jit])
        return result
