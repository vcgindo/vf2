from mta.presentation.native_mode import removed_mode
"""Readers over sealed history memberships; request semantics remain live."""
from django.conf import settings
from django.db import connection

from mta.presentation import hierarchy, history_native
from mta.presentation.context import permission_catalogue, scope, PublicationUnavailable
from mta.presentation.history_preparation import RUN_ID, recipe_digest, source_signatures, verify_guards
from mta.presentation.rrr import sql_key
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_metadata, image_query, image_rows
from mta.runtime.models import (
    BufferGraphPreparedMembership, HistoryPreparedProjection,
    ResearchAvailabilityMembership, ResearchPreparedHistoryReference,
    ResearchPreparedMasterReference,
)
from mta.runtime.relational_state import CATALOG, quote, wire_value


def admitted(run):
    """Serve only explicit fixture opt-in; enabled missing sources fail closed."""
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if not daily:
        return None
    from mta.presentation.terminal_read_mode import prepared
    if not prepared('VF_HISTORY_REPORTS_PREPARED', run):
        return None
    receipt = HistoryPreparedProjection.objects.filter(run_id=run.pk).first()
    if receipt is None:
        raise PublicationUnavailable('history_prepared_receipt_missing_or_changed')
    try:
        if daily:
            from mta.presentation.daily_preparation import source_digest
            selected, source = (run, source_digest(run))
        else:
            selected, source = removed_mode('historical_fixture')
        dimensions = source_signatures(run)
        verify_guards(connection)
    except (ValueError, PublicationUnavailable) as exc:
        raise PublicationUnavailable('history_prepared_admission_changed') from exc
    if receipt.status != 'READY' or selected.pk != run.pk or source != receipt.source_digest or (dimensions != receipt.dimension_digest) or (recipe_digest() != receipt.recipe_digest):
        raise PublicationUnavailable('history_prepared_receipt_missing_or_changed')
    return receipt


