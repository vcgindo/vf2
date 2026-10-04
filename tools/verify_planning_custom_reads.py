"""Exact custom responses and inherited ambiguity denial on retained inputs."""
import os,sys,json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation.fixture import binding
from mta.presentation.context import permission_catalogue,PublicationUnavailable
from mta.presentation.selective import image_rows
from mta.presentation.excess_read import custom_grid as excess_custom
from mta.presentation.fulfillment_read import custom_grid as fulfillment_custom
from mta.presentation.planning_custom_sql import custom_grid
from mta.runtime.models import ExcessInventoryRow,FulfillmentSummaryRow
from mta.serialization import storage,digest


def main():
    run,source=binding()
    importer={name:image_rows(run,'closing/importer/'+name) for name in ('SkuAttributeData','LocationAttributeData','SiteDescriptionTbl')}
    nms=image_rows(run,'closing/consumer_context/NMSAllItems')
    standards=image_rows(run,'closing/dbm/SKULocStandardAttributes')
    catalogue=permission_catalogue()
    broad={key:[r['id'] for r in catalogue[kind]['records']] for key,kind in
           (('product_permissions','products'),('location_permissions','locations'))}
    results=[]
    for family,model,reference in [('excess',ExcessInventoryRow,excess_custom),('fulfillment',FulfillmentSummaryRow,fulfillment_custom)]:
        qs=model.objects.filter(run=run)
        if family=='excess':qs=qs.filter(ReportDate=run.business_date)
        fields=[f.name for f in model._meta.local_fields if f.name not in ('id','run','ordinal')]
        facts=storage(list(qs.order_by('ordinal').values(*fields)))
        context=SimpleNamespace(run=run,business_date=run.business_date,output={'ClosingState':[{'importer':importer}]},
                                rows=facts if family=='excess' else {'summary':facts},nms=nms,standards=standards)
        leaf={}
        for key,kind,table,code,prefix,selected in (
                ('product_permissions','products','SkuAttributeData','SKUCode','SL',facts[0]['SKUCode']),
                ('location_permissions','locations','LocationAttributeData','WHCode','LL',facts[0]['WhCode'])):
            attr=next(r for r in importer[table] if r[code]==selected)
            leaf[key]=[next(r['id'] for r in catalogue[kind]['records'] if all(r['level_'+str(i)]==attr[prefix+str(i)] for i in (1,2,3)))]
        for label,permissions,paging in [('full',broad,None),('page2',broad,(2,50)),('restricted',leaf,(1,50)),
                                         ('empty',{'product_permissions':[],'location_permissions':[]},None),('past-end',broad,(99999,50))]:
            payload=dict(**permissions,filters=[])
            try:expected=reference(context,payload,paging)
            except PublicationUnavailable as exc:expected=str(exc)
            try:actual=custom_grid(run,payload,paging,family=family)
            except PublicationUnavailable as exc:actual=str(exc)
            assert actual==expected,(family,label,str(actual)[:500],str(expected)[:500])
            results.append(dict(family=family,case=label,rows=len(actual['data']) if isinstance(actual,dict) else None,
                                unavailable=actual if isinstance(actual,str) else None,digest=digest(actual)))
    from django.core.management import call_command
    call_command('check');call_command('makemigrations',check=True,dry_run=True);call_command('migrate',plan=True)
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))

if __name__=='__main__':main()
