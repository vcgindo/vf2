"""Independent four-grain Expedite preparation comparison on retained sources."""
import os,sys,json
from pathlib import Path
from collections import Counter
from itertools import product
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation.fixture import binding
from mta.presentation.selective import image_rows
from mta.presentation.rrr import index,sql_key
from mta.presentation.planning_grid_preparation import DIMENSIONS
from mta.presentation.planning_expedite_preparation import grid_occurrences
from mta.runtime.models import ExpediteRow,PlanningBprMasterRow


def main():
    run,source=binding();indexes={}
    for alias,table in (*DIMENSIONS,('standard','SKULocStandardAttributes')):
        path=('closing/dbm/' if alias=='standard' else 'closing/importer/')+table
        rows=[dict(r,_ordinal=i) for i,r in enumerate(image_rows(run,path))]
        fields=['SKUCode','WhCode'] if alias=='standard' else ['SKUCode','LocCode'] if alias=='pair' else ['SKUCode'] if alias in ('sd','sa') else ['WHCode']
        indexes[alias]=index(rows,*fields)
    masters=index(list(PlanningBprMasterRow.objects.filter(run=run).values()),'SKUCode','WHCode')
    facts=list(ExpediteRow.objects.filter(run=run).order_by('ordinal').values())
    results=[]
    for direction,branch in product(('parent','child'),('dispatch','availability')):
        expected=[]
        for a in facts:
            q=a['RationedQty']
            if q is None or (q<=0 if branch=='dispatch' else q!=0):continue
            if (direction=='parent' or branch=='dispatch') and sql_key(a['PipelineInventoryColor']) not in (sql_key('Black'),sql_key('Red')):continue
            sk,loc,parent=sql_key(a['SKUCode']),sql_key(a['WhCode']),sql_key(a['ParentWhCode'])
            pair=sql_key(a['SKUCode'],a['WhCode'])
            fallback=[] if direction=='child' and branch=='availability' else [{}]
            master=masters.get(sql_key(a['SKUCode'],a['ParentWhCode']),[]) if direction=='parent' and branch=='availability' else [{}]
            for standard,sd,ld,pd,sa,la,pair_row,m in product(indexes['standard'].get(pair,[]) or fallback,
                indexes['sd'].get(sk,[]) or fallback,indexes['ld'].get(loc,[]) or fallback,indexes['ld'].get(parent,[]) or [{}],
                indexes['sa'].get(sk,[]) or fallback,indexes['la'].get(loc,[]) or fallback,indexes['pair'].get(pair,[]) or fallback,master):
                row=dict(fact_ordinal=a['ordinal'],standard_ordinal=standard.get('_ordinal'),sku_description_ordinal=sd.get('_ordinal'),
                         location_description_ordinal=ld.get('_ordinal'),parent_description_ordinal=pd.get('_ordinal'),
                         sku_ordinal=sa.get('_ordinal'),location_ordinal=la.get('_ordinal'),pair_ordinal=pair_row.get('_ordinal'),
                         master_ordinal=m.get('source_ordinal'),sku_description=sd.get('SKUDescription'),location_description=ld.get('WHDescription'),parent_description=pd.get('WHDescription'))
                row.update({p.lower()+str(i):r.get(p+str(i)) for p,r in [('SL',sa),('LL',la)] for i in range(1,6)})
                expected.append(row)
        query,params=grid_occurrences(run,direction,branch)
        with connection.cursor() as c:
            c.execute(query,params);names=[d[0] for d in c.description]
            actual=[dict(zip(names,row)) for row in c.fetchall()]
        bag=lambda rows:Counter(json.dumps(r,sort_keys=True) for r in rows)
        assert bag(actual)==bag(expected),(direction,branch,len(actual),len(expected))
        results.append(dict(direction=direction,branch=branch,occurrences=len(actual),missing=0,extra=0))
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))

if __name__=='__main__':main()
