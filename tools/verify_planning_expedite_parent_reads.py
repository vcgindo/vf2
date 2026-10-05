"""Complete parent grid values/order and nested bags against source reference.

Legacy wire and browser performance remain separate gates.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation.fixture import binding,bpr_ancillary
from mta.presentation.context import permission_catalogue,scope
from mta.presentation.selective import image_rows
from mta.presentation.expedite_parent import parent_rows,parent_filter
from mta.presentation.planning_expedite_sql import parent_grid
from mta.presentation.planning_expedite_transit_preparation import pick_source,PICK_TABLE
from mta.runtime.models import ExpediteRow,PlanningBprMasterRow
from mta.serialization import digest


def main():
    run,source = binding()
    importer = {name:image_rows(run,'closing/importer/'+name) for name in
                ('SkuAttributeData','LocationAttributeData','SkuLocAttributeData','SKUDescriptionTbl','SiteDescriptionTbl')}
    standards = image_rows(run,'closing/dbm/SKULocStandardAttributes')
    nms = image_rows(run,'closing/consumer_context/NMSAllItems')
    facts = list(ExpediteRow.objects.filter(run=run).order_by('ordinal').values())
    masters = list(PlanningBprMasterRow.objects.filter(run=run).order_by('source_ordinal').values())
    remarks = bpr_ancillary(run)['BPRReport_RemarkDetails']
    pick_source(verify_values=True)
    with connection.cursor() as c:
        c.execute('SELECT "SKUCode","WhCode","ParentStockForRationing" FROM '+PICK_TABLE+' ORDER BY vf_source_ordinal')
        pick = [dict(zip(['SKUCode','WhCode','ParentStockForRationing'],row)) for row in c.fetchall()]
    catalogue = permission_catalogue()
    broad = {key:[r['id'] for r in catalogue[kind]['records']] for key,kind in
             (('product_permissions','products'),('location_permissions','locations'))}
    selected = next(row for row in facts if row['RationedQty']>0)
    leaf = {}
    for key,kind,table,code,prefix,value in (
        ('product_permissions','products','SkuAttributeData','SKUCode','SL',selected['SKUCode']),
        ('location_permissions','locations','LocationAttributeData','WHCode','LL',selected['WhCode'])):
        attr = next(row for row in importer[table] if row[code]==value)
        leaf[key] = [next(row['id'] for row in catalogue[kind]['records'] if all(row['level_'+str(i)]==attr[prefix+str(i)] for i in (1,2,3)))]
    cases = [('full',broad,(1,100000),{}),('page2',broad,(2,50),{}),('leaf',leaf,(1,100000),{}),
             ('empty',dict(product_permissions=[],location_permissions=[]),(1,50),{}),
             ('past-end',broad,(99999,50),{}),
             ('sku',broad,(1,100000),dict(productFilter=dict(filters=[dict(attributeName='sku',value=selected['SKUCode'])])))]
    if '--unpaged-only' in sys.argv:
        cases = [('full-unpaged',broad,None,{}),('leaf-unpaged',leaf,None,{}),
                 ('empty-unpaged',dict(product_permissions=[],location_permissions=[]),None,{})]
    if '--filters-only' in sys.argv:
        loc = next(row for row in importer['LocationAttributeData'] if row['WHCode']==selected['WhCode'])
        filter_cases = [
            ('stock',{'availabilityFilter':{'filters':[{'attributeName':'stock','operator':'greaterthan','value':'0'}]}}),
            ('tags',{'availabilityFilter':{'filters':[{'attributeName':'pipo,seasonality','value':'NPI'}]}}),
            ('location-type',{'supplyChainFilter':{'filters':[{'attributeName':'forlocation','value':loc['LocationType']}]}}),
            ('children-ignored',{'supplyChainFilter':{'filters':[{'attributeName':'forchildren','value':loc['LocationType']}]}}),
            ('hierarchy',{'locationFilter':{'filters':[{'attributeName':'l1','operator':'equalto','value':loc['LL1']}]}}),
            ('custom-ignored',{'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}}),
            ('custom-active',{'availabilityFilter':{'filters':[]},'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}})]
        cases = [(label,broad,(1,100000),filters) for label,filters in filter_cases]
    results = []
    for label,permissions,paging,filters in cases:
        payload = dict(**permissions,filters=filters)
        if paging is not None:
            payload['paginationParameter']=dict(pageNumber=paging[0],recordsPerPage=paging[1])
        products,locations = scope(payload,attributes=importer)
        expected = parent_rows(facts,importer,standards,masters,nms=nms,products=products,locations=locations,
                               paging=paging,matches=parent_filter(payload,importer),remarks=remarks,pick=pick,
                               corrected_unpaged='--unpaged-only' in sys.argv)
        actual = parent_grid(run,payload)['data']
        for name in expected:
            if name.endswith('transit'):
                bag = lambda rows:Counter(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in rows)
                assert bag(actual[name])==bag(expected[name]),(label,name,len(actual[name]),len(expected[name]))
            else:
                assert actual[name]==expected[name],(label,name,len(actual[name]),len(expected[name]),actual[name][:1],expected[name][:1])
        results.append(dict(case=label,counts={name:len(rows) for name,rows in actual.items()},digest=digest(actual)))
        print(json.dumps(results[-1]),flush=True)
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))


if __name__=='__main__': main()
