"""Exact separate Expedite count grain against source reference.

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
from mta.presentation.expedite_views import counts as reference
from mta.presentation.excess_filters import predicate
from mta.presentation.planning_expedite_sql import counts
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
    output={'ClosingState':[dict(importer=importer,dbm={'SKULocStandardAttributes':standards})]}
    results=[]
    cases=[('broad',broad,{}),('leaf',leaf,{}),('empty',dict(product_permissions=[],location_permissions=[]),{})]
    if '--filters-only' in sys.argv:
        parent=next(row for row in importer['LocationAttributeData'] if row['WHCode']==selected['ParentWhCode'])
        cases=[(label,broad,filters) for label,filters in [
            ('sku',{'productFilter':{'filters':[{'attributeName':'sku','value':selected['SKUCode']}]}}),
            ('stock',{'availabilityFilter':{'filters':[{'attributeName':'stock','operator':'greaterthan','value':'0'}]}}),
            ('children',{'supplyChainFilter':{'filters':[{'attributeName':'forchildren','value':parent['LocationType']}]}}),
            ('custom',{'availabilityFilter':{'filters':[]},'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}})]]
    for direction in ('parent','child'):
        for label,permissions,filters in cases:
            payload=dict(**permissions,type=direction,filters=filters)
            products,locations=scope(payload,attributes=importer)
            expected=reference(output,facts,direction,products=products,locations=locations,matches=predicate(payload,importer))
            actual=counts(run,payload)
            assert actual==expected,(direction,label,actual,expected)
            results.append(dict(direction=direction,case=label,values=actual))
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))

if __name__=='__main__':main()
