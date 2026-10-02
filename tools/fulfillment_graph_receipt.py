"""Actual deployed Fulfilment graph formatting from independently retained SQL bags."""
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
from parity.verify_fulfillment_charts import PRODUCER, PRODUCER_SHA, selected_queries
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
        assert file_sha(PRODUCER/'receipt.json') == PRODUCER_SHA
        producer = json.loads((PRODUCER/'receipt.json').read_text())
        assert producer['legacy_source'] == provenance
        assert file_sha(PRODUCER/'legacy-fulfillment.json.gz') == producer['legacy_readback_sha256']
        with gzip.open(PRODUCER/'legacy-fulfillment.json.gz','rt') as stream:
            reports = json.load(stream)
        cases = []
        for name, products, locations in (('root', [71001], [72001]), ('leaf', [71002], [72003]),
                ('overlapping', [71001,71002], [72001,72003])):
            cases.append(dict(id=name, route='GetPlanningDataGraph', payload=dict(category='orderFulfillment',
                type='review', filters={}, product_permissions=products, location_permissions=locations)))
        case = deepcopy(cases[0]); case['id'] = 'ignored-filter'
        case['payload']['filters'] = {'productFilter': {'filters':[dict(attributeName='sku', value='ABSENT')]}}
        cases.append(case)
        (target/'requests.json').write_text(json.dumps(dict(cases=cases)))
        runtime = json.loads(subprocess.check_output(['docker','inspect','freshvcf-preview-mta-1'], text=True))[0]
        command = ['docker','run','--rm','--name','freshvcf-stage2-fulfillment-graph','--network','freshvcf-test_default',
            '--memory','4g','--memory-swap','4g','--cpus','2','-v','F:/freshvcf:/app:ro',
            '-v','D:/freshvcf-build/evidence:/evidence:ro','-e','PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_','MTA_')): command += ['-e',value]
        for mount in runtime['Mounts']:
            if mount['Destination'] != '/app': command += ['-v',mount['Source']+':'+mount['Destination']+':ro']
        command += [runtime['Image'],'python','tools/excess_probe.py','/evidence/'+target.name+'/requests.json']
        if len(sys.argv)>2:
            prior=Path(sys.argv[2]).resolve()
            prior_receipt=json.loads((prior/'receipt.json').read_text())
            assert file_sha(prior/'modern.log')==prior_receipt['files']['modern.log']
            assert (prior/'requests.json').read_bytes()==(target/'requests.json').read_bytes()
            assert all(file_sha(ROOT/name)==sha for name,sha in prior_receipt['sources'].items() if name!='tools/fulfillment_graph_receipt.py')
            (target/'modern.log').write_bytes((prior/'modern.log').read_bytes())
            modern=json.loads((prior/'modern.log').read_text())
            result['modern_reused_from']=dict(path=str(prior),receipt_sha256=file_sha(prior/'receipt.json'))
        else:
            modern = json.loads(call(command, target/'modern.log'))
        assert modern['run'] == provenance['modern_run'] and modern['output_digest'] == provenance['modern_output_digest']
        observed = {r['id']:r for r in modern['observations']}
        queries = selected_queries()
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay(), connection('VFTEST_BPR') as db:
            temp_rows(db, '#Summary', 'dbo.OrderFulfillmentData', reports['summary'])
            temp_rows(db, '#Details', 'dbo.OrderFulfillmentDataDetails', reports['details'])
            for name, table in (('#Sku','SkuAttributeData'), ('#Loc','LocationAttributeData'),
                                ('#SkuDesc','SKUDescriptionTbl'), ('#LocDesc','SiteDescriptionTbl')):
                temp_rows(db, name, 'dbo.'+table, legacy['closing']['importer'][table])
            supplement_temp_hierarchy(db, catalogue)
            for case in cases:
                db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions')
                cte = auth_ctes(db, catalogue, case['payload'])
                tables = []
                for i, query in enumerate(queries):
                    cursor = db.execute(cte+query)
                    fields = [c[0] for c in cursor.description]
                    rows = [dict(zip(fields, r)) for r in cursor.fetchall()]
                    tables.append(dict(columns=[dict(name=n, type='int32'
                        if n == 'counts' else 'string') for n in fields], rows=rows))
                source = target/(case['id']+'-tables.json')
                source.write_text(json.dumps(dict(tables=tables)))
                output = target/(case['id']+'-response.json')
                process = subprocess.run(['pwsh','-NoProfile','-File',str(ROOT/'parity/invoke_legacy_quadrant.ps1'),
                    '-InputPath',str(source),'-OutputPath',str(output),'-Processor','QuadrantProcessor'],
                    cwd=target, text=True, capture_output=True)
                (target/(case['id']+'.log')).write_text(process.stdout+process.stderr)
                assert process.returncode == 0, 'See deployed invocation log'
                deployed = json.loads(output.read_text())
                assert deployed['input_sha256'] == file_sha(source)
                assert observed[case['id']]['status'] == 200
                actual, expected = observed[case['id']]['body']['data'], deployed['response']
                delta = differences(expected, actual, '/'+case['id'])
                # GetResponse output has source description grouping and first-three
                # selection. Exact bags cover that algorithm; source equal-count
                # order is not strengthened to an invented tie-break.
                result['checks'].append(dict(id=case['id'],status='PASS' if not delta else 'FAIL',
                    differences=delta,query_count=observed[case['id']]['query_count'],
                    modern_seconds=observed[case['id']]['seconds']))
        assert all(r['status'] == 'PASS' for r in result['checks'])
        result.update(status='PASS_FULFILLMENT_SCOPED_GRAPH_SQL_ACTUAL_DLL', provenance=provenance,
            handoff_receipt_sha256=file_sha(parent/'receipt.json'),
            qualification='Complete SQL bags and actual DLL GetResponse; query-declared count order. No hosted legacy or matched performance claim.')
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['sources'] = {name:file_sha(ROOT/name) for name in ('mta/presentation/fulfillment_read.py',
            'mta/presentation/fulfillment_charts.py','mta/presentation/views.py','tools/fulfillment_graph_receipt.py')}
        result['files'] = {p.name:file_sha(p) for p in target.iterdir() if p.is_file() and p.name != 'receipt.json'}
        (target/'receipt.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(dict(status=result['status'], error=result.get('error'))), flush=True)


if __name__ == '__main__': main()
