"""Exact canonical Excess INSERT for the approved, independently sourced chain."""
import argparse
import json
import os
import re
from pathlib import Path

from mta.serialization import digest, storage
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import RECEIPT, RECEIPT_SHA, selected_capture_tables
from parity.temporal import differences, fingerprint
from parity.verify_excess_consumer import SOURCE, SOURCE_SHA
from parity.verify_rrr_consumer import temp_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    if args.evidence.exists():
        raise ValueError('Preserve evidence; new directory required')
    args.evidence.mkdir(parents=True)
    result = dict(status='FAILED', engine_replays=0, persistent_sql_writes=False)
    try:
        candidate = json.loads(args.candidate.read_text())
        manifest = candidate['manifest']
        if (candidate['status'] != 'CANDIDATE_REQUIRES_INDEPENDENT_COMPARISON' or
                manifest['producer_sha256'] != SOURCE_SHA or
                manifest['opening'] != {'business_date': '2026-06-06', 'ExcessInventoryDetails': []} or
                file_sha(RECEIPT) != RECEIPT_SHA or file_sha(SOURCE) != SOURCE_SHA):
            raise ValueError('Source/input identity mismatch')
        days = json.loads(RECEIPT.read_text())['days']
        if len(days) != 12 or len(manifest['runs']) != 12:
            raise ValueError('Approved full chain required')
        inputs, provenance = [], []
        for day, run in zip(days, manifest['runs']):
            if (day['modern_run'] != run['run_id'] or day['date'] != run['business_date'] or
                    day['status'] not in ('PASS', 'PASS_WITH_LEGACY_FLAWS')):
                raise ValueError('Run/date pairing mismatch')
            path = Path(day['legacy_capture_path'])
            before = file_sha(path)
            selected = selected_capture_tables(path)
            late = dict(selected['late'])
            late['BPRLastBatchRunTbl'] = late.pop('LastBatchRunTbl')
            if (digest(selected['closing']) != day['closing_digest'] or
                    fingerprint(late) != day['legacy_boundaries']['final-bpr-bluezone'] or
                    file_sha(path) != before):
                raise ValueError('Accepted legacy populations changed')
            inputs.append(dict(run_id=run['run_id'], date=day['date'],
                rationed=selected['late']['vf_RationedReqReport'],
                standards=selected['closing']['dbm']['SKULocStandardAttributes']))
            provenance.append(dict(run_id=run['run_id'], capture=str(path), sha256=before,
                closing_digest=day['closing_digest']))
            del selected, late
            print('Verified retained inputs ' + day['date'], flush=True)
        source = SOURCE.read_text(encoding='utf-8-sig')
        sql = re.search(r'Insert into ExcessInventoryDetails WITH\(TABLOCK\)[\s\S]+?where PhysicalInventoryColor=@white and abs\(A.VirtualNorm-A.Stock\)<>0', source, re.I)
        if not sql:
            raise ValueError('Canonical INSERT not found')
        query = sql.group().replace('ExcessInventoryDetails', '#Excess').replace('vf_RationedReqReport', '#Rationed')
        query = query.replace('[$(ImporterDatabase)].dbo.SKULocStandardAttributes', '#Standard')
        expected, delta = {}, []
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay():
            for population in inputs:
                with connection('VFTEST_BPR') as db:
                    temp_rows(db, '#Rationed', 'dbo.vf_RationedReqReport', population['rationed'])
                    temp_rows(db, '#Standard', 'VFTEST_Importer.dbo.SKULocStandardAttributes', population['standards'])
                    temp_rows(db, '#Excess', 'dbo.ExcessInventoryDetails', [])
                    db.execute("DECLARE @Today date=?; DECLARE @white nvarchar(5)=N'White'; " + query, population['date'])
                    cursor = db.execute('SELECT * FROM #Excess')
                    fields = [column[0] for column in cursor.description]
                    rows = storage([dict(zip(fields, row)) for row in cursor.fetchall()])
                key = population['run_id']
                expected[key] = rows
                delta.extend(differences(rows, candidate['rows'][key], '/' + population['date']))
                print('Compared ' + population['date'], flush=True)
        (args.evidence / 'legacy-rows.json').write_text(json.dumps(expected, indent=2))
        result.update(status='PASS_EXCESS_HISTORY' if not delta else 'FAIL',
            runs=manifest['runs'], opening=manifest['opening'], producer_sha256=SOURCE_SHA,
            projections=manifest['projections'], differences=delta, legacy_provenance=provenance,
            candidate_sha256=file_sha(args.candidate), accepted_receipt_sha256=RECEIPT_SHA,
            legacy_rows_sha256=file_sha(args.evidence / 'legacy-rows.json'), query=query,
            qualification='Approved empty opening and 12 daily producer outputs; persisted publication/trend API/browser remain separate proof')
    except Exception as exc:
        result['error'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        (args.evidence / 'receipt.json').write_text(json.dumps(result, indent=2))
    print(result['status'], flush=True)
    if delta:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
