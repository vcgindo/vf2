"""Complete ordered prepared-grid responses against retained Python consumers."""
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.presentation import fixture
from mta.presentation.context import permission_catalogue
from mta.presentation.planning_grid_preparation import DIMENSIONS
from mta.presentation.planning_grid_sql import read_grid
from mta.presentation.selective import image_rows
from mta.presentation.views import scoped
from mta.presentation.excess_views import joined_rows as excess_rows
from mta.presentation.fulfillment_views import joined_rows as fulfillment_rows, detail_aliases
from mta.presentation.excess_grid import excess_grid_rows
from mta.presentation.fulfillment_grid import fulfillment_grid_rows
from mta.presentation import excess_filters, fulfillment_filters
from mta.runtime.models import ExcessInventoryRow, FulfillmentSummaryRow, FulfillmentDetailRow
from mta.serialization import storage, digest


def main():
    run, source = fixture.binding()
    importer = {name: image_rows(run, 'closing/importer/' + name) for _, name in DIMENSIONS}
    output = {'ClosingState': [{'importer': importer}]}
    catalogue = permission_catalogue()
    broad = {key: [r['id'] for r in catalogue[kind]['records']] for key, kind in
             (('product_permissions', 'products'), ('location_permissions', 'locations'))}
    leaf = {key: [next(r['id'] for r in catalogue[kind]['records'] if r['level_3'] is not None)]
            for key, kind in (('product_permissions', 'products'), ('location_permissions', 'locations'))}
    def records(model, **filters):
        fields = [f.name for f in model._meta.fields if f.name not in ('id','run','ordinal')]
        return storage(list(model.objects.filter(run=run, **filters).order_by('ordinal').values(*fields)))
    details = detail_aliases(records(FulfillmentDetailRow))
    results = []
    for family, model in [('excess', ExcessInventoryRow), ('fulfillment', FulfillmentSummaryRow)]:
        facts = records(model, **({'ReportDate':run.business_date} if family == 'excess' else {}))
        sample = facts[0]
        from mta.presentation.rrr import sql_key
        leaf = {}
        for permission_key, kind, table, code, prefix, selected_code in (
                ('product_permissions','products','SkuAttributeData','SKUCode','SL',sample['SKUCode']),
                ('location_permissions','locations','LocationAttributeData','WHCode','LL',sample['WhCode'])):
            attr = next(r for r in importer[table] if sql_key(r[code]) == sql_key(selected_code))
            leaf[permission_key] = [next(r['id'] for r in catalogue[kind]['records'] if
                all(sql_key(r['level_'+str(i)]) == sql_key(attr[prefix+str(i)]) for i in (1,2,3)))]
        cases = [('broad', broad, {}, None), ('leaf', leaf, {}, (1,50)),
                 ('empty', {'product_permissions':[], 'location_permissions':[]}, {}, (1,50)),
                 ('page2', broad, {}, (2,50)),
                 ('norm', broad, {'availabilityFilter':{'filters':[{'attributeName':'norm','operator':'greaterthan','value':'0'}]}}, (1,50)),
                 ('sku', broad, {'productFilter':{'filters':[{'attributeName':'sku','value':sample['SKUCode']}] }}, None),
                 ('location', broad, {'locationFilter':{'filters':[{'attributeName':'location','value':sample['WhCode']}] }}, None)]
        loc = next(r for r in importer['LocationAttributeData'] if r['WHCode'] == sample['WhCode'])
        cases += [('location-type',broad,{'supplyChainFilter':{'filters':[{'attributeName':'forlocation','value':loc['LocationType']}]}},(1,50)),
                  ('children',broad,{'supplyChainFilter':{'filters':[{'attributeName':'forchildren','value':loc['LocationType']}]}},(1,50)),
                  ('hierarchy',broad,{'locationFilter':{'filters':[{'attributeName':'l1','operator':'equalto','value':loc['LL1']}]}},(1,50)),
                  ('custom-null',broad,{'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}},(1,50))]
        if family == 'fulfillment':
            cases += [('coverage',broad,{'coverageFilter':{'filters':[{'attributeName':'coverage','value':sample['Coverage']}]}},(1,50))]
        cases += [('custom-active',broad,{'availabilityFilter':{'filters':[]},'customAttributeFilter':{'filters':[{'attributeName':'skulocattr1','operator':'hasnovalue','value':''}]}},(1,50))]
        for label, permissions, filters, paging in cases:
            payload = dict(**permissions, filters=filters)
            predicate = (excess_filters if family == 'excess' else fulfillment_filters).predicate(payload, importer)
            expected = excess_rows(output, facts, run.business_date, predicate=predicate) if family == 'excess' else fulfillment_rows(output, facts, predicate=predicate)
            expected = scoped(expected,payload,'WHCode',attributes=importer,preserve_join_multiplicity=True)
            expected_count = len(expected)
            expected = excess_grid_rows(expected) if family == 'excess' else fulfillment_grid_rows(expected,details)
            if paging:
                page,size=paging
                expected=[r for r in expected if (page-1)*size+1<=r['rn']<=page*size]
            started=time.monotonic()
            actual=read_grid(run,payload,family=family,paging=paging)
            actual_count=read_grid(run,payload,family=family,paging=paging,count=True)
            assert actual_count==expected_count,(family,label,'count',actual_count,expected_count)
            if actual != expected:
                first=next(((i,a,b) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None)
                raise AssertionError((family,label,len(actual),len(expected),first))
            result=dict(family=family,case=label,count=actual_count,rows=len(actual),digest=digest(actual),seconds=time.monotonic()-started)
            results.append(result)
            print(json.dumps(result),flush=True)
    from django.core.management import call_command
    call_command('check')
    call_command('makemigrations',check=True,dry_run=True)
    call_command('migrate',plan=True)
    assert fixture.binding()[1]==source
    print(json.dumps(dict(status='PASS',cases=results,source_digest=source)))

if __name__=='__main__':main()
