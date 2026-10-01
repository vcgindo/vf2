"""Deployed ExpediteProcessor chart queries/response, with no demo repairs.

Decompiled source SHA e78148cc38d5a802e014e6085111e79a40c2a6b462563e2bd412677505e654b4.
Consumes persisted Expedite/Post-Pick reports and native master attributes.
"""
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_EVEN,localcontext
from itertools import product
from mta.presentation.excess import checked_integer
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index,sql_key

BANDS=('Black','Red','Yellow','Green','White','Blue')


def _sum(values):
    values=[v for v in values if v is not None]
    return checked_integer(sum(values)) if values else None


def queries(output,rows,pick,kind,*,products,locations):
    if kind not in ('parent','child'): raise ValueError('Unsupported Expedite chart direction')
    closing=output['ClosingState'][0]; imp=closing['importer']
    descriptions=index(imp['SiteDescriptionTbl'],'WHCode'); attributes=index(imp['LocationAttributeData'],'WHCode')
    masters=index(closing['bpr']['BPRMaster'],'SKUCode','WHCode')
    def weight(row,field='WhCode'):
        return permission_multiplicity(products,row['SKUCode'])*permission_multiplicity(locations,row[field])
    def location(code):
        for desc,attr in product(descriptions.get(sql_key(code),[]),attributes.get(sql_key(code),[])):
            raw=desc['WHDescription']
            yield dict(raw=raw,Details=raw.replace("'",'') if raw is not None else None,
                LogisticsLocation=attr['LogisticsLocation'],**{f'll{i}':attr[f'LL{i}'] for i in range(1,6)})
    def group_key(code,loc):
        return (sql_key(code),sql_key(loc['raw']),sql_key(loc['LogisticsLocation']),
                *(sql_key(loc[f'll{i}']) for i in range(1,6)))
    critical={}
    for selected in rows:
        w=weight(selected,'WhCode' if kind=='parent' else 'ParentWhCode')
        if not w or selected['RationedQty']<=0 or sql_key(selected['PipelineInventoryColor']) not in (sql_key('Black'),sql_key('Red')):
            continue
        if kind=='child' and selected['IsParent']!=1: continue
        matches=[selected] if kind=='parent' else [r for r in rows if sql_key(r['SKUCode'],r['WhCode'])==sql_key(selected['SKUCode'],selected['ParentWhCode'])]
        for row in matches:
            code=row['ParentWhCode'] if kind=='parent' else row['WhCode']
            for loc in location(code):
                group=critical.setdefault(group_key(code,loc),dict(code=code,loc=loc,members=[]))
                group['members'].extend([row]*w)
    critical_rows=[]
    for g in critical.values():
        members=g['members']; loc=g['loc']
        row=dict(counts=checked_integer(len(members)),**{'ParentWhCode' if kind=='parent' else 'WhCode':g['code']},
                 **{k:v for k,v in loc.items() if k!='raw'})
        red=_sum([r['BRAgeRedCount'] for r in members]); black=_sum([r['BRAgeBlackCount'] for r in members])
        if kind=='parent':
            row.update(BRAgeRedCount1=red,BrAgeBlackCount1=black,
                BRAgeRedCount=sum(Decimal(str(r['PipelineInventoryPen']))!=100 for r in members),
                BrAgeBlackCount=sum(Decimal(str(r['PipelineInventoryPen']))==100 for r in members))
        else: row.update(BRAgeRedCount=red,BrAgeBlackCount=black)
        critical_rows.append(row)
    # JOIN bags precede SQL window SUM and final DISTINCT.
    joined=[]; pair_counts=defaultdict(int); wh_counts=defaultdict(int)
    for row in rows:
        w=weight(row)
        if not w or (kind=='child' and row['IsReceiving']!=1): continue
        n=int(row['RationedQty']>0 and sql_key(row['PipelineInventoryColor']) in (sql_key('Black'),sql_key('Red')))
        for loc in location(row['WhCode']):
            joined.append((row,loc))
            key=sql_key(row['WhCode'],row['ParentWhCode'])
            pair_counts[key]=checked_integer(pair_counts[key]+n*w)
            wh_counts[sql_key(row['WhCode'])]=checked_integer(wh_counts[sql_key(row['WhCode'])]+n*w)
    receiving=[]; seen=set()
    for row,loc in joined:
        item=dict(WhCode=row['WhCode'],ParentWhCode=row['ParentWhCode'],
            ParentwiseCount=pair_counts[sql_key(row['WhCode'],row['ParentWhCode'])],MaxPipelineInv=wh_counts[sql_key(row['WhCode'])],
            **{k:v for k,v in loc.items() if k!='raw'})
        key=tuple(sql_key(v) if isinstance(v,str) else v for v in item.values())
        if key not in seen: receiving.append(item); seen.add(key)
    receiving.sort(key=lambda r:(-r['ParentwiseCount'],-r['MaxPipelineInv']))
    result=dict(critical=critical_rows,receiving=receiving)
    if kind=='parent':
        for name in ('nil_stock','chronic'):
            groups={}
            for row in rows:
                w=weight(row); value=row['RationedQty'] if name=='nil_stock' else row['BRAge']
                if not w or value is None or (value!=0 if name=='nil_stock' else value<=0): continue
                for master in masters.get(sql_key(row['SKUCode'],row['ParentWhCode']),[]):
                    for desc in descriptions.get(sql_key(master['ParentWhCode']),[]):
                        key=sql_key(master['ParentWhCode']),sql_key(desc['WHDescription'])
                        group=groups.setdefault(key,dict(code=master['ParentWhCode'],raw=desc['WHDescription'],members=[]))
                        group['members'].extend([row]*w)
            projected=[]
            for g in groups.values():
                members=g['members']; raw=g['raw']
                row=dict(counts=checked_integer(len(members)),ParentWhCode=g['code'],Details=raw.replace("'",'') if raw is not None else None)
                red=_sum([r['BRAgeRedCount'] for r in members]); black=_sum([r['BRAgeBlackCount'] for r in members])
                if name=='nil_stock':
                    row.update(BRAgeRedCount1=red,BrAgeBlackCount1=black,
                        BRAgeRedCount=sum(Decimal(str(r['PipelineInventoryPen']))!=100 for r in members),
                        BrAgeBlackCount=sum(Decimal(str(r['PipelineInventoryPen']))==100 for r in members))
                else: row.update(BRAgeRedCount=red,BrAgeBlackCount=black)
                projected.append(row)
            result[name]=sorted(projected,key=lambda r:-r['counts'])
    cte=defaultdict(int)
    if kind=='parent':
        for row in pick:
            cte[sql_key(row['SKUCode'],row['WhCode'])]+=weight(row)*sum(
                sql_key(row['WhCode'])==sql_key(child['ParentWhCode']) for child in pick)
    pre_post=[]
    for state,field in (('Pre','DispatchColor'),('Post','PostPipelineInventoryColor')):
        counts={b:0 for b in BANDS}
        for row in pick:
            if sql_key(row['WhCode'])==sql_key(row['ParentWhCode']): continue
            w=weight(row) if kind=='child' else cte[sql_key(row['SKUCode'],row['WhCode'])]
            for band in BANDS:
                if sql_key(row[field])==sql_key(band): counts[band]=checked_integer(counts[band]+w)
        pre_post.append(dict(state=state,**{b+'Count':v for b,v in counts.items()},TotalCount=0))
    result['pre_post']=pre_post
    return result


