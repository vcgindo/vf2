"""Post-ration report colour; does not change Pick quantities or engine state."""
from decimal import Decimal,ROUND_HALF_UP,localcontext
from mta.domain.bpr_construction import _colour,MIN_PEN
from mta.presentation.excess import checked_integer
from mta.presentation.rrr import sql_key

SOURCE_HASHES={
    'PostRationEcoAvailability.sql':'ad726c858dab068a86e567dfe814b99a5309b693ebee061aaa84f60d00b2e977',
    'CalculatePenetrationAndColor.sql':'e4a62d592b660fe08d46c45eecaf7a061e60eba7c8d86d3adec239023de5e251',
    'UpdatePostRationPipelineInventoryPen.sql':'3881064e266422ceddfde472420c74b70d7799f01311afd8b650f55e0a80f554'}
FIELDS=('SKUCode','WhCode','ParentWhCode','PostPipelineInventoryPen','PostPipelineInventoryColor')


def produce(rows):
    updates={}
    for row in rows:
        if row['WhCode'] is None or row['ParentWhCode'] is None or sql_key(row['WhCode'])==sql_key(row['ParentWhCode']):
            continue
        norm,stock,git,base,blue=(row[n] for n in ('VirtualNorm','StockForReqCalc','GIT','Norm','BlueReq'))
        if any(v is None for v in (norm,stock,git,base,blue,row['RationedReq'])):
            raise ValueError('Post-ration source NULL numeric input is not accepted')
        git=checked_integer(git+row['RationedReq'])
        blue=checked_integer(blue-checked_integer(norm-base))
        checked_integer(abs(norm)); checked_integer(norm-stock); checked_integer(norm+blue)
        with localcontext() as context:
            context.prec=50
            pen=(Decimal(100)*(norm-stock-git)/abs(norm)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if norm else MIN_PEN
        pen=max(pen,MIN_PEN)
        if pen>Decimal('99999999.99'): raise OverflowError('Canonical post-ration decimal(10,2) overflow')
        inventory=checked_integer(stock+git)
        value=(format(pen,'.2f'),_colour(pen,norm,inventory,blue))
        key=sql_key(row['SKUCode'],row['WhCode'])
        if key in updates and updates[key]!=value:
            raise ValueError('Canonical post-ration UPDATE has conflicting same-key inputs; no invented winner')
        updates[key]=value
    result=[]
    for row in rows:
        selected=row['WhCode'] is not None and row['ParentWhCode'] is not None and sql_key(row['WhCode'])!=sql_key(row['ParentWhCode'])
        value=updates[sql_key(row['SKUCode'],row['WhCode'])] if selected else (None,None)
        result.append({**{n:row[n] for n in FIELDS[:3]},**dict(zip(FIELDS[3:],value))})
    return result
