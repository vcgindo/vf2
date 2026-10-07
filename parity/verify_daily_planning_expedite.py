"""Canonical scoped chart SELECTs on exact smoke source bags, session-temp only."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from mta.serialization import storage
from parity.output_archive import file_sha
from parity.legacy_isolation import exclusive_replay, connection
from parity.verify_rrr_consumer import temp_rows
from parity.verify_expedite_charts import selected_sql, SECTIONS, CTE, SOURCE_SHA
from mta.presentation.expedite_charts import response


def permission_cte(name, column, weights):
    if any(type(n) is not int or n < 1 for n in weights.values()):
        raise ValueError('Invalid permission multiplicity')
    rows = ["(N'"+code.replace("'", "''")+"')" for code, n in sorted(weights.items()) for _ in range(n)]
    body = ('SELECT code FROM (VALUES '+','.join(rows)+') V(code)' if rows else
            'SELECT CAST(NULL AS nvarchar(100)) WHERE 1=0')
    return name+'('+column+') AS ('+body+')'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    if args.receipt.exists():
        raise ValueError('Preserve existing evidence')
    exported = json.loads(args.source.read_text())
    if exported['run'] != '17f0eb84-7b6d-40e9-a288-9441a4d7a860' or exported['output_digest'] != 'e9777b060d27a77584fcc20734e5f1daba7fab38f8e1eaf99bec907cc278233f':
        raise ValueError('Only the accepted day-two smoke is selected')
    charts = selected_sql()[1]  # Producer SQL is deliberately not executed.
    results, datasets = [], []
    os.environ['VFTEST_PROFILE'] = 'fresh'
    with exclusive_replay(), connection('VFTEST_BPR') as db:
        for name, table, source in (
            ('#Pick', 'vf_PickListReport', 'pick'),
            ('#Expedite', 'ExpediteDispatches', 'expedite'),
            ('#Master', 'BPRMaster', 'master'),
            ('#Loc', 'VFTEST_Importer.dbo.LocationAttributeData', 'loc'),
            ('#LocDesc', 'VFTEST_Importer.dbo.SiteDescriptionTbl', 'locdesc'),
        ):
            temp_rows(db, name, table, exported['sources'][source])
        for case in exported['cases']:
            auth = (';WITH '+permission_cte('cte_SKUs', 'SKUCode', case['products'])+','+
                permission_cte('cte_WhCodes', 'WHCode', case['locations'])+' ')
            for kind, queries in charts.items():
                tables = []
                for family, sql in zip(SECTIONS[kind], queries):
                    if not sql.startswith(CTE):
                        raise ValueError('Canonical auth extraction changed')
                    cursor = db.execute(auth+sql[len(CTE):])
                    fields = [column[0] for column in cursor.description]
                    columns = [dict(name=c[0], type='int32' if c[1] is int else 'string')
                               for c in cursor.description]
                    legacy = storage([dict(zip(fields, row)) for row in cursor.fetchall()])
                    tables.append(dict(columns=columns, rows=legacy))
                    modern = case['charts'][kind][family]
                    results.append(dict(actor=case['actor'], kind=kind, family=family,
                        status='PASS' if modern == legacy else 'FAIL', modern=modern, legacy=legacy))
                datasets.append((case, kind, dict(tables=tables)))
    wire = []
    directory = args.receipt.with_suffix('')
    directory.mkdir()
    harness = Path(__file__).with_name('invoke_legacy_quadrant.ps1')
    for case, kind, dataset in datasets:
        prefix = case['actor']+'-'+kind
        source_path, output_path = directory/(prefix+'-input.json'), directory/(prefix+'-dll.json')
        source_path.write_text(json.dumps(dataset), encoding='utf-8')
        completed = subprocess.run(['pwsh', '-NoProfile', '-File', str(harness),
            '-Processor', 'ExpediteProcessor', '-Direction', kind,
            '-InputPath', str(source_path), '-OutputPath', str(output_path)],
            capture_output=True, text=True)
        (directory/(prefix+'.log')).write_text(completed.stdout+completed.stderr)
        if completed.returncode:
            raise RuntimeError('Pinned DLL invocation failed: '+prefix)
        native = json.loads(output_path.read_text(encoding='utf-8-sig'))
        if native['input_sha256'] != file_sha(source_path):
            raise ValueError('Native response input identity differs')
        modern = response(case['charts'][kind], kind)
        wire.append(dict(actor=case['actor'], kind=kind,
            status='PASS' if modern==native['response'] else 'FAIL',
            modern=modern, legacy=native['response'], dll_receipt_sha256=file_sha(output_path)))
    raw_pass = all(r['status']=='PASS' for r in results)
    wire_pass = all(r['status']=='PASS' for r in wire)
    result = dict(status='PASS' if raw_pass and wire_pass else
        'PASS_RESPONSE_RAW_ORDER_DIFFERS' if wire_pass else 'FAIL',
        source_sha256=file_sha(args.source), consumer_sha256=SOURCE_SHA,
        run=exported['run'], output_digest=exported['output_digest'], seal=exported['seal'],
        comparisons=results, wire=wire, comparison='complete ordered values plus actual pinned DLL response',
        permanent_sql_writes=False)
    with args.receipt.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(result['status'], len(results), args.receipt)
    return int(not wire_pass)


if __name__ == '__main__':
    raise SystemExit(main())
