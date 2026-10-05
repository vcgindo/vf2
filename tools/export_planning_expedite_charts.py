"""Export prepared chart datasets and exact permission bags for retained SQL proof."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation.fixture import binding
from mta.presentation.context import permission_catalogue,scope
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.planning_expedite_chart_sql import queries
from mta.runtime.models import ExpediteRow


def scope_cases(run,importer,catalogue):
    broad={key:[r['id'] for r in catalogue[kind]['records']] for key,kind in
           (('product_permissions','products'),('location_permissions','locations'))}
    selected=ExpediteRow.objects.filter(run=run,RationedQty__gt=0).order_by('ordinal').first()
    leaf={}
    for key,kind,table,code,prefix,value in (
        ('product_permissions','products','SkuAttributeData','SKUCode','SL',selected.SKUCode),
        ('location_permissions','locations','LocationAttributeData','WHCode','LL',selected.WhCode)):
        attr=next(row for row in importer[table] if row[code]==value)
        leaf[key]=[next(row['id'] for row in catalogue[kind]['records'] if all(
            row['level_'+str(i)]==attr[prefix+str(i)] for i in (1,2,3)))]
    return [('broad',broad),('leaf',leaf)]


def main():
    run,source=binding()
    importer,manifest=_projected_attributes(run)
    assert manifest is None
    catalogue=permission_catalogue()
    cases=[]
    for name,permissions in scope_cases(run,importer,catalogue):
        payload=dict(**permissions,filters={})
        products,locations=scope(payload,attributes=importer)
        cases.append(dict(name=name,payload=payload,products=dict(products.multiplicities),
            locations=dict(locations.multiplicities),charts={kind:queries(run,payload,kind) for kind in ('parent','child')}))
    assert binding()[1]==source
    print(json.dumps(dict(run=str(run.pk),business_date=str(run.business_date),source_digest=source,cases=cases)))


if __name__=='__main__':main()
