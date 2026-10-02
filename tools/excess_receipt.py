"""Independent retained SQL proof of the selected Excess normal/custom consumers."""
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import gzip
import pyodbc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha, iter_rows
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_excess_readmodel import PLAN, PLAN_SHA, CHART, CHART_SHA, EXCESS, EXCESS_SHA, literals, selected_queries
from parity.verify_rrr_consumer import auth_ctes, supplement_temp_hierarchy, temp_rows, PERMISSION_SHA, AUTH_SOURCE, AUTH_SHA
from parity.verify_rrr_export import call


def source_failure(case_id, message):
    name, kind = case_id.removeprefix('filter-').rsplit('-', 1)
    columns = {'missing-category':'category', 'category-code':'category', 'missing-availability':'availability',
        'missing-coverage':'coverage', 'missing-color-count':'redCount', 'red-positive-count':'redCount',
        'invalid-hierarchy-column':'sl9', 'green-count-zero':'greenCount', 'black-red-positive-count':'BlackCount'}
    if name in columns:
        code, detail = '207', "Invalid column name '"+columns[name]+"'"
    elif name in ('missing-color-age', 'black-red-age', 'green-age'):
        code, detail = '4104', '"btd.D90" could not be bound'
    elif name == 'invalid-operator':
        code, detail = '102', "Incorrect syntax near ')'"
    elif name == 'black-red-invalid-multi-column':
        code, detail = ('102', "Incorrect syntax near '('") if kind == 'grid' else ('156', "Incorrect syntax near the keyword 'NULLIF'")
    else:
        raise AssertionError('Unexpected source failure: '+case_id)
    assert '('+code+')' in message and detail in message, (case_id, message)
    return dict(code=code, detail=detail)


def custom_query():
    assert file_sha(PLAN) == PLAN_SHA
    method = PLAN.read_text().split('public responseMessage GetCustomGridData(', 1)[1]
    branch = method.split('if (category == "excessInventory")', 1)[1].split('if (category == "orderFulfillment")', 1)[0]
    query = literals(branch) + ' for json path) data'
    for old, new in (('.dbo.NMSAllItems', '#NMS'), ('.dbo.SKULocStandardAttributes', '#Standard'),
            ('ExcessInventoryDetails', '#Excess'), ('SiteDescriptionTbl', '#LocDesc'), ('LastBatchRunTbl', '#LastDate')):
        query = query.replace(old, new)
    config = [dict(header=h, colCode=c, colPosition=int(p)) for h, c, p in re.findall(
        r'header = "([^"]+)",\s*colCode = "([^"]+)",\s*colPosition = (\d+)', method)]
    assert len(config) == 46 and query.startswith(' select ( select * from')
    return query, config


def roster():
    cases = []
    for name, products, locations in (('root', [71001], [72001]), ('leaf', [71002], [72003]),
            ('other-leaf', [71003], [72004]), ('overlapping', [71001, 71002], [72001, 72003])):
        payload = dict(category='excessInventory', type='review', filters={},
            product_permissions=products, location_permissions=locations,
            paginationParameter=dict(pageNumber=1, recordsPerPage=10000))
        for kind, route in (('grid', 'GetPlanningDataGrid'), ('count', 'GetPlanningDataGridCount'),
                            ('custom', 'GetPlanningDataCustom')):
            cases.append(dict(id=name+'-'+kind, route=route, payload=deepcopy(payload), kind=kind))
    base = cases[0]['payload']
    for kind, route in (('grid', 'GetPlanningDataGrid'), ('custom', 'GetPlanningDataCustom')):
        for page in (1, 2, 18):
            payload = deepcopy(base)
            payload['paginationParameter'] = dict(pageNumber=page, recordsPerPage=5)
            cases.append(dict(id=f'{kind}-page-{page}', route=route, payload=payload, kind=kind))
        for label, paging in (('unpaged', None), ('zero-page', dict(pageNumber=0, recordsPerPage=5))):
            payload = deepcopy(base)
            payload['paginationParameter'] = paging
            cases.append(dict(id=kind+'-'+label, route=route, payload=payload, kind=kind))
    for name, filters in (('ignored', {'productFilter': {'filters': [dict(attributeName='sku', value='ABSENT')]}}),
                          ('array', [])):
        payload = deepcopy(base); payload['filters'] = filters
        cases.append(dict(id='custom-filters-'+name, route='GetPlanningDataCustom', payload=payload, kind='custom'))
    retained = json.loads(Path('D:/freshvcf-build/evidence/f3-btr-filters-modern-001/cases.json').read_text())['cases']
    for old in retained:
        if not old['payload'].get('filters'):
            continue
        for kind, route in (('grid', 'GetPlanningDataGrid'), ('count', 'GetPlanningDataGridCount')):
            case = dict(id='filter-'+old['id']+'-'+kind, kind=kind, route=route, payload=deepcopy(old['payload']))
            case['payload'].update(category='excessInventory', type='review')
            cases.append(case)
            if 'customAttributeFilter' in case['payload']['filters']:
                opened = deepcopy(case); opened['id'] += '-gate-open'
                opened['payload']['filters']['productFilter'] = {'filters': []}
                cases.append(opened)
    return cases


