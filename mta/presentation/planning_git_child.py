"""Corrected child GIT consumer, independent of frozen producer recipes.

The location SQL below retains the previously qualified reader verbatim except
its obsolete positive-child refusal; the real transporter sibling is assembled
by this module. Parent/count/chart owners and persisted business facts stay put.
"""
from types import SimpleNamespace
import json
from mta.presentation.native_mode import removed_mode
from django.db import connection, DatabaseError
from mta.presentation.planning_git import admitted_git
from mta.presentation.planning_grid_sql import GridFilters
from mta.presentation.planning_sources import admitted_sources
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.context import scope,PublicationUnavailable
from mta.presentation.selective import image_query,image_rows
from mta.presentation.rrr_sql import equal, key
from mta.runtime.models import PlanningGitMasterRow
from mta.runtime.relational_state import quote


from mta.presentation.planning_git_sql import location_transit, combined_grid
from mta.runtime.relational_state import CATALOG
from mta.presentation.permissions import PermissionCodes, _sql_equal
from mta.presentation.context import permission_catalogue
from mta.presentation.excess_read import pagination

def location_grid(run,payload,*,count=False,overview=False,resolved_scope=None,read_binding=None):
    from mta.presentation.git_read import validate_filters,NORMAL_COLUMNS
    from mta.presentation.excess_read import pagination
    kind=str(payload.get('type','')).lower()
    if kind not in ('parent','child'):raise PublicationUnavailable('selected_git_type_not_supported')
    paging=pagination(payload)
    occurrence,params=(admitted_git(run) if read_binding is None else
        admitted_git(run,read_binding=read_binding))['row'];params=list(params)
    master,values=(admitted_sources(run) if read_binding is None else
        admitted_sources(run,read_binding=read_binding.prepared))['git_master']
    from mta.presentation.daily_preparation import production_branch
    daily=production_branch(run) if read_binding is None else True
    if read_binding is not None:
        transit=read_binding.prepared.transit.rows('InTransitData')
    elif daily:
        from mta.presentation.daily_transit import PATH as TRANSIT_PATH
        transit=image_rows(run,TRANSIT_PATH)
        from mta.presentation.logistics_live import serving_transit_rows
        transit=serving_transit_rows(run,transit)
    else:
        transit=removed_mode('historical_fixture')['InTransitData']
        if transit:raise PublicationUnavailable('planning_transporter_nonempty_source_not_prepared')
    if read_binding is None:
        importer,manifest=_projected_attributes(run) if resolved_scope is None else resolved_scope[:2]
    else:
        importer,manifest=read_binding.attributes(),None
        resolved_scope=None
    if manifest:raise PublicationUnavailable('planning_git_native_hierarchy_required')
    validate_filters(payload,SimpleNamespace(attributes=importer),child_count=count and kind=='child')
    filters=GridFilters(payload,'git',PlanningGitMasterRow)
    where=filters.compile()
    if overview:
        if not count:raise ValueError('Overview requires GIT count')
        where+=' AND H.grid_eligible'
    products,locations=scope(payload,attributes=importer) if resolved_scope is None else resolved_scope[2:]
    config=[dict(header=h,colCode=c,colPosition=p) for h,c,p in NORMAL_COLUMNS]
    if not products or not locations:
        return [dict(locationwise=0,**({'transporterwise':0} if kind=='child' else {}))] if count else combined_grid(kind,[],config)
    ctes=['H AS ('+occurrence+')','A AS ('+master+')'];params.extend(values)
    ageing=None
    if daily and not count:
        from mta.presentation.daily_transit import PATH as TRANSIT_PATH
        query,values=image_query(run,TRANSIT_PATH) if read_binding is None else read_binding.image_query(TRANSIT_PATH)
        ctes.append('T AS ('+query+')');params.extend(values)
        ageing=('(SELECT max(t."Ageing"-t."SLT") FROM T t WHERE '+
                equal('t."SKUCode"','A."SKUCode"')+' AND '+equal('t."WhCode"','A."WhCode"')+')')
    for alias,codes in (('P',products),('L',locations)):
        members=sorted(codes)
        ctes.append(alias+'(code,weight) AS (VALUES '+','.join(['(%s::text,%s::bigint)']*len(members))+')')
        params.extend(v for code in members for v in (code,codes.multiplicities[code]))
    owners=set(filters.owners)
    if not count:owners.add('C')
    joins=(' FROM H JOIN A ON A.rationed_ordinal=H.rationed_ordinal AND A.standard_ordinal=H.standard_ordinal '
           'JOIN P ON A."SKUCode"=P.code JOIN L ON A.'+quote('WhCode' if kind=='parent' else 'ParentWhCode')+'=L.code')
    for alias,table,ordinal in [('B','SkuLocAttributeData','pair_ordinal'),('C','SkuAttributeData','sku_ordinal'),('D','LocationAttributeData','location_ordinal')]:
        if alias not in owners and not(alias=='D' and filters.children):continue
        path='closing/importer/'+table
        query,values=image_query(run,path) if read_binding is None else read_binding.image_query(path)
        ctes.append(alias+' AS NOT MATERIALIZED ('+query+')');params.extend(values)
        if alias in owners:joins+=' LEFT JOIN '+alias+' ON '+alias+'.vf_ordinal=H.'+ordinal
    if filters.children:
        joins+=' JOIN D parent ON '+equal('A."ParentWhCode"','parent."WHCode"')+' AND ('+' OR '.join(equal('parent."LocationType"','%s') for _ in filters.children)+')'
        params.extend(filters.children)
    params.extend(filters.params)
    if count:
        with connection.cursor() as c:
            c.execute('WITH '+','.join(ctes)+' SELECT COALESCE(sum(P.weight*L.weight),0)'+joins+' WHERE '+where,params)
            total=int(c.fetchone()[0])
        transporter_total=0
        if daily and transit and kind=='child':
            from mta.presentation.daily_git_count import count as transporter_count
            transporter_total=transporter_count(run,payload,products,locations) if read_binding is None else \
                transporter_count(run,payload,products,locations,read_binding=read_binding.prepared)
        return [dict(locationwise=total,**({'transporterwise':transporter_total} if kind=='child' else {}))]
    aliases=dict(st='Status',sc='SKUCode',wc='WhCode',t='Tags',pwc='ParentWhCode',n='Norm',vn='VirtualNorm',stk='Stock',g='Git',pip='PhysicalInventoryPen',pic='PhysicalInventoryColor',plp='PipelineInventoryPen',plc='PipelineInventoryColor',rq='Req',pr='Price')
    columns={alias:'A.'+quote(field) for alias,field in aliases.items()}
    columns.update(skd='H.sku_description',wcd='H.location_description',prn='H.parent_description',
                   eoc='C."ElephantOrderCapping"',v='C."Volume"',wt='C."Weight"')
    if ageing is not None:columns['AgeingOrder']=ageing
    columns.update({p+str(i):'H.'+p+str(i) for p in ('sl','ll') for i in range(1,6)})
    order=(ageing+' DESC NULLS LAST,' if ageing is not None else '')+'trunc(A."PhysicalInventoryPen")::integer DESC NULLS LAST,H.ordinal,copies.n'
    ctes.append('selected AS (SELECT row_number() OVER (ORDER BY '+order+') AS rn,'
                +','.join(value+' AS '+quote(alias) for alias,value in columns.items())+joins+
                ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) copies(n) WHERE H.grid_eligible AND '+where+')')
    sql='WITH '+','.join(ctes)+' SELECT * FROM selected'
    if paging is not None:
        sql+=' WHERE rn BETWEEN %s AND %s';params.extend(((paging[0]-1)*paging[1]+1,paging[0]*paging[1]))
    sql+=' ORDER BY rn'
    with connection.cursor() as c:
        c.execute(sql,params);names=[d[0] for d in c.description]
        rows=[dict(zip(names,row)) for row in c.fetchall()]
    from decimal import Decimal
    nested=location_transit(transit) if daily else {}
    if daily:
        from mta.presentation.rrr import sql_key
    for row in rows:
        for field,value in row.items():
            if isinstance(value,Decimal):row[field]=float(value)
        value=nested.get(sql_key(row.get('sc'),row.get('wc'))) if daily else None
        if daily and row.get('AgeingOrder') != (value['AgeingOrder'] if value else None):
            raise ValueError('Prepared GIT AgeingOrder differs from typed transit source')
        row.update(AgeingOrder=value['AgeingOrder'] if value else None,
                   transit=[dict(item) for item in value['transit']] if value else [])
    return combined_grid(kind,rows,config)


