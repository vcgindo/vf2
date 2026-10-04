"""Read-only qualification of the retained April request source; no replay or restore."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.stage2_vm_dataset import connect,DATABASES,DEST,FILES
from tools.stage2_vm_contract import sealed
from tools.stage2_dataset import query


def main():
    manifest, manifest_sha = sealed(DEST)
    source = next(s for s in manifest['sources'] if s['source']=='Demo_BPR_1')
    table = next(t for t in source['tables'] if t['table_name']=='OpenExpediteRequests')
    owner = json.loads((FILES/(DATABASES['BPR']+'.owner.json')).read_text())
    expected_owner = {k:source[k] for k in ('database','backup_sha256','source')}
    assert owner == expected_owner
    assert table['count']==0 and table['schema_name']=='dbo'
    with connect(DATABASES['BPR']) as db:
        identity = db.execute("SELECT DB_NAME(),DATABASEPROPERTYEX(DB_NAME(),'Updateability')").fetchone()
        assert tuple(identity)==(source['database'],'READ_ONLY')
        columns = query(db,'SELECT c.name,t.name AS type,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity '
            'FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id '
            "WHERE c.object_id=OBJECT_ID('dbo.OpenExpediteRequests') ORDER BY c.column_id")
        assert columns==table['columns']
        rows = query(db,'SELECT * FROM dbo.OpenExpediteRequests')
        assert rows==[]
    acquired = Path('D:/freshvcf-build/evidence/planning-prepared-20261005-001/april-request-history.json').read_bytes()
    assert hashlib.sha256(acquired).hexdigest()=='0aeb5e2b97699d7516bf15850a1d1b0aa450522e362a765bd413615f1fb3c3c1'
    previous = json.loads(acquired)
    assert previous['database']==source['database'] and previous['rows']==rows
    assert previous['columns']==[c['name'] for c in columns]
    value = dict(version='planning-april-empty-requests-v1',run_id='bfd75b4b-a9df-4a08-82d3-852e3324b623',
        business_date='2026-04-07',fixture_source_digest='4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73',
        manifest_sha256=manifest_sha,source=owner,table='dbo.OpenExpediteRequests',columns=columns,rows=rows,
        acquisition_sha256=hashlib.sha256(acquired).hexdigest(),read_only=True)
    raw=(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
    target=Path(sys.argv[1])
    if target.exists(): assert target.read_bytes()==raw
    else: target.write_bytes(raw)
    print(json.dumps(dict(status='PASS',sha256=hashlib.sha256(raw).hexdigest(),rows=0,manifest_sha256=manifest_sha)))


if __name__=='__main__':main()
