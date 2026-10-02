"""Selected Planning Excess joins over the persisted canonical report rows."""
from itertools import product
import re
from mta.presentation.excess_charts import SECTIONS,excess_chart_response
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index,sql_key


def joined_rows(output, rows, business_date, *, predicate=None):
    importer=output['ClosingState'][0]['importer']
    sku_desc=index(importer['SKUDescriptionTbl'],'SKUCode')
    loc_desc=index(importer['SiteDescriptionTbl'],'WHCode')
    sku_attrs=index(importer['SkuAttributeData'],'SKUCode')
    loc_attrs=index(importer['LocationAttributeData'],'WHCode')
    pair_attrs=index(importer['SkuLocAttributeData'],'SKUCode','LocCode')
    result=[]
    for a in rows:
        if a['ReportDate']!=str(business_date):
            continue
        sku,wh=sql_key(a['SKUCode']),sql_key(a['WhCode'])
        for sd,wd,pd,sa,la,_pair in product(sku_desc.get(sku,[]),loc_desc.get(wh,[]),
                loc_desc.get(sql_key(a['ParentWhCode']),[]) or [{}],sku_attrs.get(sku,[]),loc_attrs.get(wh,[]),
                pair_attrs.get(sql_key(a['SKUCode'],a['WhCode']),[])):
            weight = predicate(a, _pair, sa, la) if predicate is not None else 1
            if not weight:
                continue
            row={**a,'WHCode':a['WhCode'],'SKUName':sd['SKUDescription'],'WHName':wd['WHDescription'],
                 'ParentWHName':pd.get('WHDescription'),'Requirement':a['RequiredQty'],
                 'PhysicalPen':None if a['PhysicalInventoryPen'] is None else float(a['PhysicalInventoryPen']),
                 'PipelinePen':None if a['PipelineInventoryPen'] is None else float(a['PipelineInventoryPen']),
                 'PhysicalColor':a['PhysicalInventoryColor'],'PipelineColor':a['PipelineInventoryColor']}
            row.update({f'sl{i}':sa[f'SL{i}'] for i in range(1,6)})
            row.update({f'll{i}':la[f'LL{i}'] for i in range(1,6)})
            result.extend(dict(row) for _ in range(weight))
    return result


def chart_queries(output, rows, business_date, *, products, locations):
    """Canonical description/permission bags aggregate BEFORE attribute joins.

    None scopes are used only by the explicit unscoped validation export. HTTP
    supplies the selected publication's actual permission memberships. Preserve
    source SUM(bigint) overflow and NULL sums, not a widened Python substitute.
    """
    importer=output['ClosingState'][0]['importer']
    eligible=[]
    for row in rows:
        if row['ReportDate']!=str(business_date):
            continue
        weight=(permission_multiplicity(products,row['SKUCode']) *
                permission_multiplicity(locations,row['WhCode']))
        if weight:
            eligible.append((row,weight))
    result={}
    for section,field,amount,*_ in SECTIONS:
        is_location=field=='WHCode'
        code_field='WhCode' if is_location else 'SKUCode'
        prefix='LL' if is_location else 'SL'
        desc_field='WHDescription' if is_location else 'SKUDescription'
        descriptions=index(importer['SiteDescriptionTbl' if is_location else 'SKUDescriptionTbl'],field)
        attributes=index(importer['LocationAttributeData' if is_location else 'SkuAttributeData'],field)
        groups={}
        for row,weight in eligible:
            code=row[code_field]
            for desc in descriptions.get(sql_key(code),[]):
                detail=desc[desc_field]
                group_key=(sql_key(code),sql_key(detail))
                group=groups.setdefault(group_key,dict(code=code,detail=detail,count=0,total=None))
                group['count']+=weight
                if row['Amount'] is not None:
                    group['total']=(group['total'] or 0)+row['Amount']*weight
        projected=[]
        for group in groups.values():
            counts=group['total'] if amount else group['count']
            if counts is not None and not (-(2**63 if amount else 2**31)<=counts<(2**63 if amount else 2**31)):
                raise OverflowError('Canonical Excess aggregate overflow')
            detail=group['detail']
            if detail is not None:
                detail=(detail.replace("'",'') if is_location else
                        re.sub('-ND-',lambda _:group['code'],detail,flags=re.I))
            for attr in attributes.get(sql_key(group['code']),[]):
                projected.append({field:group['code'],'Details':detail,'counts':counts,
                    **{f'{prefix.lower()}{i}':attr[f'{prefix}{i}'] for i in range(1,6)}})
        # No invented tie-break and no TOP10 truncation.
        result[section]=sorted(projected,key=lambda row:(row['counts'] is None,-(row['counts'] or 0)))
    return result


def chart_response(output,rows,business_date,*,products,locations):
    result=excess_chart_response(chart_queries(output,rows,business_date,
                    products=products,locations=locations))
    # The deployed UiConfigAttr serializer includes its default int property.
    # Keep the registered imported helper unchanged; adapt its omitted field.
    for section in result.values():
        for config in section['uiconfig']:
            config['colPosition']=0
    return {'data':result}
