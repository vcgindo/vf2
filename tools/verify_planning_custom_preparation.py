"""Independent exact occurrence-bag proof for custom-grid preparation."""
import os,sys,json
from collections import Counter,defaultdict
from itertools import product
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation.fixture import binding
from mta.presentation.selective import image_rows
from mta.presentation.rrr import sql_key
from mta.presentation.planning_custom_preparation import custom_occurrences
from mta.runtime.models import ExcessInventoryRow,FulfillmentSummaryRow


def main():
    run,source=binding()
    sources={name:image_rows(run,path) for name,path in (
        ('nms','closing/consumer_context/NMSAllItems'),('parent','closing/importer/SiteDescriptionTbl'),
        ('standard','closing/dbm/SKULocStandardAttributes'))}
    indexes={}
    for name,rows in sources.items():
        idx=defaultdict(list)
        for ordinal,row in enumerate(rows):
            key=sql_key(row['WHCode']) if name=='parent' else sql_key(row['SKUCode'],row['WhCode'])
            if key is not None:idx[key].append((ordinal,row))
        indexes[name]=idx
    results={}
    for family,model in [('excess',ExcessInventoryRow),('fulfillment',FulfillmentSummaryRow)]:
        facts=model.objects.filter(run=run)
        if family=='excess':facts=facts.filter(ReportDate=run.business_date)
        expected=[]
        for fact in facts.order_by('ordinal').values('ordinal','SKUCode','WhCode'):
            pair=sql_key(fact['SKUCode'],fact['WhCode'])
            matches=indexes['nms'].get(pair,[]) or ([] if family=='excess' else [(None,{})])
            for nms_ordinal,nms in matches:
                parents=indexes['parent'].get(sql_key(nms.get('ParentWhCode')),[]) or ([] if family=='excess' else [(None,{})])
                standards=indexes['standard'].get(pair,[]) if family=='excess' else [(None,{})]
                for (parent_ordinal,parent),(standard_ordinal,_) in product(parents,standards):
                    row=dict(fact_ordinal=fact['ordinal'],nms_ordinal=nms_ordinal,parent_description_ordinal=parent_ordinal,
                             sku_key=None if nms.get('SKUCode') is None else nms['SKUCode'].rstrip(' ').lower(),
                             location_key=None if nms.get('WhCode') is None else nms['WhCode'].rstrip(' ').lower(),
                             parent_description=parent.get('WHDescription'))
                    if family=='excess':row['standard_ordinal']=standard_ordinal
                    expected.append(row)
        query,params=custom_occurrences(run,family)
        with connection.cursor() as c:
            c.execute(query,params);names=[d[0] for d in c.description]
            actual=[dict(zip(names,row)) for row in c.fetchall()]
        pack=lambda rows:Counter(json.dumps(r,sort_keys=True) for r in rows)
        assert pack(actual)==pack(expected),(family,len(actual),len(expected))
        results[family]=dict(occurrences=len(actual),missing=0,extra=0,unmatched_nms=sum(r['nms_ordinal'] is None for r in actual))
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',families=results,source_digest=source)))

if __name__=='__main__':main()