def response(tables,kind):
    labels={'' if r['LogisticsLocation'] is None else str(r['LogisticsLocation']) for r in tables['critical']}
    if tables['receiving'] and len(labels)>1:
        raise ValueError('Legacy Expedite receiving LogisticsLocation depends on unordered critical rows')
    return response_from_dataset(tables,kind)


def response_from_dataset(tables,kind):
    """Exact pure DLL transformation for an explicitly ordered DataSet.

    This does not confer an ordering on the SQL query. Application callers must
    use response(), which refuses source-ambiguous last-row labels.
    """
    text=lambda v:'' if v is None else str(v)
    config=[dict(header=f'LL{i}',colCode=f'll{i}',colPosition=0) for i in range(1,6)]
    wrap=lambda data:dict(data=data,uiconfig=[dict(c) for c in config])
    critical=[dict(WHDescription=text(r['Details']),SKUCounts=text(r['counts']),LogisticsLocation=text(r['LogisticsLocation']),
        RedCount=text(r['BRAgeRedCount']),BlackCount=text(r['BrAgeBlackCount']),**{f'll{i}':text(r[f'll{i}']) for i in range(1,6)}) for r in tables['critical']]
    # Deployed bug: receiving labels come from the last critical row, not their
    # own joined row. An unordered conflicting label is not a solvable tie.
    last_label=critical[-1]['LogisticsLocation'] if critical else None
    groups={}
    for row in tables['receiving']: groups.setdefault(sql_key(row['WhCode']),[]).append(row)
    receiving=[]
    for rows in groups.values():
        first=rows[0]; pairs={}
        for r in rows: pairs.setdefault((sql_key(r['ParentWhCode']),r['ParentwiseCount']),(r['ParentWhCode'],r['ParentwiseCount']))
        receiving.append(dict(WHDescription=text(first['Details']),count=[dict(pwc=text(p),count=text(n)) for p,n in pairs.values()],
            LogisticsLocation=last_label,**{f'll{i}':text(first[f'll{i}']) for i in range(1,6)}))
    def percentage(count,total):
        if not total: return '0'
        with localcontext() as context:
            context.prec=28
            ratio=Decimal(count)*100/total; rounded=ratio.quantize(Decimal('.01'),rounding=ROUND_HALF_EVEN)
        return (format(rounded,'f').rstrip('0').rstrip('.') or '0') if rounded==ratio else format(rounded,'f')
    pivots={r['state']:r for r in tables['pre_post']}
    totals={k:checked_integer(sum(v[b+'Count'] for b in BANDS)) for k,v in pivots.items()}
    prepost=[dict(color=b,**{s.lower():percentage(pivots[s][b+'Count'],totals[s]) for s in ('Pre','Post')}) for b in BANDS]
    result=dict(expediteDispatches=dict(maxEcoBlackRedSKUWithAvailableRationedQtyAtReceivingLocationsuiconfig=wrap(critical),
        maxPipelineInvBlackRedSKUWithRationedQuantityAvailableAtParentuiconfig=wrap(receiving),prePostRationing=prepost))
    if kind=='parent':
        def availability(name,count_name):
            return [dict(WHDescription=text(r['Details']),**{count_name:text(r['counts'])},LogisticsLocation=None,
                RedCount=text(r['BRAgeRedCount1' if name=='nil_stock' else 'BRAgeRedCount']),
                BlackCount=text(r['BrAgeBlackCount1' if name=='nil_stock' else 'BrAgeBlackCount'])) for r in tables[name]]
        result['createAvailabilityAtParent']=dict(
            maxEcoBlackRedWithNilRationedStockForRecievingLocations=wrap(availability('nil_stock','Counts')),
            maxContinousEcoBlackRedWithNilRationedStockAvailableForRecievingLocations=wrap(availability('chronic','SKUCounts')))
    return {'data':result}
