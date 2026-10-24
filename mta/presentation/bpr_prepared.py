from mta.presentation.native_mode import removed_mode
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
        source, kind = super().column(owner, name)
        if owner == 'T':
            return source, kind
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


def _prepared_query(run, read_binding=None):
    if read_binding is not None:
        from mta.presentation.scoped_prepared import PreparedBinding
        if not isinstance(read_binding,PreparedBinding) or read_binding.run_id!=run.pk:
            raise PublicationUnavailable('BPR_prepared_phase_owner_differs')
        return read_binding.query('bpr_candidates')
    return ('SELECT * FROM ' + quote(BprPreparedRow._meta.db_table) +
            ' WHERE run_id=%s'), [run.pk]


def _build(run, payload, importer, ancillary, paging=None, *, count=False, analytics=False,
           live_remarks=False, daily_transit=False, export=False, read_binding=None):
    ctes, params = [], []
    def add(alias, query, values):
        ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)

    query, values = _prepared_query(run,read_binding)
    if read_binding is not None and live_remarks:
        raise PublicationUnavailable('BPR_phase_live_remarks_source_unavailable')
    source_query=(lambda path:image_query(run,path)) if read_binding is None else read_binding.image_query
    add('prepared', query, values)
    products, locations = scope(payload, attributes=importer)
    if not products or not locations:
        return None, []
    for alias, codes in (('P', products), ('L', locations)):
        query, values = _values_cte([{'code': code} for code in sorted(codes)
            for _ in range(codes.multiplicities[code])], ('code',))
        add(alias, query, values)

    filters = PreparedFilters(payload, export=export)
    where = filters.compile()
    parent = ''
    if filters.children:
        query, values = source_query('closing/importer/LocationAttributeData')
        add('D', query, values)
        parent = (' JOIN D parent ON ' + equal(column('A', 'ParentWhCode'), 'parent."WHCode"') +
                  ' AND (' + ' OR '.join(equal('parent."LocationType"', '%s')
                                         for _ in filters.children) + ')')
    auth = ' JOIN P ON R.sku_key=' + key('P.code') + ' JOIN L ON R.location_key=' + key('L.code')

    if not analytics:
        if live_remarks:
            from mta.presentation import ancillary_live
            source, values = ancillary_live.image_query(
                run, ancillary_live.PATHS[ancillary_live.BPR], include_live=True)
            query = ('SELECT vf_ordinal AS ordinal,"SKUCode","WhCode","RemarkDate","Remark"'
                     ' FROM (' + source + ') daily_bpr_remarks')
        else:
            rows = [dict(ordinal=i, **{name: row[name] for name in
                ('SKUCode', 'WhCode', 'RemarkDate', 'Remark')})
                for i, row in enumerate(ancillary['BPRReport_RemarkDetails'])]
            query, values = _values_cte(
                rows, ('ordinal', 'SKUCode', 'WhCode', 'RemarkDate', 'Remark'),
                {'ordinal': '::bigint', 'RemarkDate': '::timestamp'})
        add('remarks', query, values)
        add('latest_dates', 'SELECT ' + key('"SKUCode"') + ' AS sku_key,' + key('"WhCode"') +
            ' AS loc_key,max("RemarkDate") AS latest FROM remarks GROUP BY 1,2', [])
        add('latest_remarks', 'SELECT M.* FROM remarks M JOIN latest_dates D ON ' +
            key('M."SKUCode"') + '=D.sku_key AND ' + key('M."WhCode"') +
            '=D.loc_key AND M."RemarkDate"=D.latest', [])
    remarks_join = (' LEFT JOIN latest_remarks RM ON R.sku_key=' + key('RM."SKUCode"') +
                    ' AND R.location_key=' + key('RM."WhCode"'))
    if count:
        params.extend(filters.children)
        params.extend(filters.params)
        return ('WITH ' + ','.join(ctes) + ' SELECT count(*) FROM prepared R' +
                remarks_join + auth + parent + ' WHERE R.s_ordinal IS NOT NULL AND (' + where + ')'), params
    if analytics:
        params.extend(filters.children)
        params.extend(filters.params)
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
    if export:
        query, values = source_query('closing/btr/BufferTrendPhysicalInv')
        add('T', query, values)
        params.extend(filters.children)
        params.extend(filters.params)
        select = ','.join(value + ' AS ' + quote(name) for name, value in projection())
        if daily_transit:
            select += ',' + column('A', 'EcoColor') + ' AS _base_eco'
        joins = (' FROM prepared R' + auth + parent + remarks_join +
                 ' LEFT JOIN T ON R.sku_key=' + key('T."SKUCode"') +
                 ' AND R.location_key=' + key('T."WhCode"'))
        # Export filters the final join bag once. Grid key selection/rejoining
        # would multiply occurrences and apply filters at the wrong boundary.
        return ('WITH ' + ','.join(ctes) + ' SELECT ' + select + joins +
                ' WHERE ' + where + ' ORDER BY ' + ordering(True) +
                ',RM.ordinal,T.vf_ordinal'), params
    params.extend(filters.children)
    params.extend(filters.params)
    page, size = paging
    selected = ('SELECT R.sku_key,R.location_key FROM prepared R' + auth + parent +
                ' WHERE ' + where + ' ORDER BY ' + ordering(False) + ' LIMIT %s OFFSET %s')
    ctes.append('selected AS (' + selected + ')')
    params.extend((size, (page - 1) * size))
    ctes.append('selected_counts AS (SELECT sku_key,location_key,count(*)::bigint AS copies'
                ' FROM selected GROUP BY 1,2)')
    query, values = source_query('closing/btr/BufferTrendPhysicalInv')
    add('T', query, values)
    select = ','.join(value + ' AS ' + quote(name) for name, value in projection())
    if daily_transit:
        select += ',' + column('A', 'EcoColor') + ' AS _base_eco'
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


