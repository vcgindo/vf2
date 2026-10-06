"""Bounded canonical SQL proof for an exact-duplicate GIT custom result."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parity.git_queries import PLAN, PLAN_SHA, queries
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha


def expected():
    row = dict(sc='A', wc='L', sd='A desc', wd='Location', dd=3,
        ss='Delay', s='Open', pwc='P', pn='Parent', n=10, mn=1, rlt=2,
        rcp=1, gcp=1, ocp=1, moc=1, rq=7, ps=1, frf='FG', da=True,
        odn='O', ts='Delay', tn='Carrier', tc='T', fl='P', itq=2,
        cd='2026-06-01', slt=2, ag=5, lc='LR1', sl1='S', ll1='North')
    return [dict(RN=index, **row) for index in range(1, 5)]


def seed(db):
    statements = (
        'CREATE TABLE #PS(SKUCode nvarchar(50) NULL)',
        "INSERT INTO #PS VALUES ('A'),('A')",
        'CREATE TABLE #LS(WhCode nvarchar(50) NULL)',
        "INSERT INTO #LS VALUES ('L')",
        'CREATE TABLE #Transporter(SKUCode nvarchar(50),WhCode nvarchar(50),ParentWhCode nvarchar(50),OrderNo nvarchar(50),SKUStatus nvarchar(50),Status nvarchar(50),InTransitQty int,TruckStatus nvarchar(50),TransporterName nvarchar(100),TransporterCode nvarchar(50),TransporterContact nvarchar(100),CreationDate date,SLT int,Ageing int,ETA date,CurrentLocation nvarchar(100),Remark nvarchar(100),LRCode nvarchar(50))',
        "INSERT INTO #Transporter VALUES ('A','L','P','O','Delay','Open',2,'Delay','Carrier','T',NULL,'2026-06-01',2,5,NULL,NULL,NULL,'LR1'),('A','L','P','O','Delay','Open',2,'Delay','Carrier','T',NULL,'2026-06-01',2,5,NULL,NULL,NULL,'LR1')",
        'CREATE TABLE #Git(SKUCode nvarchar(50),WhCode nvarchar(50),Req int)',
        "INSERT INTO #Git VALUES ('A','L',7)",
        'CREATE TABLE #Transit(SKUCode nvarchar(50),WhCode nvarchar(50),TLT int,SLT int)',
        "INSERT INTO #Transit VALUES ('A','L',5,2)",
        'CREATE TABLE #Nms(SKUCode nvarchar(50),WhCode nvarchar(50),SKUDescription nvarchar(100),WHDescription nvarchar(100),ParentWhCode nvarchar(50),Norm int,MinNorm int,RLT int,RCP int,GCP int,OCP int,MinOrderCount int,PackSize int,FGRMFlag nvarchar(20),DBMActive bit,SL1 nvarchar(50),SL2 nvarchar(50),SL3 nvarchar(50),SL4 nvarchar(50),SL5 nvarchar(50),LL1 nvarchar(50),LL2 nvarchar(50),LL3 nvarchar(50),LL4 nvarchar(50),LL5 nvarchar(50))',
        "INSERT INTO #Nms VALUES ('A','L','A desc','Location','P',10,1,2,1,1,1,1,1,'FG',1,'S',NULL,NULL,NULL,NULL,'North',NULL,NULL,NULL,NULL)",
        'CREATE TABLE #LocDesc(WHCode nvarchar(50),WHDescription nvarchar(100))',
        "INSERT INTO #LocDesc VALUES ('P','Parent')",
    )
    for statement in statements:
        db.execute(statement)


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: verify_daily_git_custom_sql.py EVIDENCE_DIRECTORY')
    target = Path(sys.argv[1])
    target.mkdir(parents=True, exist_ok=False)
    receipt = dict(status='FAILED', persistent_database_writes=False,
                   database_creation=False, engine_replays=0,
                   qualification='One exact-duplicate connector case; no retained shipment/application parity.')
    try:
        if file_sha(PLAN) != PLAN_SHA:
            raise ValueError('Pinned PlanningProcessor differs')
        auth = ';WITH cte_SKUs AS (SELECT SKUCode FROM #PS), cte_WhCodes AS (SELECT WhCode FROM #LS) '
        query = queries(auth, {'product_permissions': [1], 'location_permissions': [1]})['child-custom']
        (target / 'query.sql').write_text(query, encoding='utf-8')
        (target / 'fixture.json').write_text(json.dumps(dict(
            declaration='Exact-duplicate connector rows; not retained shipment facts.',
            transporter_occurrences=2, product_scope_occurrences=2,
            transit_occurrences=1, expected_rows=expected()), indent=2), encoding='utf-8')
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                database = db.execute('SELECT DB_NAME()').fetchval()
                seed(db)
                cursor = db.execute(query)
                record = cursor.fetchone()
                actual = json.loads(record[0]) if record and record[0] is not None else []
        comparison = dict(expected=expected(), actual=actual, equal=actual == expected())
        (target / 'comparison.json').write_text(json.dumps(comparison, indent=2), encoding='utf-8')
        if not comparison['equal']:
            raise AssertionError('Canonical GIT custom SQL rows differ')
        receipt.update(status='PASS_BOUNDED_GIT_CUSTOM_SQL', database=database,
            base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            source={str(PLAN): PLAN_SHA}, rows=len(actual), complete_rows_equal=True,
            transformations=[
                'Extract GetCustomGridData through parity.git_queries.',
                'Redirect only relation identifiers to connection-local #tables.',
                'Supply resolved scope occurrences through duplicate #PS rows.',
            ],
            proof_source_sha256=file_sha(Path(__file__)))
        receipt['file_hashes'] = {path.name: file_sha(path) for path in target.iterdir()
                                  if path.is_file()}
    except Exception as error:
        receipt['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        (target / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
