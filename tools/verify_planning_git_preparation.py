"""Complete independent GIT count/grid occurrence proof on retained April data."""
import os,sys,json
from collections import Counter
from itertools import product
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation.fixture import binding
from mta.presentation.selective import image_rows
from mta.presentation.rrr import index,sql_key
from mta.presentation.planning_git_preparation import git_occurrences
from mta.presentation.planning_grid_preparation import DIMENSIONS
from mta.runtime.models import PlanningGitMasterRow


def main():
    run,source=binding()
    indexes={}
    for alias,table in DIMENSIONS:
        rows=[dict(row,_ordinal=i) for i,row in enumerate(image_rows(run,'closing/importer/'+table))]
        indexes[alias]=index(rows,*(['SKUCode','LocCode'] if alias=='pair' else ['SKUCode'] if alias in ('sd','sa') else ['WHCode']))
    expected=[]
    for a in PlanningGitMasterRow.objects.filter(run=run).values():
        if not a['Git'] or a['Git']<=0 or sql_key(a['PhysicalInventoryColor']) not in (('black',),('red',)):continue
        sku,loc,parent=sql_key(a['SKUCode']),sql_key(a['WhCode']),sql_key(a['ParentWhCode'])
        for sd,ld,pd,sa,la,pair in product(indexes['sd'].get(sku,[]),indexes['ld'].get(loc,[]),indexes['ld'].get(parent,[]) or [{}],
                                          indexes['sa'].get(sku,[]),indexes['la'].get(loc,[]),indexes['pair'].get(sql_key(a['SKUCode'],a['WhCode']),[]) or [{}]):
            row=dict(rationed_ordinal=a['rationed_ordinal'],standard_ordinal=a['standard_ordinal'],
                     sku_description_ordinal=sd['_ordinal'],location_description_ordinal=ld['_ordinal'],
                     parent_description_ordinal=pd.get('_ordinal'),sku_ordinal=sa['_ordinal'],location_ordinal=la['_ordinal'],
                     pair_ordinal=pair.get('_ordinal'),sku_description=sd['SKUDescription'],location_description=ld['WHDescription'],
                     parent_description=pd.get('WHDescription'),grid_eligible=bool(pair))
            row.update({p.lower()+str(i):r[p+str(i)] for p,r in [('SL',sa),('LL',la)] for i in range(1,6)})
            expected.append(row)
    query,params=git_occurrences(run)
    with connection.cursor() as c:
        c.execute(query,params);names=[d[0] for d in c.description]
        actual=[dict(zip(names,row)) for row in c.fetchall()]
    bag=lambda rows:Counter(json.dumps(row,sort_keys=True) for row in rows)
    assert bag(actual)==bag(expected),(len(actual),len(expected))
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',count_occurrences=len(actual),grid_occurrences=sum(r['grid_eligible'] for r in actual),source_digest=source)))

if __name__=='__main__':main()
