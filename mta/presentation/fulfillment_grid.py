"""Pinned deployed-shaped Fulfilment aliases and nested order projection."""
from collections import defaultdict
from decimal import Decimal
from mta.presentation.rrr import sql_key as _key

ALIASES = {
    'c':'Coverage','t':'Tags','sc':'SKUCode','sd':'SKUName','wc':'WHCode','wcd':'WHName',
    'vn':'VirtualNorm','n':'Norm','s':'Stock','git':'GIT','rq':'RationedQty','nr':'NormReq',
    'sr':'SpikeReq','rpc':'RelPSOAndCNR','tq':'Requirement','g':'Gap','pip':'PhysicalPen',
    'pic':'PhysicalColor','plp':'PipelinePen','plc':'PipelineColor','tsnp':'TotalSnP',
    **{f'{prefix}{i}':f'{prefix}{i}' for prefix in ('sl','ll') for i in range(1,6)},
}

COLUMNS = (
    ('Coverage','c',1),('Tags','t',2),('SKU Code','sc',3),('SKU Description','sd',4),
    ('Location Code','wc',5),('Location','wcd',6),('Virtual Norm','vn',7),('Norm','n',8),
    ('Stock','s',9),('GIT','git',10),('Rationed Qty','rq',11),('Norm Requirement','nr',12),
    ('Total Requirement','tq',15),('Gap','g',16),('On-hand Inventory Pen','pip',17),
    ('Pipeline Inventory Pen','plp',18),('Price','p',19),('Business','sl1',20),
    ('Category','sl2',21),('Family','sl3',22),('Total SnP','tsnp',23),
    ('Zone','ll1',25),('Location Group','ll2',26),('WH Type','ll3',27),
)

def fulfillment_grid_rows(rows, details):
    orders = defaultdict(list)
    for detail in details:
        if (key := _key(detail['SKUCode'], detail['WHCode'])) is not None:
            orders[key].append({
                'on':detail.get('OrderNo'), 'id':detail.get('IntroDate'),
                'pq':int(detail['PendingQty']) if detail.get('PendingQty') is not None else None,
                'dd':str(detail['DueDate']) if detail.get('DueDate') is not None else '-',
                'c':detail.get('Customer'),
                # SQL ISNULL(BIGINT, '-') converts '-' to numeric zero.
                'p':int(detail['Price']) if detail.get('Price') is not None else 0,
                'os':detail.get('OrderStatus'),
            })
    ordered = sorted(rows, key=lambda r: (r['SKUCode'].rstrip().casefold(),r['WHCode'].rstrip().casefold()), reverse=True)
    ordered.sort(key=lambda r:(r['Gap'] is None, -Decimal(str(r['Gap'])) if r['Gap'] is not None else 0))
    return [dict(rn=index, **{alias:row.get(field) for alias,field in ALIASES.items()},
                 p=str(int(row['Price'])) if row.get('Price') is not None else '-',
                 transit=orders.get(_key(row['SKUCode'],row['WHCode']), []))
            for index,row in enumerate(ordered,1)]

def fulfillment_grid_config():
    return [dict(header=header,colCode=code,colPosition=position) for header,code,position in COLUMNS]
