"""Create only owned empty Fresh oracle databases from pinned canonical DDL.

No drops, restores, source-data copies or existing database rebuilds. Schema
installation is transactional. Known DDL duplicate/missing-drop behavior is
recorded, not treated as calculation parity or a repair of business logic.
"""
import hashlib
import json
from pathlib import Path
import re
import secrets

from parity.legacy_isolation import DATA, MAPPING, PRINCIPAL, raw_connection, validate_files, exclusive_replay

SOURCE = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts')
DDL = {role: SOURCE / relative for role, relative in {
    'Importer': 'DBCreation/Importer_DBCreation.sql',
    'BPR': 'DBCreation/BPR_DBCreation.sql',
    'DBM': 'DBCreation/DBM_DBCreation.sql',
    'BTR': 'DBCreation/BTR_DBCreation.sql',
    'Interface': 'SiteSpecific/GulfOil/Interface_DBCreation.sql',
    'Intermediate': 'DBCreation/Intermediate_DBCreation.sql',
    'Vendor': 'DBCreation/Vendor_DBCreation.sql',
    'Distributor': 'DBCreation/Distributor_DBCreation.sql',
}.items()}


def consume(cursor):
    while True:
        if cursor.description:
            columns = [c[0].lower() for c in cursor.description]
            rows = cursor.fetchall()
            if rows and set(columns) & {'error', 'errornumber', 'errormessage'}:
                raise ValueError('DDL returned an error result set')
        if not cursor.nextset():
            break


def schema_signature(connection):
    """Live object/column/constraint fingerprint, independent of business rows."""
    queries = (
        "SELECT s.name,o.name,o.type,m.definition FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.is_ms_shipped=0 AND o.type IN ('U','V','P','FN','IF','TF','TR') ORDER BY s.name,o.name,o.type",
        "SELECT s.name,o.name,c.column_id,c.name,t.name,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,c.collation_name,cc.definition,dc.definition FROM sys.columns c JOIN sys.objects o ON o.object_id=c.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.types t ON t.user_type_id=c.user_type_id LEFT JOIN sys.computed_columns cc ON cc.object_id=c.object_id AND cc.column_id=c.column_id LEFT JOIN sys.default_constraints dc ON dc.object_id=c.default_object_id WHERE o.is_ms_shipped=0 ORDER BY s.name,o.name,c.column_id",
        "SELECT s.name,o.name,i.name,i.is_unique,i.type,ic.key_ordinal,ic.is_included_column,c.name FROM sys.indexes i JOIN sys.objects o ON o.object_id=i.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id WHERE o.is_ms_shipped=0 ORDER BY s.name,o.name,i.name,ic.key_ordinal,ic.index_column_id",
        "SELECT s.name,o.name,c.name,c.definition FROM sys.check_constraints c JOIN sys.objects o ON o.object_id=c.parent_object_id JOIN sys.schemas s ON s.schema_id=o.schema_id ORDER BY s.name,o.name,c.name",
        "SELECT s.name,o.name,f.name,rs.name,ro.name,pc.name,rc.name FROM sys.foreign_keys f JOIN sys.foreign_key_columns fc ON fc.constraint_object_id=f.object_id JOIN sys.objects o ON o.object_id=f.parent_object_id JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.objects ro ON ro.object_id=f.referenced_object_id JOIN sys.schemas rs ON rs.schema_id=ro.schema_id JOIN sys.columns pc ON pc.object_id=o.object_id AND pc.column_id=fc.parent_column_id JOIN sys.columns rc ON rc.object_id=ro.object_id AND rc.column_id=fc.referenced_column_id ORDER BY s.name,o.name,f.name,fc.constraint_column_id",
    )
    schema = [[list(row) for row in connection.execute(sql)] for sql in queries]
    return hashlib.sha256(json.dumps(schema,sort_keys=True,default=str).encode()).hexdigest()


def provision_execution_principal(master):
    if not master.execute('SELECT COUNT(*) FROM sys.server_principals WHERE name=?', PRINCIPAL).fetchval():
        # Random password is never logged/saved and login is disabled. Windows
        # provisioner may impersonate it; oracle calculations cannot revert.
        password=secrets.token_urlsafe(48)
        master.execute(f"CREATE LOGIN [{PRINCIPAL}] WITH PASSWORD=N'{password}', CHECK_POLICY=ON")
        master.execute(f'ALTER LOGIN [{PRINCIPAL}] DISABLE')
    if not master.execute('SELECT is_disabled FROM sys.server_principals WHERE name=?', PRINCIPAL).fetchval():
        raise ValueError('Oracle execution principal must not allow direct login')
    if master.execute('SELECT COUNT(*) FROM sys.server_role_members WHERE member_principal_id=SUSER_ID(?)',PRINCIPAL).fetchval():
        raise ValueError('Oracle principal must not belong to a server role')
    if master.execute("SELECT COUNT(*) FROM sys.server_permissions WHERE grantee_principal_id=SUSER_ID(?) AND NOT (class_desc='SERVER' AND permission_name='CONNECT SQL' AND state_desc='GRANT')",PRINCIPAL).fetchval():
        raise ValueError('Unexpected server grants to oracle principal')
    for database in MAPPING.values():
        with raw_connection(database) as target:
            validate_files(target,database)
            if not target.execute('SELECT USER_ID(?)',PRINCIPAL).fetchval():
                target.execute(f'CREATE USER [{PRINCIPAL}] FOR LOGIN [{PRINCIPAL}]')
            target.execute(f'GRANT CONTROL ON DATABASE::[{database}] TO [{PRINCIPAL}]')


