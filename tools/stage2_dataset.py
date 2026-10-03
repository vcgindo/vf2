"""Bounded Stage 2 source assessment/capture. Never invokes a calculation engine.

Only the eight pinned Demo backups and uniquely owned restored clones are read.
Original databases, interrupted clones and application authentication are excluded.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import gzip
from datetime import date, datetime
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE = Path('D:/freshvcf-build/evidence/legacy-ui-june17-alignment-001')
DEST = Path('D:/freshvcf-build/evidence/stage2-shared-dataset-20261003-001')
DATA = Path('D:/freshvcf-build/sqlserver/stage2-shared-dataset-20261003-001')
ROLES = ('Importer', 'BPR', 'DBM', 'BTR', 'Interface', 'IntermediateDB', 'Vendor', 'Distributor')
DATABASES = {r: 'VFTEST_Fresh_S2_20261003_001_' + r for r in ROLES}


def require_reconciled_source():
    # Human correction relayed/verified from review chat on 3 October 2026.
    # Deliberately no command-line override: a new source must be reconciled and
    # assigned new owned resources before this bounded implementation resumes.
    raise RuntimeError('SOURCE HOLD: original populated databases from F:/VFlow_Source_Backup '
                       'are unavailable; existing local Demo imports are synthetic and quarantined. '
                       'See docs/STAGE2_DATASET_HANDOFF.md')


def scalar(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def encode(row):
    return (json.dumps([scalar(v) for v in row], ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def export():
    require_reconciled_source()
    manifest = json.loads((DEST / 'dataset-manifest.json').read_text())
    for source in manifest['sources']:
        with connection(source['database']) as clone:
            if query(clone, 'SELECT DATABASEPROPERTYEX(DB_NAME(),\'Updateability\') AS mode')[0]['mode'] != 'READ_ONLY':
                raise ValueError('Frozen clone must remain read-only')
            for table in source['tables']:
                if table['table_name'] == 'EnvironmentConfiguration':
                    table['exclusion'] = 'Runtime configuration may contain credentials; retained only in original backup, not needed by Stage 2 report consumers.'
                    continue
                path = DEST / 'tables' / source['source'] / (table['schema_name'] + '.' + table['table_name'] + '.jsonl.gz')
                path.parent.mkdir(parents=True, exist_ok=True)
                # SQL datetime2 may carry seven fractional digits, unlike Python datetime.
                columns = [f'CONVERT(nvarchar(40),{sq(c["name"])},126)' if c['type'] == 'datetime2' else sq(c['name']) for c in table['columns']]
                cursor = clone.cursor()
                cursor.execute('SELECT ' + ','.join(columns) + ' FROM ' + sq(table['schema_name']) + '.' + sq(table['table_name']))
                h = hashlib.sha256(); count = 0; nulls = [0] * len(columns)
                with gzip.open(path, 'wb') as out:
                    while True:
                        batch = cursor.fetchmany(1000)
                        if not batch: break
                        for row in batch:
                            raw = encode(row); out.write(raw); h.update(raw); count += 1
                            nulls = [n + (v is None) for n, v in zip(nulls, row)]
                cursor.close()
                if count != table['count']: raise ValueError('Frozen source count changed')
                table.update(file=path.relative_to(DEST).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    values_sha256=h.hexdigest(), null_counts=nulls,
                    order='Frozen extraction ordinal only; no SQL business ordering is invented.')
        print('Exported', source['source'], flush=True)
    manifest['inventory_sha256'] = hashlib.sha256((ROOT / 'docs/audit-2026-10-01/PAGE_INTERACTION_INVENTORY.csv').read_bytes()).hexdigest()
    write('dataset-manifest.json', manifest)


def write(name, value):
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / name).write_text(json.dumps(value, indent=2, default=str), encoding='utf-8')


def connection(database='master'):
    import pyodbc
    if database not in ('master', *DATABASES.values()):
        raise ValueError('Unowned database')
    return pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
        f'DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes',
        autocommit=True, timeout=10)


def query(conn, sql, *args):
    cursor = conn.cursor()
    try:
        cursor.execute(sql, *args)
        result = []
        while True:
            if cursor.description:
                names = [c[0] for c in cursor.description]
                result.extend(dict(zip(names, row)) for row in cursor.fetchall())
            if not cursor.nextset():
                return result
    finally:
        cursor.close()


def sq(name):
    return '[' + name.replace(']', ']]') + ']'


def assess_restore():
    require_reconciled_source()
    from parity.legacy_isolation import exclusive_replay
    import os
    os.environ['VFTEST_PROFILE'] = 'fresh'
    pins = {r['name']: r for r in json.loads((SOURCE / 'backup-manifest.json').read_text())}
    DATA.mkdir(parents=True, exist_ok=True)
    manifest = dict(version=1, identity='stage2-shared-dataset-20261003-001',
        origin='legacy-derived-ui-fixture', engine_execution=False, sources=[])
    with exclusive_replay(validate_schema=False), connection() as master:
        for role, target in DATABASES.items():
            name = 'Demo_' + role + '_1'
            backup = SOURCE / 'backups' / (name + '.copyonly.bak')
            pin = pins[backup.name]
            if backup.stat().st_size != pin['bytes'] or hashlib.sha256(backup.read_bytes()).hexdigest() != pin['sha256']:
                raise ValueError('Backup identity differs: ' + name)
            headers = query(master, 'RESTORE HEADERONLY FROM DISK=?', str(backup))
            if len(headers) != 1 or headers[0]['DatabaseName'] != name or headers[0]['IsDamaged']:
                raise ValueError('Invalid backup header: ' + name)
            query(master, 'RESTORE VERIFYONLY FROM DISK=? WITH CHECKSUM', str(backup))
            files = query(master, 'RESTORE FILELISTONLY FROM DISK=?', str(backup))
            owner = DATA / (target + '.owner.json')
            exists = query(master, 'SELECT DB_ID(?) AS id', target)[0]['id'] is not None
            expected = dict(database=target, backup_sha256=pin['sha256'], source=name)
            if exists:
                if not owner.exists() or json.loads(owner.read_text()) != expected:
                    raise ValueError('Existing database lacks matching ownership: ' + target)
            else:
                moves = []
                for i, item in enumerate(files):
                    path = str(DATA / (target + '_' + str(i) + ('.ldf' if item['Type'] == 'L' else '.mdf')))
                    moves.append("MOVE N'" + item['LogicalName'].replace("'", "''") + "' TO N'" + path.replace("'", "''") + "'")
                query(master, 'RESTORE DATABASE ' + sq(target) + ' FROM DISK=? WITH ' + ','.join(moves) + ', RECOVERY, CHECKSUM', str(backup))
                owner.write_text(json.dumps(expected), encoding='utf-8')
            physical = query(master, 'SELECT physical_name FROM sys.master_files WHERE database_id=DB_ID(?)', target)
            if not physical or any(not Path(r['physical_name']).resolve().is_relative_to(DATA.resolve()) for r in physical):
                raise ValueError('Clone file ownership mismatch')
            query(master, 'ALTER DATABASE ' + sq(target) + ' SET READ_ONLY')
            entry = dict(**expected, bytes=pin['bytes'], header=headers[0], tables=[])
            with connection(target) as clone:
                tables = query(clone, 'SELECT s.name AS schema_name,t.name AS table_name FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id WHERE t.is_ms_shipped=0 ORDER BY s.name,t.name')
                for table in tables:
                    qualified = sq(table['schema_name']) + '.' + sq(table['table_name'])
                    columns = query(clone, 'SELECT c.name,t.name AS type,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE c.object_id=OBJECT_ID(?) ORDER BY c.column_id', qualified)
                    count = query(clone, 'SELECT COUNT_BIG(*) AS n FROM ' + qualified)[0]['n']
                    dates = {}
                    for col in columns:
                        if col['type'] in ('date','datetime','datetime2','smalldatetime','datetimeoffset'):
                            dates[col['name']] = query(clone, 'SELECT MIN(' + sq(col['name']) + ') AS minimum,MAX(' + sq(col['name']) + ') AS maximum FROM ' + qualified)[0]
                    entry['tables'].append(dict(**table, columns=columns, count=count, dates=dates))
            manifest['sources'].append(entry)
            write('dataset-manifest.json', manifest)
            print(name, len(entry['tables']), sum(t['count'] for t in entry['tables']), flush=True)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['assess', 'export'])
    args = parser.parse_args()
    assess_restore() if args.command == 'assess' else export()
