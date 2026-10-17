from mta.presentation.native_mode import removed_mode
"""One current scoped read of the retained, sealed Planning contributions."""
import json
from types import SimpleNamespace
from uuid import UUID
from django.conf import settings
from django.db import connection
from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable, scope

# Exact producer recipe of the accepted immutable contribution generation.
# This pins production provenance, independently of this response reader.
PREPARED_RECIPE = '189dd5148e1c9b4e13eb33a285ae666823925d4bead69e583d670745bf01ba9d'
METRICS = ('git_parent','git_child','git_custom','expedite_parent','expedite_child',
           'expedite_custom','excess_review','excess_custom','fulfillment_review','fulfillment_custom')
INT32 = frozenset(('expedite_parent','expedite_child','expedite_custom','excess_custom','fulfillment_custom'))


def read(run, payload):
    from mta.presentation.legacy_ui import _no_active_filters
    from mta.presentation.bpr_sql import _projected_attributes
    if not _no_active_filters(payload):
        raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
    from mta.presentation.planning_summary_admission import require_ready
    from mta.presentation import native_publication
    if native_publication.enabled():
        native_publication.require_mode()
        receipt = require_ready(run)
        from mta.presentation.selective import image_rows
        from mta.presentation import hierarchy
        from mta.presentation.context import permission_catalogue
        attrs = {name: image_rows(run, 'closing/importer/' + name) for name in ('SkuAttributeData', 'LocationAttributeData')}
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            attrs = hierarchy.project_attributes(attrs, permission_catalogue(), manifest)
    else:
        from mta.presentation.daily_planning.sources import _projected_attributes as daily_attributes
        require(run, 'overview')
        receipt = require_ready(run)
        attrs, _ = daily_attributes(run)
    return (counts(receipt, scope(payload, attributes=attrs)), run.business_date.isoformat())


def counts(receipt, resolved):
    products,locations=resolved
    totals={name:0 for name in METRICS}
    if products and locations:
        from mta.presentation.bpr_sql import _values_cte
        from mta.presentation.rrr_sql import equal
        ctes=[];params=[]
        for alias,codes in (('P',products),('L',locations)):
            sql,values=_values_cte([dict(code=code,weight=codes.multiplicities[code]) for code in sorted(codes)],('code','weight'),{'weight':'::bigint'})
            ctes.append(alias+' AS ('+sql+')');params.extend(values)
        branches=[]
        for profile,product,location in (
            ('raw','P.code=C.product_key','L.code=C.location_key'),
            ('normalized',equal('P.code','C.product_key'),equal('L.code','C.location_key'))):
            branches.append('SELECT C.metric,C.occurrence_count::numeric*(P.weight*L.weight) AS amount '
                'FROM mta.fresh_mta_planningsummarycontribution C JOIN P ON '+product+
                ' JOIN L ON '+location+" WHERE C.equality_profile='"+profile+"' AND C.receipt_id=%s")
        query='WITH '+','.join(ctes)+' SELECT metric,sum(amount) FROM ('+' UNION ALL '.join(branches)+') weighted GROUP BY metric'
        with connection.cursor() as c:
            c.execute(query,[*params,receipt.pk,receipt.pk]);totals.update((k,int(v)) for k,v in c.fetchall())
    for metric in INT32:
        if totals[metric]>2147483647:
            from django.db import DataError
            raise DataError('integer out of range')
    return [dict(category='git/wip',parentCount=str(totals['git_parent']),childCount=str(totals['git_child']),custom=str(totals['git_custom'])),
        dict(category='expedite',parentCount=str(totals['expedite_parent']),childCount=str(totals['expedite_child']),custom=str(totals['expedite_custom'])),
        dict(category='excessInventory',reviewCount=str(totals['excess_review']),custom=str(totals['excess_custom'])),
        dict(category='orderFulfillment',reviewCount=str(totals['fulfillment_review']),custom=str(totals['fulfillment_custom']))]
