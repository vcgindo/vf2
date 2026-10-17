from mta.presentation.native_mode import removed_mode
"""RRR reader over sealed occurrence membership; live auth/filter/page remain live."""
from django.db import connection
from django.conf import settings

from mta.presentation import hierarchy
from mta.presentation.context import permission_catalogue, scope, PublicationUnavailable
from mta.presentation.rrr import DIRECT_FIELDS, ALIASES, NULL_DASH
from mta.presentation.rrr_filters import rrr_predicate
from mta.presentation.rrr_preparation import a_selections, recipe_digest, source_signatures, verify_guards
from mta.presentation.selective import image_query, image_rows
from mta.runtime.models import RrrPreparedMembership, RrrPreparedProjection, PickBand
from mta.runtime.relational_state import CATALOG, quote


def admitted_relation(run):
    """Return None only when this run has never opted into prepared RRR."""
    if not settings.VF_RRR_PREPARED:
        return None
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if not daily or not getattr(run, 'pk', None):
        return None
    receipt = RrrPreparedProjection.objects.filter(run_id=run.pk).first()
    if receipt is None:
        raise PublicationUnavailable('rrr_prepared_receipt_required')
    try:
        if daily:
            from mta.presentation.daily_preparation import source_digest
            source = source_digest(run)
            selected = run
        else:
            selected, source = removed_mode('historical_fixture')
        dimensions, pick = source_signatures(run)
        verify_guards(connection)
    except (ValueError, PublicationUnavailable) as exc:
        raise PublicationUnavailable('rrr_prepared_admission_changed') from exc
    if selected.pk != run.pk or receipt.source_digest != source or receipt.dimension_digest != dimensions or (receipt.pick_digest != pick) or (receipt.recipe_digest != recipe_digest(run)):
        raise PublicationUnavailable('rrr_prepared_receipt_missing_or_changed')
    return ('SELECT * FROM mta.' + quote(RrrPreparedMembership._meta.db_table) + ' WHERE run_id=%s', [run.pk])


def read_prepared(run, payload, *, paging, count, relation, relation_params):
    """Read the same selected fields and bags from exact admitted ordinals."""
    from mta.presentation.rrr_sql import Filters, equal, key
    importer = {name: image_rows(run, 'closing/importer/' + name) for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    if manifest:
        raise PublicationUnavailable('rrr_prepared_native_hierarchy_required')
    rrr_predicate(payload, importer)
    products, locations = scope(payload, attributes=importer)
    if not products or not locations:
        return 0 if count else []
    ctes, params = (['H AS (' + relation + ')'], list(relation_params))
    for alias, path in (('R', 'reports/bpr/vf_RationedReqReport'), ('S', 'closing/dbm/SKULocStandardAttributes'), ('B', 'closing/importer/SkuLocAttributeData'), ('C', 'closing/importer/SkuAttributeData'), ('D', 'closing/importer/LocationAttributeData')):
        query, values = image_query(run, path)
        if manifest and alias in ('C', 'D'):
            table, prefix = ('SkuAttributeData', 'SL') if alias == 'C' else ('LocationAttributeData', 'LL')
            rows = importer[table]
            ctes.append(alias + 'native AS NOT MATERIALIZED (' + query + ')')
            params.extend(values)
            ctes.append(alias + 'hierarchy AS (VALUES ' + ','.join(['(%s,%s,%s,%s)'] * len(rows)) + ')')
            params.extend((value for ordinal, row in enumerate(rows) for value in (ordinal, *[row[prefix + str(i)] for i in (1, 2, 3)])))
            columns = [name for name, _ in CATALOG['tables']['Importer/' + table] if name not in [prefix + str(i) for i in (1, 2, 3)]]
            query = 'SELECT N.vf_ordinal,' + ','.join(('N.' + quote(name) for name in columns)) + ',' + ','.join(('H.column' + str(i + 1) + ' AS ' + quote(prefix + str(i)) for i in (1, 2, 3))) + ' FROM ' + alias + 'native N JOIN ' + alias + 'hierarchy H ON N.vf_ordinal=H.column1'
            values = []
        ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)
    ctes.append('A AS (SELECT H.*,' + ','.join(a_selections()) + ' FROM H JOIN R ON R.vf_ordinal=H.rationed_ordinal' + ' JOIN mta.' + quote(PickBand._meta.db_table) + ' K ON K.run_id=H.run_id AND K.ordinal=H.band_ordinal)')
    for alias, codes in (('P', products), ('L', locations)):
        members = [code for code in sorted(codes) for _ in range(codes.multiplicities[code])]
        ctes.append(alias + ' AS (VALUES ' + ','.join(['(%s)'] * len(members)) + ')')
        params.extend(members)
    filters = Filters(payload)
    where = filters.compile()
    joins = ' FROM A JOIN S ON S.vf_ordinal=A.standard_ordinal JOIN B ON B.vf_ordinal=A.pair_ordinal JOIN C ON C.vf_ordinal=A.sku_ordinal JOIN D ON D.vf_ordinal=A.location_ordinal JOIN P ON A."SKUCode"=P.column1 JOIN L ON A."WhCode"=L.column1'
    if filters.children:
        joins += ' JOIN D parent ON ' + equal('A."ParentWhCode"', 'parent."WHCode"') + ' AND (' + ' OR '.join((equal('parent."LocationType"', '%s') for _ in filters.children)) + ')'
        params.extend(filters.children)
    params.extend(filters.params)
    columns = [(name, 'A.' + quote(name)) for name in DIRECT_FIELDS]
    columns += [(name, 'A.' + quote(source)) for name, source in ALIASES.items()]
    columns += [(prefix.lower() + str(i), owner + '.' + quote(prefix + str(i))) for owner, prefix in (('C', 'SL'), ('D', 'LL')) for i in range(1, 6)]
    columns += [(prefix + str(i), 'COALESCE(' + owner + '.' + quote('c' + str(i)) + ",'-')") for prefix, owner in (('SKULocAttr', 'B'), ('SKUAttr', 'C'), ('LocAttr', 'D')) for i in range(1, 16)]
    selected = 'count(*)' if count else ','.join((('COALESCE(' + value + ",'-')" if name in NULL_DASH else value) + ' AS ' + quote(name) for name, value in columns))
    query = 'WITH ' + ','.join(ctes) + ' SELECT ' + selected + joins + ' WHERE ' + where
    if not count:
        query += ' ORDER BY A.dispatch_color_sequence NULLS FIRST, A.dispatch_pen DESC NULLS LAST,A.location_key,A.sku_key,A.ordinal'
        if paging is not None:
            query += ' LIMIT %s OFFSET %s'
            params.extend((paging[1], (paging[0] - 1) * paging[1]))
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        if count:
            return cursor.fetchone()[0]
        rows = [dict(zip((column[0] for column in cursor.description), values)) for values in cursor.fetchall()]
    if any((row['ParentNorm'] is None for row in rows)):
        raise ValueError('Canonical RRR ParentNorm NULL conversion is not comparable')
    return rows