def _with_transit(rows, ancillary):
    from mta.presentation.rrr import index, sql_key
    transit = index(ancillary['InTransitData'], 'SKUCode', 'WhCode')
    for row in rows:
        base_colour = row.pop('_base_eco')
        items = []
        for source in transit.get(sql_key(row['SKUCode'], row['WHCode']), []):
            item = {target: source[field] for target, field in (('lc', 'OrderNo'),
                ('cd', 'CreationDate'), ('slt', 'SLT'), ('tlt', 'TLT'), ('ag', 'Ageing'),
                ('eta', 'ETA'), ('cl', 'CurrentLocationCode'), ('qty', 'InTransitQty'),
                ('remarks', 'Remark'))}
            item['exeecocolor'] = base_colour
            items.append(item)
        row['intransit'] = items or None
        yield row


def _export_rows(run, query, params, ancillary, daily):
    from mta.presentation.report_verification import verification_scope
    with verification_scope(run), transaction.atomic(), connection.cursor() as control:
        control.execute("SELECT current_setting('jit')")
        previous_jit = control.fetchone()[0]
        control.execute('SET LOCAL jit=off')
        with connection.chunked_cursor() as cursor:
            cursor.execute(query, params)
            names = [field[0] for field in cursor.description]
            def dictionaries():
                while records := cursor.fetchmany(500):
                    for record in records:
                        yield dict(zip(names, record))
            rows = dictionaries()
            yield from _with_transit(rows, ancillary) if daily else rows
        control.execute("SELECT set_config('jit',%s,true)", [previous_jit])


def _primed_export(rows):
    # Execute and fetch before HTTP headers, retaining the cursor/verification
    # lifetime through iteration. Explicit close propagates a cancelled download.
    sentinel = object()
    first = next(rows, sentinel)
    if first is sentinel:
        return iter(())
    class Remaining:
        def __init__(self):
            self.first = first
            self.closed = False

        def __iter__(self):
            return self

        def __next__(self):
            if self.closed:
                raise StopIteration
            if self.first is not sentinel:
                value, self.first = self.first, sentinel
                return value
            try:
                return next(rows)
            except BaseException:
                self.close()
                raise

        def close(self):
            if not self.closed:
                self.closed = True
                self.first = sentinel
                rows.close()
    return Remaining()


