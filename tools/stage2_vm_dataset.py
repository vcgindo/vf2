"""Bounded original VM source capture; superseded synthetic tools remain held."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import gzip

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.stage2_dataset import query,sq,encode

SOURCE=Path('E:/vflow_backup_dump')
DEST=Path('D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002')
FILES=Path('D:/freshvcf-build/sqlserver/stage2-vm-dataset-20261003-002')
ROLES=('Importer','BPR','BTR','DBM','Interface','IntermediateDB','Vendor','Distributor')
REQUIRED_ROLES=('Importer','BPR','BTR','DBM')
DATABASES={r:'VFTEST_Fresh_S2_VM_20261003_002_'+r for r in ROLES}
RESERVE=16*1024**3


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024**2),b''):h.update(chunk)
    return h.hexdigest()


def connect(database='master'):
    import pyodbc
    if database not in ('master',*DATABASES.values()):raise ValueError('Unowned target')
    return pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
        f'DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes',autocommit=True,timeout=10)


def write(name,value):
    DEST.mkdir(parents=True,exist_ok=True)
    target=DEST/name
    temporary=target.with_suffix(target.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,default=str),encoding='utf-8')
    temporary.replace(target)


def capture(*,roles=ROLES,manifest_name='dataset-manifest.json',pin_original=False):
    if (DEST/'manifest-seal.json').exists():raise ValueError('Sealed dataset; capture cannot mutate it')
    from parity.legacy_isolation import exclusive_replay
    os.environ['VFTEST_PROFILE']='fresh'
    DEST.mkdir(parents=True,exist_ok=True);FILES.mkdir(parents=True,exist_ok=True)
    manifest_path=DEST/manifest_name
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else dict(
        version=2,identity=DEST.name,origin='human-supplied-original-vm-backups',
        authority='E:/vflow_backup_dump; preserved application F:/VFlow_Source_Backup',
        engine_execution=False,sources=[])
    with exclusive_replay(validate_schema=False),connect() as master:
        manifest['sql_version']=query(master,"SELECT CAST(SERVERPROPERTY('ProductVersion') AS varchar) AS version")[0]['version']
        manifest['missing_roles']=[r for r in REQUIRED_ROLES if not (SOURCE/f'Demo_{r}_1.bak').exists()]
        manifest['optional_roles_not_supplied']=[r for r in ROLES if r not in REQUIRED_ROLES and not (SOURCE/f'Demo_{r}_1.bak').exists()]
        for role in roles:
            original=SOURCE/f'Demo_{role}_1.bak'
            if not original.exists():continue
            source='Demo_'+role+'_1';target=DATABASES[role]
            previous=next((s for s in manifest['sources'] if s['source']==source),None)
            pin_this=pin_original or bool(previous and previous.get('capture_mode')=='original-byte-pin-and-readonly-restore')
            frozen=original if pin_this else DEST/'backups'/original.name
            if not pin_this:frozen.parent.mkdir(exist_ok=True)
            before=original.stat(); original_sha=sha(original)
            if frozen.exists():
                if sha(frozen)!=original_sha:raise ValueError('Changed source; preserve old attempt and use new identity')
            else:
                if shutil.disk_usage(DEST).free < before.st_size+RESERVE:raise ValueError('Insufficient capacity to freeze backup')
                with original.open('rb') as src,frozen.open('xb') as dst:shutil.copyfileobj(src,dst,4*1024**2)
            after=original.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns) or sha(frozen)!=original_sha:
                raise ValueError('Original changed during capture or copied bytes differ')
            print('Frozen',source,original_sha,flush=True)
            headers=query(master,'RESTORE HEADERONLY FROM DISK=?',str(frozen))
            if len(headers)!=1:raise ValueError('Exactly one backup set required')
            header=headers[0]
            if header['DatabaseName']!=source or header['BackupType']!=1 or header['Position']!=1 or header['IsDamaged']:
                raise ValueError('Unexpected backup identity/type/damage')
            if int(manifest['sql_version'].split('.')[0])<header['SoftwareVersionMajor']:raise ValueError('Server older than backup')
            filelist=query(master,'RESTORE FILELISTONLY FROM DISK=?',str(frozen))
            # These VM originals do not contain backup checksums. Do not invent a
            # checksum requirement or downgrade a failed VERIFYONLY to a pass.
            query(master,'RESTORE VERIFYONLY FROM DISK=?',str(frozen))
            owner=FILES/(target+'.owner.json')
            expected=dict(database=target,backup_sha256=original_sha,source=source)
            exists=query(master,'SELECT DB_ID(?) AS id',target)[0]['id'] is not None
            if exists:
                if not owner.exists() or json.loads(owner.read_text())!=expected:raise ValueError('Unowned existing target')
            else:
                needed=sum(f['Size'] for f in filelist)
                if shutil.disk_usage(FILES).free<needed+RESERVE:raise ValueError('Insufficient restore capacity')
                moves=[]
                for i,item in enumerate(filelist):
                    if item['Type'] not in ('D','L'):raise ValueError('Unsupported file type')
                    path=FILES/(target+'_'+str(i)+('.ldf' if item['Type']=='L' else '.mdf'))
                    moves.append("MOVE N'"+item['LogicalName'].replace("'","''")+"' TO N'"+str(path).replace("'","''")+"'")
                query(master,'RESTORE DATABASE '+sq(target)+' FROM DISK=? WITH '+','.join(moves)+', RECOVERY',str(frozen))
                owner.write_text(json.dumps(expected),encoding='utf-8')
            physical=query(master,'SELECT physical_name FROM sys.master_files WHERE database_id=DB_ID(?)',target)
            if not physical or any(not Path(r['physical_name']).resolve().is_relative_to(FILES.resolve()) for r in physical):raise ValueError('Unexpected restored file path')
            query(master,'ALTER DATABASE '+sq(target)+' SET READ_ONLY')
            entry=dict(**expected,original=str(original),bytes=before.st_size,header=header,files=filelist,
                verifyonly='PASS',backup_checksums=bool(header['HasBackupChecksums']),tables=[],
                capture_mode='original-byte-pin-and-readonly-restore' if pin_this else 'owned-copy-and-readonly-restore')
            with connect(target) as clone:
                tables=query(clone,'SELECT s.name AS schema_name,t.name AS table_name FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id WHERE t.is_ms_shipped=0 ORDER BY s.name,t.name')
                for table in tables:
                    qualified=sq(table['schema_name'])+'.'+sq(table['table_name'])
                    columns=query(clone,'SELECT c.name,t.name AS type,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE c.object_id=OBJECT_ID(?) ORDER BY c.column_id',qualified)
                    count=query(clone,'SELECT COUNT_BIG(*) AS n FROM '+qualified)[0]['n']
                    entry['tables'].append(dict(**table,columns=columns,count=count))
                entry['last_batch']=query(clone,'SELECT * FROM dbo.LastBatchRunTbl') if any(t['table_name']=='LastBatchRunTbl' for t in tables) else None
            if sha(original)!=original_sha:raise ValueError('Original changed during restore')
            if previous:
                if previous['backup_sha256']!=original_sha:raise ValueError('Cannot replace a frozen source in this dataset')
                old_tables={(t['schema_name'],t['table_name']):t for t in previous['tables']}
                for table in entry['tables']:
                    old=old_tables[(table['schema_name'],table['table_name'])]
                    if old['columns']!=table['columns'] or old['count']!=table['count']:raise ValueError('Read-only source inventory drift')
                    table.update({k:old[k] for k in ('file','sha256','values_sha256','null_counts','order','disposition') if k in old})
            manifest['sources']=[s for s in manifest['sources'] if s['source']!=source]+[entry]
            write(manifest_name,manifest)
            print('Restored/inventoried',source,len(entry['tables']),sum(t['count'] for t in entry['tables']),flush=True)
    return manifest


def selected_tables():
    # Union of existing report consumer bindings, plus direct projections and
    # ancillary/config/history inputs. Unselected tables remain fully preserved
    # in the frozen backup and read-only restored database, not discarded.
    from tools.stage2_consumer_load import PREFIXES,PROJECTIONS
    catalogue=json.loads((ROOT/'baseline/production-state-schema.json').read_text())
    result={tuple(v) for k,v in catalogue['bindings'].items() if k.startswith(PREFIXES)}
    result.update(('BPR',name) for name in PROJECTIONS.values())
    result.update({('Importer','InTransitData'),('BPR','BPRReport_RemarkDetails'),
        ('BTR','RationingHistory'),('Importer','ui_ReportColumnTypes'),
        ('Importer','PRODUCT_PERMISSION'),('Importer','LOCATION_PERMISSION'),
        ('BPR','ui_ReportConfigurations'),('BPR','DownloadableUIReportSettings'),
        ('BPR','ColorSequence'),('BPR','BPRSettingsTbl'),('Importer','ImporterSettingsTbl')})
    # DBM's existing grid/history readers declare this finite dependency union.
    # Internal order/suspension calculation scratch remains preserved in backups.
    dbm_reports={'DBMMaster','Suggestions','NormAcceptanceTbl','SKUDescriptionTbl',
        'SiteDescriptionTbl','ReasonCodes','SkuAttributeData','SkuLocAttributeData',
        'LocationAttributeData','LastBatchRunTbl','DailyConsumption','SuspendHistory',
        'NormChangeLogTbl','SuspendStockType','SuspendConsumptionType','SuggestionsLog'}
    result={pair for pair in result if pair[0]!='DBM' or pair[1] in dbm_reports}
    # Neither is read by the existing Stage2 presentation modules. They are F2
    # calculation/other-workflow dependencies, not missing UI fixture inputs.
    result-={('Distributor','DistributorList'),('SyntheticMetadata','OrderIdentity')}
    return {(r,n.casefold()) for r,n in result}


def export():
    if (DEST/'manifest-seal.json').exists():raise ValueError('Sealed dataset; export cannot mutate it')
    manifest=json.loads((DEST/'dataset-manifest.json').read_text())
    supplied={s['source'].removeprefix('Demo_').removesuffix('_1') for s in manifest['sources']}
    manifest['missing_roles']=[r for r in REQUIRED_ROLES if r not in supplied]
    manifest['optional_roles_not_supplied']=[r for r in ROLES if r not in REQUIRED_ROLES and r not in supplied]
    selected=selected_tables()
    for source in manifest['sources']:
        role=source['source'].removeprefix('Demo_').removesuffix('_1')
        with connect(source['database']) as clone:
            if query(clone,"SELECT DATABASEPROPERTYEX(DB_NAME(),'Updateability') AS mode")[0]['mode']!='READ_ONLY':raise ValueError('Source clone changed')
            for table in source['tables']:
                if (role,table['table_name'].casefold()) not in selected:
                    table['disposition']='Preserved in frozen backup/clone; outside existing Stage2 consumer input union.'
                    continue
                path=DEST/'tables'/source['source']/(table['schema_name']+'.'+table['table_name']+'.jsonl.gz')
                path.parent.mkdir(parents=True,exist_ok=True)
                if table.get('sha256'):
                    if sha(path)!=table['sha256']:raise ValueError('Frozen export drift')
                    continue
                if path.exists():raise ValueError('Unfinished export retained; inspect before assigning a new attempt')
                if shutil.disk_usage(DEST).free<RESERVE:raise ValueError('Capacity reserve reached')
                cols=[f'CONVERT(nvarchar(40),{sq(c["name"])},126)' if c['type']=='datetime2' else sq(c['name']) for c in table['columns']]
                cursor=clone.cursor();cursor.execute('SELECT '+','.join(cols)+' FROM '+sq(table['schema_name'])+'.'+sq(table['table_name']))
                h=hashlib.sha256();count=0;nulls=[0]*len(cols)
                with gzip.open(path,'wb',compresslevel=1) as out:
                    while True:
                        batch=cursor.fetchmany(1000)
                        if not batch:break
                        for row in batch:
                            raw=encode(row);out.write(raw);h.update(raw);count+=1
                            for i,v in enumerate(row):
                                if v is None:nulls[i]+=1
                cursor.close()
                if count!=table['count']:raise ValueError('Frozen source population changed')
                table.update(file=path.relative_to(DEST).as_posix(),sha256=sha(path),values_sha256=h.hexdigest(),
                    null_counts=nulls,order='Frozen extraction ordinal; no invented business ordering')
                write('dataset-manifest.json',manifest)
                print('Exported',source['source'],table['table_name'],count,flush=True)
    manifest['inventory_sha256']=sha(ROOT/'docs/audit-2026-10-01/PAGE_INTERACTION_INVENTORY.csv')
    write('dataset-manifest.json',manifest)


def reconcile():
    manifest=json.loads((DEST/'dataset-manifest.json').read_text())
    captured=json.loads((DEST/'capture-DBM.json').read_text())
    if captured['identity']!=manifest['identity'] or captured['origin']!=manifest['origin']:raise ValueError('Capture identity differs')
    for source in captured['sources']:
        if source['source']!='Demo_DBM_1':raise ValueError('Unexpected separate capture source')
        prior=[s for s in manifest['sources'] if s['source']==source['source']]
        if len(prior)>1:raise ValueError('Duplicate source')
        if prior:
            if prior[0]['backup_sha256']!=source['backup_sha256']:raise ValueError('Different DBM capture')
            fields=('schema_name','table_name','columns','count')
            if [{k:t[k] for k in fields} for t in prior[0]['tables']]!=[{k:t[k] for k in fields} for t in source['tables']]:raise ValueError('Capture inventory differs')
        else:
            if (DEST/'manifest-seal.json').exists():raise ValueError('Cannot add to sealed dataset')
            manifest['sources'].append(source)
    supplied={s['source'].removeprefix('Demo_').removesuffix('_1') for s in manifest['sources']}
    manifest['missing_roles']=[r for r in REQUIRED_ROLES if r not in supplied]
    manifest['optional_roles_not_supplied']=[r for r in ROLES if r not in REQUIRED_ROLES and r not in supplied]
    if manifest!=json.loads((DEST/'dataset-manifest.json').read_text()):write('dataset-manifest.json',manifest)
    print('DBM capture reconciled')


def seal():
    from tools.stage2_vm_contract import roster,sealed
    manifest=json.loads((DEST/'dataset-manifest.json').read_text())
    supplied=[s['source'].removeprefix('Demo_').removesuffix('_1') for s in manifest['sources']]
    if len(set(supplied))!=len(supplied) or set(REQUIRED_ROLES)-set(supplied):raise ValueError('Required source set incomplete/ambiguous')
    selected=selected_tables()
    for source in manifest['sources']:
        role=source['source'].removeprefix('Demo_').removesuffix('_1')
        for table in source['tables']:
            if (role,table['table_name'].casefold()) in selected:
                if not {'file','sha256','values_sha256','null_counts','count','order'}<=table.keys():raise ValueError('Selected export incomplete')
                if len(table['null_counts'])!=len(table['columns']):raise ValueError('NULL vector incomplete')
    tables=roster(manifest)
    if manifest['missing_roles']:raise ValueError('Required source absent')
    if (DEST/'manifest-seal.json').exists():
        sealed(DEST);print('Existing manifest seal verified');return
    for source,table in tables.values():
        if sha(DEST/table['file'])!=table['sha256']:raise ValueError('Frozen file changed')
    write('manifest-seal.json',dict(identity=manifest['identity'],manifest_sha256=sha(DEST/'dataset-manifest.json'),tables=len(tables),rows=sum(t['count'] for s,t in tables.values())))
    print('Sealed',len(tables),'exports')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['capture','export','reconcile','seal'])
    parser.add_argument('--dbm-completed-copy',action='store_true',help='Pin completed DBM original and restore separately; preserve interrupted capture')
    args=parser.parse_args()
    if args.command=='capture':
        capture(roles=('DBM',),manifest_name='capture-DBM.json',pin_original=True) if args.dbm_completed_copy else capture()
    elif args.command=='export':export()
    elif args.command=='reconcile':reconcile()
    else:seal()