def direct_permissions(payload, attributes):
    """Child DATA's supplied-ID joins; caller has admitted the scope IDs.

    Unlike the count/location reader, this SQL does not expand a root ID into
    descendant permission IDs. Preserve raw code occurrences and NULL denial.
    """
    catalogue = permission_catalogue()
    result = []
    for key, kind, table, code, prefix in (
        ('product_permissions', 'products', 'SkuAttributeData', 'SKUCode', 'SL'),
        ('location_permissions', 'locations', 'LocationAttributeData', 'WHCode', 'LL')):
        selected = {int(value) for value in payload.get(key, [])}
        records = [record for record in catalogue[kind]['records'] if record['id'] in selected]
        counts = {}
        for row in attributes[table]:
            for record in records:
                if all(_sql_equal(row[prefix + str(i)], record['level_' + str(i)]) for i in (1, 2, 3)):
                    counts[row[code]] = counts.get(row[code], 0) + 1
        result.append(PermissionCodes(counts))
    return tuple(result)


class TransporterFilters(GridFilters):
    """Resolve Commons predicates at the child DATA query's actual owners."""
    def __init__(self, payload):
        super().__init__(payload, 'git', None)
        self.numeric_spellings = {}
        for item in self.items('availabilityFilter'):
            spelling = item['attributeName']
            if spelling.lower() in ('norm', 'stock', 'git', 'virtualnorm'):
                self.numeric_spellings.setdefault(spelling.lower(), []).append(spelling)

    def compare(self, owner, field, operator, wanted):
        if owner == 'A' and field in self.numeric_spellings:
            spelling = self.numeric_spellings[field].pop(0)
            # Commons emits caller spelling unchanged; the child's exact-case
            # replacements alone redirect Git/Stock/ Norm onto missing a fields.
            if field == 'norm':
                raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:child data missing or ambiguous Norm')
            if spelling not in ('Git', 'Stock'):
                owner = 'V'
        return super().compare(owner, field, operator, wanted)

    def column(self, owner, name):
        lower = name.lower()
        if owner == 'B' or (owner == 'C' and lower not in ('sl1', 'sl2', 'sl3', 'sl4', 'sl5')):
            raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:child data missing outer attribute alias')
        if owner == 'D' and lower in ('locationtype', 'll1', 'll2', 'll3', 'll4', 'll5'):
            raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:child data ambiguous location hierarchy')
        table, alias = {
            'A': ('BPR/GoodsInTransitTransporterMaster', 'a'),
            'C': ('Importer/NMSAllItems', 'nms'),
            'D': ('Importer/LocationAttributeData', 'la'),
            'V': ('BPR/vf_RationedReqReport', 'vf'),
        }[owner]
        if owner == 'A' and lower == 'tags':
            table, alias = 'Importer/SKULocStandardAttributes', 'slsa'
        if owner == 'A' and lower == 'virtualnorm':
            table, alias = 'BPR/vf_RationedReqReport', 'vf'
        fields = {field.lower(): (field, kind) for field, kind in CATALOG['tables'][table]}
        if lower not in fields:
            raise PublicationUnavailable('LEG-GIT-FILTER-INVALID-SQL:child data missing column ' + name)
        field, kind = fields[lower]
        return alias + '.' + quote(field), kind


