"""Independent complete occurrence bags for six Expedite chart grains."""
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
from mta.presentation.planning_expedite_chart_preparation import members,prepost_members
from mta.runtime.models import ExpediteRow,PlanningBprMasterRow


def main():
    run,source=binding()
    facts=list(ExpediteRow.objects.filter(run=run).order_by('ordinal').values())
    fact_index=index(facts,'SKUCode','WhCode')
    masters=index(list(PlanningBprMasterRow.objects.filter(run=run).values()),'SKUCode','WHCode')
    dims={}
    for alias,table in [('d','SiteDescriptionTbl'),('l','LocationAttributeData')]:
        dims[alias]=index([dict(row,_ordinal=i) for i,row in enumerate(image_rows(run,'closing/importer/'+table))],'WHCode')
    results=[]
    for direction,family in [('parent',f) for f in ('critical','receiving','nil_stock','chronic')]+[('child',f) for f in ('critical','receiving')]:
        expected=[]
        for s in facts:
            attr=family in ('critical','receiving')
            if family=='critical':
                if s['RationedQty']<=0 or sql_key(s['PipelineInventoryColor']) not in (sql_key('Black'),sql_key('Red')):continue
                if direction=='child' and s['IsParent']!=1:continue
                matched=[(a,None,a['WhCode']) for a in fact_index.get(sql_key(s['SKUCode'],s['ParentWhCode']),[])] if direction=='child' else [(s,None,s['ParentWhCode'])]
            elif family=='receiving':
                if direction=='child' and s['IsReceiving']!=1:continue
                matched=[(s,None,s['WhCode'])]
            else:
                if family=='nil_stock' and s['RationedQty']!=0:continue
                if family=='chronic' and (s['BRAge'] is None or s['BRAge']<=0):continue
                matched=[(s,m,m['ParentWhCode']) for m in masters.get(sql_key(s['SKUCode'],s['ParentWhCode']),[])]
            for a,m,code in matched:
                for d,l in product(dims['d'].get(sql_key(code),[]),dims['l'].get(sql_key(code),[]) if attr else [{}]):
                    norm=lambda v:None if v is None else sql_key(v)[0]
                    row=dict(scope_ordinal=s['ordinal'],fact_ordinal=a['ordinal'],master_ordinal=m['source_ordinal'] if m else None,
                        description_ordinal=d['_ordinal'],location_ordinal=l.get('_ordinal'),code=code,code_key=norm(code),
                        description=d['WHDescription'],description_key=norm(d['WHDescription']))
                    row.update({f.lower():l.get(f) for f in ('LogisticsLocation','LL1','LL2','LL3','LL4','LL5')})
                    expected.append(row)
        query,params=members(run,direction,family)
        with connection.cursor() as c:
            c.execute(query,params);names=[col[0] for col in c.description]
            actual=[dict(zip(names,row)) for row in c.fetchall()]
        bag=lambda rows:Counter(json.dumps(row,sort_keys=True) for row in rows)
        assert bag(actual)==bag(expected),(direction,family,len(actual),len(expected))
        results.append(dict(direction=direction,family=family,rows=len(actual)))
    from mta.presentation.planning_expedite_transit_preparation import PICK_TABLE
    with connection.cursor() as c:
        c.execute('SELECT vf_source_ordinal,"SKUCode","WhCode","ParentWhCode" FROM '+PICK_TABLE+' ORDER BY vf_source_ordinal')
        pick=[dict(zip(['ordinal','SKUCode','WhCode','ParentWhCode'],row)) for row in c.fetchall()]
    by_pair=index(pick,'SKUCode','WhCode')
    children=Counter(sql_key(row['ParentWhCode']) for row in pick if row['ParentWhCode'] is not None)
    expected=[]
    for s in pick:
        weight=children[sql_key(s['WhCode'])]
        if not weight:continue
        for t in by_pair.get(sql_key(s['SKUCode'],s['WhCode']),[]):
            if t['WhCode'] is None or t['ParentWhCode'] is None or sql_key(t['WhCode'])==sql_key(t['ParentWhCode']):continue
            expected.append((s['ordinal'],t['ordinal'],weight))
    query,params=prepost_members(run)
    with connection.cursor() as c:
        c.execute(query,params);actual=c.fetchall()
    assert Counter(actual)==Counter(expected)
    results.append(dict(direction='parent',family='pre_post',rows=len(actual),weighted_occurrences=sum(row[2] for row in actual)))
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))

if __name__=='__main__':main()
