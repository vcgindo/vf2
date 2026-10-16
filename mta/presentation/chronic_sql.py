"""Bounded Chronic reads over the retained typed sources, with live access scope.

The grid's NMS LEFT join and charts' description INNER joins are deliberately
separate. Raw source equality includes Python's None equality; filter and parent
comparisons retain their existing SQL-profile normalization.
"""
from django.db import connection, transaction

from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.insight_filters import InsightPredicate, unavailable
from mta.presentation.rrr_sql import Filters, equal
from mta.presentation.selective import image_metadata, image_query, image_rows
from mta.runtime.relational_state import quote, wire_value


def native_equal(left, right):
    # Hash-joinable NULL equality without conflating NULL and the empty string.
    return ('((' + left + ' IS NULL)=(' + right + ' IS NULL) AND COALESCE(' +
            left + ",'')=COALESCE(" + right + ",''))")


def native_fixture(run):
    """An approved hierarchy opt-in keeps its existing projected reader."""
    from mta.presentation import hierarchy
    try:
        return hierarchy.selected_manifest(run) is None
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc


def read_chronic(run, payload, kind):
    from mta.presentation.daily_preparation import production_branch
    if (run.kind != 'LEGACY_UI_FIXTURE' and not production_branch(run)) or kind not in (
            'chronic-grid', 'chronic-loc', 'chronic-sku'):
        raise ValueError('admitted_chronic_kind_required')
    if not native_fixture(run):
        raise PublicationUnavailable('chronic_SQL_hierarchy_supplement_not_bound')
    attrs = {name: image_rows(run, 'closing/btr/' + name)
             for name in ('SkuAttributeData','LocationAttributeData')}
    predicate = InsightPredicate(payload, attrs['LocationAttributeData'], kind=kind)
    products, locations = scope(payload, attributes=attrs)
    if production_branch(run):
        fact_path = 'closing/btr/ChronicUnavalabilityData'
        fact = image_metadata(run, fact_path)
        if fact['count'] == 0:
            # Empty native images have no observed wire fields. Validate the
            # retained empty population after validating the canonical filter.
            image_rows(run, fact_path, metadata=fact)
            return []
    ctes, params, wires = [], [], {}
    paths = {'_a':'closing/btr/ChronicUnavalabilityData',
             '_sku':'closing/btr/SkuAttributeData',
             '_location':'closing/btr/LocationAttributeData',
             '_pair':'closing/btr/SkuLocAttributeData',
             '_description':('closing/consumer_context/NMSAllItems' if kind=='chronic-grid' else
                             'closing/btr/SiteDescriptionTbl' if kind=='chronic-loc' else
                             'closing/btr/SKUDescriptionTbl')}
    for alias,path in paths.items():
        item=image_metadata(run,path); query,values=image_query(run,path)
        ctes.append(alias+' AS NOT MATERIALIZED ('+query+')'); params.extend(values)
        wires[alias]={name:wire for name,_,wire in item['fields']}
    def col(alias,field):
        expr=alias+'.'+quote(field)
        return expr+'::text' if wires[alias][field]=='str' else expr
    class Compiler(Filters):
        def column(self,alias,field):
            wire=wires[alias][field]
            return col(alias,field), 'text' if wire=='str' else wire
    compiler=Compiler({})
    def term(node):
        if node[0]=='or':return '('+' OR '.join(term(n) for n in node[1])+')'
        if node[0]=='in':
            expr,_=compiler.column(*node[1]);compiler.params.extend(node[2])
            return '('+' OR '.join(equal(expr,'%s') for _ in node[2])+')'
        return compiler.compare(*node[1],node[2],node[3])
    try:where=' AND '.join(term(n) for n in predicate.sql_terms) or 'TRUE'
    except PublicationUnavailable as exc:unavailable(str(exc).partition(':')[2])
    if not products or not locations:return []
    for alias,codes in (('P',products),('L',locations)):
        ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(codes))+')')
        params.extend(v for code in sorted(codes,key=lambda v:(v is not None,str(v)))
                      for v in (code,codes.multiplicities[code]))
    a_sku='_a."SKUCode"';a_loc='_a."WhCode"'
    grid=kind=='chronic-grid';loc=kind=='chronic-loc'
    join_type=' LEFT JOIN ' if grid else ' JOIN '
    joins=' FROM _a'
    for alias,pairs,jtype in (
        ('_sku',[(a_sku,'"SKUCode"')],join_type),
        ('_location',[(a_loc,'"WHCode"')],join_type),
        ('_pair',[(a_sku,'"SKUCode"'),(a_loc,'"LocCode"')],' LEFT JOIN '),
        ('_description',([(a_sku,'"SKUCode"'),(a_loc,'"WhCode"')] if grid else
                         [(a_loc,'"WHCode"')] if loc else [(a_sku,'"SKUCode"')]),join_type)):
        joins+=jtype+alias+' ON '+' AND '.join(native_equal(left,alias+'.'+right) for left,right in pairs)
    joins+=' JOIN P ON '+native_equal(a_sku,'P.code')+' JOIN L ON '+native_equal(a_loc,'L.code')
    if predicate.children:
        joins+=' JOIN _location parent ON '+equal('_a."ParentWhCode"','parent."WHCode"')
        joins+=' AND ('+' OR '.join(equal('parent."LocationType"','%s') for _ in predicate.children)+')'
        params.extend(predicate.children)
    params.extend(compiler.params)
    weight='P.weight*L.weight'
    outputs=[]
    def output(name,expr,wire=None):outputs.append((name,expr,wire))
    ordinal=lambda alias:'COALESCE('+alias+'.vf_ordinal,-1)'
    if grid:
        fields=[('skucode','_a','SKUCode'),('skudesc','_description','SKUDescription'),
                ('location','_a','WhCode'),('parentloc','_a','ParentWhCode'),
                ('RLT','_a','RLT'),('BlackRedAgeing','_a','BRAge'),
                ('PhysicalInventoryPen','_a','PhysicalInventoryPen'),('Techcolor','_a','PhysicalInventoryColor'),
                ('PipelineInventoryPen','_a','PipelineInventoryPen'),('ecocolor','_a','PipelineInventoryColor'),
                ('RationedStockatparent','_a','RationedQty')]
        for name,alias,field in fields:output(name,col(alias,field),wires[alias][field])
        # The wire contains repeated identical rows for access-join weights.
        # Expand only those final projected rows, avoiding generate_series' fixed
        # 1000-row estimate multiplying the sort into a spurious multi-million bag.
        output('_copies',weight,'int')
        tail=' WHERE '+where+' ORDER BY '+','.join(ordinal(a) for a in
              ('_a','_description','_location','_sku','_pair'))
    else:
        key=a_loc if loc else a_sku
        output('whcode' if loc else 'sku',key,'str')
        def maximum(alias,field):
            expr=col(alias,field); wire=wires[alias][field]
            return ('bool_or('+expr+')' if wire=='bool' else
                    'max('+expr+(' COLLATE "C"' if wire=='str' else '')+')')
        desc='WHDescription' if loc else 'SKUDescription'
        output('location' if loc else 'SKUDescription',maximum('_description',desc),wires['_description'][desc])
        for name,color in (('redCount','Red'),('blackCount','Black')):
            output(name,'COALESCE(sum('+weight+') FILTER (WHERE _a."PhysicalInventoryColor"=\''+color+'\'),0)','int')
        aliases=({'LogisticsLocation':'LogisticsLocation',**{f'LL{i}':f'LL{i}' for i in range(1,6)}} if loc else
                 {'elephantOrderCapping':'ElephantOrderCapping','weight':'Weight','volume':'Volume',
                  **{f'SL{i}':f'SL{i}' for i in range(1,6)}})
        aliases.update({('c1' if i==1 else f'C{i}'):f'c{i}' for i in range(1,16)})
        owner='_location' if loc else '_sku'
        for name,field in aliases.items():output(name,maximum(owner,field),wires[owner][field])
        output('countSku' if loc else 'countloc','sum('+weight+')','int')
        first='||'.join('lpad('+ordinal(a)+'::text,20,\'0\')' for a in
                        ('_a','_sku','_location','_pair','_description'))
        tail=' WHERE '+where+' AND _a."BRAge">_a."RLT" GROUP BY '+key
        tail+=' ORDER BY sum('+weight+') DESC,min('+first+') COLLATE "C"'
    sql='WITH '+','.join(ctes)+' SELECT '+','.join(expr+' AS '+quote(name) for name,expr,_ in outputs)+joins+tail
    with transaction.atomic(),connection.cursor() as cur:
        cur.execute("SELECT current_setting('jit'),current_setting('enable_mergejoin')")
        previous_jit,previous_merge=cur.fetchone()
        cur.execute('SET LOCAL jit=off')
        # The qualified grid plan sorted both complete 97k occurrence bags to
        # serve 3,340 rows and spilled them. Hash joins retain the same raw keys
        # and duplicates; ordering is applied explicitly only to the result.
        if grid:cur.execute('SET LOCAL enable_mergejoin=off')
        cur.execute(sql,params)
        rows=cur.fetchall()
        cur.execute("SELECT set_config('jit',%s,true),set_config('enable_mergejoin',%s,true)",
                    [previous_jit,previous_merge])
    result=[]
    for row in rows:
        item={name:wire_value(value,wire) for (name,_,wire),value in zip(outputs,row) if value is not None}
        if grid:
            for field in ('PhysicalInventoryPen','PipelineInventoryPen'):
                if field in item:item[field]=float(item[field])
        copies=item.pop('_copies',1)
        result.extend(dict(item) for _ in range(copies))
    return result
