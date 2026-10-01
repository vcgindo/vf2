"""Deployed GuidedInsightsProcessor SKUDesc/WHDesc lookup contracts.

Pinned DLL0222eb96; deployed method source d2f578a2 (GetSKUDescription and
GetWHDescription). Both query BufferTrend descriptions and BufferTrend-owned
attribute membership. Preserve every auth/description join occurrence and NULL
omission; the scalar SQL JSON empty result is null.
"""
from collections import Counter

from mta.presentation import hierarchy
from mta.presentation.context import PublicationUnavailable, permission_catalogue, scope, selected_run
from mta.presentation.insight_response import scalar_json_rows
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import sql_key
from mta.presentation.selective import image_rows


def description_rows(rows, codes, kind):
    fields = (('SKUCode', 'sc'), ('SKUDescription', 'sd')) if kind == 'sku' else (
        ('WHCode', 'wc'), ('WHDescription', 'wd'))
    weights = Counter()
    for code in codes:
        key = sql_key(code)
        if key is not None:
            weights[key] += permission_multiplicity(codes, code)
    result = []
    for row in rows:
        for _ in range(weights[sql_key(row[fields[0][0]])]):
            result.append({alias: row[field] for field, alias in fields if row[field] is not None})
    return scalar_json_rows(result)


def selected_descriptions(payload, kind):
    if kind not in ('sku', 'location'):
        raise ValueError('unknown_description_kind')
    run = selected_run()
    attributes = {name: image_rows(run, 'closing/btr/' + name)
                  for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            attributes = hierarchy.project_attributes(attributes, permission_catalogue(), manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    products, locations = scope(payload, attributes=attributes)
    table = 'SKUDescriptionTbl' if kind == 'sku' else 'SiteDescriptionTbl'
    return description_rows(image_rows(run, 'closing/btr/' + table),
                            products if kind == 'sku' else locations, kind)
