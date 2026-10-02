"""Actual deployed Excess graph formatting from independently retained SQL bags."""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha, iter_rows
from parity.temporal import differences
from parity.verify_excess_readmodel import EXCESS, EXCESS_SHA, selected_queries
from parity.verify_rrr_consumer import auth_ctes, supplement_temp_hierarchy, temp_rows, PERMISSION_SHA
from parity.verify_rrr_export import call


def main():
    target = Path(sys.argv[1]).resolve()
    assert target.parent == Path('D:/freshvcf-build/evidence').resolve()
    target.mkdir(exist_ok=False)
    result = dict(status='FAILED', engine_replays=0, persistent_writes=False, checks=[])
    try:
        parent = Path('D:/freshvcf-build/evidence/f3-stage2-excess-004')
        receipt = json.loads((parent/'receipt.json').read_text())
        assert file_sha(parent/'legacy-input-handoff.json.gz') == receipt['files']['legacy-input-handoff.json.gz']
        with gzip.open(parent/'legacy-input-handoff.json.gz', 'rt') as stream:
            handoff = json.load(stream)
        legacy, provenance = handoff['values'], handoff['provenance']
        permission = Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        assert file_sha(permission) == PERMISSION_SHA
        catalogue = json.loads(permission.read_text())
        assert file_sha(EXCESS/'receipt.json') == EXCESS_SHA
        producer = json.loads((EXCESS/'receipt.json').read_text())
        assert producer['legacy_source'] == provenance
        excess = list(iter_rows(EXCESS/'legacy-excess.jsonl.gz', producer['legacy_rows']))
        cases = []
        for name, products, locations in (('root', [71001], [72001]), ('leaf', [71002], [72003]),
                ('overlapping', [71001,71002], [72001,72003])):
            cases.append(dict(id=name, route='GetPlanningDataGraph', payload=dict(category='excessInventory',
                type='review', filters={}, product_permissions=products, location_permissions=locations)))
        case = deepcopy(cases[0]); case['id'] = 'ignored-filter'
        case['payload']['filters'] = {'productFilter': {'filters':[dict(attributeName='sku', value='ABSENT')]}}
        cases.append(case)
        (target/'requests.json').write_text(json.dumps(dict(cases=cases)))
        runtime = json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'], text=True))[0]
        command = ['docker','run','--rm','--name','freshvcf-stage2-excess-graph','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v','F:/freshvcf:/app:ro',
            '-v','D:/freshvcf-build/evidence:/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_','MTA_')): command += ['-e',value]
        for mount in runtime['Mounts']:
            if mount['Destination'] != '/app': command += ['-v',mount['Source']+':'+mount['Destination']+':ro']
        command += [runtime['Image'],'python','tools/excess_probe.py','/evidence/'+target.name+'/requests.json']
        modern = json.loads(call(command, target/'modern.log'))
        assert modern['run'] == provenance['modern_run'] and modern['output_digest'] == provenance['modern_output_digest']
        observed = {r['id']:r for r in modern['observations']}
        _, _, queries, _ = selected_queries()
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay(), connection('VFTEST_BPR') as db:
            temp_rows(db, '#Excess', 'dbo.ExcessInventoryDetails', excess)
            for name, table in (('#Sku','SkuAttributeData'), ('#Loc','LocationAttributeData'),
                                ('#SkuDesc','SKUDescriptionTbl'), ('#LocDesc','SiteDescriptionTbl')):
                temp_rows(db, name, 'dbo.'+table, legacy['closing']['importer'][table])
            temp_rows(db, '#LastDate', 'dbo.LastBatchRunTbl', legacy['late']['LastBatchRunTbl'])
            supplement_temp_hierarchy(db, catalogue)
            for case in cases:
                db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions')
                cte = auth_ctes(db, catalogue, case['payload'])
                tables = []
                for i, query in enumerate(queries):
                    cursor = db.execute(cte+query)
                    fields = [c[0] for c in cursor.description]
                    rows = [dict(zip(fields, r)) for r in cursor.fetchall()]
                    tables.append(dict(columns=[dict(name=n, type=('int64' if i%2 else 'int32')
                        if n == 'counts' else 'string') for n in fields], rows=rows))
                source = target/(case['id']+'-tables.json')
                source.write_text(json.dumps(dict(tables=tables)))
                output = target/(case['id']+'-response.json')
                process = subprocess.run(['pwsh','-NoProfile','-File',str(ROOT/'parity/invoke_legacy_quadrant.ps1'),
                    '-InputPath',str(source),'-OutputPath',str(output),'-Processor','ExcessInventoryProcessor'],
                    cwd=target, text=True, capture_output=True)
                (target/(case['id']+'.log')).write_text(process.stdout+process.stderr)
                assert process.returncode == 0, 'See deployed invocation log'
                deployed = json.loads(output.read_text())
                assert deployed['input_sha256'] == file_sha(source)
                assert observed[case['id']]['status'] == 200
                actual, expected = observed[case['id']]['body']['data'], deployed['response']
                delta = differences(expected, actual, '/'+case['id'])
                # SQL orders by count alone; compare full bags plus that order,
                # never claim stable relative order for equal-valued locations.
                order = {}
                for section in expected['data']:
                    measure = next(k for k in expected['data'][section]['data'][0]
                        if k in ('SKUCounts','SumOfAmount','WHCount','SumAmount')) if expected['data'][section]['data'] else None
                    order[section] = ([r[measure] for r in expected['data'][section]['data']] ==
                        [r[measure] for r in actual['data'][section]['data']])
                result['checks'].append(dict(id=case['id'], status='PASS' if not delta and all(order.values()) else 'FAIL',
                    differences=delta, declared_order_matches=order, query_count=observed[case['id']]['query_count'],
                    modern_seconds=observed[case['id']]['seconds']))
        assert all(r['status'] == 'PASS' for r in result['checks'])
        result.update(status='PASS_EXCESS_SCOPED_GRAPH_SQL_ACTUAL_DLL', provenance=provenance,
            handoff_receipt_sha256=file_sha(parent/'receipt.json'),
            qualification='Complete SQL bags and actual DLL GetResponse; query-declared count order. No hosted legacy or matched performance claim.')
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['sources'] = {name:file_sha(ROOT/name) for name in ('mta/presentation/excess_read.py',
            'mta/presentation/excess_views.py','mta/presentation/views.py','tools/excess_graph_receipt.py')}
        result['files'] = {p.name:file_sha(p) for p in target.iterdir() if p.is_file() and p.name != 'receipt.json'}
        (target/'receipt.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(dict(status=result['status'], error=result.get('error'))), flush=True)


if __name__ == '__main__': main()