def build():
    baseline = json.loads((Path(__file__).resolve().parents[1] / 'baseline/manifest.json').read_text())
    pins = {str(Path(r['path']).resolve()): r['sha256'] for r in baseline['engine_sources']}
    DATA.mkdir(parents=True, exist_ok=True)
    receipts = []
    with exclusive_replay(validate_schema=False), raw_connection('master') as master:
        for role, path in DDL.items():
            raw = path.read_bytes()
            source_hash = hashlib.sha256(raw).hexdigest()
            if pins.get(str(path.resolve())) != source_hash:
                raise ValueError('Unpinned schema source: ' + str(path))
            database = MAPPING['VFTEST_' + role]
            receipt_path = DATA / (database + '-schema.json')
            exists = bool(master.execute('SELECT DB_ID(?)', database).fetchval())
            if exists:
                validate_files(master, database)
                if receipt_path.exists():
                    receipt = json.loads(receipt_path.read_text())
                    if receipt['source_sha256'] != source_hash:
                        raise ValueError('Previously provisioned schema source changed')
                    with raw_connection(database) as target:
                        if schema_signature(target) != receipt.get('schema_sha256'):
                            raise ValueError('Live Fresh schema differs from its receipt: '+database)
                    receipts.append(receipt)
                    continue
            else:
                # SQL Server on Windows requires native filesystem separators.
                mdf = str(DATA / (database + '.mdf'))
                ldf = str(DATA / (database + '_log.ldf'))
                master.execute(f"CREATE DATABASE [{database}] ON PRIMARY (NAME=N'{database}', FILENAME=N'{mdf}') "
                               f"LOG ON (NAME=N'{database}_log', FILENAME=N'{ldf}')")
                validate_files(master, database)
            connection = raw_connection(database)
            try:
                if connection.execute('SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0').fetchval():
                    raise ValueError('Existing nonempty schema has no owned receipt: ' + database)
                encoding = 'utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'cp1252'
                batches = [b for b in re.split(r'(?im)^\s*GO\s*(?:--.*)?$', raw.decode(encoding)) if b.strip()]
                connection.autocommit = False
                exceptions = []
                cursor = connection.cursor()
                for index, sql in enumerate(batches, 1):
                    if re.search(r'\bUSE\s|\b(?:ALTER|CREATE|DROP)\s+DATABASE|\b(?:Demo_|VF4_GM_|VFTEST_Block2_)', sql, re.I):
                        raise ValueError('Schema script leaves its owned database')
                    # Avoid executing the three known bootstrap errors inside a
                    # transaction: SQL Server can roll back all preceding DDL.
                    # This is schema provisioning only, never calculation SQL.
                    exception = None
                    if role == 'Importer' and re.search(r'CREATE\s+TABLE\s+\[dbo\]\.\[NMSTaskStatusActionMaster\]', sql, re.I):
                        if cursor.execute("SELECT OBJECT_ID('dbo.NMSTaskStatusActionMaster','U')").fetchval():
                            exception = 'duplicate NMSTaskStatusActionMaster CREATE'
                    elif role == 'Importer' and re.search(r'INSERT\s+\[dbo\]\.\[EnvironmentConfiguration\]', sql, re.I):
                        key = re.search(r"VALUES\s*\(\s*N?'([^']+)'", sql, re.I)
                        if key and cursor.execute('SELECT COUNT(*) FROM dbo.EnvironmentConfiguration WHERE ConfigKey=?', key[1]).fetchval():
                            exception = 'duplicate EnvironmentConfiguration seed'
                    elif role == 'Intermediate':
                        drop = re.search(r'(?im)^\s*DROP\s+TABLE\s+([^\r\n]+)', sql)
                        if drop and not cursor.execute("SELECT OBJECT_ID(?,'U')", drop[1].replace('[','').replace(']','').strip().rstrip(';')).fetchval():
                            exception = 'absent table DROP on empty schema; execute remaining CREATE'
                            remainder = sql[:drop.start()] + sql[drop.end():]
                            if re.search(r'\bCREATE\s+TABLE\b', remainder, re.I):
                                consume(cursor.execute(remainder))
                    if exception:
                        exceptions.append({'batch': index, 'source_behavior': exception, 'sql_sha256': hashlib.sha256(sql.encode()).hexdigest()})
                        continue
                    try:
                        consume(cursor.execute(sql))
                    except Exception as error:
                        raise RuntimeError(f'{database}: canonical DDL batch{index} failed') from error
                tables = connection.execute('SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0').fetchval()
                connection.commit()
                receipt = dict(database=database, source=str(path), source_sha256=source_hash,
                               table_count=tables, ddl_exceptions=exceptions,
                               schema_sha256=schema_signature(connection),
                               scope='schema only; no calculation or parity assertion')
                receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
                receipts.append(receipt)
                print(json.dumps({'database': database, 'tables': tables, 'ddl_exceptions': len(exceptions)}), flush=True)
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
        provision_execution_principal(master)
    return receipts


if __name__ == '__main__':
    build()
