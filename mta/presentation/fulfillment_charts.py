"""Selected deployed QuadrantProcessor queries and GetResponse projection.

Source decompilation SHA256:
9f084f3550ab5c6ca8193de71b70ee6d7341aa1647004776ff152dd9fd858d60.
No demo-only code grouping, score sort, TOP10 or repaired category selection.
"""
from mta.presentation.rrr import index,sql_key
from mta.presentation.permissions import permission_multiplicity

SECTIONS=(('location_orders','details','WhCode','OrderStatus','maximumOverdueOrders','location','ll'),
          ('sku_orders','details','SKUCode','OrderStatus','categorizationOfPendingQuantity','product','sl'),
          ('location_gap','summary','WhCode','Coverage','maxSkuWithGap','location','ll'),
          ('sku_gap','summary','SKUCode','Coverage','maxNumberOfLocationsWithGap','product','sl'))


def chart_queries(output,reports,*,products,locations):
    importer=output['ClosingState'][0]['importer']
    queries={}
    for section,table,field,band,*_ in SECTIONS:
        is_location=field=='WhCode'
        code='WHCode' if is_location else 'SKUCode'
        desc='WHDescription' if is_location else 'SKUDescription'
        prefix='LL' if is_location else 'SL'
        descriptions=index(importer['SiteDescriptionTbl' if is_location else 'SKUDescriptionTbl'],code)
        attributes=index(importer['LocationAttributeData' if is_location else 'SkuAttributeData'],code)
        groups={}
        for row in reports[table]:
            weight=permission_multiplicity(products,row['SKUCode'])*permission_multiplicity(locations,row['WhCode'])
            if not weight: continue
            for description in descriptions.get(sql_key(row[field]),[]):
                group=groups.setdefault((sql_key(row[field]),sql_key(row[band]),sql_key(description[desc])),
                    dict(code=row[field],band=row[band],description=description[desc],count=None if section=='sku_orders' else 0))
                if section=='sku_orders':
                    if row['PendingQty'] is not None: group['count']=(group['count'] or 0)+row['PendingQty']*weight
                elif section!='location_orders' or row['OrderNo'] is not None:
                    group['count']+=weight
        rows=[]
        for group in groups.values():
            if group['count'] is not None and not -2**31<=group['count']<2**31:
                raise OverflowError('Canonical Fulfilment COUNT/SUM(int) overflow')
            description=group['description']
            for attr in attributes.get(sql_key(group['code']),[]):
                rows.append(dict(counts=group['count'],**{code:group['code'],band:group['band']},
                    Details=None if description is None else description.replace("'",''),
                    **{f'{prefix.lower()}{i}':attr[f'{prefix}{i}'] for i in range(1,6)}))
        queries[section]=sorted(rows,key=lambda r:(r['counts'] is None,-(r['counts'] or 0)))
    return queries


def chart_response(queries):
    """Source groups by description and inspects only its first three rows.

    NULL descriptions cannot satisfy the DataView filter before Rows[0]. That
    source flaw is explicit, not repaired into an invented label/group. No such
    row is represented as a successfully accepted chart.
    """
    text=lambda value:'' if value is None else str(value)
    result={}
    for section,_,_,band,response_key,label,prefix in SECTIONS:
        config=[dict(header=f'{prefix.upper()}{i}',colCode=f'{prefix}{i}',colPosition=0) for i in range(1,6)]
        groups={}
        for row in queries[section]:
            if row['Details'] is None:
                raise ValueError('Legacy Fulfilment NULL description cannot select DataView Rows[0]')
            groups.setdefault(row['Details'].casefold(),[]).append(row)
        mapping=({'Over Due':'overdue','Due':'due','Others':'others'} if band=='OrderStatus' else
                 {'Gap < 33%':'smaller','Gap > 67%':'greater','33% <= Gap <= 67%':'between'})
        data=[]
        for rows in groups.values():
            first=rows[0]
            item={label:first['Details'],**{name:'0' for name in mapping.values()}}
            for row in rows[:3]:
                if row[band] in mapping: item[mapping[row[band]]]=text(row['counts'])
            item.update({c['colCode']:text(first[c['colCode']]) for c in config if c['colCode'] in first})
            data.append(item)
        result[response_key]=dict(data=data,uiconfig=config)
    return {'data':result}
