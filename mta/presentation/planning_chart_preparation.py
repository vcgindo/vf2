"""One-time description membership and post-aggregate chart display matches.

Normal grid occurrences are intentionally not reused: their extra INNER joins
would remove eligible chart facts and change COUNT/SUM multiplicity.
"""
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_query
from mta.runtime.models import ExcessInventoryRow, FulfillmentSummaryRow, FulfillmentDetailRow
from mta.runtime.relational_state import quote

FAMILIES = {'excess': ExcessInventoryRow, 'fulfillment_summary': FulfillmentSummaryRow,
            'fulfillment_detail': FulfillmentDetailRow}


def recipe_digest():
    import inspect
    from mta.serialization import digest
    return digest(dict(version=1, query=inspect.getsource(chart_ingredients), families=list(FAMILIES)))


def chart_ingredients(run, family, direction):
    if run.kind != 'LEGACY_UI_FIXTURE' or str(run.business_date) != '2026-04-07':
        raise ValueError('Planning chart preparation requires retained April fixture')
    if family not in FAMILIES or direction not in ('sku','location'):
        raise ValueError('Unknown Planning chart grain')
    location = direction == 'location'
    code = 'WhCode' if location else 'SKUCode'
    dim_code = 'WHCode' if location else 'SKUCode'
    description = 'WHDescription' if location else 'SKUDescription'
    band = {'excess':None,'fulfillment_summary':'Coverage','fulfillment_detail':'OrderStatus'}[family]
    fact = 'SELECT * FROM mta.' + quote(FAMILIES[family]._meta.db_table) + ' WHERE run_id=%s'
    params = [run.pk]
    if family == 'excess':
        fact += ' AND "ReportDate"=%s'
        params.append(run.business_date)
    desc, values = image_query(run,'closing/importer/' + ('SiteDescriptionTbl' if location else 'SKUDescriptionTbl'))
    params.extend(values)
    attr, values = image_query(run,'closing/importer/' + ('LocationAttributeData' if location else 'SkuAttributeData'))
    params.extend(values)
    band_expr = 'A.' + quote(band) if band else 'NULL::text'
    common = ('WITH A AS (' + fact + '), D AS (' + desc + '), T AS (' + attr + '), raw AS (SELECT '
              'row_number() OVER (ORDER BY A.ordinal,D.vf_ordinal)-1 AS ordinal,'
              'A.ordinal AS fact_ordinal,D.vf_ordinal AS description_ordinal,A.' + quote(code) + ' AS code,'
              'D.' + quote(description) + ' AS description,' + band_expr + ' AS band FROM A JOIN D ON '
              + equal('A.' + quote(code),'D.' + quote(dim_code)) + '), members AS (SELECT *,min(ordinal) OVER (PARTITION BY '
              + ','.join(key(name) for name in ('code','description','band')) + ') AS group_ordinal FROM raw) ')
    members = common + 'SELECT ordinal,group_ordinal,fact_ordinal,description_ordinal,code,description,band FROM members ORDER BY ordinal'
    prefix = 'LL' if location else 'SL'
    displays = (common + 'SELECT row_number() OVER (ORDER BY G.group_ordinal,T.vf_ordinal)-1 AS ordinal,'
                'G.group_ordinal,T.vf_ordinal AS attribute_ordinal,'
                + ','.join('T.' + quote(prefix+str(i)) + ' AS h' + str(i) for i in range(1,6))
                + ' FROM (SELECT DISTINCT ON (group_ordinal) * FROM members ORDER BY group_ordinal,ordinal) G '
                'JOIN T ON ' + equal('G.code','T.' + quote(dim_code)) + ' ORDER BY ordinal')
    return dict(members=(members,params),displays=(displays,params))
