"""Read retained April SQL charts and compare complete prepared datasets.

Executes only canonical consumer SELECTs against verified read-only owned DBs.
No calculation producer, restore, replay, or source write is executed.
"""
import json,sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.stage2_vm_dataset import connect,DATABASES,DEST,FILES
from tools.stage2_vm_contract import sealed
from parity.verify_expedite_charts import selected_sql,SECTIONS,CTE,SOURCE_SHA


def main():
    exported=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
    target=Path(sys.argv[2]).resolve()
    assert target.is_relative_to(Path('D:/freshvcf-build/evidence').resolve()) and not target.exists()
    target.mkdir()
    assert exported['run']=='bfd75b4b-a9df-4a08-82d3-852e3324b623'
    assert exported['business_date']=='2026-04-07'
    assert exported['source_digest']=='4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73'
    manifest,manifest_sha=sealed(DEST)
    assert manifest_sha=='afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836'
    for role in ('BPR','Importer'):
        source=next(s for s in manifest['sources'] if s['source']=='Demo_'+role+'_1')
        owner=json.loads((FILES/(DATABASES[role]+'.owner.json')).read_text())
        assert owner=={k:source[k] for k in ('database','backup_sha256','source')}
        with connect(DATABASES[role]) as db:
            assert tuple(db.execute("SELECT DB_NAME(),DATABASEPROPERTYEX(DB_NAME(),'Updateability')").fetchone())==(source['database'],'READ_ONLY')
    # selected_sql only extracts pinned text; its returned producer SQL is
    # deliberately discarded and never executed by this consumer proof.
    charts=selected_sql()[1]
    replacements={name:'['+DATABASES[role]+'].dbo.['+table+']' for name,role,table in
        [('#Pick','BPR','vf_PickListReport'),('#Expedite','BPR','ExpediteDispatches'),
         ('#Master','BPR','BPRMaster'),('#LocDesc','Importer','SiteDescriptionTbl'),
         ('#Loc','Importer','LocationAttributeData')]}
    def cte(name,column,weights):
        assert all(isinstance(code,str) and isinstance(n,int) and 0<n<1000 for code,n in weights.items())
        values=["(N'"+code.replace("'","''")+"')" for code,n in sorted(weights.items()) for _ in range(n)]
        body='SELECT code FROM (VALUES '+','.join(values)+') V(code)' if values else 'SELECT CAST(NULL AS nvarchar(100)) WHERE 1=0'
        return name+'('+column+') AS ('+body+')'
    results=[]
    bag=lambda rows:Counter(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in rows)
    with connect(DATABASES['BPR']) as db:
        db.timeout=180
        for case in exported['cases']:
            prefix=';WITH '+cte('cte_SKUs','SKUCode',case['products'])+','+cte('cte_WhCodes','WHCode',case['locations'])+' '
            for kind,queries in charts.items():
                tables=[];comparisons=[]
                for family,original in zip(SECTIONS[kind],queries):
                    assert original.startswith(CTE)
                    query=prefix+original[len(CTE):]
                    for old,new in replacements.items():query=query.replace(old,new)
                    assert '#' not in query
                    cursor=db.execute(query)
                    columns=[dict(name=c[0],type='int32' if c[1] is int else 'string') for c in cursor.description]
                    expected=[dict(zip([c['name'] for c in columns],row)) for row in cursor.fetchall()]
                    actual=case['charts'][kind][family]
                    missing=bag(expected)-bag(actual);extra=bag(actual)-bag(expected)
                    comparisons.append(dict(family=family,rows=len(expected),missing=sum(missing.values()),extra=sum(extra.values()),ordered_equal=actual==expected))
                    tables.append(dict(columns=columns,rows=expected))
                    (target/(case['name']+'-'+kind+'-'+family+'.sql')).write_text(query,encoding='utf-8')
                (target/(case['name']+'-'+kind+'-dataset.json')).write_text(json.dumps(dict(tables=tables),ensure_ascii=False),encoding='utf-8')
                results.append(dict(case=case['name'],kind=kind,comparisons=comparisons))
    passed=all(c['missing']==c['extra']==0 for r in results for c in r['comparisons'])
    result=dict(status='BAGS_MATCH_ORDER_AND_WIRE_REQUIRE_QUALIFICATION' if passed else 'FAILED',
        results=results,source_sha256=SOURCE_SHA,manifest_sha256=manifest_sha,engine_execution=False,persistent_writes=False)
    (target/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
    if not passed:raise AssertionError('Retained SQL chart values differ; see retained complete datasets')


if __name__=='__main__':main()
