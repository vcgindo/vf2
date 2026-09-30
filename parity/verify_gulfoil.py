"""Selected retained raw-file acceptance; not a sizeable raw-ingestion claim."""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path

from mta.application.r1_file_input import map_csv_inputs
from mta.application.r1_gulfoil_input import map_landing_rows
from mta.planning.engine import calculate_current_day
from mta.serialization import storage, digest
from parity.current_day import compare
from parity.verify_raw import options
from parity.verify_current_day import file_hash

ROOT = Path(__file__).resolve().parents[1]


def bag(rows):
    return Counter(json.dumps(storage(row), sort_keys=True) for row in rows)


def typed_adapter_rows(table, rows):
    """SQL INT conversion only; preserve NULLs, multiplicity and all fields.

    The producer holds Decimal until its standard-input seam. The canonical
    DailyDataRaw and PSOData columns are INT. No rounding/tolerance is allowed.
    OrderId is the pure producer's spelling of SQL's OrderID, not a value change.
    """
    fields = {'DailyDataRaw': ('Stock','Consumption','GIT','Receipts','PSO'),
              'PSOData': ('Qty',)}.get(table, ())
    result=[]
    for row in rows:
        item=dict(row)
        if table=='PSOData' and 'OrderId' in item:
            if 'OrderID' in item:raise ValueError('Duplicate order identity field')
            item['OrderID']=item.pop('OrderId')
        for name in fields:
            value=item[name]
            if value is not None:
                number=Decimal(str(value))
                if not number.is_finite() or number!=number.to_integral_value() or not -2147483648<=number<=2147483647:
                    raise ValueError('Non-INT adapter output: '+table+'.'+name)
                item[name]=int(number)
        result.append(item)
    return result


def verify(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ROOT/'baseline/gulfoil-reuse.json').read_text())
    for row in [dict(path=str(ROOT/manifest['input']['path']),sha256=manifest['input']['sha256']), *manifest['receipts']]:
        if file_hash(Path(row['path'])) != row['sha256']:
            raise ValueError('Retained identity changed: '+row['path'])
    base = Path(manifest['receipts'][0]['path']).parent
    def read(name): return json.loads((base/name).read_text())
    bundle = json.loads((ROOT/manifest['input']['path']).read_text())
    contract = read('selected-v2-report-comparison-contract.json')
    if contract['source']['source_bundle'] != bundle:
        raise ValueError('Canonical receipt source bundle differs')
    legacy = read('selected-v2-legacy.json')
    if legacy != read('selected-v2-legacy-repeat.json'):
        raise ValueError('Retained legacy repeatability differs')
    adapter = read('selected-v2-adapter.json')
    scripts = {**adapter['scripts'], **{r['path']:r['sha256'] for r in legacy['scripts']}}
    canonical = Path('F:/VFlow_Source_Backup/deployed-demo/MTA/V6')
    parser_reconciliation = None
    for name, expected in scripts.items():
        original = Path(name)
        deployed = Path('F:/VFlow_Local/local-runtime/mta-engine')/original.relative_to(canonical)
        if original.name == 'ReadDailyDataToInterface.py' and file_hash(original)==expected:
            from parity.reconcile_gulfoil_parser import reconcile
            parser_reconciliation = reconcile()
        elif file_hash(original)!=expected or file_hash(deployed)!=expected:
            raise ValueError('Canonical deployment source differs: '+name)
    modern = storage(calculate_current_day(bundle))
    generated = modern['r1_gulfoil_adapter'][0]
    adapter_comparisons = {}
    for boundary in ('landing', 'transformation'):
        for table, expected in adapter[boundary].items():
            actual = generated[boundary][table]
            a,b = (bag(typed_adapter_rows(table, side)) for side in (expected,actual)) if boundary=='transformation' else (bag(expected),bag(actual))
            adapter_comparisons[boundary+'/'+table] = dict(status='PASS' if a==b else 'FAIL',
                legacy_rows=len(expected),modern_rows=len(actual),
                legacy_only=[json.loads(r) for r in (a-b).elements()],modern_only=[json.loads(r) for r in (b-a).elements()])
    comparisons = compare(legacy['checkpoints'], modern, **options(bundle))
    if set(comparisons)!=set(read('selected-v2-calculation-comparison.json')):
        raise ValueError('Selected calculation roster differs')
    parser_results=[]
    for case in read('selected-file-cases/summary.json'):
        name = case['case']
        source = read(f'selected-file-cases/{name}/input.json')
        expected = read(f'selected-file-cases/{name}/result.json')
        files = [dict(name=f['name'], content=f['text'].encode(f['encoding']),encoding=f['encoding']) for f in source['files']]
        parsed = map_csv_inputs(source['mapping'],files,source['standard_input']['raw_master_entry']['business_date'])
        landing = map_landing_rows(parsed['tables'],source['interface_columns'],profile='GulfOil')
        error = parsed.get('error','')
        category = 'NO_COLUMNS' if error.startswith('No columns') else 'MISSING_REQUIRED_HEADER' if error.startswith('Missing columns') else 'OTHER' if error else None
        matched = (set(landing)==set(expected['legacy']) and
                   all(bag(landing[t])==bag(rows) for t,rows in expected['legacy'].items()) and
                   category==expected['legacy_class'] and parsed['missing']==expected['expected_missing'])
        parser_results.append(dict(case=name,status='PASS' if matched else 'FAIL',parsed=parsed))
    passed = all(r['status']=='PASS' for r in [*comparisons.values(),*adapter_comparisons.values(),*parser_results])
    evidence=dict(fixture=Path(manifest['input']['path']).name,input=bundle,input_sha256=digest(bundle),
                  legacy=legacy,modern=modern,contracts=comparisons,adapter_contracts=adapter_comparisons,
                  parser_cases=parser_results,status='PASS' if passed else 'FAIL',
                  parser_reconciliation=parser_reconciliation,
                  oracle='RETAINED_CANONICAL_RECEIPT',source_scripts=scripts,register=manifest)
    (destination/evidence['fixture']).write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    summary=dict(status=evidence['status'],calculation_contracts=len(comparisons),adapter_contracts=len(adapter_comparisons),
                 parser_cases=len(parser_results),failures=[k for k,v in {**comparisons,**adapter_comparisons}.items() if v['status']!='PASS'])
    (destination/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))
    return passed


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination')
    raise SystemExit(0 if verify(parser.parse_args().destination) else 1)
