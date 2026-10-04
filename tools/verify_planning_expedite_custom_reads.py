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
    from mta.presentation.expedite_custom import custom_rows
    from mta.presentation.planning_expedite_custom_sql import custom_grid
    from decimal import Decimal
    nms=image_rows(run,'closing/consumer_context/NMSAllItems')
    bpr=image_rows(run,'reports/bpr/BPR_Table')
    results=[]
    for label,permissions,paging in [('full',broad,None),('page2',broad,(2,50)),('leaf',leaf,None),('empty',dict(product_permissions=[],location_permissions=[]),None),('past-end',broad,(99999,50))]:
        payload=dict(**permissions,filters={},paginationParameter=None if paging is None else dict(pageNumber=paging[0],recordsPerPage=paging[1]))
        products,locations=scope(payload,attributes=importer)
        expected=custom_rows(facts,nms=nms,products=products,locations=locations,paging=paging,bpr_rows=bpr,site_descriptions=importer['SiteDescriptionTbl'],visible_dynamic_attributes=[])
        expected=[{k:float(v) if isinstance(v,Decimal) else v for k,v in row.items()} for row in expected]
        actual=custom_grid(run,payload)['data']
        assert actual==expected,(label,len(actual),len(expected),actual[:1],expected[:1])
        results.append(dict(case=label,rows=len(actual),digest=digest(actual)))
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))

if __name__=='__main__':main()
