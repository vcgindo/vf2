"""Deployed SCIH/BPR consumers over committed wide BTR colour histories.

No calculation rerun or reconstruction from a different history population.
"""
from datetime import date
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from itertools import product
import json
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.rrr import index,sql_key

COLOURS=(('B','Black'),('R','Red'),('Y','Yellow'),('G','Green'),('BU','Blue'),('W','White'))


def percentage(value,total):
    """C# decimal division/*100, Math.Round(2,ToEven), ToString scale."""
    if total==0: return '0'
    with localcontext() as ctx:
        ctx.prec=29; ctx.rounding=ROUND_HALF_EVEN
        result=Decimal(value)/Decimal(total)*100
        scale=max(0,-result.as_tuple().exponent)
        return format(round(result,min(2,scale)),'f')


def colour_counts(state,kind,columns,*,products,locations,with_pair=True):
    table='BufferTrendDispatch' if kind=='eco' else 'BufferTrendPhysicalInv'
    skus=index(state['SkuAttributeData'],'SKUCode'); locs=index(state['LocationAttributeData'],'WHCode')
    pairs=index(state['SkuLocAttributeData'],'SKUCode','LocCode') if with_pair else None
    totals={column:{alias:0 for alias,_ in COLOURS} for column in columns}; population=0
    for row in state[table]:
        sku,wh=row['SKUCode'],row['WhCode']
        weight=permission_multiplicity(products,sku)*permission_multiplicity(locations,wh)
        weight*=len(skus.get(sql_key(sku),[]))*len(locs.get(sql_key(wh),[]))
        if with_pair: weight*=max(1,len(pairs.get(sql_key(sku,wh),[])))
        if not weight: continue
        population+=weight
        for column in columns:
            for alias,colour in COLOURS:
                if row[column]==colour: totals[column][alias]+=weight
    return [dict(D=column,**{a:totals[column][a] if population else None for a,_ in COLOURS}) for column in columns]


def graph_response(counts,labels):
    # The source uses Rows[0]; missing date metadata is not synthesized.
    dates=labels[0]; absolute=[]; relative=[]; totals={a:0 for a,_ in COLOURS}
    for row in counts:
        day=date.fromisoformat(dates[row['D']][:10]).strftime('%d-%m-%Y')
        values={a:row[a] or 0 for a,_ in COLOURS}; total=sum(values.values())
        absolute.append(dict(dt=day,**{a.lower():str(v) for a,v in values.items()}))
        relative.append(dict(dt=day,**{a.lower():percentage(v,total) for a,v in values.items()}))
        for alias,value in values.items():
            totals[alias]+=value
            if not -(2**31)<=totals[alias]<2**31: raise OverflowError('Legacy chart Int32 sum overflow')
    total=sum(totals.values())
    if not -(2**31)<=total<2**31: raise OverflowError('Legacy chart Int32 total overflow')
    summary=[dict(category='Absolute Value',**{'sum'+a:str(v) for a,v in totals.items()}),
        dict(category='Percentage',**{'sum'+a:percentage(v,total) for a,v in totals.items()})]
    return dict(absolute=absolute,percentage=relative,summary=summary,avail=percentage(total-totals['B'],total))


def buffer_graph(state,kind,days,*,products,locations):
    if not 1<=days<=90: raise ValueError('Buffer graph days outside retained columns')
    columns=tuple(f'D{i}' for i in range(91-days,91))
    counts=colour_counts(state,kind,columns,products=products,locations=locations)
    return graph_response(counts,state['BufferTrendDates'])


def historical_availability(state,*,products,locations):
    counts=colour_counts(state,'tech',tuple(f'D{i}' for i in range(1,91)),
        products=products,locations=locations,with_pair=False)
    result={}
    for start,end in ((1,30),(31,60),(61,90)):
        rows=counts[start-1:end]; total=sum((r[a] or 0) for r in rows for a,_ in COLOURS)
        black=sum(r['B'] or 0 for r in rows)
        value=float(percentage(total-black,total))
        # System.Text.Json writes integral doubles without a decimal suffix.
        result[f'availability_{start:02d}_{end}']=int(value) if value.is_integer() else value
    return [result]


def research_rows(state,master,data,*,products,locations):
    """SCIH self/child/parent SELECT UNION (distinct), including omitted NULLs."""
    if not isinstance(data,list) or not data: raise ValueError('Selected research data required')
    selected={sql_key(r['SKUCode'],r['WhCode']) for r in data}
    columns=tuple(f'D{i}' for i in range(1,91)); result=[]
    def allowed(sku,wh):
        return permission_multiplicity(products,sku)>0 and permission_multiplicity(locations,wh)>0
    def emit(row,kind,pen,sku,wh,child=None,parent=None):
        value=dict(Type=kind,Pen=pen,SKUCode=sku,Whcode=wh,ChildCode=child,ParentWhCode=parent,
            Age=row['Age'],BRAge=row['BRAge'],**{c:row[c] for c in columns})
        result.append({k:v for k,v in value.items() if v is not None})
    for table,pen in (('BufferTrendPhysicalInv','Tech'),('BufferTrendDispatch','Eco')):
        rows=state[table]; by_pair=index(rows,'SKUCode','WhCode')
        for row in rows:
            sku,wh,parent=row['SKUCode'],row['WhCode'],row['ParentWhCode']
            if sql_key(sku,wh) in selected and allowed(sku,wh): emit(row,'Self',pen,sku,wh)
            if sql_key(sku,parent) in selected and allowed(sku,parent): emit(row,'Child',pen,sku,parent,child=wh)
        for owner in master:
            sku,wh=owner['SKUCode'],owner['WhCode']
            if sql_key(sku,wh) not in selected or not allowed(sku,wh): continue
            for row in by_pair.get(sql_key(sku,owner['ParentWhCode']),[]):
                emit(row,'Parent',pen,sku,wh,parent=row['WhCode'])
    # UNION removes exact duplicate projected rows. No source ordering exists.
    seen=set(); unique=[]
    for row in result:
        identity=json.dumps(row,sort_keys=True,separators=(',',':'))
        if identity not in seen: seen.add(identity); unique.append(row)
    return unique or None
