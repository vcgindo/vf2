"""GIT prepared reader scope/count/page regression proof."""
import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.presentation.fixture import binding
from mta.presentation.context import permission_catalogue,scope,PublicationUnavailable
from mta.presentation.bpr_sql import _projected_attributes
from mta.presentation.planning_git_sql import grid
from mta.runtime.models import PlanningGitMasterRow,PlanningGitOccurrence
from mta.presentation.permissions import permission_multiplicity
from mta.serialization import digest


def main():
    run,source=binding();catalogue=permission_catalogue();attrs,_=_projected_attributes(run)
    payload={k:[r['id'] for r in catalogue[t]['records']] for k,t in [('product_permissions','products'),('location_permissions','locations')]}
    products,locations=scope(payload,attributes=attrs)
    masters={(r['rationed_ordinal'],r['standard_ordinal']):r for r in PlanningGitMasterRow.objects.filter(run=run).values()}
    expected={kind:0 for kind in ('parent','child')}
    for occurrence in PlanningGitOccurrence.objects.filter(run=run).values():
        row=masters[occurrence['rationed_ordinal'],occurrence['standard_ordinal']]
        for kind,field in [('parent','WhCode'),('child','ParentWhCode')]:
            expected[kind]+=permission_multiplicity(products,row['SKUCode'])*permission_multiplicity(locations,row[field])
    for kind in expected:
        actual=grid(run,dict(payload,type=kind),count=True)
        assert actual[0]['locationwise']==expected[kind]
        if kind=='child':assert actual[0]['transporterwise']==0
    all_rows=grid(run,dict(payload,type='parent'))['data']
    assert len(all_rows)==expected['parent']
    assert [r['rn'] for r in all_rows]==list(range(1,len(all_rows)+1))
    page=grid(run,dict(payload,type='parent',paginationParameter=dict(pageNumber=2,recordsPerPage=50)))['data']
    assert page==all_rows[50:100]
    assert all(r['transit']==[] and r['AgeingOrder'] is None for r in all_rows)
    assert grid(run,dict(type='parent',product_permissions=[],location_permissions=[]))['data']==[]
    try:grid(run,dict(payload,type='child'))
    except PublicationUnavailable as e:assert '207/8120' in str(e)
    else:raise AssertionError('invalid combined child SQL was hidden')
    from django.core.management import call_command
    call_command('check');call_command('makemigrations',check=True,dry_run=True);call_command('migrate',plan=True)
    assert binding()[1]==source
    print(json.dumps(dict(status='PASS',counts=expected,parent_rows=len(all_rows),parent_digest=digest(all_rows),
                         qualification='Scope/page/internal values only; independent legacy wire comparison still required')))

if __name__=='__main__':main()
