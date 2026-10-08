"""Four fresh C5 backup fixtures; no engine, accepted database or scheduler use."""
import argparse
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mta.application.operational_inputs import typed_value
from mta.serialization import storage

SOURCE = Path('F:/VFlow_Local/local-runtime/mta-engine')
EVIDENCE = Path('D:/freshvcf-build/evidence/cohort2-20261008-001')
DATA = Path('D:/freshvcf-build/sqlserver')
INPUT = Path('D:/freshvcf-build/evidence/pick-closure-20261008-001/positive/input-v1.json')
INPUT_HASH = '7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d'
ROLES = {'Importer': 'MasterDataRaw', 'BPR': 'DailyDataRaw', 'DBM': 'SOBDataRaw', 'BTR': 'MOQDataRaw1'}
SQLCMD = Path('C:/Program Files/Microsoft SQL Server/Client SDK/ODBC/180/Tools/Binn/SQLCMD.EXE')


def pin(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identifier(value):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', value):
        raise ValueError('Unsafe fixture identifier')
    return '[' + value + ']'


def literal(value):
    return "N'" + str(value).replace("'", "''") + "'"


def drain(cursor):
    while cursor.nextset():
        pass


def schema_image(connection, table):
    columns = [list(row) for row in connection.execute('''SELECT c.column_id,c.name,t.name,
        c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,c.collation_name,
        CONVERT(nvarchar(80),ic.seed_value),CONVERT(nvarchar(80),ic.increment_value),
        CONVERT(nvarchar(80),ic.last_value)
        FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id
        LEFT JOIN sys.identity_columns ic ON ic.object_id=c.object_id AND ic.column_id=c.column_id
        WHERE c.object_id=OBJECT_ID(?) ORDER BY c.column_id''', 'dbo.'+table)]
    keys = [list(row) for row in connection.execute('''SELECT i.name,i.type_desc,i.is_unique,
        i.is_primary_key,k.key_ordinal,k.is_descending_key,c.name
        FROM sys.indexes i JOIN sys.index_columns k ON k.object_id=i.object_id AND k.index_id=i.index_id
        JOIN sys.columns c ON c.object_id=k.object_id AND c.column_id=k.column_id
        WHERE i.object_id=OBJECT_ID(?) ORDER BY i.index_id,k.key_ordinal''', 'dbo.'+table)]
    return dict(columns=columns, keys=keys)


def run(owner, output):
    import pyodbc
    pyodbc.pooling = False
    token = uuid.UUID(owner).hex
    output = Path(output).resolve()
    if output.parent != EVIDENCE.resolve() or output.exists() or output.suffix != '.json':
        raise ValueError('New exact Cohort2 evidence path required')
    directory = (DATA / ('cohort2-backup-' + token)).resolve()
    if directory.parent != DATA.resolve() or directory.exists():
        raise ValueError('New owned SQL fixture storage required')
    names = {role: 'VFTEST_Fresh_Cohort2Backup_' + token + '_' + role for role in ROLES}
    targets = {role: name + '_Restore' for role, name in names.items()}
    if pin(INPUT) != INPUT_HASH:
        raise ValueError('Retained raw fixture identity differs')
    source_map = json.loads((ROOT / 'docs/COHORT2_SOURCE_EXIT_MAP.json').read_text())
    source_pins = {}
    for entry in source_map['canonical_sources']:
        path = Path(entry['path'])
        if path.name in ('Backup.bat', 'CompressBackup.bat'):
            if pin(path) != entry['sha256']:
                raise ValueError('Canonical backup source changed')
            source_pins[str(path)] = pin(path)
    if len(source_pins) != 2:
        raise ValueError('Both native backup wrappers must be pinned')
    pre = (SOURCE / 'Engine/StdSettingsPre.bat').read_text()
    post = (SOURCE / 'Engine/StdSettingsPost.bat').read_text()
    for setting in (*('DoPostBkp' + role for role in ROLES), 'DBBkpCompress'):
        if not re.search(r'^set ' + setting + r'=1\s*$', pre, re.M | re.I):
            raise ValueError('Canonical backup activation differs: ' + setting)
    if 'set DBCompressionsFlag=COMPRESSION,' not in post:
        raise ValueError('Canonical native compression binding differs')
    case = json.loads(INPUT.read_text())['case']
    raw = {'MasterDataRaw': case['static_day']['raw_master'],
           'DailyDataRaw': case['days'][0]['raw_daily'],
           'SOBDataRaw': case['static_day']['supplier_feeds']['SOBDataRaw'],
           'MOQDataRaw1': case['static_day']['supplier_feeds']['MOQDataRaw1']}
    schema_file = ROOT / 'baseline/cohort2-native-source-schema.json'
    schemas = json.loads(schema_file.read_text())['tables']
    populations = {}
    for table, rows in raw.items():
        columns = schemas['Importer/' + table]
        if any(set(row) != {c['name'] for c in columns} for row in rows):
            raise ValueError('Complete raw fixture fields required: ' + table)
        populations[table] = [[typed_value(row[c['name']], c, reserve_null_token=False) for c in columns] for row in rows]
    receipt = dict(status='STARTED', owner=owner, sources=source_pins, input_sha256=INPUT_HASH,
        schema_sha256=pin(schema_file), sqlcmd_sha256=pin(SQLCMD), databases=names, restore_targets=targets,
        data_directory=str(directory), proof='four native pre/full and post/differential backup branches',
        fixture='Each role holds one declared raw-feed table. Post state appends the same raw rows once to prove duplicate preservation; no business calculation.',
        external_compression='DISABLED: canonical DBBkpCompress=1', checks=[])
    directory.mkdir()
    def save():
        output.write_text(json.dumps(storage(receipt), indent=2) + '\n', encoding='utf-8')
    def connection(db):
        if db not in {'master', *names.values(), *targets.values()}:
            raise ValueError('Connection outside declared fixture namespace')
        return pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=' + db +
            ';Trusted_Connection=yes;TrustServerCertificate=yes', autocommit=True, timeout=10)
    def files(db):
        return [(directory / (db + suffix)).resolve() for suffix in ('.mdf', '_log.ldf')]
    def validate_files(admin, db):
        actual = [Path(r[0]).resolve() for r in admin.execute('SELECT physical_name FROM sys.master_files WHERE database_id=DB_ID(?)', db)]
        if set(actual) != set(files(db)):
            raise ValueError('SQL fixture physical ownership differs: ' + db)
    def rows(db, table):
        with connection(db) as c:
            return [list(row) for row in c.execute('SELECT * FROM dbo.' + identifier(table) + ' ORDER BY fixture_ordinal')]
    try:
        with connection('master') as admin:
            server = list(admin.execute("SELECT CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')),CONVERT(nvarchar(128),SERVERPROPERTY('Edition')),CONVERT(nvarchar(128),SERVERPROPERTY('ProductVersion'))").fetchone())
            if server[0] != 'RFCLABS':
                raise ValueError('SQL instance identity differs')
            receipt['server'] = server
            for db in (*names.values(), *targets.values()):
                if admin.execute('SELECT DB_ID(?)', db).fetchone()[0] is not None or any(p.exists() for p in files(db)):
                    raise ValueError('Fixture/restore target exists; no replacement permitted')
            save()
            for role, db in names.items():
                data, log = files(db)
                admin.execute('CREATE DATABASE ' + identifier(db) + ' ON PRIMARY (NAME=' + literal(db) + ',FILENAME=' + literal(data) +
                    ',SIZE=8MB,MAXSIZE=64MB,FILEGROWTH=8MB) LOG ON (NAME=' + literal(db+'_log') + ',FILENAME=' + literal(log) +
                    ',SIZE=8MB,MAXSIZE=64MB,FILEGROWTH=8MB)')
                validate_files(admin, db)
                table = ROLES[role]; columns = schemas['Importer/' + table]
                definitions = []
                for col in columns:
                    kind = col['type'] + ('(' + col['parameters'] + ')' if col['parameters'] else '')
                    definitions.append(identifier(col['name']) + ' ' + kind + (' NULL' if col['nullable'] else ' NOT NULL'))
                with connection(db) as c:
                    c.execute('CREATE TABLE dbo.' + identifier(table) + ' (fixture_ordinal bigint IDENTITY(1,1) NOT NULL PRIMARY KEY,' + ','.join(definitions) + ')')
                    c.cursor().executemany('INSERT dbo.' + identifier(table) + ' (' + ','.join(identifier(col['name']) for col in columns) + ') VALUES (' + ','.join('?' for _ in columns) + ')', populations[table])
            # Invoke the unchanged wrapper. Every path it may delete has been
            # resolved to this new owned directory; no prior backup is present.
            env = dict(os.environ, ROOT=str(SOURCE), Server='localhost', BackupFolder=str(directory),
                DBBkpCompress='1', DBCompressionsFlag='COMPRESSION,', DistributorSystemActive='0', VendorSystemActive='0')
            env['PATH'] = str(SQLCMD.parent) + os.pathsep + env.get('PATH', '')
            for role, db in names.items():
                env['BufferTrendDatabase' if role == 'BTR' else role+'Database'] = db
                env['DoPostBkp'+role] = '1'
                for stage in ('Pre','Post'):
                    name = role+'-'+stage+'.bak'
                    if (directory/name).exists() or (directory/name).resolve().parent != directory:
                        raise ValueError('Backup path ownership differs')
                    env[role+'Bkp'+stage] = name
            for stage in ('pre', 'post'):
                if stage == 'post':
                    for role, db in names.items():
                        table = ROLES[role]; columns = schemas['Importer/' + table]
                        with connection(db) as c:
                            c.cursor().executemany('INSERT dbo.' + identifier(table) + ' (' + ','.join(identifier(col['name']) for col in columns) + ') VALUES (' + ','.join('?' for _ in columns) + ')', populations[table])
                result = subprocess.run(['cmd.exe','/d','/c',str(SOURCE/'Engine/Backup.bat'),stage,str(directory/(stage+'.log'))],
                    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=False)
                (directory/(stage+'-console.log')).write_bytes(result.stdout)
                receipt[stage+'_returncode'] = result.returncode
                # Batch exit/log text is not accepted as backup success.
                for role in ROLES:
                    backup = directory/(role+'-'+stage.title()+'.bak')
                    if not backup.is_file():
                        raise ValueError('Native backup missing: ' + str(backup))
            for role, db in names.items():
                base, diff = (directory/(role+'-'+stage+'.bak') for stage in ('Pre','Post'))
                headers=[]
                for path in (base,diff):
                    cur=admin.execute('RESTORE HEADERONLY FROM DISK='+literal(path))
                    header=dict(zip([d[0] for d in cur.description],cur.fetchone()));drain(cur)
                    headers.append(header)
                if (headers[0]['BackupType'] != 1 or headers[1]['BackupType'] != 5
                        or any(h['DatabaseName'] != db or h['Compressed'] != 1 for h in headers)
                        or headers[1]['DatabaseBackupLSN'] != headers[0]['CheckpointLSN']):
                    raise ValueError('Native full/differential/compression chain differs')
                target=targets[role];data,log=files(target)
                if admin.execute('SELECT DB_ID(?)',target).fetchone()[0] is not None:
                    raise ValueError('Restore target appeared; refusing replacement')
                drain(admin.execute('RESTORE DATABASE '+identifier(target)+' FROM DISK='+literal(base)+' WITH NORECOVERY, MOVE '+literal(db)+' TO '+literal(data)+', MOVE '+literal(db+'_log')+' TO '+literal(log)))
                drain(admin.execute('RESTORE DATABASE '+identifier(target)+' FROM DISK='+literal(diff)+' WITH RECOVERY'))
                validate_files(admin,target)
                expected,actual=rows(db,ROLES[role]),rows(target,ROLES[role])
                if expected != actual or len(actual) != 2*len(populations[ROLES[role]]):
                    raise ValueError('Full/differential restored typed rows or ordinals differ')
                with connection(db) as original, connection(target) as restored:
                    expected_schema, actual_schema = schema_image(original,ROLES[role]), schema_image(restored,ROLES[role])
                if expected_schema != actual_schema:
                    raise ValueError('Restored schema/key/identity state differs')
                receipt['checks'].append(dict(role=role,status='PASS',rows=storage(actual),headers=storage(headers),
                    schema=actual_schema,
                    backups=[dict(path=str(p),sha256=pin(p),size=p.stat().st_size) for p in (base,diff)]))
                save()
        receipt['status']='PASS'
    except Exception as error:
        receipt.update(status='FAIL',failure_type=type(error).__name__,failure=str(error))
    finally:
        save()
    return receipt


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',required=True);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();result=run(args.owner,args.output)
    print(json.dumps(dict(status=result['status'],checks=len(result['checks']),output=str(args.output))))
    raise SystemExit(result['status']!='PASS')
