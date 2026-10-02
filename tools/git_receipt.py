"""Compare terminal GIT routes with retained independent SQL/DLL contracts."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parity.output_archive import file_sha
from parity.temporal import differences


def main():
    target = Path(sys.argv[1]).resolve()
    assert target.parent == Path('D:/freshvcf-build/evidence').resolve()
    target.mkdir(exist_ok=False)
    result = dict(status='FAILED', engine_replays=0, serving_changes=False, persistent_writes=False)
    try:
        source = target.parent/'f3-stage2-git-filters-001'
        assert file_sha(source/'receipt.json') == 'ef961a530945a1be380a3be6267b2aefb2789beed0f62b0f11d1629c13385469'
        sql = json.loads((source/'receipt.json').read_text())
        for name, sha in sql['file_hashes'].items():
            assert file_sha(source/name) == sha, name
        wire = target.parent/'f3-stage2-git-terminal-wire-001'
        assert file_sha(wire/'receipt.json') == '7a8481ab22525ae8aefa7b275491343249db38e791128edf6791aaa89c0b0575'
        dll = json.loads((wire/'receipt.json').read_text())
        assert sql['legacy_source'] == dll['legacy_source']
        configurations = json.loads((source/'configurations.json').read_text())
        invalid = {'missing-category', 'missing-availability', 'missing-coverage', 'missing-color-count',
                   'missing-color-age', 'invalid-operator', 'invalid-hierarchy-column', 'category-code',
                   'red-positive-count', 'black-red-positive-count', 'green-count-zero', 'black-red-age',
                   'green-age', 'black-red-invalid-multi-column'}
        extra = {'product-hierarchy', 'same-attribute-OR', 'cross-attribute-AND'} | {
            n+'-gate-open' for n in ('text-equalto', 'text-notequalto', 'text-contains', 'text-doesnotcontain',
            'text-startswith', 'text-doesnotstartwith', 'text-endswith', 'text-doesnotendwith',
            'sql-like-brackets', 'empty-hasvalue', 'empty-hasnovalue')}
        for name, branches in sql['observations'].items():
            for branch, observation in branches.items():
                error = branch == 'child-transporter-grid' or (
                    name in invalid and branch not in ('child-custom', 'chart-0', 'chart-1', 'chart-2', 'chart-3')) or (
                    name in extra and branch in ('child-transporter-count', 'child-count-wire'))
                assert (observation['status'] == 'SQL_ERROR') == error, (name, branch)
                if error:
                    assert any('('+code+')' in observation['message'] for code in ('207','8120','4104','102','156'))
                else:
                    expected = [[0]] if branch.endswith('-count') else [[None]] if branch.endswith(('-grid','-custom')) else []
                    if branch.endswith('-count-wire'):
                        assert json.loads(observation['rows'][0][0]) == [dict(locationwise=0, **({'transporterwise':0} if branch.startswith('child') else {}))]
                    else:
                        assert observation['rows'] == expected, (name, branch)
        # The owned DB has no GIT config population. Independently reconcile
        # the retained imported config against pinned deployed INSERT scripts.
        scripts = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation')
        config_path, type_path = scripts/'UI_ReportConfiguration_2.0.sql', scripts/'UI_ReportColumnTypes_2.0.sql'
        assert file_sha(config_path) == '4b248637cd659bdf05730964513bf555103d83521a268e93cddb24bc8c6f34da'
        assert file_sha(type_path) == '51883c78e5effbb55b303f07b99df9c84a3a336b0525d19b0540a9b95df02a19'
        imported = json.loads((ROOT/'mta/config/git_selected_ui.json').read_text())
        config_proof = {}
        for name in imported:
            types = dict(re.findall(r"VALUES \(N'"+name+r"', N'([^']+)', N'([^']+)'\)", type_path.read_text(encoding='utf-8-sig')))
            rows = []
            for code, position, header, visible, alignment, value in re.findall(
                r"VALUES \(N'"+name+r"', N'([^']+)', (\d+), N'([^']*)', ([01]), N'([^']*)', (N'[^']*'|NULL), NULL\)", config_path.read_text(encoding='utf-8-sig')):
                if visible != '1': continue
                row = dict(ReportName=name, Col_Code=code, Col_Position=int(position), Header=header, Visible=True, CellAlignment=alignment)
                if value != 'NULL': row['Value'] = value[2:-1]
                if code in types: row['DataType'] = types[code]
                rows.append(row)
            assert rows and sorted(rows,key=lambda r:r['Col_Code']) == sorted(imported[name],key=lambda r:r['Col_Code']), name
            config_proof[name] = dict(rows=rows, imported_order_matches=rows == imported[name])
        (target/'ui-config-proof.json').write_text(json.dumps(config_proof, indent=2))
        cases, expected = [], {}
        requests = json.loads((source/'requests.json').read_text())
        for request in requests:
            for kind, route, direction in (('parent-grid','GetPlanningDataGrid','parent'),
                ('parent-count','GetPlanningDataGridCount','parent'), ('child-grid','GetPlanningDataGrid','child'),
                ('child-count','GetPlanningDataGridCount','child'), ('custom','GetPlanningDataCustom','child'),
                ('graph','GetPlanningDataGraph','child')):
                payload = dict(request['payload'], type=direction)
                cid = request['id']+'/'+kind
                cases.append(dict(id=cid, route=route, payload=payload))
                flaw = kind == 'child-grid' or (kind in ('parent-grid','parent-count','child-count') and request['id'] in invalid) or (kind == 'child-count' and request['id'] in extra)
                if flaw:
                    expected[cid] = dict(status=503, source_flaw=True)
                else:
                    data = {'graph':dll['chart_response'], 'custom':dict(data=[],uiConfig=configurations['custom-columns']),
                            'parent-grid':dict(data=[],uiConfig=configurations['normal-columns']),
                            'parent-count':[dict(locationwise=0)], 'child-count':[dict(locationwise=0,transporterwise=0)]}[kind]
                    expected[cid] = dict(status=200, data=data)
        (target/'requests.json').write_text(json.dumps(dict(cases=cases),indent=2))
        runtime = json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'],text=True))[0]
        command = ['docker','run','--rm','--name','freshvcf-stage2-git-proof','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v',ROOT.as_posix()+':/app:ro',
            '-v','D:/freshvcf-build/evidence:/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_', 'MTA_')): command += ['-e',value]
        for mount in runtime['Mounts']:
            if mount['Destination'] != '/app': command += ['-v',mount['Source']+':'+mount['Destination']+':ro']
        completed = subprocess.run(command+[runtime['Image'],'python','tools/excess_probe.py','/evidence/'+target.name+'/requests.json'],capture_output=True,text=True)
        (target/'modern.json').write_text(completed.stdout)
        (target/'modern.log').write_text(completed.stderr)
        assert completed.returncode == 0, 'See modern.log'
        modern = json.loads(completed.stdout)
        assert modern['run'] == sql['legacy_source']['modern_run'] and modern['output_digest'] == sql['legacy_source']['modern_output_digest']
        delta, flaws = [], []
        assert len(modern['observations']) == len(expected)
        for observation in modern['observations']:
            cid = observation['id']; wanted = expected[cid]
            delta += differences(wanted['status'],observation['status'],'/'+cid+'/status')
            if wanted.get('source_flaw'):
                assert observation['body']['error'].startswith('LEG-GIT-'), observation
                flaws.append(dict(id=cid, status='EXPLICIT_UNAVAILABLE_NOT_WIRE_PARITY', error=observation['body']['error']))
            else:
                message = '' if cid.endswith('/graph') else None
                body = dict(recordCount=None,data=wanted['data'],status=200,msg=message,errorCount=None,error=None,conflictErrorCount=None,conflictError=None)
                delta += differences(body,observation['body'],'/'+cid+'/body')
        result.update(status='PASS_VALID_TERMINAL_ROUTES_WITH_EXPLICIT_SOURCE_FLAW_BLOCKERS' if not delta else 'FAILED',
            comparisons=len(expected), differences=delta, source_flaws=flaws, legacy_source=sql['legacy_source'],
            dependency_image=runtime['Image'], config_source_sha256={str(p):file_sha(p) for p in (config_path,type_path)},
            source_receipt_sha256=file_sha(source/'receipt.json'), dll_receipt_sha256=file_sha(wire/'receipt.json'),
            qualification='Read-only private Django routes. Source-invalid branches explicitly unavailable, NOT legacy silent-empty wire parity. No authenticated browser/restart/performance acceptance.')
        assert not delta, 'See receipt differences'
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__,message=str(exc)); raise
    finally:
        result['sources'] = {name:file_sha(ROOT/name) for name in ('tools/git_receipt.py','mta/presentation/git_read.py','mta/presentation/views.py','tools/excess_probe.py')}
        result['files'] = {p.name:file_sha(p) for p in target.iterdir() if p.is_file() and p.name != 'receipt.json'}
        (target/'receipt.json').write_text(json.dumps(result,indent=2))
    print(result['status'],result['comparisons'])


if __name__ == '__main__': main()
