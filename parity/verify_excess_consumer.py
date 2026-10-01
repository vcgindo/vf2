"""Canonical Excess INSERT projection over independently retained legacy facts.

No daily replay or history rewrite. The exact producer INSERT executes only in
session-temp tables; modern operational rows are independently exported/read.
"""
import argparse
import json
import os
from pathlib import Path
import re

from mta.serialization import storage
from parity.legacy_isolation import exclusive_replay,connection
from parity.output_archive import file_sha,iter_rows,write_rows
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_rrr_consumer import temp_rows

SOURCE=Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/CollectExcessInventoryDetails.sql')
SOURCE_SHA='71bb48766d3af7a739b90c511124f9ad99072066283536fd28a9530f3640b8c4'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path)
    parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    if args.evidence.exists():
        raise ValueError('Preserve previous evidence; choose a new directory')
    args.evidence.mkdir(parents=True)
    result=dict(status='FAILED',engine_replays=0,persistent_sql_writes=False)
    try:
        receipt=json.loads((args.modern/'receipt.json').read_text())
        if receipt['status']!='PERSISTED_READBACK_PASS_COMPARISON_REQUIRED' or receipt['producer_sha256']!=SOURCE_SHA:
            raise ValueError('Wrong modern publication identity')
        root=Path(__file__).resolve().parents[1]
        for name,sha in receipt['sources'].items():
            if file_sha(root/name)!=sha:
                raise ValueError('Modern publication source changed')
        modern=list(iter_rows(args.modern/receipt['file'],receipt))
        if not modern:
            raise ValueError('This full-estate report check requires a nonempty population')
        legacy,provenance=terminal_inputs()
        if (provenance['modern_run']!=receipt['run']['id'] or
            provenance['modern_output_digest']!=receipt['run']['output_digest'] or
            provenance['date']!=receipt['business_date']):
            raise ValueError('Legacy/modern run pairing differs')
        if file_sha(SOURCE)!=SOURCE_SHA:
            raise ValueError('Canonical source changed')
        source=SOURCE.read_text(encoding='utf-8-sig')
        sql=re.search(r'Insert into ExcessInventoryDetails WITH\(TABLOCK\)[\s\S]+?where PhysicalInventoryColor=@white and abs\(A.VirtualNorm-A.Stock\)<>0',source,re.I)
        if not sql:
            raise ValueError('Canonical INSERT extraction changed')
        query=sql.group().replace('ExcessInventoryDetails','#Excess').replace('vf_RationedReqReport','#Rationed')
        query=query.replace('[$(ImporterDatabase)].dbo.SKULocStandardAttributes','#Standard')
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                temp_rows(db,'#Rationed','dbo.vf_RationedReqReport',legacy['late']['vf_RationedReqReport'])
                temp_rows(db,'#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',legacy['closing']['dbm']['SKULocStandardAttributes'])
                temp_rows(db,'#Excess','dbo.ExcessInventoryDetails',[])
                db.execute('DECLARE @Today date=?; DECLARE @white nvarchar(5)=N\'White\'; '+query,receipt['business_date'])
                cursor=db.execute('SELECT * FROM #Excess')
                fields=[c[0] for c in cursor.description]
                expected=storage([dict(zip(fields,r)) for r in cursor.fetchall()])
        delta=differences(expected,modern,'/current-day-ExcessInventoryDetails')
        result.update(status='PASS_CURRENT_DAY_EXCESS_REPORT' if not delta else 'FAIL',
            legacy_source=provenance,producer_sha256=SOURCE_SHA,query=query,
            modern_receipt_sha256=file_sha(args.modern/'receipt.json'),
            rows=len(expected),fields=len(fields),differences=delta,
            legacy_rows=write_rows(args.evidence/'legacy-excess.jsonl.gz',expected),
            qualification='Current-day producer/persisted report only; historical retention, API scopes/filters and UI remain separate obligations')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','rows','fields')}))
    if delta:
        raise SystemExit(1)


if __name__=='__main__':
    main()
