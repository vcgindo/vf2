"""Complete child grid values/types/order against source reference.

Legacy wire and browser performance remain separate gates.
"""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation.fixture import binding,bpr_ancillary
from mta.presentation.context import permission_catalogue,scope
from mta.presentation.selective import image_rows
from mta.presentation.expedite_child import child_rows
from mta.presentation.excess_filters import predicate
from mta.presentation.planning_expedite_sql import child_grid
from mta.runtime.models import ExpediteRow
from mta.serialization import digest


def main():
    run,source = binding()
    importer = {name:image_rows(run,'closing/importer/'+name) for name in
                ('SkuAttributeData','LocationAttributeData','SkuLocAttributeData','SKUDescriptionTbl','SiteDescriptionTbl')}
    standards = image_rows(run,'closing/dbm/SKULocStandardAttributes')
    facts = list(ExpediteRow.objects.filter(run=run).order_by('ordinal').values())
    catalogue = permission_catalogue()
    broad = {key:[r['id'] for r in catalogue[kind]['records']] for key,kind in
             (('product_permissions','products'),('location_permissions','locations'))}
    selected = next(row for row in facts if row['RationedQty']>0)
    leaf = {}
    for key,kind,table,code,prefix,value in (
        ('product_permissions','products','SkuAttributeData','SKUCode','SL',selected['SKUCode']),
        ('location_permissions','locations','LocationAttributeData','WHCode','LL',selected['ParentWhCode'])):
        attr = next(row for row in importer[table] if row[code]==value)
        leaf[key] = [next(row['id'] for row in catalogue[kind]['records'] if all(row['level_'+str(i)]==attr[prefix+str(i)] for i in (1,2,3)))]
    cases = [('full',broad,None,{}),('page2',broad,(2,50),{}),('leaf',leaf,(1,100000),{}),
             ('empty',dict(product_permissions=[],location_permissions=[]),(1,50),{}),
             ('past-end',broad,(99999,50),{}),
             ('sku',broad,(1,100000),dict(productFilter=dict(filters=[dict(attributeName='sku',value=selected['SKUCode'])])))]
    if '--filters-only' in sys.argv:
        loc = next(row for row in importer['LocationAttributeData'] if row['WHCode']==selected['WhCode'])
        filter_cases = [
            ('stock',{'availabilityFilter':{'filters':[{'attributeName':'stock','operator':'greaterthan','value':'0'}]}}),
            ('tags',{'availabilityFilter':{'filters':[{'attributeName':'pipo,seasonality','value':'NPI'}]}}),
            ('location-type',{'supplyChainFilter':{'filters':[{'attributeName':'forlocation','value':loc['LocationType']}]}}),
            ('children',{'supplyChainFilter':{'filters':[{'attributeName':'forchildren','value':loc['LocationType']}]}}),
            ('hierarchy',{'locationFilter':{'filters':[{'attributeName':'l1','operator':'equalto','value':loc['LL1']}]}}),
            ('custom-ignored',{'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}}),
            ('custom-active',{'availabilityFilter':{'filters':[]},'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}})]
        cases = [(label,broad,(1,100000),filters) for label,filters in filter_cases]
    if '--export-and-parent-filter' in sys.argv:
        parent = next(row for row in importer['LocationAttributeData'] if row['WHCode']==selected['ParentWhCode'])
        cases = [('unpaged',broad,None,{}),('children-positive',broad,None,
            {'supplyChainFilter':{'filters':[{'attributeName':'forchildren','value':parent['LocationType']}]}})]
    results = []
    for label,permissions,paging,filters in cases:
        payload = dict(**permissions,filters=filters,paginationParameter=None if paging is None else dict(pageNumber=paging[0],recordsPerPage=paging[1]))
        products,locations = scope(payload,attributes=importer)
        expected = child_rows(facts,importer,standards,products=products,locations=locations,
                              paging=paging,matches=predicate(payload,importer),business_date=run.business_date,requests=[],transit=[])
        actual = child_grid(run,payload)['data']
        for name in expected:
            assert actual[name]==expected[name],(label,name,len(actual[name]),len(expected[name]),actual[name][:1],expected[name][:1])
        results.append(dict(case=label,counts={name:len(rows) for name,rows in actual.items()},digest=digest(actual)))
        print(json.dumps(results[-1]),flush=True)
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))


if __name__=='__main__': main()