GROUP_FIELDS = ('TransporterCode', 'OrderNo', 'ParentWhCode', 'WhCode')


def transporter_query(run, payload, products, locations, *, read_binding=None):
    from mta.presentation.daily_git_preparation import sources, NMS_PATH, TRANSPORTER_PATH
    filters = TransporterFilters(payload)
    where = filters.compile()
    options = {} if read_binding is None else dict(read_binding=read_binding.prepared)
    relations, _bindings, _config = sources(run, chart=False, **options)
    paths = dict(a=TRANSPORTER_PATH, nms=NMS_PATH,
        slsa='closing/dbm/SKULocStandardAttributes', vf='reports/bpr/vf_RationedReqReport',
        d='closing/importer/SiteDescriptionTbl', la='closing/importer/LocationAttributeData',
        sd='closing/importer/SKUDescriptionTbl', sa='closing/importer/SkuAttributeData',
        sla='closing/importer/SkuLocAttributeData')
    ctes, params = [], []
    for alias, path in paths.items():
        sql, values = relations[path] if path in relations else (
            image_query(run, path) if read_binding is None else read_binding.prepared.image_query(path))
        ctes.append(alias + ' AS (' + sql + ')')
        params.extend(values)
    for alias, codes in (('P', products), ('L', locations)):
        members = sorted(codes)
        sql = ('VALUES ' + ','.join('(%s::text,%s::bigint)' for _ in members) if members else
               'SELECT NULL::text,0::bigint WHERE FALSE')
        ctes.append(alias + '(code,weight) AS (' + sql + ')')
        params.extend(value for code in members for value in (code, codes.multiplicities[code]))
    joins = (' FROM a JOIN slsa ON ' + equal('a."SKUCode"', 'slsa."SKUCode"') +
        ' AND ' + equal('a."WhCode"', 'slsa."WhCode"') +
        ' JOIN vf ON ' + equal('a."SKUCode"', 'vf."SKUCode"') + ' AND ' + equal('a."WhCode"', 'vf."WhCode"') +
        ' JOIN d wd ON ' + equal('a."WhCode"', 'wd."WHCode"') +
        ' JOIN d pd ON ' + equal('a."WhCode"', 'pd."WHCode"') +
        ' JOIN la ON ' + equal('a."WhCode"', 'la."WHCode"') +
        ' JOIN nms ON ' + equal('a."SKUCode"', 'nms."SKUCode"') + ' AND ' + equal('a."WhCode"', 'nms."WhCode"') +
        ' JOIN P ON ' + equal('a."SKUCode"', 'P.code') +
        ' JOIN L ON ' + equal('a."ParentWhCode"', 'L.code') +
        ' CROSS JOIN LATERAL generate_series(1,P.weight*L.weight) permission_copy(n)')
    if filters.children:
        joins += (' JOIN la parent ON ' + equal('a."ParentWhCode"', 'parent."WHCode"') + ' AND (' +
                  ' OR '.join(equal('parent."LocationType"', '%s') for _ in filters.children) + ')')
        params.extend(filters.children)
    params.extend(filters.params)
    aggregates = dict(st='max(a."Status")', phy='max(a."PhysicalInventoryPen")',
        tn='max(a."TransporterName")', tc='max(a."TransporterCode")',
        fc='max(pd."WHDescription")', wc='max(wd."WHDescription")',
        tq='sum(a."InTransitQty")::integer', trc='max(a."TransporterContact")',
        cd='max(a."CreationDate")', slt='max(a."SLT")', ag='max(a."Ageing")',
        eta='max(a."ETA")', cl='max(a."CurrentLocation")', re='max(a."Remark")')
    aggregates['on'] = 'max(a."OrderNo")'
    aggregates['_parent'] = 'max(a."ParentWhCode")'
    aggregates['_wh'] = 'max(a."WhCode")'
    # Native CI grouping cannot define which raw spelling is returned when its
    # key spellings differ. Do not invent a case/padding representative.
    aggregates['_ambiguous_key'] = '(' + ' OR '.join(
        'count(DISTINCT a.' + quote(name) + ')>1' for name in GROUP_FIELDS) + ')'
    ctes.append('grouped AS (SELECT ' + ','.join(value + ' AS ' + quote(name) for name, value in aggregates.items()) +
        joins + ' WHERE ' + key('a."PhysicalInventoryColor"') + " IN ('black','red') AND (" + where +
        ') GROUP BY ' + ','.join(key('a.' + quote(name)) for name in GROUP_FIELDS) + ')')
    ctes.append('numbered AS (SELECT row_number() OVER (ORDER BY trunc((ag-slt)::numeric)::integer '
        'DESC NULLS LAST,trunc(phy)::integer DESC NULLS LAST)::integer AS rn,* FROM grouped)')
    paging = pagination(payload)
    page = ''
    if paging is not None:
        page = ' WHERE rn BETWEEN %s AND %s'
        params += [(paging[0]-1)*paging[1]+1, paging[0]*paging[1]]
    ctes.append('selected AS (SELECT * FROM numbered' + page + ')')
    nested = [('SKUCode','ta."SKUCode"'), ('InTransitQty','ta."InTransitQty"'),
        ('PhysicalInventoryColor','ta."PhysicalInventoryColor"'),
        ('PipelineInventoryColor','ta."PipelineInventoryColor"'), ('pr','ta."Price"'),
        ('Business','c."SL1"'), ('Category','c."SL2"'), ('wt','own_nms."Weight"'),
        ('v','own_nms."Volume"'), ('eoc','own_nms."ElephantOrderCapping"'),
        ('Price','ta."Price"'), ('SL1','c."SL1"'), ('SL2','c."SL2"')]
    nested_sql = ('SELECT ' + ','.join(expression + ' AS ' + quote(name) for name, expression in nested) +
        ' FROM a ta JOIN sd b ON ' + equal('ta."SKUCode"','b."SKUCode"') +
        ' JOIN sa c ON ' + equal('ta."SKUCode"','c."SKUCode"') +
        ' LEFT JOIN sla own_pair ON ' + equal('ta."SKUCode"','own_pair."SKUCode"') +
        ' AND ' + equal('ta."WhCode"','own_pair."LocCode"') +
        ' JOIN nms own_nms ON ' + equal('ta."SKUCode"','own_nms."SKUCode"') +
        ' AND ' + equal('ta."WhCode"','own_nms."WhCode"') +
        ' WHERE ' + ' AND '.join(equal('ta.' + quote(field), 'g.' + quote(alias))
            for field, alias in zip(GROUP_FIELDS, ('tc','on','_parent','_wh'))))
    return ('WITH ' + ','.join(ctes) + ' SELECT g.*,COALESCE((SELECT jsonb_agg(to_jsonb(detail)) FROM (' +
            nested_sql + ") detail),'[]'::jsonb) AS transit FROM selected g ORDER BY rn", params)


