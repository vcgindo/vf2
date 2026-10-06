"""Canonical child-transporter count on connection-local connector fixtures only."""
import json
import os
from pathlib import Path
import sys
import subprocess

from mta.runtime.test_git_count_cases import fixture, cases
from parity.git_queries import request_queries, PLAN, PLAN_SHA
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha


def main():
    target=Path(sys.argv[1]); target.mkdir(parents=True,exist_ok=False)
    result=dict(status='FAILED', qualification='Bounded connector count with actual DLL filter expressions',
                persistent_database_writes=False, canonical_source=str(PLAN),
                canonical_sha256=PLAN_SHA, cases=[])
    try:
        assert file_sha(PLAN)==PLAN_SHA
        data=fixture()
        (target/'inputs.json').write_text(json.dumps(data,indent=2))
        requests=[dict(id=c['id'],payload=dict(filters=c.get('filters',{}),
                  product_permissions=[],location_permissions=[])) for c in cases()]
        request_path=target/'requests.json';request_path.write_text(json.dumps(dict(cases=requests)))
        subprocess.run(['pwsh','-NoProfile','-File',str(Path(__file__).with_name('invoke_legacy_rrr_filters.ps1')),
            '-InputPath',str(request_path),'-OutputPath',str(target/'filters.json'),'-Report','GitCount'],check=True)
        compiled={row['id']:row for row in json.loads((target/'filters.json').read_text(encoding='utf-8-sig'))['cases']}
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay(), connection('VFTEST_BPR') as db:
            bindings=dict(Transporter='dbo.GoodsInTransitTransporterMaster',
                Standard='VFTEST_Importer.dbo.SKULocStandardAttributes',
                Rationed='dbo.vf_RationedReqReport',
                LocDesc='VFTEST_Importer.dbo.SiteDescriptionTbl',
                Loc='VFTEST_Importer.dbo.LocationAttributeData',
                Pair='VFTEST_Importer.dbo.SkuLocAttributeData')
            for name, table in bindings.items():
                # Copy only the columns read by the exact count query, with their
                # deployed types, avoiding unrelated required report fields.
                columns=','.join('['+field+']' for field in data[name][0])
                db.execute('SELECT TOP 0 '+columns+' INTO #'+name+' FROM '+table)
                db.cursor().executemany('INSERT INTO #'+name+' VALUES ('+
                    ','.join('?' for _ in data[name][0])+')',
                    [tuple(row.values()) for row in data[name]])
            db.execute('CREATE TABLE #Products(SKUCode nvarchar(50)); CREATE TABLE #Locations(WHCode nvarchar(50))')
            auth=';WITH cte_SKUs AS (SELECT SKUCode FROM #Products), cte_WhCodes AS (SELECT WHCode FROM #Locations) '
            for case in cases():
                payload=next(r['payload'] for r in requests if r['id']==case['id'])
                query=request_queries(auth,payload,{name:compiled[case['id']] for name in
                    ('GitCount','GitGrid','GitTransporter')})['child-transporter-count']
                (target/(case['id']+'.sql')).write_text(query)
                db.execute('DELETE FROM #Products; DELETE FROM #Locations')
                # Duplicate scope rows deliberately exercise native GROUP BY collapse.
                for code in case['products']*2:db.execute('INSERT INTO #Products VALUES (?)',code)
                for code in case['locations']*2:db.execute('INSERT INTO #Locations VALUES (?)',code)
                actual=int(db.execute(query).fetchone()[0])
                result['cases'].append(dict(**case,actual=actual,passed=actual==case['expected']))
                assert actual==case['expected'],case['id']
        result['status']='PASS'
    finally:
        result['proof_sha256']=file_sha(Path(__file__))
        result['fixture_sha256']=file_sha(Path(__file__).resolve().parents[1]/'mta/runtime/test_git_count_cases.py')
        (target/'receipt.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':main()
