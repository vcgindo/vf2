"""One-time exact Excess/Fulfillment normal-grid occurrences.

Consumers must persist these results before serving. These are deliberately not
chart grains: chart descriptions aggregate before attribute expansion. Custom
NMS grids also have different join rules and must not reuse these occurrences.
"""
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query
from mta.runtime.models import ExcessInventoryRow, FulfillmentSummaryRow
from mta.runtime.relational_state import quote

DIMENSIONS = (
    ('sd', 'SKUDescriptionTbl'), ('ld', 'SiteDescriptionTbl'),
    ('sa', 'SkuAttributeData'), ('la', 'LocationAttributeData'),
    ('pair', 'SkuLocAttributeData'),
)


def recipe_digest():
    import inspect
    from mta.serialization import digest
    return digest(dict(version=1, dimensions=DIMENSIONS, query=inspect.getsource(grid_occurrences)))


def grid_occurrences(run, family):
    """Return typed source occurrences with display and filter-owner references."""
    if family not in ('excess', 'fulfillment'):
        raise ValueError('Unknown Planning normal-grid family')
    if getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE' or str(run.business_date) != '2026-04-07':
        raise ValueError('Planning occurrence preparation requires the April fixture')
    model = ExcessInventoryRow if family == 'excess' else FulfillmentSummaryRow
    fact = 'SELECT * FROM mta.' + quote(model._meta.db_table) + ' WHERE run_id=%s'
    params = [run.pk]
    if family == 'excess':
        fact += ' AND "ReportDate"=%s'
        params.append(run.business_date)
    ctes = ['a AS (' + fact + ')']
    for alias, table in DIMENSIONS:
        query, values = image_query(run, 'closing/importer/' + table)
        ctes.append(alias + ' AS (' + query + ')')
        params.extend(values)
    fields = [('fact_ordinal', 'a.ordinal'),
              ('sku_description_ordinal', 'sd.vf_ordinal'),
              ('location_description_ordinal', 'ld.vf_ordinal'),
              ('sku_ordinal', 'sa.vf_ordinal'), ('location_ordinal', 'la.vf_ordinal'),
              ('pair_ordinal', 'pair.vf_ordinal'),
              ('sku_key', key('a."SKUCode"')), ('location_key', key('a."WhCode"')),
              ('parent_key', key('a."ParentWhCode"')),
              ('sku_description', 'sd."SKUDescription"'),
              ('location_description', 'ld."WHDescription"')]
    joins = (' FROM a JOIN sd ON ' + equal('a."SKUCode"', 'sd."SKUCode"')
             + ' JOIN ld ON ' + equal('a."WhCode"', 'ld."WHCode"')
             + ' JOIN sa ON ' + equal('a."SKUCode"', 'sa."SKUCode"')
             + ' JOIN la ON ' + equal('a."WhCode"', 'la."WHCode"')
             + ' JOIN pair ON ' + equal('a."SKUCode"', 'pair."SKUCode"')
             + ' AND ' + equal('a."WhCode"', 'pair."LocCode"'))
    if family == 'excess':
        fields += [('parent_description_ordinal', 'pd.vf_ordinal'),
                   ('parent_description', 'pd."WHDescription"')]
        joins += ' LEFT JOIN ld pd ON ' + equal('a."ParentWhCode"', 'pd."WHCode"')
    fields += [(prefix.lower() + str(i), alias + '.' + quote(prefix + str(i)))
               for alias, prefix in (('sa', 'SL'), ('la', 'LL')) for i in range(1, 6)]
    # Ordinals retain actual occurrence ancestry. They are not an authorization
    # to add tie-breaks to consumer ORDER BY clauses that legacy leaves ambiguous.
    return ('WITH ' + ','.join(ctes) + ' SELECT '
            + ','.join(expression + ' AS ' + quote(name) for name, expression in fields)
            + joins), params