def transporter_grid(run, payload, products, locations, *, read_binding=None):
    from decimal import Decimal
    def wire(value):
        if isinstance(value, Decimal):
            return int(value) if value == value.to_integral_value() else float(value)
        if isinstance(value, list):
            return [wire(item) for item in value]
        if isinstance(value, dict):
            return {name: wire(item) for name, item in value.items()}
        return value
    sql, params = transporter_query(run, payload, products, locations, read_binding=read_binding)
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        names = [column[0] for column in cursor.description]
        rows = [dict(zip(names, row)) for row in cursor.fetchall()]
    for index, row in enumerate(rows):
        if row.pop('_ambiguous_key'):
            raise PublicationUnavailable('GIT_child_group_key_spelling_ambiguous')
        row.pop('_parent'); row.pop('_wh')
        # Django's raw PostgreSQL cursor returns JSONB as text; a configured
        # standalone psycopg cursor may already return the decoded structure.
        if isinstance(row['transit'], str):
            row['transit'] = json.loads(row['transit'], parse_float=Decimal)
        rows[index] = wire(row)
    return rows


def grid(run, payload, *, count=False, read_binding=None):
    if count or str(payload.get('type','')).lower() != 'child':
        from mta.presentation.planning_git_sql import grid as original_grid
        return original_grid(run, payload, count=count, read_binding=read_binding)
    try:
        location = location_grid(run, payload, read_binding=read_binding)['locationWise']
        attributes, manifest = (_projected_attributes(run) if read_binding is None else (read_binding.attributes(), None))
        if manifest:
            raise PublicationUnavailable('planning_git_native_hierarchy_required')
        # The location owner already validated the IDs against this same catalogue.
        products, locations = direct_permissions(payload, attributes)
        rows = transporter_grid(run, payload, products, locations, read_binding=read_binding)
        from mta.presentation.legacy_ui import UI_CONFIGS
        return dict(locationWise=location, transporterWise=dict(data=rows, uiConfig=UI_CONFIGS['GIT_To_Child_TW']))
    except PublicationUnavailable:
        raise
    except (DatabaseError, ValueError, KeyError, TypeError) as error:
        raise PublicationUnavailable('GIT_corrected_child_query_unavailable') from error

