"""Canonical CollectDataToExpediteDispatches report; no ration/DBM calculation."""
from decimal import Decimal,localcontext,ROUND_DOWN,ROUND_HALF_UP
from mta.presentation.excess import checked_integer
from mta.presentation.rrr import index,sql_key

PRODUCER_SHA='894ba52512be0bb39ec4e97aff603ed1da572c4463d6c319b9a2ae20a54f753d'
FIELDS=('SKUCode','WhCode','ParentWhCode','PhysicalInventoryPen','PhysicalInventoryColor',
    'PipelineInventoryPen','PipelineInventoryColor','RationedQty','Req','StockAtParent',
    'ParentPipelineInventoryColor','RLT','BRAge','BRAgeRedCount','BRAgeBlackCount',
    'Norm','VirtualNorm','Stock','GIT','PotentialLossPerDay','IsParent','IsReceiving')
AGE_FIELDS=('BRAge','BRAgeRedCount','BRAgeBlackCount')


def potential_loss(norm,rlt,price):
    if norm==0: return 0
    if norm is None or norm<0 or rlt is None: return None
    # SQL INT/(INT*decimal(2,1)), then decimal(18,3) price multiplication.
    with localcontext() as context:
        context.prec=50
        ratio=(Decimal(rlt)/Decimal(norm)).quantize(Decimal('0.00000000000001'),rounding=ROUND_DOWN)
        amount=(ratio*Decimal(str(price or 0))).quantize(Decimal('0.00000000001'),rounding=ROUND_HALF_UP)
        return checked_integer(amount.quantize(Decimal(1),rounding=ROUND_HALF_UP),64)


def unique_update(rows,fields,label):
    values={tuple(row[field] for field in fields) for row in rows}
    if len(values)>1:
        raise ValueError('Canonical Expedite ambiguous '+label+' UPDATE; no invented winner')
    return dict(zip(fields,next(iter(values)))) if values else {}


def produce(pick,masters,standards,rationed,ages):
    master=index(masters,'SKUCode','WhCode'); standard=index(standards,'SKUCode','WhCode')
    parents=index(rationed,'SKUCode','WhCode'); age=index(ages,'SKUCode','WhCode')
    result=[]
    for source in pick:
        if sql_key(source['DispatchColor']) not in {sql_key(v) for v in ('Black','Red','Yellow')}:
            continue
        if source['WhCode'] is None or source['ParentWhCode'] is None or sql_key(source['WhCode'])==sql_key(source['ParentWhCode']):
            continue
        key=sql_key(source['SKUCode'],source['WhCode'])
        for m in master.get(key,[]):
            for attr in standard.get(key,[]) or [dict(Price=None)]:
                row={name:None for name in FIELDS}
                for name in ('SKUCode','WhCode','ParentWhCode','PhysicalInventoryColor','Req','Norm','VirtualNorm','Stock','GIT'):
                    row[name]=source[name]
                row.update(PipelineInventoryColor=source['DispatchColor'],RationedQty=source['RationedReq'],RLT=m['RLT'],
                           PotentialLossPerDay=potential_loss(m['Norm'],m['RLT'],attr['Price']),IsParent=False,IsReceiving=True)
                for target,field in (('PhysicalInventoryPen','PhysicalInventoryPen'),('PipelineInventoryPen','DispatchPen')):
                    row[target]=None if source[field] is None else format(Decimal(str(source[field])),'.2f')
                for field in ('RationedQty','Req','Norm','VirtualNorm','Stock','GIT','RLT'):
                    row[field]=checked_integer(row[field])
                    if row[field] is None: raise ValueError('Canonical Expedite NOT NULL '+field)
                if row['PipelineInventoryPen'] is None: raise ValueError('Canonical Expedite NOT NULL PipelineInventoryPen')
                parent=unique_update(parents.get(sql_key(source['SKUCode'],source['ParentWhCode']),[]),
                                     ('Stock','DispatchColor'),'parent')
                if parent: row.update(StockAtParent=parent['Stock'],ParentPipelineInventoryColor=parent['DispatchColor'])
                if key not in age: raise ValueError('Produced Expedite lacks its accepted BTR ageing state')
                row.update(unique_update(age[key],AGE_FIELDS,'age'))
                result.append(row)
    child_parents={sql_key(r['SKUCode'],r['ParentWhCode']) for r in result}
    for row in result:
        row['IsParent']=sql_key(row['SKUCode'],row['WhCode']) in child_parents
    if set(age)!={sql_key(r['SKUCode'],r['WhCode']) for r in result}:
        raise ValueError('Expedite membership differs from accepted BTR ageing population')
    return result
