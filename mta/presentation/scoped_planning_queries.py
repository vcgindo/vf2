"""Existing Planning SELECTs with explicit generation-owned providers.

Default Full producers/recipes stay in their original modules. Exact SQL and
parameter equivalence is qualified against those producers in PostgreSQL tests.
"""
from mta.presentation.rrr_sql import equal,key
from mta.presentation.planning_grid_preparation import DIMENSIONS
from mta.presentation.planning_chart_preparation import FAMILIES
from mta.runtime.models import ExcessInventoryRow,FulfillmentSummaryRow
from mta.runtime.relational_state import quote

FACTS={'excess':'ExcessInventoryDetails','fulfillment':'OrderFulfillmentSummary',
       'fulfillment_summary':'OrderFulfillmentSummary','fulfillment_detail':'OrderFulfillmentDetails'}

def grid_occurrences(run, family, read_binding):
    if family not in ('excess', 'fulfillment'):
        raise ValueError('Unknown Planning normal-grid family')
    model = ExcessInventoryRow if family == 'excess' else FulfillmentSummaryRow
    fact,params=read_binding.fact_query(FACTS[family])
    params=list(params)
    if family=='excess':
        fact+=' AND "ReportDate"=%s';params.append(run.business_date)
    ctes = ['a AS (' + fact + ')']
    for alias, table in DIMENSIONS:
        query, values = read_binding.image_query( 'closing/importer/' + table)
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

def custom_occurrences(run, family, read_binding):
    if family not in ('excess','fulfillment'):raise ValueError('Unknown custom family')
    model=ExcessInventoryRow if family=='excess' else FulfillmentSummaryRow
    fact,params=read_binding.fact_query(FACTS[family])
    params=list(params)
    if family=='excess':
        fact+=' AND "ReportDate"=%s';params.append(run.business_date)
    ctes=['B AS ('+fact+')']
    for alias,path in [('A','closing/consumer_context/NMSAllItems'),('C','closing/importer/SiteDescriptionTbl'),
                       ('E','closing/dbm/SKULocStandardAttributes')]:
        if alias=='E' and family=='fulfillment':continue
        query,values=read_binding.image_query(path);ctes.append(alias+' AS ('+query+')');params.extend(values)
    join='JOIN' if family=='excess' else 'LEFT JOIN'
    joins=' FROM B '+join+' A ON '+equal('B."SKUCode"','A."SKUCode"')+' AND '+equal('B."WhCode"','A."WhCode"')
    joins+=' '+join+' C ON '+equal('A."ParentWhCode"','C."WHCode"')
    fields=[('fact_ordinal','B.ordinal'),('nms_ordinal','A.vf_ordinal'),('parent_description_ordinal','C.vf_ordinal'),
            ('sku_key',key('A."SKUCode"')),('location_key',key('A."WhCode"')),
            ('parent_description','C."WHDescription"')]
    if family=='excess':
        joins+=' JOIN E ON '+equal('B."SKUCode"','E."SKUCode"')+' AND '+equal('B."WhCode"','E."WhCode"')
        fields.append(('standard_ordinal','E.vf_ordinal'))
    return 'WITH '+','.join(ctes)+' SELECT '+','.join(value+' AS '+quote(name) for name,value in fields)+joins,params

def chart_ingredients(run, family, direction, read_binding):
    if family not in FAMILIES or direction not in ('sku','location'):
        raise ValueError('Unknown Planning chart grain')
    location = direction == 'location'
    code = 'WhCode' if location else 'SKUCode'
    dim_code = 'WHCode' if location else 'SKUCode'
    description = 'WHDescription' if location else 'SKUDescription'
    band = {'excess':None,'fulfillment_summary':'Coverage','fulfillment_detail':'OrderStatus'}[family]
    fact,params=read_binding.fact_query(FACTS[family])
    params=list(params)
    if family=='excess':
        fact+=' AND "ReportDate"=%s';params.append(run.business_date)
    desc, values = read_binding.image_query('closing/importer/' + ('SiteDescriptionTbl' if location else 'SKUDescriptionTbl'))
    params.extend(values)
    attr, values = read_binding.image_query('closing/importer/' + ('LocationAttributeData' if location else 'SkuAttributeData'))
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
