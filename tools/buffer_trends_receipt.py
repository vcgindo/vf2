"""Independent deployed graph filter/SQL/.NET proof from retained terminal facts."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import pyodbc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parity.history_queries import buffer_query, CTE, SOURCES
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_history_consumers import rows
from parity.verify_rrr_consumer import auth_ctes, supplement_temp_hierarchy, temp_rows, PERMISSION_SHA
from parity.verify_rrr_export import call


def assert_source_failure(case_id, message):
    name = case_id.rsplit('-', 1)[0]
    columns = {'positive-stock':'stock', 'git-zero':'git', 'pipeline-color':'pic',
        'physical-color':'ohic', 'missing-tags':'tags', 'missing-availability':'availability',
        'missing-coverage':'coverage', 'invalid-hierarchy-column':'sl9'}
    if name in columns:
        state, code, detail = '42S22', '207', "Invalid column name '"+columns[name]+"'"
    elif name in ('missing-category','category-code'):
        state, code, detail = '42000', '4104', 'b.category'
    elif name in ('missing-color-age','black-red-age','green-age'):
        state, code, detail = '42000', '4104', 'btd.D90'
    elif name in ('invalid-operator','black-red-invalid-multi-column'):
        state, code, detail = '42000', '102', 'Incorrect syntax'
    else:
        raise AssertionError('Unregistered source failure: '+case_id)
    assert state in message and '('+code+')' in message and detail in message, (case_id,message)


def roster():
    parent = Path('D:/freshvcf-build/evidence/f3-btr-filters-modern-001')
    receipt = json.loads((parent/'receipt.json').read_text())
    assert file_sha(parent/'cases.json') == receipt['cases_sha256']
    retained = json.loads((parent/'cases.json').read_text())['cases']
    cases = []
    for old in retained:
        for kind in ('tech', 'eco'):
            case = dict(id=old['id']+'-'+kind, payload=deepcopy(old['payload']))
            case['payload'].update(bufferTrendType=kind, days=30)
            cases.append(case)
            if 'customAttributeFilter' in case['payload']['filters']:
                gated = deepcopy(case)
                gated['id'] += '-gate-open'
                gated['payload']['filters']['productFilter'] = {'filters': []}
                cases.append(gated)
    for kind in ('tech', 'eco'):
        for days in (1, 7, 12, 60, 90):
            case = deepcopy(cases[0]); case['id'] = f'{kind}-{days}-days'
            case['payload'].update(bufferTrendType=kind, days=days)
            cases.append(case)
        # Source bare OR allows the second colour to bypass preceding predicates.
        for op in ('greaterthan', 'equalto'):
            case = deepcopy(next(c for c in cases if c['id']=='sku-code-'+kind))
            case['id'] = f'{kind}-black-red-precedence-{op}'
            case['payload']['filters']['colorFilter'] = {'filters': [
                dict(attributeName='black/red', operator=op, value='0', type='colorcount')]}
            cases.append(case)
    return cases


def main():
    target = Path(sys.argv[1]).resolve()
    assert target.parent == Path('D:/freshvcf-build/evidence').resolve()
    target.mkdir(exist_ok=False)
    result = dict(status='FAILED', engine_replays=0, persistent_writes=False, serving_changes=False, checks=[])
    try:
        cases = roster()
        (target/'requests.json').write_text(json.dumps(dict(cases=cases), indent=2))
        runtime = json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'], text=True))[0]
        command = ['docker','run','--rm','--name','freshvcf-stage2-buffer-trends','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v','F:/freshvcf:/app:ro',
            '-v','D:/freshvcf-build/evidence:/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_','MTA_')): command += ['-e',value]
        for mount in runtime['Mounts']:
            if mount['Destination'] != '/app': command += ['-v',mount['Source']+':'+mount['Destination']+':ro']
        command += [runtime['Image'],'python','tools/buffer_trends_probe.py','/evidence/'+target.name+'/requests.json']
        modern = json.loads(call(command,target/'modern.log'))
        observed = {row['id']: row for row in modern['observations']}
        call(['pwsh','-NoProfile','-File',str(ROOT/'parity/invoke_legacy_rrr_filters.ps1'),
            '-InputPath',str(target/'requests.json'),'-OutputPath',str(target/'filters.json'),
            '-Report','BufferTrends'],target/'filters.log')
        filters = {row['id']: row for row in json.loads((target/'filters.json').read_text())['cases']}
        permission = Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(permission) == PERMISSION_SHA
        catalogue = json.loads(permission.read_text())
        print('Modern observations complete; loading pinned independent terminal inputs',flush=True)
        legacy, provenance = terminal_inputs()
        assert modern['run'] == provenance['modern_run'] and modern['output_digest'] == provenance['modern_output_digest']
        formatter = dict(selected=[dict(SKUCode='337',WhCode='AG515802')], auth=CTE, graphs={},
            availability=[{a:0 for a in ('B','R','Y','G','BU','W')} for _ in range(90)])
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay(), connection('VFTEST_BTR') as db:
            for table in ('BufferTrendPhysicalInv','BufferTrendDispatch','BufferTrendDates',
                          'SkuAttributeData','LocationAttributeData','SkuLocAttributeData'):
                alias = '#Sku' if table=='SkuAttributeData' else '#Loc' if table=='LocationAttributeData' else '#'+table
                temp_rows(db,alias,'dbo.'+table,legacy['closing']['btr'][table])
            supplement_temp_hierarchy(db,catalogue)
            for case in cases:
                db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions')
                payload = case['payload']; f = filters[case['id']]
                query = buffer_query(payload['bufferTrendType'],payload['days'],sql_filter=f['sql_filter'],
                    sql_join_filter=f['sql_join_filter'],auth_cte=auth_ctes(db,catalogue,payload))
                query = query.replace('#SkuAttributeData','#Sku').replace('#LocationAttributeData','#Loc')
                (target/(case['id']+'.sql')).write_text(query)
                try:
                    cursor = db.execute(query)
                    counts = rows(cursor)
                    assert cursor.nextset(), 'missing graph dates'
                    labels = rows(cursor)
                except pyodbc.Error as exc:
                    # Source invalid identifiers/syntax only, never runtime/resource errors.
                    assert_source_failure(case['id'], str(exc))
                    assert observed[case['id']]['status'] == 503, (case['id'],str(exc),observed[case['id']])
                    result['checks'].append(dict(id=case['id'],status='LEGACY_FLAW_NOT_PARITY',legacy_error=str(exc),
                        modern_error=observed[case['id']]['body']))
                    continue
                assert observed[case['id']]['status'] == 200, (case['id'],observed[case['id']])
                formatter['graphs'][case['id']] = dict(counts=counts,labels=labels)
        (target/'formatter-input.json').write_text(json.dumps(formatter))
        call(['pwsh','-NoProfile','-File',str(ROOT/'parity/invoke_legacy_history.ps1'),
            '-InputPath',str(target/'formatter-input.json'),'-OutputPath',str(target/'legacy-graphs.json')],target/'formatter.log')
        expected = json.loads((target/'legacy-graphs.json').read_text())
        assert expected['input_sha256'] == file_sha(target/'formatter-input.json')
        for name, graph in expected['graphs'].items():
            actual = observed[name]['body']['data']
            delta = differences(graph,actual,'/'+name)
            result['checks'].append(dict(id=name,status='PASS' if graph==actual and not delta else 'FAIL',
                ordered_body_equal=graph==actual, differences=delta, query_count=observed[name]['query_count'],
                modern_seconds=observed[name]['seconds']))
        assert all(row['status'] in ('PASS','LEGACY_FLAW_NOT_PARITY') for row in result['checks'])
        assert len(result['checks']) == len(cases)
        result.update(status='PASS_BUFFER_TRENDS_SQL_DOTNET_WITH_DECLARED_FLAWS',provenance=provenance,
            strict_pass=sum(r['status']=='PASS' for r in result['checks']),
            declared_flaws=sum(r['status']=='LEGACY_FLAW_NOT_PARITY' for r in result['checks']),
            source_sha256=SOURCES['scih'][1],
            qualification='Actual pinned DLL filters, extracted deployed SQL, independent .NET graph formatting; private PostgreSQL API, not authenticated browser or matched performance')
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['sources'] = {name:file_sha(ROOT/name) for name in ('mta/presentation/buffer_trends_sql.py',
            'mta/presentation/views.py','parity/history_queries.py','parity/invoke_legacy_rrr_filters.ps1',
            'tools/buffer_trends_probe.py','tools/buffer_trends_receipt.py')}
        result['files'] = {p.name:file_sha(p) for p in target.iterdir() if p.is_file() and p.name!='receipt.json'}
        (target/'receipt.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(dict(status=result['status'], error=result.get('error'),
            strict=result.get('strict_pass'), flaws=result.get('declared_flaws'))),flush=True)


if __name__ == '__main__': main()