def _attributes(run):
    state = {name: image_rows(run, 'closing/btr/' + name)
             for name in ('SkuAttributeData','LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        return (hierarchy.project_attributes(state, permission_catalogue(), manifest), manifest) if manifest else (state, None)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc


def _selected(pairs):
    pairs = sorted(pair for pair in pairs if pair is not None)
    return ('VALUES ' + ','.join(['(%s,%s)'] * len(pairs)),
            [value for pair in pairs for value in pair])


def _source_rows(run, path, reference_model, selected, *, family=None, source_field):
    selected = [pair for pair in selected if pair is not None]
    if not selected:
        return []
    item = image_metadata(run, path)
    relation, params = image_query(run, path)
    keys, selected_params = _selected(selected)
    table = 'mta.' + quote(reference_model._meta.db_table)
    family_sql, family_params = ('', []) if family is None else (' AND M.family=%s', [family])
    fields = item['fields']
    sql = ('WITH A AS (' + relation + '),K AS (' + keys + ') SELECT '
           + ','.join('A.' + quote(column) for _, column, _ in fields)
           + ' FROM A JOIN (SELECT DISTINCT M.' + source_field + ' FROM ' + table
           + ' M JOIN K ON M.owner_sku_key=K.column1 AND M.owner_location_key=K.column2'
           + ' WHERE M.run_id=%s' + family_sql + ') S ON A.vf_ordinal=S.' + source_field
           + ' ORDER BY A.vf_ordinal')
    with connection.cursor() as cursor:
        cursor.execute(sql, params + selected_params + [run.pk] + family_params)
        return [{name: wire_value(value, kind) for (name, _, kind), value in zip(fields, row)}
                for row in cursor.fetchall()]


def read_research(run, payload):
    data = payload.get('data')
    if not isinstance(data, list) or not data:
        raise ValueError('Selected research data required')
    selected = {sql_key(row['SKUCode'], row['WhCode']) for row in data}
    attributes, _ = _attributes(run)
    products, locations = scope(payload, attributes=attributes)
    masters = _source_rows(run, 'reports/bpr/vf_RationedReqReport',
                           ResearchPreparedMasterReference, selected, source_field='rationed_ordinal')
    parents = {sql_key(row['SKUCode'], row['ParentWhCode']) for row in masters}
    state = attributes
    for family, name in (('physical','BufferTrendPhysicalInv'), ('dispatch','BufferTrendDispatch')):
        state[name] = _source_rows(run, 'closing/btr/' + name,
                                   ResearchPreparedHistoryReference, selected | parents,
                                   family=family, source_field='history_ordinal')
    return history_native.research_rows(state, masters, data, products=products, locations=locations)


def _dimension_ctes(run, attributes, manifest, *, metadata=None):
    ctes, params = ([], [])
    for alias, table, prefix in (('sa', 'SkuAttributeData', 'SL'), ('la', 'LocationAttributeData', 'LL')):
        path = 'closing/btr/' + table
        query, values = image_query(run, path, **{} if metadata is None else {'metadata': metadata[path]})
        if not manifest:
            ctes.append(alias + ' AS (' + query + ')')
            params.extend(values)
            continue
        ctes.append(alias + 'native AS (' + query + ')')
        params.extend(values)
        rows = attributes[table]
        ctes.append(alias + 'hierarchy AS (VALUES ' + ','.join(['(%s,%s,%s,%s)'] * len(rows)) + ')')
        params.extend((v for ordinal, row in enumerate(rows) for v in (ordinal, *[row[prefix + str(i)] for i in (1, 2, 3)])))
        fields = [name for name, _ in CATALOG['tables']['BTR/' + table] if name not in [prefix + str(i) for i in (1, 2, 3)]]
        ctes.append(alias + ' AS (SELECT ' + ','.join(('N.' + quote(name) for name in fields)) + ',' + ','.join(('H.column' + str(i + 1) + ' AS ' + quote(prefix + str(i)) for i in (1, 2, 3))) + ' FROM ' + alias + 'native N JOIN ' + alias + 'hierarchy H ON N.vf_ordinal=H.column1)')
    return (ctes, params)


def read_historical_availability(run, payload):
    from mta.presentation.terminal_read_mode import prepared
    if prepared('VF_RESEARCH_AVAILABILITY_PREPARED', run):
        return read_availability_bands(run, payload)
    attributes, manifest = _attributes(run)
    products, locations = scope(payload, attributes=attributes)
    if not products or not locations:
        return [dict(availability_01_30=0, availability_31_60=0, availability_61_90=0)]
    a, params = image_query(run, 'closing/btr/BufferTrendPhysicalInv')
    ctes = ['A AS (' + a + ')']; dim_ctes, dim_params = _dimension_ctes(run, attributes, manifest)
    ctes += dim_ctes; params += dim_params
    for alias, codes in (('P',products), ('L',locations)):
        ctes.append(alias + ' AS (VALUES ' + ','.join(['(%s,%s)'] * len(codes)) + ')')
        params.extend(value for code in sorted(codes) for value in (code, codes.multiplicities[code]))
    table = 'mta.' + quote(ResearchAvailabilityMembership._meta.db_table)
    joins = (' FROM ' + table + ' M JOIN A ON A.vf_ordinal=M.history_ordinal'
             + ' JOIN sa ON sa.vf_ordinal=M.sku_ordinal JOIN la ON la.vf_ordinal=M.location_ordinal'
             + ' JOIN P ON A."SKUCode"=P.column1 JOIN L ON A."WhCode"=L.column1')
    expressions = []
    for first, last in ((1,30),(31,60),(61,90)):
        cells = ['A.' + quote('D' + str(i)) for i in range(first,last+1)]
        for colours in (("'Black'",), tuple("'" + colour + "'" for _, colour in history_native.COLOURS)):
            expressions.append('sum((' + '+'.join('CASE WHEN ' + cell + ' IN (' + ','.join(colours)
                + ') THEN 1 ELSE 0 END' for cell in cells) + ')*P.column2*L.column2)')
    with connection.cursor() as cursor:
        cursor.execute('WITH ' + ','.join(ctes) + ' SELECT ' + ','.join(expressions)
                       + joins + ' WHERE M.run_id=%s', params + [run.pk])
        totals = cursor.fetchone()
    result = {}
    for i, (first,last) in enumerate(((1,30),(31,60),(61,90))):
        black, total = (value or 0 for value in totals[i*2:i*2+2])
        value = float(history_native.percentage(total-black,total))
        result[f'availability_{first:02d}_{last}'] = int(value) if value.is_integer() else value
    return [result]


def read_availability_bands(run, payload):
    """Aggregate sealed exact source occurrences under live native scopes."""
    from mta.presentation import research_availability_preparation as preparation
    from mta.runtime.models import ResearchAvailabilityBand, ResearchAvailabilityBandProjection
    history = admitted(run)
    receipt = ResearchAvailabilityBandProjection.objects.filter(run_id=run.pk).first()
    if history is None or receipt is None or receipt.status != 'READY' or (
            receipt.source_digest != history.source_digest or
            receipt.membership_digest != history.availability_digest or
            receipt.row_count != history.availability_count or
            receipt.recipe_digest != preparation.recipe_digest()):
        raise PublicationUnavailable('research_availability_band_receipt_missing_or_changed')
    try:
        preparation.verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('research_availability_band_guards_changed') from exc
    attributes, _ = _attributes(run)
    products, locations = scope(payload, attributes=attributes)
    if not products or not locations:
        return [dict(availability_01_30=0, availability_31_60=0, availability_61_90=0)]
    ctes, params = [], []
    for alias, codes in (('P', products), ('L', locations)):
        ctes.append(alias + ' AS (VALUES ' + ','.join(['(%s,%s)'] * len(codes)) + ')')
        params.extend(value for code in sorted(codes) for value in (code, codes.multiplicities[code]))
    expressions = [
        'sum(B.' + quote(prefix + f'{first:02d}_{last}') + '*P.column2*L.column2)'
        for first, last in preparation.BANDS for prefix in ('black_', 'recognized_')]
    with connection.cursor() as cursor:
        cursor.execute('WITH ' + ','.join(ctes) + ' SELECT ' + ','.join(expressions) +
                       ' FROM mta.' + quote(ResearchAvailabilityBand._meta.db_table) +
                       ' B JOIN P ON B.sku_code=P.column1 JOIN L ON B.location_code=L.column1'
                       ' WHERE B.run_id=%s', params + [run.pk])
        totals = cursor.fetchone()
    result = {}
    for i, (first, last) in enumerate(preparation.BANDS):
        black, total = (value or 0 for value in totals[i * 2:i * 2 + 2])
        value = float(history_native.percentage(total - black, total))
        result[f'availability_{first:02d}_{last}'] = int(value) if value.is_integer() else value
    return [result]


def read_graph(run, payload, *, columns, filters, where, attributes, manifest, products, locations, dates,
               metadata=None):
    if not products or not locations:
        return history_native.graph_response([dict(D=c, **{a:None for a,_ in history_native.COLOURS})
                                              for c in columns], dates)
    family = 'dispatch' if str(payload.get('bufferTrendType','tech')).lower() == 'eco' else 'physical'
    path = 'BufferTrendDispatch' if family == 'dispatch' else 'BufferTrendPhysicalInv'
    path = 'closing/btr/' + path
    pair_path = 'closing/btr/SkuLocAttributeData'
    a, params = image_query(run, path,
        **({} if metadata is None else {'metadata': metadata[path]}))
    sla, sla_params = image_query(run, pair_path,
        **({} if metadata is None else {'metadata': metadata[pair_path]}))
    ctes = ['A AS (' + a + ')', 'sla AS (' + sla + ')']; params += sla_params
    dim_ctes, dim_params = _dimension_ctes(run, attributes, manifest,
        **({} if metadata is None else {'metadata': metadata})); ctes += dim_ctes; params += dim_params
    for alias, codes in (('P',products),('L',locations)):
        members = [code for code in sorted(codes) for _ in range(codes.multiplicities[code])]
        ctes.append(alias + ' AS (VALUES ' + ','.join(['(%s)'] * len(members)) + ')'); params.extend(members)
    table = 'mta.' + quote(BufferGraphPreparedMembership._meta.db_table)
    source_keys = ((key('A."SKUCode"'), 'M.sku_key'),
                   (key('A."WhCode"'), 'M.location_key'))
    indexed_filter = any(source in where for source, _ in source_keys)
    joins = (' FROM (SELECT * FROM ' + table + ' WHERE run_id=%s AND family=%s) M'
             + ' JOIN A ON A.vf_ordinal=M.history_ordinal'
             + ' JOIN sa ON sa.vf_ordinal=M.sku_ordinal JOIN la ON la.vf_ordinal=M.location_ordinal'
             + ' LEFT JOIN sla ON sla.vf_ordinal=M.pair_ordinal'
             + ' JOIN P ON ' + ('M.sku_key=' + key('P.column1') if indexed_filter
                               else equal('A."SKUCode"','P.column1'))
             + ' JOIN L ON ' + ('M.location_key=' + key('L.column1') if indexed_filter
                               else equal('A."WhCode"','L.column1')))
    # The sealed graph recipe stores these exact SQL-normalized source keys.
    # Qualify the indexed membership before fetching wide history rows. Keep the
    # original predicate structure, including the canonical unparenthesized OR.
    # Leave the already measured unfiltered Tech/Eco access path unchanged.
    if indexed_filter:
        for source, prepared in source_keys:
            where = where.replace(source, prepared)
    child_params = []
    if filters.children:
        joins += (' JOIN la parent ON ' + equal('A."ParentWhCode"','parent."WHCode"') + ' AND ('
                  + ' OR '.join(equal('parent."LocationType"','%s') for _ in filters.children) + ')')
        child_params.extend(filters.children)
    projection = ','.join('sum(CASE WHEN ' + equal('A.' + quote(column), "'" + colour + "'")
        + ' THEN 1 ELSE 0 END)::integer' for column in columns for _, colour in history_native.COLOURS)
    with connection.cursor() as cursor:
        cursor.execute('WITH ' + ','.join(ctes) + ' SELECT ' + projection + joins
                       + ' WHERE ' + where,
                       params + [run.pk, family] + child_params + filters.params)
        totals = cursor.fetchone()
    counts = [dict(D=column, **{alias:totals[i*6+j] for j,(alias,_) in enumerate(history_native.COLOURS)})
              for i,column in enumerate(columns)]
    return history_native.graph_response(counts, dates)
