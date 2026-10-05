"""Complete scoped prepared chart datasets against the existing source reader.

This is internal aggregate/formatter proof, not legacy wire or browser acceptance.
"""
import os, sys, json, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation.fixture import binding
from mta.presentation.selective import image_rows
from mta.presentation.context import permission_catalogue,scope
from mta.presentation.expedite_charts import queries as reference,response
from mta.presentation.planning_expedite_chart_sql import queries
from mta.presentation.planning_expedite_transit_preparation import PICK_TABLE
from mta.runtime.models import ExpediteRow,PlanningBprMasterRow
from mta.serialization import digest
from django.db import connection
from tools.export_planning_expedite_charts import scope_cases


def main():
    run,source=binding()
    importer={name:image_rows(run,'closing/importer/'+name) for name in
              ('SkuAttributeData','LocationAttributeData','SkuLocAttributeData','SKUDescriptionTbl','SiteDescriptionTbl')}
    facts=list(ExpediteRow.objects.filter(run=run).order_by('ordinal').values())
    masters=list(PlanningBprMasterRow.objects.filter(run=run).order_by('source_ordinal').values())
    output={'ClosingState':[{'importer':importer,'bpr':{'BPRMaster':masters}}]}
    with connection.cursor() as c:
        c.execute('SELECT * FROM '+PICK_TABLE+' ORDER BY vf_source_ordinal')
        names=[col[0] for col in c.description]
        pick=[dict(zip(names,row)) for row in c.fetchall()]
    catalogue=permission_catalogue()
    results=[]
    cases=scope_cases(run,importer,catalogue)+[('empty',dict(product_permissions=[],location_permissions=[]))]
    for name,permissions in cases:
        if len(sys.argv)>1 and name not in sys.argv[1:]:continue
        payload=dict(**permissions,filters={})
        products,locations=scope(payload,attributes=importer)
        for kind in ('parent','child'):
            expected=reference(output,facts,pick,kind,products=products,locations=locations)
            started=time.perf_counter()
            actual=queries(run,payload,kind)
            seconds=time.perf_counter()-started
            if name=='leaf' and kind=='parent':assert actual['critical'], 'Restricted case must contain critical data'
            for family in expected:
                assert actual[family]==expected[family],(name,kind,family,len(actual[family]),len(expected[family]),
                    next(((a,b) for a,b in zip(actual[family],expected[family]) if a!=b),None))
            # Preserve ambiguous-source denial; a formatter check does not
            # authorize the April parent presentation exception.
            try:
                expected_response=response(expected,kind,receiving_own_label=kind=='parent')
            except ValueError as exc:
                try:response(actual,kind,receiving_own_label=kind=='parent')
                except ValueError as actual_exc:assert str(exc)==str(actual_exc)
                else:raise AssertionError('Source ambiguity was not preserved')
                disposition=str(exc)
            else:
                assert response(actual,kind,receiving_own_label=kind=='parent')==expected_response
                disposition='MATCH'
            results.append(dict(case=name,kind=kind,rows={k:len(v) for k,v in actual.items()},
                                digest=digest(actual),seconds=seconds,formatter=disposition))
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',results=results,source_digest=source)))


if __name__=='__main__':main()
