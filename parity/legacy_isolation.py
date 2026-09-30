"""Exclusive Fresh-only SQL namespace. No live/default/Block2 target permitted."""
from contextlib import contextmanager
import os
import json
from pathlib import Path
import re
import threading

ROLES = ('Importer','BPR','DBM','BTR','Interface','Intermediate','Vendor','Distributor')
MAPPING = {'VFTEST_' + name: 'VFTEST_Fresh_' + name for name in ROLES}
DATA = Path('D:/freshvcf-build/sqlserver')
TOKEN = re.compile(r'\bVFTEST_[A-Za-z0-9_]+\b', re.I)
_lease = None
_lease_owner = None
_mutex = threading.Lock()
PRINCIPAL = 'freshvcf_oracle_replay'


def bind_sql(sql):
    if re.search(r'\b(?:Demo_|VF4_GM_|VFTEST_Block2_)[A-Za-z0-9_]+\b', sql, re.I):
        raise ValueError('Protected database reference')
    if re.search(r'\b(?:ALTER|DROP|CREATE|BACKUP|RESTORE)\s+DATABASE\b|\b(?:xp_|sp_configure)', sql, re.I):
        raise ValueError('Database/server mutation is not an oracle calculation')
    code = re.sub(r"'(?:''|[^'])*'|--[^\r\n]*|/\*[\s\S]*?\*/", ' ', sql)
    if re.search(r'\b(?:REVERT|GRANT|DENY|REVOKE|OPENROWSET|OPENDATASOURCE|OPENQUERY)\b|\bEXEC(?:UTE)?\s+AS\b|\bEXEC(?:UTE)?\b[^\r\n;]*\bAT\s+\[?\w+', code, re.I):
        raise ValueError('Privilege/remote operation is not an oracle calculation')
    for database in re.findall(r'\bUSE\s+\[?([\w]+)\]?',code,re.I):
        if database.casefold() not in {n.casefold() for n in (*MAPPING,*MAPPING.values())}:
            raise ValueError('Database context outside Fresh roles')
    # Database.schema.object references must use an explicit owned role;
    # server.database.schema.object and system database mutations are denied.
    for database in re.findall(r'(?<![\w#])\[?([A-Za-z_][\w]*)\]?\s*\.\s*\[?[A-Za-z_][\w]*\]?\s*\.',code):
        if database.casefold() not in {n.casefold() for n in (*MAPPING,*MAPPING.values())}:
            raise ValueError('Cross-database reference outside Fresh roles: '+database)
    def replace(match):
        value = match.group()
        for alias, physical in MAPPING.items():
            if value.casefold() in {alias.casefold(), physical.casefold()}:
                return physical
        raise ValueError('Unapproved test database: ' + value)
    return TOKEN.sub(replace, sql)


def raw_connection(database):
    import pyodbc
    # NO REVERT sessions must never return to an administrator's ODBC pool.
    pyodbc.pooling = False
    if database not in {'master', *MAPPING.values()}:
        raise ValueError('Connection outside Fresh namespace')
    if os.environ.get('VFTEST_PROFILE') != 'fresh':
        raise ValueError('Explicit VFTEST_PROFILE=fresh required')
    return pyodbc.connect(
        'DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
        f'DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes',
        autocommit=True, timeout=10)


def validate_files(raw, database):
    paths = raw.execute('SELECT physical_name FROM sys.master_files WHERE database_id=DB_ID(?)', database).fetchall()
    if not paths or any(not Path(p[0]).resolve().is_relative_to(DATA.resolve()) for p in paths):
        raise ValueError('Database absent or physical path outside owned Fresh directory: ' + database)


class Cursor:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, *args):
        if re.search(r'\bDB_ID\s*\(\s*\?\s*\)', sql, re.I):
            if len(args) == 1 and isinstance(args[0], (list, tuple)):
                args = (tuple(MAPPING.get(v, v) for v in args[0]),)
            else:
                args = tuple(MAPPING.get(v, v) for v in args)
        self.raw.execute(bind_sql(sql), *args)
        return self

    def executemany(self, sql, rows):
        self.raw.executemany(bind_sql(sql), rows)
        return self

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def __iter__(self):
        return iter(self.raw)


class Connection:
    def __init__(self, raw):
        self.raw = raw

    def cursor(self):
        return Cursor(self.raw.cursor())

    def execute(self, sql, *args):
        return self.cursor().execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.raw.close()


def connection(database='master'):
    if _lease is None or _lease_owner != threading.get_ident():
        raise ValueError('Exclusive Fresh replay lease required')
    if database != 'master' and database not in MAPPING:
        raise ValueError('Expected a declared logical Fresh role')
    physical = 'master' if database == 'master' else MAPPING[database]
    raw = raw_connection(physical)
    try:
        if physical != 'master':
            validate_files(raw, physical)
        # Login is disabled for direct authentication and owns no server or
        # live-database permission. NO REVERT prevents escape to Windows admin.
        raw.execute(f"EXECUTE AS LOGIN = '{PRINCIPAL}' WITH NO REVERT")
        if raw.execute('SELECT SUSER_SNAME()').fetchval() != PRINCIPAL:
            raise ValueError('Fresh-only execution principal was not applied')
        return Connection(raw)
    except Exception:
        raw.close()
        raise


@contextmanager
def exclusive_replay(*, validate_schema=True):
    global _lease, _lease_owner
    if not _mutex.acquire(blocking=False):
        raise ValueError('Do not nest Fresh replay ownership')
    raw = None
    try:
        raw = raw_connection('master')
        code = raw.execute("DECLARE @r int; EXEC @r=sp_getapplock @Resource='freshvcf-oracle', "
                           "@LockMode='Exclusive', @LockOwner='Session', @LockTimeout=0; SELECT @r").fetchval()
        if code < 0:
            raise ValueError('Fresh oracle is already owned by another replay')
        _lease = raw
        _lease_owner = threading.get_ident()
        if validate_schema:
            from parity.provision_legacy import schema_signature
            for database in MAPPING.values():
                receipt=json.loads((DATA/(database+'-schema.json')).read_text())
                with raw_connection(database) as target:
                    validate_files(target,database)
                    if receipt.get('database')!=database or receipt.get('schema_sha256')!=schema_signature(target):
                        raise ValueError('Fresh oracle schema drift: '+database)
        yield
    finally:
        _lease = None
        _lease_owner = None
        if raw is not None:
            raw.close()
        _mutex.release()
