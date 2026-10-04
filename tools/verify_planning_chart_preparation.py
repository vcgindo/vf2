"""Qualify chart ingredients against full ordered independent consumer datasets."""
import os,sys,json,re
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation import fixture
from mta.presentation.context import permission_catalogue,scope
from mta.presentation.selective import image_rows
from mta.presentation.planning_chart_preparation import chart_ingredients,FAMILIES
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.excess_views import chart_queries as excess_reference
from mta.presentation.fulfillment_charts import chart_queries as fulfillment_reference
from mta.serialization import storage,digest


def main():
    run,source=fixture.binding()
    importer={name:image_rows(run,'closing/importer/'+name) for name in
              ('SKUDescriptionTbl','SiteDescriptionTbl','SkuAttributeData','LocationAttributeData')}
    output={'ClosingState':[{'importer':importer}]}
    catalogue=permission_catalogue()
    payload={key:[r['id'] for r in catalogue[kind]['records']] for key,kind in
             (('product_permissions','products'),('location_permissions','locations'))}
    products,locations=scope(payload,attributes=importer)
    facts={}
    ingredients={}
    for family,model in FAMILIES.items():
        qs=model.objects.filter(run=run)
        if family=='excess':qs=qs.filter(ReportDate=run.business_date)
        fields=[f.name for f in model._meta.local_fields if f.name not in ('id','run')]
        facts[family]={row['ordinal']:row for row in storage(list(qs.order_by('ordinal').values(*fields)))}
        if '--stored' in sys.argv:
            continue
        for direction in ('sku','location'):
            ingredients[family,direction]={}
            for grain,(query,params) in chart_ingredients(run,family,direction).items():
                with connection.cursor() as c:
                    c.execute(query,params)
                    names=[d[0] for d in c.description]
                    ingredients[family,direction][grain]=[dict(zip(names,row)) for row in c.fetchall()]
    def actual(family,direction,amount=False):
        groups={}
        for member in ingredients[family,direction]['members']:
            fact=facts[family][member['fact_ordinal']]
            weight=permission_multiplicity(products,fact['SKUCode'])*permission_multiplicity(locations,fact['WhCode'])
            if not weight:continue
            summed=amount or (family=='fulfillment_detail' and direction=='sku')
            group=groups.setdefault(member['group_ordinal'],dict(**member,count=None if summed else 0))
            if summed:
                value=fact['Amount' if amount else 'PendingQty']
                if value is not None:group['count']=(group['count'] or 0)+value*weight
            elif family!='fulfillment_detail' or fact['OrderNo'] is not None:
                group['count']+=weight
        rows=[]
        for display in ingredients[family,direction]['displays']:
            group=groups.get(display['group_ordinal'])
            if group is None:continue
            name=group['description']
            if name is not None:
                name=(re.sub('-ND-',lambda _:group['code'],name,flags=re.I)
                      if family=='excess' and direction=='sku' else name.replace("'",''))
            row=dict(counts=group['count'],Details=name)
            row['WHCode' if direction=='location' else 'SKUCode']=group['code']
            if family!='excess':row['Coverage' if family=='fulfillment_summary' else 'OrderStatus']=group['band']
            row.update({('ll' if direction=='location' else 'sl')+str(i):display['h'+str(i)] for i in range(1,6)})
            rows.append((group['ordinal'],display['attribute_ordinal'],row))
        rows.sort(key=lambda item:(item[2]['counts'] is None,-(item[2]['counts'] or 0),item[0],item[1]))
        return [row for _,_,row in rows]
    results=[]
    for restricted in (False,True):
        if restricted:
            # A real populated pair's permission hierarchy, not the first arbitrary leaf.
            sample=next(iter(facts['excess'].values()))
            for key,kind,table,code,prefix,selected in (
                    ('product_permissions','products','SkuAttributeData','SKUCode','SL',sample['SKUCode']),
                    ('location_permissions','locations','LocationAttributeData','WHCode','LL',sample['WhCode'])):
                attr=next(r for r in importer[table] if r[code]==selected)
                payload[key]=[next(r['id'] for r in catalogue[kind]['records'] if all(
                    r['level_'+str(i)]==attr[prefix+str(i)] for i in (1,2,3)))]
            products,locations=scope(payload,attributes=importer)
        if '--stored' in sys.argv:
            from mta.presentation.planning_chart_sql import chart_queries
            sql_excess=chart_queries(run,payload,'excess')
            sql_fulfillment=chart_queries(run,payload,'fulfillment')
        references=excess_reference(output,list(facts['excess'].values()),run.business_date,products=products,locations=locations)
        for section,expected in references.items():
            rows=sql_excess[section] if '--stored' in sys.argv else actual('excess','location' if section.startswith('location') else 'sku',section.endswith('value'))
            assert rows==expected,('excess',restricted,section,len(rows),len(expected))
            results.append(dict(family='excess',restricted=restricted,section=section,rows=len(rows),digest=digest(rows)))
        references=fulfillment_reference(output,dict(summary=list(facts['fulfillment_summary'].values()),details=list(facts['fulfillment_detail'].values())),products=products,locations=locations)
        for section,expected in references.items():
            rows=sql_fulfillment[section] if '--stored' in sys.argv else actual('fulfillment_detail' if section.endswith('orders') else 'fulfillment_summary','location' if section.startswith('location') else 'sku')
            assert rows==expected,('fulfillment',restricted,section,len(rows),len(expected))
            results.append(dict(family='fulfillment',restricted=restricted,section=section,rows=len(rows),digest=digest(rows)))
    if '--stored' in sys.argv:
        from django.core.management import call_command
        call_command('prepare_planning_charts',verify_only=True)
        call_command('check')
        call_command('makemigrations',check=True,dry_run=True)
        call_command('migrate',plan=True)
    assert fixture.binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))

if __name__=='__main__':main()
