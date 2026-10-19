"""External, one-day synthetic benchmark; never operates a serving installation.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import argparse
import csv
import gzip
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE_EVIDENCE = Path('D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019')
EVIDENCE = Path(os.environ.get('VF_LARGE_BENCHMARK_EVIDENCE', str(BASE_EVIDENCE))).resolve()
if not EVIDENCE.is_relative_to(BASE_EVIDENCE.resolve()):
    raise ValueError('Benchmark attempt must stay inside the original evidence root')
SOURCE = 'VFTEST_Fresh_S2_VM_20261003_002_'
ROLES = ('Importer', 'BPR', 'BTR', 'DBM')
DAY = '2026-04-08'
FIELDS = ('SKUCode', 'WhCode', 'Stock', 'Consumption', 'GIT', 'Receipts', 'PSO', 'ReportDate')


def dump(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, default=str)
        stream.write('\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def connect(database='master'):
    import pyodbc
    pyodbc.pooling = False
    c = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
        f'DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes',
        autocommit=True, timeout=10)
    c.timeout = 120
    return c


def read(cursor, sql, *parameters):
    cursor.execute(sql, *parameters)
    fields = [c[0] for c in cursor.description]
    return [dict(zip(fields, row)) for row in cursor.fetchall()]


def next_row(row):
    """A synthetic conserved successor; no computed Norm/recommendation inputs.

    Keep NULL availability. For known stocks retain nonnegative source receipts,
    cap source consumption at available stock, and derive the next closing stock.
    A NULL stock stays NULL, leaving missing-input handling to the real engine.
    """
    result = dict(row)
    stock, consumed, received = row['Stock'], row['Consumption'], row['Receipts']
    if stock is not None:
        receipts = max(received or 0, 0)
        consumption = min(max(consumed or 0, 0), max(stock + receipts, 0))
        result['Stock'] = stock + receipts - consumption
        result['Consumption'] = None if consumed is None else consumption
        result['Receipts'] = None if received is None else receipts
    result['ReportDate'] = DAY
    return result


def cell(value):
    if value is None:
        return r'\N'
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, bool):
        return str(int(value))
    return str(value)


def export(cursor, table, path):
    """Full typed raw/source population, with explicit deterministic row order."""
    cursor.execute('SELECT TOP 0 * FROM dbo.[' + table + ']')
    fields = [c[0] for c in cursor.description]
    columns = read(cursor, "SELECT c.name,t.name AS type,c.max_length,c.precision,c.scale,c.is_nullable AS nullable "
        "FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id "
        "WHERE c.object_id=OBJECT_ID(?) ORDER BY c.column_id", 'dbo.' + table)
    # Source tables have no occurrence ordinal. Declare a stable full-value sort;
    # tied identical rows remain duplicate occurrences in both readers.
    order = ','.join('[' + c['name'] + ']' for c in columns
        if c['type'] not in ('text', 'ntext', 'image', 'xml'))
    cursor.execute('SELECT * FROM dbo.[' + table + '] ORDER BY ' + order)
    count = 0
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\r\n')
        writer.writerow(fields)
        while True:
            records = cursor.fetchmany(4096)
            if not records:
                break
            for row in records:
                writer.writerow([cell(v) for v in row])
            count += len(records)
    return dict(file=path.name, rows=count, columns=columns, sha256=sha(path),
                order='full source-column value order; identical duplicates retained')


def freeze():
    if (EVIDENCE / 'case.json').exists():
        raise ValueError('Frozen case already exists; do not regenerate')
    pack = EVIDENCE / 'csv'
    pack.mkdir()
    owner = str(uuid4())
    metadata = dict(schema='large-data-synthetic-day-v1', owner=owner,
        created_utc=datetime.now(timezone.utc).isoformat(),
        authority='Direct human: Use synthetic next-day benchmark; stop after legacy day one',
        opening_date='2026-04-07', business_date=DAY,
        source_dataset='stage2-vm-dataset-20261003-002',
        source_manifest_sha256=sha('D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/dataset-manifest.json'),
        source_databases={r: SOURCE+r for r in ROLES},
        source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        excluded=['GulfOil customer CSV-to-Interface/Intermediate source preprocessing',
            'external notification delivery and operational backup jobs',
            'modern execution, cross-engine parity and browser timings until later release'],
        unchanged=['3005 and its databases/services', 'four large SQL source databases',
                   'modern installation controlled by human', 'frontend and MTO'],
        recipe='For each known Stock: retain nonnegative Receipts; Consumption=min(max(source Consumption,0),max(Stock+Receipts,0)); next Stock=Stock+Receipts-Consumption. Preserve NULL cells, codes, GIT, PSO and duplicate rows. NULL Stock rows retain their source values; ordinary missing-input policy owns them.',
        csv=dict(encoding='UTF-8', delimiter=',', null_token=r'\N', newline='CRLF'),
        opening_source='Exact pinned original four SQL backup images and retained ordered typed history exports; no calculated next-day outputs supplied',
        populations={}, configuration={})
    c = connect()
    try:
        q = c.cursor()
        states = read(q, "SELECT name,is_read_only,state_desc FROM sys.databases WHERE name LIKE 'VFTEST_Fresh_S2_VM_20261003_002_%'")
        if len(states) != 4 or any(not r['is_read_only'] or r['state_desc'] != 'ONLINE' for r in states):
            raise ValueError('All four protected sources must remain ONLINE/READ_ONLY')
        for role in ROLES:
            q.execute('USE [' + SOURCE + role + ']')
            last = q.execute('SELECT CONVERT(date,LastRunDate) FROM dbo.LastBatchRunTbl').fetchall()
            if len(last) != 1 or str(last[0][0]) != metadata['opening_date']:
                raise ValueError('Opening date differs: ' + role)
            settings = {}
            for table in ('ImporterSettingsTbl', 'BPRSettingsTbl', 'DBMSettingsTbl', 'VFSettings'):
                if q.execute("SELECT OBJECT_ID(?, 'U')", 'dbo.'+table).fetchval():
                    settings[table] = read(q, 'SELECT * FROM dbo.[' + table + '] ORDER BY Parameter')
            metadata['configuration'][role] = settings
        q.execute('USE [' + SOURCE + 'Importer]')
        for table in ('MasterDataRaw', 'MasterData', 'SkuAttributeData', 'LocationAttributeData',
                      'SkuLocAttributeData', 'SOBDataRaw', 'MOQDataRaw', 'LocationVehicleMaster'):
            if q.execute("SELECT OBJECT_ID(?, 'U')", 'dbo.'+table).fetchval():
                metadata['populations'][table] = export(q, table, pack/(table+'.csv'))
        daily_source = read(q, 'SELECT '+','.join(FIELDS)+' FROM dbo.DailyDataRaw ORDER BY '+','.join(FIELDS))
        if len(daily_source) != 97097:
            raise ValueError('Frozen source daily row count changed')
        source_dates = {str(r['ReportDate']) for r in daily_source}
        if source_dates != {metadata['opening_date']}:
            raise ValueError('Mixed daily source dates')
        daily = [next_row(row) for row in daily_source]
        known = 0
        for old, new in zip(daily_source, daily):
            if old['Stock'] is not None:
                assert new['Stock'] == old['Stock'] + (new['Receipts'] or 0) - (new['Consumption'] or 0)
                known += 1
        path = pack/'DailyDataRaw.csv'
        with path.open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\r\n')
            writer.writeheader()
            for row in daily:
                writer.writerow({k: cell(v) for k,v in row.items()})
        sys.path.insert(0, str(ROOT))
        from mta.application.production_csv import parse_csv
        from mta.application.production_csv_contract import feeds
        from mta.application.native_daily_contract import FEED_SCHEMA
        actual, ordinals = parse_csv(path.read_bytes(), feeds(FEED_SCHEMA)['DailyDataRaw.csv']['columns'], path.name)
        expected = [{k:str(v) if isinstance(v,date) else v for k,v in row.items()} for row in daily]
        if actual != expected or len(ordinals) != len(daily):
            raise ValueError('Production CSV reader changed values/types/NULLs/order')
        metadata['populations']['DailyDataRaw'] = dict(file=path.name, sha256=sha(path), rows=len(daily),
            known_stock_rows=known, null_stock_rows=len(daily)-known,
            positive_consumption_rows=sum((r['Consumption'] or 0)>0 for r in daily),
            positive_receipt_rows=sum((r['Receipts'] or 0)>0 for r in daily),
            complete_production_csv_parser_readback=True, all_known_stock_ledger_identities=True)
        manifest = json.loads(Path('D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/dataset-manifest.json').read_text(encoding='utf-8-sig'))
        metadata['backup_sources'] = [{k:v for k,v in s.items() if k in
            ('source','database','backup','backup_sha256','backup_bytes','backup_path','path','backup_header','header')}
            for s in manifest['sources']]
        dump(EVIDENCE/'case.json', metadata)
        print(json.dumps(dict(status='CASE_FROZEN', case=str(EVIDENCE/'case.json'),
            case_sha256=sha(EVIDENCE/'case.json'), daily=metadata['populations']['DailyDataRaw']),indent=2))
    finally:
        c.close()


def bindings():
    case = json.loads((EVIDENCE/'case.json').read_text())
    execution_owner = EVIDENCE/'execution-owner.json'
    if execution_owner.exists():
        attempt = json.loads(execution_owner.read_text())
        if attempt['case_sha256'] != sha(EVIDENCE/'case.json'):
            raise ValueError('Attempt changed the frozen business case')
        case = dict(case, owner=attempt['owner'])
    owner = UUID(case['owner'])
    from parity import legacy_isolation as isolation
    if isolation._lease is not None:
        raise ValueError('Cannot replace an active owner')
    isolation.MAPPING.clear()
    isolation.MAPPING.update({'VFTEST_'+r: 'VFTEST_Fresh_Benchmark_'+owner.hex+'_'+r
                             for r in isolation.ROLES})
    isolation.DATA = Path('D:/freshvcf-build/sqlserver')/('large-data-benchmark-'+str(owner))
    isolation.PRINCIPAL = 'vf_benchmark_'+owner.hex
    os.environ['VFTEST_PROFILE'] = 'fresh'
    return case, isolation


def verify_pack():
    """Compare every exported source value after the actual production parser."""
    from mta.application.production_csv import parse_csv
    case = json.loads((EVIDENCE/'case.json').read_text())
    results = {}
    with connect(SOURCE+'Importer') as c:
        for table, item in case['populations'].items():
            path = EVIDENCE/'csv'/item['file']
            if sha(path) != item['sha256']:
                raise ValueError('Frozen CSV changed: '+table)
            if table == 'DailyDataRaw':
                results[table] = item
                continue
            columns = item['columns']
            parser_columns = [{**col,'parameters':str(col['precision'])+','+str(col['scale'])
                if col['type'] in ('decimal','numeric') else ''} for col in columns]
            actual, ordinals = parse_csv(path.read_bytes(), parser_columns, path.name)
            order = ','.join('['+x['name']+']' for x in columns if x['type'] not in ('text','ntext','image','xml'))
            q = c.cursor()
            q.execute('SELECT * FROM dbo.['+table+'] ORDER BY '+order)
            count = 0
            for record in q:
                expected = {col['name']:value.isoformat() if isinstance(value,(date,datetime)) else
                    format(value,'f') if isinstance(value,Decimal) else value
                    for col,value in zip(columns,record)}
                if count >= len(actual) or actual[count] != expected:
                    raise ValueError('CSV typed value/order mismatch: '+table+' row'+str(count+1))
                count += 1
            if count != len(actual) or count != item['rows'] or len(ordinals)!=count:
                raise ValueError('CSV occurrence count mismatch: '+table)
            results[table] = dict(rows=count, complete_typed_values_NULLs_duplicates_ordinals='PASS',sha256=item['sha256'])
            del actual, ordinals
    result = dict(status='PASS',case_sha256=sha(EVIDENCE/'case.json'),populations=results,
        limitation='Raw CSV/parser proof plus pinned full legacy opening/history backups. Not a fresh modern native initialization or whole assembled modern feed-batch acceptance.')
    dump(EVIDENCE/'csv-pack-verification.json',result)
    print(json.dumps(result,indent=2))


def complete_pack():
    """Freeze every daily feed; source-backed carry populations are explicit."""
    from mta.application.production_csv import parse_csv
    from mta.application.production_csv_contract import feeds
    from mta.application.native_daily_contract import FEED_SCHEMA
    case = json.loads((EVIDENCE/'case.json').read_text())
    mapping = dict(MasterDataRawNonNMS='MasterDataRawNonNMS',NoNormMasterRaw='NoNormMasterRaw',
        AcceptedNorms='AcceptedNorms',OrderData='OrderDataRaw',OrderFeed='PSOData',
        SOBDataRaw='SOBDataRaw',MOQDataRaw1='MOQDataRaw1',MOQDataRaw2='MOQDataRaw2',
        InTransitRaw='InTransitDataRaw',Transporters='TransporterMaster',MasterDataRaw='MasterDataRaw')
    result = {}
    with connect(SOURCE+'Importer') as c:
        for filename, spec in feeds(FEED_SCHEMA).items():
            stem = Path(filename).stem
            path = EVIDENCE/'csv'/filename
            fields = [x['name'] for x in spec['columns']]
            if filename in ('DistributorTransactions.csv','VendorTransactions.csv'):
                # These subsystems are disabled by the selected canonical shell
                # configuration. No fake transaction or output is introduced.
                records = []
                source = 'Explicitly disabled canonical Vendor/Distributor system'
            elif stem == 'DailyDataRaw':
                records = None
                source = 'Frozen synthetic recipe in case.json'
            else:
                table = mapping[stem]
                q = c.execute('SELECT '+','.join('['+f+']' for f in fields)+' FROM dbo.['+table+'] ORDER BY '+','.join('['+f+']' for f in fields))
                records = [dict(zip(fields,row)) for row in q]
                source = SOURCE+'Importer.dbo.'+table
            if not path.exists():
                with path.open('x',encoding='utf-8',newline='') as stream:
                    writer = csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n')
                    writer.writeheader()
                    for row in records:
                        writer.writerow({k:cell(v) for k,v in row.items()})
            parsed, ordinals = parse_csv(path.read_bytes(),spec['columns'],filename)
            if records is not None:
                expected = [{k:cell(v) if isinstance(v,(date,datetime,Decimal)) else v for k,v in row.items()} for row in records]
                if parsed != expected:
                    raise ValueError('Complete production reader mismatch: '+filename)
            if len(parsed) != len(ordinals):
                raise ValueError('Occurrence mismatch')
            result[filename] = dict(rows=len(parsed),sha256=sha(path),source=source,
                complete_production_csv_parser_values_types_NULLs_duplicates_order='PASS')
        # Additional requirement stock is a real configured input, not a hidden
        # calculated seed. Freeze it separately; whole modern admission pending.
        table = 'AdditionalDataStockForReqCalc'
        result[table+'.csv'] = export(c.cursor(),table,EVIDENCE/'csv'/(table+'.csv'))
    batch = dict(schema='vectorflow-daily-csv-v1',batch_id='large-data-synthetic-20260408',
        business_date=DAY,feeds={name:'PRESENT' for name in feeds(FEED_SCHEMA)})
    dump(EVIDENCE/'csv'/'batch.json',batch)
    dump(EVIDENCE/'csv-pack.json',dict(case_sha256=sha(EVIDENCE/'case.json'),feeds=result,
        opening='Pinned complete four-database backup state/history; raw/master CSV exports additionally retained',
        limitation='CSV complete daily roster and typed parser proof; target-specific modern binding/opening assembly and modern admission remain step6, not claimed here'))
    print(json.dumps({'status':'RAW_CSV_PACK_READY','files':{k:v['rows'] for k,v in result.items()}},indent=2))


def create_targets():
    case, isolation = bindings()
    if (EVIDENCE/'targets.json').exists() or isolation.DATA.exists():
        raise ValueError('Target setup is single-use; preserve existing attempt')
    if shutil.disk_usage('D:/').free < 35*1024**3:
        raise ValueError('Insufficient storage for copied data plus20GiB free reserve')
    started = time.perf_counter()
    with isolation.raw_connection('master') as c:
        if any(c.execute('SELECT DB_ID(?)', d).fetchval() is not None for d in isolation.MAPPING.values()):
            raise ValueError('Namespace collision; no adoption/replacement permitted')
    from parity.provision_legacy import build, consume
    standard = build()
    # Same pinned site scratch extension used by the existing canonical runner.
    path = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/SiteSpecific/GulfOil/Intermediate_DBCreation.sql')
    baseline = json.loads((ROOT/'baseline/manifest.json').read_text())
    pin = next(r['sha256'] for r in baseline['engine_sources'] if Path(r['path']) == path)
    if sha(path) != pin:
        raise ValueError('Site scratch DDL changed')
    skipped = []
    with isolation.raw_connection(isolation.MAPPING['VFTEST_Intermediate']) as c:
        c.autocommit = False
        try:
            for index, batch in enumerate(re.split(r'(?im)^\s*GO\s*(?:--.*)?$', path.read_bytes().decode('cp1252')),1):
                if not batch.strip():
                    continue
                drop = re.search(r'(?im)^\s*DROP TABLE \[dbo\]\.\[([^]]+)\]\s*$', batch)
                if drop:
                    if c.execute("SELECT OBJECT_ID(?, 'U')", 'dbo.'+drop[1]).fetchval():
                        raise ValueError('Site schema attempts to replace an existing object')
                    rest = batch[:drop.start()]+batch[drop.end():]
                    if re.sub(r'/\*[\s\S]*?\*/|--[^\r\n]*','',rest).strip():
                        raise ValueError('Unexpected site DROP batch')
                    skipped.append(index)
                    continue
                consume(c.execute(isolation.bind_sql(batch)))
            c.commit()
        except Exception:
            c.rollback()
            raise
    result = dict(owner=case['owner'], case_sha256=sha(EVIDENCE/'case.json'),
        namespace=dict(isolation.MAPPING), data_directory=str(isolation.DATA),
        principal=isolation.PRINCIPAL, schemas=standard,
        site_schema_sha256=pin, absent_site_drop_batches=skipped,
        seconds=time.perf_counter()-started, business_days_executed=0)
    dump(EVIDENCE/'targets.json', result)
    print(json.dumps({k:v for k,v in result.items() if k!='schemas'},indent=2))


def initialize_targets():
    case, isolation = bindings()
    receipt = json.loads((EVIDENCE/'targets.json').read_text())
    if receipt['namespace'] != dict(isolation.MAPPING) or (EVIDENCE/'initialization.json').exists():
        raise ValueError('Unexpected or already initialized target')
    from parity.provision_legacy import consume, provision_execution_principal
    source = json.loads(Path('D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/dataset-manifest.json').read_text(encoding='utf-8-sig'))
    started = time.perf_counter()
    copied = []
    with isolation.raw_connection('master') as c:
        for role in ROLES:
            item = next(s for s in source['sources'] if s['database'] == SOURCE+role)
            backup = Path(item['original'])
            if backup.stat().st_size != item['bytes']:
                raise ValueError('Pinned backup length changed')
            actual = read(c.cursor(), 'RESTORE HEADERONLY FROM DISK=?', str(backup))
            if len(actual)!=1 or str(actual[0]['BackupSetGUID']).lower()!=item['header']['BackupSetGUID'].lower():
                raise ValueError('Pinned native backup identity changed')
            database = isolation.MAPPING['VFTEST_'+role]
            isolation.validate_files(c, database)
            moves = []
            for file in item['files']:
                suffix = '.mdf' if file['Type']=='D' else '_log.ldf'
                target = isolation.DATA/(database+suffix)
                if not target.resolve().is_relative_to(isolation.DATA.resolve()):
                    raise ValueError('Restore path outside owner directory')
                moves.append("MOVE N'"+file['LogicalName'].replace("'","''")+"' TO N'"+str(target).replace("'","''")+"'")
            # REPLACE applies only to the freshly-created, empty owner above;
            # never an existing source/serving/prior benchmark database.
            if c.execute('SELECT SUM(p.rows) FROM ['+database+'].sys.partitions p JOIN ['+database+'].sys.tables t ON p.object_id=t.object_id WHERE p.index_id IN (0,1)').fetchval() is None:
                raise ValueError('Owned schema missing')
            tick = time.perf_counter()
            consume(c.execute('RESTORE DATABASE ['+database+"] FROM DISK=N'"+str(backup).replace("'","''")+"' WITH REPLACE,RECOVERY,"+','.join(moves)))
            consume(c.execute('ALTER DATABASE ['+database+'] SET READ_WRITE'))
            isolation.validate_files(c, database)
            copied.append(dict(role=role, target=database, source_backup=str(backup),
                source_backup_sha256=item['backup_sha256'], backup_set_guid=item['header']['BackupSetGUID'],
                seconds=time.perf_counter()-tick))
            print(json.dumps(copied[-1]),flush=True)
        # A new disabled least-privileged login; restored users cannot redirect it.
        provision_execution_principal(c)
    checks = {}
    for role in ROLES:
        with isolation.raw_connection(isolation.MAPPING['VFTEST_'+role]) as c:
            last = c.execute('SELECT CONVERT(date,LastRunDate) FROM dbo.LastBatchRunTbl').fetchall()
            if len(last)!=1 or str(last[0][0])!=case['opening_date']:
                raise ValueError('Restored date differs')
            checks[role] = dict(last_date=str(last[0][0]), tables=c.execute('SELECT COUNT(*) FROM sys.tables').fetchval())
    with isolation.raw_connection(isolation.MAPPING['VFTEST_Importer']) as c:
        for table in ('MasterData','MasterDataRaw','SkuAttributeData','LocationAttributeData','SkuLocAttributeData'):
            count = c.execute('SELECT COUNT_BIG(*) FROM dbo.['+table+']').fetchval()
            if count != case['populations'][table]['rows']:
                raise ValueError('Restored population differs: '+table)
        # Real permission boundary: server resources and protected sources denied.
        consume(c.execute("EXECUTE AS LOGIN='"+isolation.PRINCIPAL+"' WITH NO REVERT"))
        denied = []
        for db in case['source_databases'].values():
            try:
                c.execute('SELECT TOP 0 * FROM ['+db+'].dbo.LastBatchRunTbl')
            except Exception:
                denied.append(db)
            else:
                raise ValueError('Benchmark principal can access a protected source')
    result = dict(status='INITIALIZED',owner=case['owner'],restores=copied,
        opening_checks=checks,protected_source_denials=denied,
        total_restore_and_verification_seconds=time.perf_counter()-started,
        proof='Native restore of the same pinned backup sets used by protected source; full archive identity plus opening/population checks, not an output parity claim',
        business_days_executed=0)
    dump(EVIDENCE/'initialization.json',result)
    print(json.dumps(result,indent=2))


def prepare_execution():
    case, isolation = bindings()
    canonical = Path('F:/VFlow_Local/local-runtime/mta-engine')
    destination = EVIDENCE/'canonical'
    if destination.exists():
        raise ValueError('Keep prior execution preparation; no replacement')
    settings = {}
    for relative in ('Engine/StdSettingsPre.bat','Engine/SiteSpecific/GulfOil/Settings.bat'):
        for line in (canonical/relative).read_text(encoding='utf-8-sig').splitlines():
            match = re.match(r'^\s*set\s+([A-Za-z_][\w]*)=(.*)$',line,re.I)
            if match:
                settings[match[1].upper()] = match[2].strip()
    for name in ('Engine','Scripts'):
        shutil.copytree(canonical/name,destination/name)
    bridge = ROOT/'tools/large_data_legacy_sqlcmd.py'
    replaced = []
    for path in (destination/'Engine').rglob('*.bat'):
        raw = path.read_bytes()
        text = raw.decode('utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'cp1252')
        if re.search(r'sqlcmd\.exe',text,re.I):
            text = re.sub(r'sqlcmd\.exe',lambda _: '"'+sys.executable+'" "'+str(bridge)+'"',text,flags=re.I)
            path.write_bytes(text.replace('\r\n','\n').replace('\n','\r\n').encode('cp1252'))
            replaced.append(path.relative_to(destination).as_posix())
    folders = {name:EVIDENCE/sub for name,sub in dict(LOGFOLDER='logs',OUTPUTFOLDER='outputs',
        REPORTSDOWNLOADLOC='downloads',INPUTFOLDER='csv',BACKUPFOLDER='backups',
        UIMODIFICATIONCLIENTLOGFOLDER='upload-logs').items()}
    for path in folders.values():
        path.mkdir(exist_ok=True)
    settings.update({k:str(v) for k,v in folders.items()})
    settings.update(ROOT=str(destination),SERVER='localhost',SITE='GulfOil',
        RUNDATE=DAY,RUNDATETIME=DAY+' 00:00:00',YEAR='2026',MONTH='04',DAY='08',HR='00',MIN='00',AMPM='',
        IMPORTERDATABASE=isolation.MAPPING['VFTEST_Importer'],DBMDATABASE=isolation.MAPPING['VFTEST_DBM'],
        BPRDATABASE=isolation.MAPPING['VFTEST_BPR'],BUFFERTRENDDATABASE=isolation.MAPPING['VFTEST_BTR'],
        INTERMEDIATEDATABASE=isolation.MAPPING['VFTEST_Intermediate'],INTERFACEDATABASE=isolation.MAPPING['VFTEST_Interface'],
        VENDORDATABASE=isolation.MAPPING['VFTEST_Vendor'],DISTRIBUTORDATABASE=isolation.MAPPING['VFTEST_Distributor'],
        DBRDATABASE='Not-defined',USERDATABASE='Not-defined')
    for name in ('Main','Settings','DBM','BPR','Importer','BTR','FullkitChecking'):
        settings['LOG'+name.upper()] = str(EVIDENCE/'logs'/(name+'.log'))
    settings['ERRORDUMP'] = str(EVIDENCE/'logs'/'Error.log')
    settings['BTROUTPUTFOLDER'] = str(EVIDENCE/'outputs'/'BTR')
    (EVIDENCE/'outputs'/'BTR').mkdir()
    settings['TEMPLATELOC'] = str(destination/'Scripts'/'Excel Templates')
    if (EVIDENCE/'report-tools'/'7z.exe').is_file():
        settings['ZIP'] = str(EVIDENCE/'report-tools')
    settings['PSOIMPORTSCRIPT'] = '"'+str(destination/'Scripts/SiteSpecific/GulfOil/Importer/ImportPSOData.sql')+'"'
    settings['SCRIPTEXECUTIONFLAGQUERY'] = 'update A set A.IsScriptExecuted=1 from '+settings['IMPORTERDATABASE']+'.dbo.ScriptExecutedFlag A where ScriptName='
    # All source path destinations are redirected into the private output root.
    # Existing endpoint/settings/account rows are never edited.
    for key,value in list(settings.items()):
        if key not in folders and (key.endswith('FOLDER') or key.endswith('DOWNLOADLOC')):
            private = EVIDENCE/'outputs'/key.lower()
            private.mkdir(exist_ok=True)
            settings[key] = str(private)
    dangerous = [k for k in settings if re.search(r'PASSWORD|SECRET|TOKEN|CONNECTIONSTRING',k,re.I)]
    for k in dangerous:
        del settings[k]
    dump(EVIDENCE/'execution-environment.json',dict(case_sha256=sha(EVIDENCE/'case.json'),
        settings=settings,transport_only_bat_copies=replaced,
        source_settings_hashes={r:sha(canonical/r) for r in ('Engine/StdSettingsPre.bat','Engine/SiteSpecific/GulfOil/Settings.bat')},
        boundary='Canonical generic SQL/BAT conditions and reports. Database/path/transport bindings only; notification delivery and backup not timed. No original BAT/settings/source edited.'))
    print(json.dumps(dict(status='EXECUTION_PREPARED',translated_bat_files=len(replaced))))


def load_inputs():
    from collections import Counter
    from mta.application.production_csv import parse_csv
    from mta.application.production_csv_contract import feeds
    from mta.application.native_daily_contract import FEED_SCHEMA
    case,isolation = bindings()
    if (EVIDENCE/'input-load.json').exists():
        raise ValueError('Input load already accepted; no replay')
    plan = dict(MasterDataRaw='MasterDataRaw',MasterDataRawNonNMS='MasterDataRawNonNMS',
        NoNormMasterRaw='NoNormMasterRaw',DailyDataRaw='DailyDataRaw',AcceptedNorms='AcceptedNorms',
        SOBDataRaw='SOBDataRaw',MOQDataRaw1='MOQDataRaw1',MOQDataRaw2='MOQDataRaw2',
        OrderData='OrderDataRaw',OrderFeed='PSOData',InTransitRaw='InTransitDataRaw',Transporters='TransporterMaster')
    roster = feeds(FEED_SCHEMA)
    packed = json.loads((EVIDENCE/'csv-pack.json').read_text())
    results = {}
    with isolation.raw_connection(isolation.MAPPING['VFTEST_Importer']) as c:
        from parity.provision_legacy import consume
        consume(c.execute("EXECUTE AS LOGIN='"+isolation.PRINCIPAL+"' WITH NO REVERT"))
        for name,table in plan.items():
            filename = name+'.csv'
            path = EVIDENCE/'csv'/filename
            if sha(path)!=packed['feeds'][filename]['sha256']:
                raise ValueError('CSV changed before SQL loading')
            columns = roster[filename]['columns']
            records,_ = parse_csv(path.read_bytes(),columns,filename)
            fields = [v['name'] for v in columns]
            values = [tuple(r[f] for f in fields) for r in records]
            c.execute('TRUNCATE TABLE dbo.['+table+']')
            if values:
                q = c.cursor()
                q.fast_executemany = True
                sql = 'INSERT INTO dbo.['+table+'] ('+','.join('['+f+']' for f in fields)+') VALUES ('+','.join('?' for f in fields)+')'
                for start in range(0,len(values),2048):
                    q.executemany(sql,values[start:start+2048])
                q.close()
            q = c.execute('SELECT '+','.join('['+f+']' for f in fields)+' FROM dbo.['+table+']')
            def plain(row):
                return tuple(v.isoformat() if isinstance(v,(date,datetime)) else format(v,'f') if isinstance(v,Decimal) else v for v in row)
            if Counter(plain(r) for r in q)!=Counter(values):
                raise ValueError('Complete SQL typed readback differs: '+filename)
            results[filename] = dict(rows=len(records),full_SQL_typed_values_NULLs_duplicate_multiplicities='PASS',
                input_order='Inserted in exact frozen CSV order; physical SQL tables have no ordinal/order contract')
            print(json.dumps({filename:len(records)}),flush=True)
        # Derive the next-day date for the approved carried raw requirement stock;
        # retain the original export and log the explicit dated projection.
        original = EVIDENCE/'csv'/'AdditionalDataStockForReqCalc.csv'
        with original.open(encoding='utf-8',newline='') as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames
            records = list(reader)
        dated = EVIDENCE/'daily-support'
        dated.mkdir()
        with (dated/original.name).open('x',encoding='utf-8',newline='') as stream:
            writer = csv.DictWriter(stream,fieldnames=columns,lineterminator='\r\n');writer.writeheader()
            for record in records:
                record['ReportDate'] = DAY
                writer.writerow(record)
        q = c.cursor()
        q.execute('TRUNCATE TABLE AdditionalDataStockForReqCalc')
        for record in records:
            q.execute('INSERT INTO AdditionalDataStockForReqCalc(SKUCode,WhCode,StockForReqCalc,ReportDate) VALUES (?,?,?,?)',
                record['SKUCode'],record['WhCode'],None if record['StockForReqCalc']==r'\N' else int(record['StockForReqCalc']),DAY)
        results['AdditionalDataStockForReqCalc.csv'] = dict(rows=len(records),
            original_sha256=sha(original),dated_sha256=sha(dated/original.name),
            transformation='ReportDate only: source7April to synthetic8April; quantities/identities retained',
            modern_admission='Additional requirement stock is not in the14-file public CSV roster; exact native source/binding support must be resolved before step6, no waiver or modern parity claim')
    dump(EVIDENCE/'input-load.json',dict(status='PASS',files=results))


def run_day():
    case,isolation = bindings()
    if not (EVIDENCE/'initialization.json').exists():
        raise ValueError('Initialize once before execution')
    if (EVIDENCE/'day-attempt.json').exists():
        existing=json.loads((EVIDENCE/'day-attempt.json').read_text())
        calls=[json.loads(line) for line in (EVIDENCE/'sql-calls.jsonl').read_text().splitlines()]
        calibration={hashlib.sha256(text.encode()).hexdigest() for text in
            ('SELECT DB_NAME() AS owned_database, SUSER_SNAME() AS restricted_login','EXIT (SELECT 2)')}
        if (existing['completed_stages'] or (EVIDENCE/'input-load.json').exists()
                or any(r['source']!='canonical-batch-inline-query' or r['source_text_sha256'] not in calibration for r in calls)):
            raise ValueError('Prior business SQL exists; no automatic replay')
        for role in ROLES:
            with isolation.raw_connection(isolation.MAPPING['VFTEST_'+role]) as c:
                if str(c.execute('SELECT CONVERT(date,LastRunDate) FROM LastBatchRunTbl').fetchval())!=case['opening_date']:
                    raise ValueError('Startup recovery opening changed')
        with (EVIDENCE/'pre-execution-observer-error-attempt.json').open('xb') as preserved:
            preserved.write((EVIDENCE/'day-attempt.json').read_bytes())
        (EVIDENCE/'day-attempt.json').unlink()
    environment = os.environ.copy()
    environment.update(json.loads((EVIDENCE/'execution-environment.json').read_text(encoding='utf-8-sig'))['settings'])
    # Native report compression is a tool dependency, not an engine default.
    if not Path(environment.get('ZIP',''),'7z.exe').is_file():
        raise ValueError('Native7z executable not configured; no daily SQL invoked')
    with isolation.raw_connection(isolation.MAPPING['VFTEST_Importer']) as c:
        # Delivery-only suppression on this private copy; rule/calculation settings
        # and source/serving alert rows are preserved. Record original intents.
        if not (EVIDENCE/'notification-delivery-exclusion.json').exists():
            alerts = read(c.cursor(),'SELECT * FROM EmailAlertSettings')
            c.execute('UPDATE EmailAlertSettings SET IsActive=0')
            dump(EVIDENCE/'notification-delivery-exclusion.json',dict(original=alerts,
                reason='No real email delivery from isolated benchmark; external notification not timed'))
    root = EVIDENCE/'canonical'
    bridge = ROOT/'tools/large_data_legacy_sqlcmd.py'
    def sql(role,relative):
        return '"'+sys.executable+'" "'+str(bridge)+'" -C -E -S localhost -d '+isolation.MAPPING['VFTEST_'+role]+' -i "'+str(root/'Scripts'/relative)+'"'
    def bat(name):
        return 'call "'+str(root/'Engine'/name)+'" go'
    stages = [
        ('reset-and-clock', '\r\n'.join([bat('GenericPreProcessing.bat'),bat('SetRunDate.bat'),
            sql('Importer','Importer/ClearMasterInputTables.sql'),sql('Importer','Importer/ClearNonMasterInputTables.sql')])),
        ('csv-ingestion-and-complete-readback','"'+sys.executable+'" "'+str(Path(__file__))+'" load-inputs'),
        ('native-input-validation','\r\n'.join([sql('Importer','Importer/InitialiseSkuLocStdAttributeData.sql'),bat('ValidateAndProcessInputData.bat')])),
        ('native-norm-controls','\r\n'.join([bat('NormChangesRun.bat'),bat('ValidateParentNorm.bat')])),
        ('bpr-rrr-pick-planning-and-reports',bat('RunCoreBPR.bat')),
        ('post-bpr-attributes',sql('BPR','SiteSpecific/GulfOil/BPR/CalculatedAttributes.sql')),
        ('dbm-and-reports',bat('RunCoreDBM.bat')),
        ('btr-guided-and-reports',bat('RunCoreBufferTrend.bat')),
        ('post-btr-attributes',sql('BTR','SiteSpecific/GulfOil/BTR/CalculateAttributeBasedonBTR.sql')),
    ]
    attempt = dict(status='RUNNING',business_date=DAY,owner=case['owner'],started_utc=datetime.now(timezone.utc).isoformat(),
        completed_stages=[],scope='One synthetic normalized-CSV shared legacy day; no second calculation/day',
        limits='No artificial CPU/RAM ceiling. Finite120min total/20GiB free storage fail-stop; no service or cache restart.')
    dump(EVIDENCE/'day-attempt.json',attempt)
    start = time.perf_counter()
    from tools.benchmark_windows_metrics import sample
    with connect() as observer:
        sql_pid=int(observer.execute("SELECT CONVERT(int,SERVERPROPERTY('ProcessID'))").fetchval())
        server_settings=read(observer.cursor(),"SELECT name,CONVERT(int,value_in_use) AS value_in_use FROM sys.configurations WHERE name IN ('max server memory (MB)','min server memory (MB)','max degree of parallelism','cost threshold for parallelism')")
        dmv_before=read(observer.cursor(),'SELECT physical_memory_in_use_kb FROM sys.dm_os_process_memory')[0]
        cpu_before=read(observer.cursor(),'SELECT process_kernel_time_ms,process_user_time_ms FROM sys.dm_os_sys_info')[0]
    dump(EVIDENCE/'resource-context.json',dict(sql_pid=sql_pid,logical_cpus=os.cpu_count(),
        server_settings=server_settings,before={**sample(sql_pid),**dmv_before,**cpu_before},
        qualification='Shared SQL Server process including warmed restore buffers/background work; no cache flush or resource-setting mutation. One observed run, not p95/capacity proof.'))
    stop=threading.Event()
    def monitor():
        with connect() as sql_observer, (EVIDENCE/'resources.jsonl').open('x',encoding='utf-8') as stream:
            while not stop.is_set():
                metrics=sample(sql_pid)
                try:
                    memory=sql_observer.execute('SELECT physical_memory_in_use_kb FROM sys.dm_os_process_memory').fetchval()
                    cpu=sql_observer.execute('SELECT process_kernel_time_ms,process_user_time_ms FROM sys.dm_os_sys_info').fetchone()
                    metrics.update(sql_rss_bytes=int(memory)*1024,sql_cpu_seconds=sum(cpu)/1000,
                        sql_process_metrics_source='SQL Server read-only DMVs')
                except Exception as error:
                    metrics['sql_observer_error']=type(error).__name__
                stream.write(json.dumps(dict(elapsed_seconds=time.perf_counter()-start,
                    disk_free_bytes=shutil.disk_usage('D:/').free,**metrics))+'\n')
                stream.flush()
                stop.wait(1)
    sampler=threading.Thread(target=monitor,daemon=True);sampler.start()
    for name,command in stages:
        if (EVIDENCE/'day-failure.json').exists():
            raise ValueError('Previous SQL failure; stop and preserve')
        script = EVIDENCE/(name+'.cmd')
        script.write_bytes(('@echo off\r\n'+command+'\r\n').encode('cp1252'))
        stage_start = time.perf_counter()
        with (EVIDENCE/(name+'.log')).open('wb') as log:
            process = subprocess.Popen(['cmd.exe','/d','/c',str(script)],env=environment,stdout=log,stderr=subprocess.STDOUT)
            while process.poll() is None:
                if time.perf_counter()-start>7200 or shutil.disk_usage('D:/').free<20*1024**3:
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    raise RuntimeError('Owned benchmark deadline/storage stop; shared services untouched')
                time.sleep(1)
        item = dict(stage=name,seconds=time.perf_counter()-stage_start,exit_code=process.returncode)
        attempt['completed_stages'].append(item)
        if process.returncode or (EVIDENCE/'day-failure.json').exists():
            stop.set();sampler.join()
            attempt.update(status='FAILED',failed_stage=name,elapsed_seconds=time.perf_counter()-start)
            (EVIDENCE/'day-attempt.json').write_text(json.dumps(attempt,indent=2),encoding='utf-8')
            raise RuntimeError('Legacy stage failed: '+name+'; no automatic replay')
        (EVIDENCE/'day-attempt.json').write_text(json.dumps(attempt,indent=2),encoding='utf-8')
        print(json.dumps(item),flush=True)
    attempt.update(status='EXECUTION_FINISHED_AWAITING_FINAL_READBACK',elapsed_seconds=time.perf_counter()-start)
    stop.set();sampler.join()
    (EVIDENCE/'day-attempt.json').write_text(json.dumps(attempt,indent=2),encoding='utf-8')
    print(json.dumps(attempt,indent=2))



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['freeze','verify-pack','complete-pack','create','initialize','prepare-execution','load-inputs','run'])
    args = parser.parse_args()
    {'freeze':freeze,'verify-pack':verify_pack,'complete-pack':complete_pack,'create':create_targets,'initialize':initialize_targets,
        'prepare-execution':prepare_execution,'load-inputs':load_inputs,'run':run_day}[args.operation]()