def main():
    target = Path(sys.argv[1]).resolve()
    assert target.parent == Path('D:/freshvcf-build/evidence').resolve()
    target.mkdir(exist_ok=False)
    result = dict(status='FAILED', engine_replays=0, persistent_writes=False, serving_changes=False, checks=[])
    try:
        cases = roster()
        (target/'requests.json').write_text(json.dumps(dict(cases=cases), indent=2))
        runtime = json.loads(subprocess.check_output(['docker', 'inspect', 'freshvcf-preview-mta-1'], text=True))[0]
        command = ['docker','run','--rm','--name','freshvcf-stage2-excess','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v','F:/freshvcf:/app:ro',
            '-v','D:/freshvcf-build/evidence:/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_', 'MTA_')): command += ['-e', value]
        for mount in runtime['Mounts']:
            if mount['Destination'] != '/app': command += ['-v', mount['Source']+':'+mount['Destination']+':ro']
        command += [runtime['Image'], 'python', 'tools/excess_probe.py', '/evidence/'+target.name+'/requests.json']
        if len(sys.argv) > 2 and sys.argv[2] != '-':
            parent = Path(sys.argv[2]).resolve()
            receipt = json.loads((parent/'receipt.json').read_text())
            assert file_sha(parent/'modern.log') == receipt['files']['modern.log']
            assert (parent/'requests.json').read_bytes() == (target/'requests.json').read_bytes()
            assert all(file_sha(ROOT/name) == sha for name, sha in receipt['sources'].items()
                if name != 'tools/excess_receipt.py')
            modern = json.loads((parent/'modern.log').read_text())
            result['modern_reused_from'] = dict(path=str(parent), receipt_sha256=file_sha(parent/'receipt.json'))
        else:
            modern = json.loads(call(command, target/'modern.log'))
        observed = {row['id']: row for row in modern['observations']}
        failures = {name:row['body'] for name,row in observed.items() if row['status'] not in (200, 503)}
        assert not failures, failures
        filters = {}
        (target/'filter-requests.json').write_text(json.dumps(dict(cases=[c for c in cases if c['kind'] != 'custom'])))
        for kind, report in (('grid', 'ExcessGrid'), ('count', 'ExcessCount')):
            call(['pwsh', '-NoProfile', '-File', str(ROOT/'parity/invoke_legacy_rrr_filters.ps1'),
                '-InputPath', str(target/'filter-requests.json'), '-OutputPath', str(target/(kind+'-filters.json')),
                '-Report', report], target/(kind+'-filters.log'))
            filters[kind] = {r['id']:r for r in json.loads((target/(kind+'-filters.json')).read_text())['cases']}
        permission = Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(permission) == PERMISSION_SHA
        catalogue = json.loads(permission.read_text())
        print('Modern observations complete; loading independent retained inputs', flush=True)
        if len(sys.argv) > 3:
            handoff = Path(sys.argv[3]).resolve()
            parent_receipt = json.loads((handoff/'receipt.json').read_text())
            assert file_sha(handoff/'legacy-input-handoff.json.gz') == parent_receipt['files']['legacy-input-handoff.json.gz']
            with gzip.open(handoff/'legacy-input-handoff.json.gz', 'rt', encoding='utf-8') as stream:
                retained = json.load(stream)
            legacy, provenance = retained['values'], retained['provenance']
            result['legacy_reused_from'] = dict(path=str(handoff), receipt_sha256=file_sha(handoff/'receipt.json'))
        else:
            legacy, provenance = terminal_inputs()
            # Exact independent handoff for diagnosis, never modern input.
            with gzip.open(target/'legacy-input-handoff.json.gz', 'wt', encoding='utf-8') as stream:
                json.dump(dict(provenance=provenance, values=legacy), stream)
        assert modern['run'] == provenance['modern_run'] and modern['output_digest'] == provenance['modern_output_digest']
        assert file_sha(EXCESS/'receipt.json') == EXCESS_SHA
        producer = json.loads((EXCESS/'receipt.json').read_text())
        assert producer['legacy_source'] == provenance and producer['status'] == 'PASS_CURRENT_DAY_EXCESS_REPORT'
        excess = list(iter_rows(EXCESS/'legacy-excess.jsonl.gz', producer['legacy_rows']))
        normal_sql, count_sql, _, normal_config = selected_queries()
        custom_sql, custom_config = custom_query()
        os.environ['VFTEST_PROFILE'] = 'fresh'
        expected = {}
        with exclusive_replay(), connection('VFTEST_BPR') as db:
            dynamic = db.execute("SELECT Col_Code FROM ui_ReportConfigurations WHERE reportname='adminbpr' AND Visible=1 AND (Col_Code LIKE 'SKUAttr%' OR Col_Code LIKE 'LocAttr%' OR Col_Code LIKE 'SKULocAttr%')").fetchall()
            assert not dynamic, 'Selected custom attributes changed'
            temp_rows(db, '#Excess', 'dbo.ExcessInventoryDetails', excess)
            for name, table in (('#Sku','SkuAttributeData'), ('#Loc','LocationAttributeData'),
                    ('#Pair','SkuLocAttributeData'), ('#SkuDesc','SKUDescriptionTbl'), ('#LocDesc','SiteDescriptionTbl')):
                temp_rows(db, name, 'dbo.'+table, legacy['closing']['importer'][table])
            temp_rows(db, '#NMS', 'VFTEST_Importer.dbo.NMSAllItems', legacy['closing']['consumer_context']['NMSAllItems'])
            result['native_nms_rows'] = len(legacy['closing']['consumer_context']['NMSAllItems'])
            temp_rows(db, '#Standard', 'VFTEST_Importer.dbo.SKULocStandardAttributes', legacy['closing']['dbm']['SKULocStandardAttributes'])
            temp_rows(db, '#LastDate', 'dbo.LastBatchRunTbl', legacy['late']['LastBatchRunTbl'])
            # Scope attributes only; do not fill native NMSAllItems hierarchy.
            supplement_temp_hierarchy(db, catalogue)
            for case in cases:
                db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions')
                payload, kind = case['payload'], case['kind']
                query = count_sql if kind == 'count' else custom_sql if kind == 'custom' else normal_sql
                if kind in ('grid', 'count'):
                    f = filters[kind][case['id']]
                    join = f['sql_join_filter'].replace('LocationAttributeData', '#Loc')
                    query = query.replace('#Excess a ', '#Excess a '+join+' ')
                    if f['sql_filter']:
                        if kind == 'grid':
                            query = query.replace(')a order by RN', ' and '+f['sql_filter']+')a order by RN')
                        else:
                            query += ' and '+f['sql_filter']
                paging = payload.get('paginationParameter')
                bounds = ''
                if paging is not None:
                    page, size = (paging[k] for k in ('pageNumber','recordsPerPage'))
                    bounds = f' where RN between ({page}-1)*{size}+1 and ({page}*{size}) '
                if kind == 'grid': query = query.replace(')a order by RN', ')a '+bounds+' order by RN')
                if kind == 'custom': query = query.replace(' for json path) data', bounds+' for json path) data')
                query = auth_ctes(db, catalogue, payload) + query
                (target/(case['id']+'.sql')).write_text(query)
                try:
                    value = db.execute(query).fetchone()[0]
                except pyodbc.Error as exc:
                    message = str(exc)
                    source_failure(case['id'], message)
                    assert observed[case['id']]['status'] == 503, (case['id'], message, observed[case['id']])
                    result['checks'].append(dict(id=case['id'], status='LEGACY_FLAW_NOT_PARITY',
                        legacy_error=message, modern_error=observed[case['id']]['body']))
                    continue
                assert observed[case['id']]['status'] == 200, (case['id'], observed[case['id']]['body'])
                if kind != 'count':
                    # SQL scalar empty JSON is DBNull. Custom's ToString is
                    # empty => List<string>(); normal helper null => empty list.
                    value = dict(data=json.loads(value) if value else [], uiConfig=custom_config if kind == 'custom' else normal_config)
                expected[case['id']] = value
                actual = observed[case['id']]['body']['data']
                delta = differences(value, actual, '/'+case['id'])
                result['checks'].append(dict(id=case['id'], status='PASS' if value == actual and not delta else 'FAIL',
                    complete_ordered_body_equal=value == actual, differences=delta,
                    rows=value if kind == 'count' else len(value['data']), query_count=observed[case['id']]['query_count'],
                    modern_seconds=observed[case['id']]['seconds']))
        (target/'legacy-responses.json').write_text(json.dumps(expected, indent=2))
        failed = [r for r in result['checks'] if r['status'] not in ('PASS', 'LEGACY_FLAW_NOT_PARITY')]
        assert not failed, failed
        assert file_sha(AUTH_SOURCE) == AUTH_SHA
        result.update(status='PASS_SELECTED_EXCESS_NORMAL_CUSTOM_SQL_NOT_JOURNEY_ACCEPTANCE', provenance=provenance,
            producer_receipt_sha256=EXCESS_SHA, selected_dynamic_columns=[],
            source_hashes={str(PLAN): PLAN_SHA, str(CHART): CHART_SHA, str(AUTH_SOURCE): AUTH_SHA},
            qualification='Complete retained SQL cells/config/order and actual DLL filter invocation; ExecuteScalar deserialization source verified. Private PostgreSQL API, not gateway/browser or matched performance.')
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['sources'] = {name:file_sha(ROOT/name) for name in ('mta/presentation/excess_read.py',
            'mta/presentation/excess_filters.py', 'mta/presentation/excess_views.py',
            'mta/presentation/views.py', 'mta/presentation/urls.py', 'parity/invoke_legacy_rrr_filters.ps1',
            'tools/excess_probe.py', 'tools/excess_receipt.py')}
        result['files'] = {p.name:file_sha(p) for p in target.iterdir() if p.is_file() and p.name != 'receipt.json'}
        (target/'receipt.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(dict(status=result['status'], error=result.get('error'))), flush=True)


if __name__ == '__main__': main()
