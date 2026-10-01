"""Selected deployed RRR joins over existing typed operational rows.

No engine invocation, full production reconstruction, fixture or output cache.
The retained Python selector remains the independent affected regression target.
SQL predicates/count/order/page run in PostgreSQL; serialization stays unchanged.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import re

from django.db import connection

from mta.presentation.context import permission_catalogue, scope, PublicationUnavailable
from mta.presentation import hierarchy
from mta.presentation.pick_storage import read_pick_bands
from mta.presentation.rrr import DIRECT_FIELDS, ALIASES, NULL_DASH
from mta.presentation.rrr_filters import OPERATORS, rrr_predicate, unavailable
from mta.presentation.selective import image_query, image_rows
from mta.runtime.models import PickProjection
from mta.runtime.relational_state import CATALOG, quote


def key(column):
    return "lower(rtrim(" + column + "::text,' '))"


def equal(left, right):
    return key(left) + '=' + key(right)


def like_pattern(pattern):
    # SQL LIKE %, _, bracket classes; same selected subset as sql_like.
    parts, i = [], 0
    while i < len(pattern):
        char = pattern[i]
        if char == '%': parts.append('.*')
        elif char == '_': parts.append('.')
        elif char == '[':
            end = pattern.find(']', i + 2 if pattern[i+1:i+2] == ']' else i + 1)
            if end == -1: parts.append(r'\[')
            else:
                content = pattern[i+1:end]
                negate = '^' if content.startswith('^') else ''
                content = content[1:] if negate else content
                parts.append('[' + negate + content.replace('\\', r'\\') + ']')
                i = end
        else: parts.append(re.escape(char))
        i += 1
    return '^' + ''.join(parts) + '$'


class Filters:
    def __init__(self, payload):
        self.groups = payload.get('filters') or {}
        self.params, self.where, self.children = [], [], []

    def items(self, group):
        return [i for i in (self.groups.get(group) or {}).get('filters', [])
                if i.get('attributeName') != '']

    def column(self, owner, name):
        table = {'A':'BPR/vf_RationedReqReport', 'B':'Importer/SkuLocAttributeData',
                 'C':'Importer/SkuAttributeData', 'D':'Importer/LocationAttributeData'}[owner]
        fields = {n.casefold():(n,t) for n,t in CATALOG['tables'][table]}
        if name.casefold() not in fields: unavailable('missing column ' + name)
        actual, kind = fields[name.casefold()]
        return owner + '.' + quote(actual), kind

    def compare(self, owner, field, operator, wanted):
        column, kind = self.column(owner, field)
        numeric = kind in ('int','bigint','decimal','numeric','float','real')
        if operator not in OPERATORS: unavailable('unknown deployed operator')
        if operator in ('hasvalue','hasnovalue'):
            empty = '(' + column + " IS NULL OR " + column + ('=0)' if numeric else "::text ~ '^ *$')")
            return 'NOT ' + empty if operator == 'hasvalue' else empty
        if operator in ('contains','doesnotcontain','startswith','doesnotstartwith','endswith','doesnotendwith'):
            pattern = (wanted+'%' if operator.endswith('startwith') or operator=='startswith' else
                       '%'+wanted if operator.endswith('endwith') or operator=='endswith' else '%'+wanted+'%')
            self.params.append(like_pattern(pattern))
            match = '(' + column + '::text ~* %s)'
            return '(' + column + ' IS NULL OR NOT ' + match + ')' if operator.startswith('doesnot') else match
        operation = {'equalto':'=', 'notequalto':'<>', 'greaterthan':'>',
            'greaterthanequalto':'>=', 'smallerthan':'<', 'smallerthanequalto':'<='}[operator]
        if numeric or operation not in ('=','<>'):
            try:
                value = Decimal(wanted)
                if not value.is_finite(): raise InvalidOperation
                if kind in ('int','bigint') and operation in ('=','<>') and value != value.to_integral_value():
                    raise InvalidOperation
            except (InvalidOperation, ValueError): unavailable('canonical numeric conversion')
            self.params.append(value)
            expression = column + '::numeric' + operation + '%s'
        else:
            self.params.append(wanted)
            expression = key(column) + operation + key('%s')
        return '(' + column + ' IS NULL OR ' + expression + ')' if operation=='<>' else expression

    def in_list(self, owner, field, values):
        if not values: return
        column, _ = self.column(owner, field)
        self.params.extend(values)
        self.where.append('(' + ' OR '.join(equal(column, '%s') for _ in values) + ')')

    def grouped(self, items, mapper):
        groups = defaultdict(list)
        for item in items: groups[item['attributeName']].append(item)
        for attribute, items in groups.items():
            owner, field = mapper(attribute)
            self.where.append('(' + ' OR '.join(self.compare(owner,field,i.get('operator'),i['value'])
                                               for i in items) + ')')

    def compile(self):
        supply = defaultdict(list)
        for i in self.items('supplyChainFilter'): supply[i['attributeName'].lower()].append(i['value'])
        for name, owner, field in (('forlocation','D','LocationType'),
                ('forlocationlocationcode','A','WhCode'),('forchildrenlocationcode','A','ParentWhCode')):
            self.in_list(owner,field,supply[name])
        self.children = supply['forchildren']
        for group, special, code in (('productFilter','sku','SKUCode'),('locationFilter','location','WhCode')):
            items = self.items(group)
            self.in_list('A',code,[i['value'] for i in items if i['attributeName'].lower()==special])
            self.grouped([i for i in items if i['attributeName'].lower()!=special],
                lambda name,group=group: ('C',name.replace('p','sl')) if group=='productFilter' else ('D','l'+name))
        for i in self.items('availabilityFilter'):
            name = i['attributeName'].lower()
            if name in ('norm','stock','git','virtualnorm'):
                self.where.append(self.compare('A',name,i.get('operator'),i['value']))
        for name, field in (('pic','DispatchColor'),('ohic','PhysicalInventoryColor')):
            self.in_list('A',field,[i['value'] for i in self.items('availabilityFilter') if i['attributeName'].lower()==name])
        custom = [i for i in self.items('customAttributeFilter') if any(p in i['attributeName'].lower()
                    for p in ('skulocattr','skuattr','locattr'))]
        def custom_field(name):
            for prefix, owner in (('skulocattr','B'),('skuattr','C'),('locattr','D')):
                if prefix in name.lower(): return owner,name.lower().replace(prefix,'c')
        self.grouped(custom,custom_field)
        return ' AND '.join(self.where) or 'TRUE'


def read_rrr(run, payload, *, paging, count=False):
    importer = {name:image_rows(run,'closing/importer/'+name)
                for name in ('SkuAttributeData','LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        if manifest:
            importer = hierarchy.project_attributes(importer,permission_catalogue(),manifest)
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc
    # Preserve the accepted predicate's structural/legacy-invalid branch guards.
    rrr_predicate(payload,importer)
    products, locations = scope(payload,attributes=importer)
    try: bands = read_pick_bands(run)
    except PickProjection.DoesNotExist as exc:
        raise PublicationUnavailable('selected_run_pick_projection_not_published') from exc
    if not products or not locations or not bands: return 0 if count else []

    ctes, params = [], []
    def add(name, query, values, *, materialized=False):
        ctes.append(name + (' AS MATERIALIZED (' if materialized else ' AS (') + query + ')'); params.extend(values)
    for alias, path in (('R','reports/bpr/vf_RationedReqReport'),
            ('S','closing/dbm/SKULocStandardAttributes'),('B','closing/importer/SkuLocAttributeData')):
        query, values = image_query(run,path); add(alias,query,values)
    for alias, table, code, prefix in (('C','SkuAttributeData','SKUCode','SL'),('D','LocationAttributeData','WHCode','LL')):
        query, values = image_query(run,'closing/importer/'+table)
        if manifest:
            add(alias+'native',query,values)
            rows = importer[table]
            add(alias+'hierarchy','VALUES '+','.join(['(%s,%s,%s,%s)']*len(rows)),
                [v for ordinal,row in enumerate(rows) for v in (ordinal,*[row[prefix+str(i)] for i in (1,2,3)])])
            columns = [n for n,_ in CATALOG['tables']['Importer/'+table] if n not in [prefix+str(i) for i in (1,2,3)]]
            add(alias,'SELECT '+','.join('N.'+quote(n) for n in columns)+','+
                ','.join('H.column'+str(i+1)+' AS '+quote(prefix+str(i)) for i in (1,2,3))+
                ' FROM '+alias+'native N JOIN '+alias+'hierarchy H ON N.vf_ordinal=H.column1',[])
        else: add(alias,query,values)
    add('bands','VALUES '+','.join(['(%s,%s,%s,%s,%s,%s,%s,%s)']*len(bands)),
        [v for b in bands for v in (b['sku_code'],b['location_code'],b['parent_location_code'],
                                   *[int(b[k]) for k in ('to_black','to_red','to_yellow','to_green','to_blue')])])
    virtual = equal('K.column2','K.column3')
    copies = dict(ParentWhCode='WhCode',ParentWhName='WhName',ParentNorm='Norm',
        TechPenParent='TechPen',TechColorParent='TechColor',EcoPenParent='EcoPen',EcoColorParent='EcoColor',
        LeftoverParentStock='LeftoverStock',ParentPackSize='PackSize',AvgSiblingsNorm='AvgChildrenNorm',
        ParentStockPercentageForRationing='StockPercentageForRationing',ParentNormPercentReservation='NormPercentReservation')
    zero = set(('Req','AllocatedForVirtualNormReq','AllocatedForNormReq','AllocatedForSnPReq','RationedReq',
        'RationedCasePacks','LeftoverStock','SpikeOverdueAtParent','ResidualChildrenSnP','AvgChildrenNorm'))
    selections = []
    for name, kind in CATALOG['tables']['BPR/vf_RationedReqReport']:
        original = 'R.'+quote(name)
        if name in copies: expression='CASE WHEN '+virtual+' THEN R.'+quote(copies[name])+' ELSE '+original+' END'
        elif name in zero or name=='IsNormed':
            expression='CASE WHEN '+virtual+' THEN '+('FALSE' if name=='IsNormed' else '0')+' ELSE '+original+' END'
        elif name=='AllocatedForDirectOrders': expression='CASE WHEN '+virtual+' THEN '+original+' ELSE 0 END'
        else: expression=original
        selections.append(expression+' AS '+quote(name))
    for i,name in enumerate(('TOR_B','TOR_R','TOY','TOG','TOBlue'),4):
        selections.append('K.column'+str(i)+' AS '+quote(name))
    add('A','SELECT '+','.join(selections)+' FROM R JOIN bands K ON '+equal('R."SKUCode"','K.column1')+
        ' AND '+equal('R."WhCode"','K.column2'),[],materialized=True)
    for alias, codes in (('P',products),('L',locations)):
        # An actual permission bag, not an unbounded generate_series estimate.
        members = [code for code in sorted(codes) for _ in range(codes.multiplicities[code])]
        add(alias,'VALUES '+','.join(['(%s)']*len(members)),members)
    filters = Filters(payload); where = filters.compile()
    # Correlated bounded joins prevent PostgreSQL from expanding the complete
    # estate before selecting the small produced Pick bag. OFFSET 0 is only a
    # planner fence: it removes no occurrence and introduces no tie-break.
    joins = ' FROM A JOIN LATERAL (SELECT * FROM S WHERE '+equal('A."SKUCode"','S."SKUCode"')+' AND '+equal('A."WhCode"','S."WhCode"')+' OFFSET 0) S ON TRUE'
    joins += ' JOIN LATERAL (SELECT * FROM B WHERE '+equal('A."SKUCode"','B."SKUCode"')+' AND '+equal('A."WhCode"','B."LocCode"')+' OFFSET 0) B ON TRUE'
    joins += ' JOIN LATERAL (SELECT * FROM C WHERE '+equal('A."SKUCode"','C."SKUCode"')+' OFFSET 0) C ON TRUE'
    joins += ' JOIN LATERAL (SELECT * FROM D WHERE '+equal('A."WhCode"','D."WHCode"')+' OFFSET 0) D ON TRUE'
    joins += ' LEFT JOIN LATERAL (SELECT * FROM B WHERE '+equal('A."SKUCode"','B."SKUCode"')+' AND '+equal('A."WhCode"','B."LocCode"')+' OFFSET 0) sla ON TRUE'
    joins += ' JOIN P ON A."SKUCode"=P.column1 JOIN L ON A."WhCode"=L.column1'
    if filters.children:
        joins += (' JOIN D parent ON '+equal('A."ParentWhCode"','parent."WHCode"')+' AND ('+
            ' OR '.join(equal('parent."LocationType"','%s') for _ in filters.children)+')')
        params.extend(filters.children)
    params.extend(filters.params)
    columns = [(name,'A.'+quote(name)) for name in DIRECT_FIELDS]
    columns += [(name,'A.'+quote(source)) for name,source in ALIASES.items()]
    columns += [(prefix.lower()+str(i),owner+'.'+quote(prefix+str(i)))
                for owner,prefix in (('C','SL'),('D','LL')) for i in range(1,6)]
    columns += [(prefix+str(i),'COALESCE('+owner+'.'+quote('c'+str(i))+",'-')")
                for prefix,owner in (('SKULocAttr','B'),('SKUAttr','C'),('LocAttr','D')) for i in range(1,16)]
    select = 'count(*)' if count else ','.join(('COALESCE('+value+",'-')" if name in NULL_DASH else value)+' AS '+quote(name)
                                             for name,value in columns)
    query = 'WITH '+','.join(ctes)+' SELECT '+select+joins+' WHERE '+where
    if not count:
        query += ' ORDER BY A."DispatchColorSequence" NULLS FIRST, A."DispatchPen" DESC NULLS LAST,'+key('A."WhCode"')+','+key('A."SKUCode"')+' LIMIT %s OFFSET %s'
        params.extend((paging[1],(paging[0]-1)*paging[1]))
    with connection.cursor() as cursor:
        # Retain pick_rows' unique-position/parent guard. Repeated band rows are
        # valid; repeated produced ration positions must not silently multiply.
        source_query, source_params = image_query(run,'reports/bpr/vf_RationedReqReport')
        identities = sorted({(b['sku_code'],b['location_code'],b['parent_location_code']) for b in bands})
        cursor.execute('WITH positions AS ('+source_query+'), selected AS (VALUES '+
            ','.join(['(%s,%s,%s)']*len(identities))+') SELECT K.column1,K.column2 FROM selected K '+
            'LEFT JOIN positions R ON '+equal('R."SKUCode"','K.column1')+' AND '+equal('R."WhCode"','K.column2')+
            ' GROUP BY K.column1,K.column2,K.column3 HAVING count(R.vf_ordinal)<>1 OR '+
            '(NOT '+equal('K.column2','K.column3')+' AND bool_and('+equal('R."ParentWhCode"','K.column3')+') IS DISTINCT FROM TRUE)',
            source_params+[v for row in identities for v in row])
        if cursor.fetchone(): raise ValueError('Pick band requires its unique produced rationed-report position/parent')
        cursor.execute(query,params)
        if count: return cursor.fetchone()[0]
        rows = [dict(zip((c[0] for c in cursor.description),row)) for row in cursor.fetchall()]
    if any(r['ParentNorm'] is None for r in rows):
        raise ValueError('Canonical RRR ParentNorm NULL conversion is not comparable')
    return rows
