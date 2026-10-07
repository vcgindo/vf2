"""Read-only accepted artifacts versus canonical Norm SQL in session temp tables.

This proves producer values under the approved MTO=0 gate exception, never
unchanged canonical gating or engine parity. No permanent SQL tables are written.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path

from mta.presentation.daily_rrr_colour import (
    norm_rrr_colour_rows, OUTPUT_FIELDS, SOURCE_SQL_SHA256, _BAND_MAP)
from mta.serialization import digest, storage
from parity.output_archive import OutputArchive, file_sha
from parity.legacy_isolation import exclusive_replay, connection
from parity.verify_rrr_consumer import temp_rows

ROOT = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR')
SQL = ROOT/'OrderAllocationReports/GenerateRRR_OrderAllocation.sql'
PICK = ROOT/'Ration_Scripts/GenerateBifurcationOfRationedReq.sql'
PICK_SHA = '8da7fde0a88fd29a8c1f3af0d92ff578be50262f1b5605be8421a1686c45f0b5'


def source(archive_path, expected_output):
    archive = OutputArchive(archive_path)
    archive.verify(expected_output)
    capabilities = {row['capability']: row['rows'] for row in archive['CalculationOutputs']}
    rationed = archive['BPRFinal'][0]['vf_RationedReqReport']
    masters = archive['ClosingState'][0]['bpr']['BPRMaster']
    bands = capabilities['r1_requirement_band']
    context = dict(run_id=archive.manifest['run_id'], instance_port=3006,
        synthetic=True, is_mto_environment=0, order_capabilities_complete=True)
    orders = {name: capabilities[name] for name in ('r1_order_route', 'r1_order_bpp')}
    # This proof rejects all order/advance populations; it does not infer a
    # general AllocatedOrders or vf_ReqCalculation mapping for positive orders.
    if any(orders.values()) or capabilities['r1_advance_stock_allocation']:
        raise ValueError('This exact smoke proof requires complete empty order/advance capabilities')
    orders['AllocatedOrders'] = []
    result = norm_rrr_colour_rows(rationed_report=rationed, requirement_bands=bands,
        bpr_master=masters, advance_stock_allocations=[], order_capabilities=orders,
        context=context)
    return archive, capabilities, rationed, masters, bands, result


def canonical_sql():
    if file_sha(SQL) != SOURCE_SQL_SHA256 or file_sha(PICK) != PICK_SHA:
        raise ValueError('Pinned producer source drift')
    pick = PICK.read_text().split('insert into vf_PickListReport With(Tablock)', 1)[1]
    pick = 'insert into vf_PickListReport With(Tablock)' + pick.split("print N'Keep Allocated", 1)[0]
    # Preserve the complete Norm CTE, native INSERT/UNION and Blue UPDATE.
    sql = SQL.read_text()
    sql = sql[sql.index(';with cteTOR'):sql.index('\nselect \n    A.[SKUCode]')]
    bindings = {
        '[$(IntermediateDatabase)].dbo.BifurcationOfAllocatedOrders': '#Bifurcation',
        'vf_RationedReqReport': '#Rationed', 'vf_PickListReport': '#Pick',
        'RequirementInColorBand': '#Bands', 'BPRMaster': '#Master',
        'vf_ReqCalculation': '#Req', 'RRR_OrderAllocation': '#Result',
    }
    for old, new in bindings.items():
        pick = pick.replace(old, new)
        sql = sql.replace(old, new)
    return pick, sql


def verify(archive_path, expected_output):
    archive, capabilities, rationed, masters, bands, modern = source(archive_path, expected_output)
    pick_sql, report_sql = canonical_sql()
    with connection('VFTEST_BPR') as db:
        for name, table, rows in (
            ('#Rationed', 'vf_RationedReqReport', rationed),
            ('#Master', 'BPRMaster', masters),
            ('#Pick', 'vf_PickListReport', []),
            ('#Result', 'RRR_OrderAllocation', []),
            ('#Bifurcation', 'VFTEST_Intermediate.dbo.BifurcationOfAllocatedOrders', []),
        ):
            temp_rows(db, name, table, rows)
        # Copy the native physical types of exactly the columns read by this
        # producer. Unread mandatory columns are neither guessed nor defaulted.
        for name, table, rows in (
            ('#Bands', 'RequirementInColorBand',
             [{target: row[field] for field, target in _BAND_MAP.items()} for row in bands]),
            ('#Req', 'vf_ReqCalculation',
             [dict(SKUCode=row['sku_code'], WhCode=row['location_code'], AdvAllocDone=0)
              for row in capabilities['r1_requirement']]),
        ):
            fields = list(rows[0])
            columns = ','.join('['+f+']' for f in fields)
            db.execute('SELECT TOP 0 '+columns+' INTO '+name+' FROM '+table)
            db.cursor().executemany('INSERT INTO '+name+' ('+columns+') VALUES ('+
                ','.join('?' for _ in fields)+')', [tuple(row[f] for f in fields) for row in rows])
        # Complete empty advance allocations give zero at each requirement
        # occurrence. Populate its actual source grain, not the output rows.
        for sql in (pick_sql, report_sql):
            cursor = db.execute('SET NOCOUNT ON; SET ANSI_WARNINGS OFF; ' + sql)
            while cursor.nextset():
                pass
        cursor = db.execute('SELECT ' + ','.join('['+f+']' for f in OUTPUT_FIELDS) + ' FROM #Result')
        legacy = storage([dict(zip(OUTPUT_FIELDS, row)) for row in cursor.fetchall()])
    modern = storage(modern)
    # The DDL's decimal CasePacks stores integer division as a decimal value.
    # Normalize only its physical decimal representation for the full-row check.
    for rows in (modern, legacy):
        for row in rows:
            if row['RationedCasePacks'] is not None:
                from decimal import Decimal
                row['RationedCasePacks'] = str(Decimal(str(row['RationedCasePacks'])).normalize())
    actual, expected = Counter(map(digest, modern)), Counter(map(digest, legacy))
    return dict(run_id=archive.manifest['run_id'], output_digest=expected_output,
        producer_sha256=SOURCE_SQL_SHA256, pick_sha256=PICK_SHA,
        gate='approved-MTO0-exception-not-canonical-gating-parity',
        status='PASS' if actual == expected else 'FAIL',
        modern=modern, legacy=legacy, missing=list((expected-actual).elements()),
        extra=list((actual-expected).elements()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True)
    parser.add_argument('--output-digest', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    target = Path(args.receipt)
    if target.exists():
        raise ValueError('Evidence must be append-only')
    os.environ['VFTEST_PROFILE'] = 'fresh'
    with exclusive_replay():
        result = verify(args.archive, args.output_digest)
    with target.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(result['status'], target)
    return int(result['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
