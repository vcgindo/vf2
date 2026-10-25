"""The ten original quadrant measures over prepared phase-owned relations."""
from django.db import connection, DataError
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.planning_summary import METRICS, INT32
from mta.presentation.rrr_sql import equal


def contribution_queries(view):
    # Same count grains as planning_summary_daily.contribution_queries. Facts
    # and occurrence relations have explicit phase owners; no Full table joins.
    run = view.run
    def grouped(metric, relation, params, product, location, profile='raw'):
        return ('SELECT %s::text AS metric,' + product + ' AS product_key,' + location +
            ' AS location_key,%s::text AS equality_profile,count(*)::bigint AS occurrence_count ' +
            relation + ' GROUP BY 2,3'), [metric, profile, *params]
    git, gp = view.git.query(); master, mp = view.git.prepared.query('git_master')
    for direction, owner in (('parent', 'WhCode'), ('child', 'ParentWhCode')):
        relation = ('FROM (' + git + ') H JOIN (' + master + ') A ON '
            'A.rationed_ordinal=H.rationed_ordinal AND A.standard_ordinal=H.standard_ordinal WHERE H.grid_eligible')
        yield grouped('git_' + direction, relation, [*gp, *mp], 'A."SKUCode"', 'A."' + owner + '"')
    expedite, ep = view.expedite.query('grid')
    facts, fp = view.expedite.fact_query('ExpediteDispatches')
    eligible = "H.direction='child' AND H.branch='dispatch' AND " + ' AND '.join(
        'H.' + name + ' IS NOT NULL' for name in ('standard_ordinal', 'sku_description_ordinal',
        'location_description_ordinal', 'sku_ordinal', 'location_ordinal', 'pair_ordinal'))
    eligible += " AND lower(rtrim(A.\"PipelineInventoryColor\"::text,' ')) IN ('red','black')"
    for direction, owner in (('parent', 'WhCode'), ('child', 'ParentWhCode')):
        relation = ('FROM (' + expedite + ') H JOIN (' + facts + ') A '
            'ON A.run_id=H.run_id AND A.ordinal=H.fact_ordinal WHERE ' + eligible)
        yield grouped('expedite_' + direction, relation, [*ep, *fp], 'A."SKUCode"', 'A."' + owner + '"')
    for family, fact in (('excess', 'ExcessInventoryDetails'), ('fulfillment', 'OrderFulfillmentSummary')):
        sql, params = view.planning.query(family + '_grid')
        facts, fp = view.planning.fact_query(fact)
        yield grouped(family + '_review', 'FROM (' + sql + ') H JOIN (' + facts + ') A '
            'ON A.run_id=H.run_id AND A.ordinal=H.fact_ordinal', [*params, *fp], 'A."SKUCode"', 'A."WhCode"')
    for family, fact, owner, condition in (
        ('expedite', 'ExpediteDispatches', 'ParentWhCode',
         "A.\"RationedQty\">0 AND lower(rtrim(A.\"PipelineInventoryColor\"::text,' ')) IN ('red','black')"),
        ('excess', 'ExcessInventoryDetails', 'WhCode', 'A."ReportDate"=%s'),
        ('fulfillment', 'OrderFulfillmentSummary', 'WhCode', 'TRUE')):
        sql, params = view.planning.fact_query(fact)
        yield grouped(family + '_custom', 'FROM (' + sql + ') A WHERE ' + condition,
            [*params, *([run.business_date] if family == 'excess' else [])], 'A."SKUCode"', 'A."' + owner + '"')
    from mta.presentation.daily_transit import PATH, TRANSPORTER_PATH
    a, ap = view.git.image_query(TRANSPORTER_PATH); t, tp = view.git.image_query(PATH)
    relation = 'FROM (' + a + ') A JOIN (' + t + ') T ON ' + equal('A."SKUCode"', 'T."SKUCode"') + ' AND ' + equal('A."WhCode"', 'T."WhCode"')
    yield grouped('git_custom', relation, [*ap, *tp], 'A."SKUCode"', 'A."WhCode"', 'normalized')


def read(view, payload):
    from mta.presentation.legacy_ui import _no_active_filters
    from mta.presentation.bpr_sql import _values_cte
    if not _no_active_filters(payload): raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
    products, locations = scope(payload, attributes=view.planning.attributes())
    totals = {metric: 0 for metric in METRICS}
    if products and locations:
        ctes = []; params = []
        for alias, codes in (('P', products), ('L', locations)):
            sql, values = _values_cte([dict(code=c, weight=codes.multiplicities[c]) for c in sorted(codes)],
                ('code', 'weight'), {'weight': '::bigint'})
            ctes.append(alias + ' AS (' + sql + ')'); params.extend(values)
        queries = list(contribution_queries(view))
        ctes.append('C AS (' + ' UNION ALL '.join('(' + q + ')' for q, _ in queries) + ')')
        params.extend(v for _, values in queries for v in values)
        branches = []
        for profile, product, location in (('raw', 'P.code=C.product_key', 'L.code=C.location_key'),
                ('normalized', equal('P.code', 'C.product_key'), equal('L.code', 'C.location_key'))):
            branches.append('SELECT C.metric,C.occurrence_count::numeric*(P.weight*L.weight) AS amount '
                'FROM C JOIN P ON ' + product + ' JOIN L ON ' + location + " WHERE C.equality_profile='" + profile + "'")
        with connection.cursor() as cursor:
            cursor.execute('WITH ' + ','.join(ctes) + ' SELECT metric,sum(amount) FROM (' +
                ' UNION ALL '.join(branches) + ') weighted GROUP BY metric', params)
            totals.update((key, int(value)) for key, value in cursor.fetchall())
    if any(totals[key] > 2147483647 for key in INT32): raise DataError('integer out of range')
    values = [dict(category='git/wip', parentCount=str(totals['git_parent']), childCount=str(totals['git_child']), custom=str(totals['git_custom'])),
        dict(category='expedite', parentCount=str(totals['expedite_parent']), childCount=str(totals['expedite_child']), custom=str(totals['expedite_custom'])),
        dict(category='excessInventory', reviewCount=str(totals['excess_review']), custom=str(totals['excess_custom'])),
        dict(category='orderFulfillment', reviewCount=str(totals['fulfillment_review']), custom=str(totals['fulfillment_custom']))]
    return values, view.run.business_date.isoformat()
