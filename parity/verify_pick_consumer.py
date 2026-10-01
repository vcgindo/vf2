"""Read-only comparison to the retained Fresh SQL terminal Pick report.

No reset, seed, batch replay, SQL update, or live/Block2 database connection.
This proves the native consumer handoff, not filters, permissions or API typing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from mta.serialization import storage
from parity.legacy_isolation import exclusive_replay, connection
from parity.output_archive import iter_rows, write_rows
from parity.temporal import differences


def retained_projection(sql_source, columns, manifest):
    """Execute source SELECT aliases over independent retained legacy facts.

    Population/bands come from the already accepted legacy Pick capture.
    No ration/band expression or batch is re-executed. Only session temp tables
    are populated; physical Fresh database tables remain untouched.
    """
    from parity.retained_consumer_input import terminal_inputs
    values, provenance = terminal_inputs()
    if (provenance['modern_run'] != manifest['run']['id'] or
            provenance['modern_output_digest'] != manifest['run']['output_digest']):
        raise ValueError('Retained legacy/modern run pairing differs')
    selects = re.findall(r'insert into vf_PickListReport With\(Tablock\)\s*(SELECT[\s\S]+?)\s+from vf_RationedReqReport A',
                         sql_source, flags=re.IGNORECASE)
    if len(selects) != 2:
        raise ValueError('Expected exactly the two pinned source report SELECTs')
    for i, select in enumerate(selects):
        for field in ('TOR_B','TOR_R','TOY','TOG','TOBlue'):
            select, n = re.subn(r'\b'+field+r'=0\b',field+'=C.'+field,select)
            if n != 1:
                raise ValueError('Source band alias differs')
        selects[i] = select + ' FROM #Rationed A JOIN #Bands C ON A.SKUCode=C.SKUCode AND A.WhCode=C.WhCode AND '
    selects[0] += 'A.ParentWhCode=C.ParentWhCode AND C.WhCode<>C.ParentWhCode'
    selects[1] += 'C.WhCode=C.ParentWhCode'
    quote = lambda n:'['+n.replace(']',']]')+']'
    insert = 'INSERT INTO #Projected '+' UNION ALL '.join(selects)
    query = 'SELECT '+','.join(map(quote,columns))+' FROM #Projected'
    rationed = values['late']['vf_RationedReqReport']
    fields = list(rationed[0])
    band_fields = ('SKUCode','WhCode','ParentWhCode','TOR_B','TOR_R','TOY','TOG','TOBlue')
    band_source = ('sku_code','location_code','parent_location_code','to_black','to_red','to_yellow','to_green','to_blue')
    with exclusive_replay():
        with connection('VFTEST_BPR') as bpr:
            bpr.execute('SELECT TOP 0 * INTO #Rationed FROM dbo.vf_RationedReqReport')
            bpr.execute('SELECT TOP 0 '+','.join(map(quote,band_fields))+' INTO #Bands FROM dbo.vf_PickListReport')
            # Preserve the source INSERT's target-column conversion (notably
            # its bit IsNormed). UNION's inferred int type is not the stored
            # report type and must not be normalized in the comparator.
            bpr.execute('SELECT TOP 0 * INTO #Projected FROM dbo.vf_PickListReport')
            bpr.cursor().executemany('INSERT INTO #Rationed ('+','.join(map(quote,fields))+') VALUES ('+
                ','.join('?' for _ in fields)+')',[tuple(r[f] for f in fields) for r in rationed])
            bpr.cursor().executemany('INSERT INTO #Bands VALUES ('+','.join('?' for _ in band_fields)+')',
                                    [tuple(r[f] for f in band_source) for r in values['bands']])
            bpr.execute(insert)
            legacy = storage([dict(zip(columns,row)) for row in bpr.execute(query).fetchall()])
    return legacy, insert+'; '+query, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern', type=Path)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--retained', action='store_true', help='Use dated accepted captures, not current rolled-back SQL tables')
    args = parser.parse_args()
    if args.evidence.exists():
        raise ValueError('Preserve earlier evidence; use a new directory')
    args.evidence.mkdir(parents=True)
    receipt_path = args.modern/'receipt.json'
    manifest = json.loads(receipt_path.read_text())
    modern = list(iter_rows(args.modern/manifest['file'],manifest))
    if not modern or manifest['business_date'] != '2026-06-17':
        raise ValueError('This read-only check is bounded to the retained nonempty day12 report')
    columns = list(modern[0])
    if any(set(r)!=set(columns) for r in modern):
        raise ValueError('Mixed modern projection columns')
    root = Path(__file__).resolve().parents[1]
    producer = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/Ration_Scripts/GenerateBifurcationOfRationedReq.sql')
    if hashlib.sha256(producer.read_bytes()).hexdigest() != '8da7fde0a88fd29a8c1f3af0d92ff578be50262f1b5605be8421a1686c45f0b5':
        raise ValueError('Selected producer source changed')
    for name, sha in manifest['sources'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != sha:
            raise ValueError('Modern consumer source changed since export')
    selected = ','.join('['+name.replace(']',']]')+']' for name in columns)
    query = 'SELECT '+selected+' FROM dbo.vf_PickListReport'
    result = dict(status='FAILED', modern_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                  run=manifest['run'], query=query, calculations_executed=0, persistent_database_writes=False)
    try:
        os.environ['VFTEST_PROFILE'] = 'fresh'
        if args.retained:
            legacy, query, provenance = retained_projection(producer.read_text(encoding='utf-8-sig'), columns, manifest)
            result.update(query=query, retained_source=provenance, temporary_session_tables=True,
                          persistent_database_writes=False)
        else:
            with exclusive_replay():
                with connection('VFTEST_BPR') as bpr:
                    dates = bpr.execute('SELECT CONVERT(date, LastRunDate) FROM dbo.LastBatchRunTbl').fetchall()
                    if [str(r[0]) for r in dates] != [manifest['business_date']]:
                        raise ValueError('Fresh SQL is not at the selected terminal date')
                    legacy = storage([dict(zip(columns,row)) for row in bpr.execute(query).fetchall()])
                # A separate terminal DBM date check excludes a stale BPR-only replay.
                with connection('VFTEST_DBM') as dbm:
                    dates = dbm.execute('SELECT CONVERT(date, LastRunDate) FROM dbo.LastBatchRunTbl').fetchall()
                    if [str(r[0]) for r in dates] != [manifest['business_date']]:
                        raise ValueError('Fresh DBM terminal date differs')
        legacy_meta = write_rows(args.evidence/'legacy-pick.jsonl.gz',legacy)
        delta = differences(legacy,modern,'/selected-native-Pick-consumer')
        result.update(status='FAIL' if delta else 'PASS_NATIVE_CONSUMER_HANDOFF',
            legacy=legacy_meta, modern_rows=len(modern), fields=len(columns), differences=delta,
            qualification='Selected native consumer fields only; API filters/scopes/serialization require their own comparisons')
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','modern_rows','fields')}))
    if delta:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