def _read_bpr(run, payload, *, paging=None, count=False, analytics=False, export=False):
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if not daily:
        raise ValueError('BPR prepared reader requires an admitted source run')
    if export and (count or analytics):
        raise ValueError('BPR_export_mode_conflict')
    if not export and not count and (not analytics) and (not isinstance(paging, tuple) or len(paging) != 2 or any((type(value) is not int or value < 1 for value in paging))):
        raise ValueError('positive_BPR_pagination_required')
    if daily:
        from mta.presentation.selective import image_rows
        from mta.presentation import hierarchy
        importer = {name: image_rows(run, 'closing/importer/' + name) for name in ('SkuAttributeData', 'LocationAttributeData')}
        manifest = hierarchy.selected_manifest(run)
    else:
        importer, manifest = _projected_attributes(run)
    BprPredicate(payload, importer['LocationAttributeData'], export=export)
    if manifest:
        raise PublicationUnavailable('BPR_prepared_hierarchy_supplement_not_bound')
    if daily:
        from mta.presentation.daily_preparation import ancillary_rows, source_digest as daily_source_digest
        source_digest = daily_source_digest(run)
        ancillary = ancillary_rows(run)
        from mta.presentation.logistics_live import serving_transit_rows
        ancillary['InTransitData'] = serving_transit_rows(run, ancillary['InTransitData'])
    else:
        selected, source_digest = removed_mode('historical_fixture')
        if selected.pk != run.pk:
            raise PublicationUnavailable('BPR_prepared_receipt_missing_or_changed')
        ancillary = removed_mode('historical_fixture')
    receipt = BprPreparedProjection.objects.filter(run_id=run.pk).first()
    if receipt is None or receipt.source_digest != source_digest or receipt.schema_digest != schema_digest():
        raise PublicationUnavailable('BPR_prepared_receipt_missing_or_changed')
    from mta.runtime.bpr_prepared_schema import verify_guards
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('BPR_prepared_guards_changed') from exc
    if not daily and ancillary['InTransitData']:
        raise PublicationUnavailable('nonempty_BPR_transit_wire_not_yet_validated')
    from mta.presentation.ancillary_live import serving_live
    query, params = _build(run, payload, importer, ancillary, paging, count=count, analytics=analytics, live_remarks=serving_live(run), daily_transit=daily, export=export)
    if query is None:
        if analytics:
            return [{prefix + color: 0 for prefix in ('OnHand', 'Pipeline') for color in ('Black', 'Red', 'Yellow', 'Green', 'White', 'Blue', 'Grey')}]
        return 0 if count else []
    if export:
        return _export_rows(run, query, params, ancillary, daily)
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('jit')")
        previous_jit = cursor.fetchone()[0]
        cursor.execute('SET LOCAL jit=off')
        cursor.execute(query, params)
        if count:
            result = cursor.fetchone()[0]
        else:
            names = [field[0] for field in cursor.description]
            result = [dict(zip(names, row)) for row in cursor.fetchall()]
        cursor.execute("SELECT set_config('jit',%s,true)", [previous_jit])
        if daily and (not count) and (not analytics):
            result = list(_with_transit(result, ancillary))
        return result


def read_bpr(run, payload, *, paging=None, count=False, analytics=False, export=False):
    if not export:
        return _read_bpr(run, payload, paging=paging, count=count, analytics=analytics)
    if count or analytics:
        raise ValueError('BPR_export_mode_conflict')
    def verified_rows():
        from mta.presentation.report_verification import verification_scope
        # Own admission from eager metadata/receipt validation through the last
        # cursor batch; a scope around only HTTP construction expires too early.
        with verification_scope(run):
            rows = _read_bpr(run, payload, paging=paging, export=True)
            try:
                yield from rows
            finally:
                close = getattr(rows, 'close', None)
                if close:
                    close()
    return _primed_export(verified_rows())
