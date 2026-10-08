"""Per-script durable SQL primitive for a new complete-day benchmark owner.

Not a complete-day runner. The existing rollback oracle is unchanged. Provision
and bind the new namespace before entering the existing exclusive replay lease;
preflight the full enabled script roster before executing any of its scripts.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import threading
from uuid import UUID

from parity import legacy_isolation as isolation

VARIABLE = re.compile(r'\$\(([^)]+)\)')
GO = re.compile(r'^\s*GO\s*$', re.M | re.I)


class SQLScriptFailure(RuntimeError):
    """Failed attempt receipt, including resultsets preceding the failure."""
    def __init__(self, receipt):
        self.receipt = receipt
        super().__init__('Complete-day SQL script failed: ' + receipt['source_path'])


@dataclass(frozen=True)
class PreparedScript:
    source_path: str
    source_sha256: str
    role: str
    sql: str
    variables: tuple


def namespace(owner_id):
    """This convention cannot select an earlier default/offline Fresh owner."""
    owner = UUID(str(owner_id))
    if owner.int == 0 or str(owner_id) != str(owner):
        raise ValueError('Explicit nonzero complete-day owner required')
    return {'VFTEST_' + role: 'VFTEST_Fresh_CompleteDaily_' + owner.hex + '_' + role
            for role in isolation.ROLES}


def data_directory(owner_id):
    namespace(owner_id)
    return Path('D:/freshvcf-build/sqlserver') / ('complete-daily-' + str(owner_id))


def _owned(owner_id, namespace_mapping, *, leased=False):
    expected = namespace(owner_id)
    if (namespace_mapping != expected or dict(isolation.MAPPING) != expected
            or isolation.DATA.resolve() != data_directory(owner_id).resolve()):
        raise ValueError('New complete-day owner namespace must be explicitly bound')
    if leased and (isolation._lease is None or isolation._lease_owner != threading.get_ident()):
        raise ValueError('Exclusive complete-day SQL lease required')
    return expected


def _source(path, expected):
    raw = Path(path).read_bytes()
    if not isinstance(expected, str) or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Complete-day canonical SQL source identity differs')
    encoding = ('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else
                'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'cp1252')
    return raw.decode(encoding)


def _compile(sql, variables):
    if not isinstance(variables, dict) or any(type(key) is not str for key in variables):
        raise ValueError('Explicit SQL variable mapping required')
    missing = set(VARIABLE.findall(sql)) - set(variables)
    if missing:
        raise ValueError('Unbound canonical SQL variables: ' + ','.join(sorted(missing)))
    if any(type(value) not in (str, int) for value in variables.values()):
        raise ValueError('Explicit SQL variables require text or integer values')
    sql = VARIABLE.sub(lambda match: str(variables[match.group(1)]), sql)
    if '$(' in sql:
        raise ValueError('Residual canonical SQL variable')
    return isolation.bind_sql(sql)


def preflight_scripts(scripts, *, owner_id, namespace):
    """Hash and guard the ENTIRE supplied roster before its first mutation.

    Each entry supplies source_path, source_sha256, role and variables. No
    configuration defaults or canonical text edits are invented here.
    """
    _owned(owner_id, namespace)
    if not isinstance(scripts, (list, tuple)) or not scripts:
        raise ValueError('Explicit complete-day script roster required')
    prepared = []
    for item in scripts:
        if item['role'] not in isolation.ROLES:
            raise ValueError('Explicit owned SQL role required')
        sql = _source(item['source_path'], item['source_sha256'])
        variables = item['variables']
        sql = _compile(sql, variables)
        prepared.append(PreparedScript(str(Path(item['source_path']).resolve()),
            item['source_sha256'], item['role'], sql, tuple(sorted(variables.items()))))
    return tuple(prepared)


def _results(cursor, results=None):
    """Ordinal cells preserve duplicate labels/rows and native typed values."""
    results = [] if results is None else results
    caught = False
    while True:
        if cursor.description:
            fields = [column[0] for column in cursor.description]
            rows = [list(row) for row in cursor.fetchall()]
            results.append(dict(fields=fields, rows=rows))
            if rows and any(str(field).lower() in ('error', 'errornumber', 'errormessage')
                            for field in fields):
                caught = True
        if not cursor.nextset():
            return results, caught


def _connection(role):
    connection = isolation.connection('VFTEST_' + role)
    if connection.raw.autocommit is not True:
        connection.raw.close()
        raise ValueError('Canonical per-script SQL requires autocommit=True')
    return connection


def execute_script(script, *, owner_id, namespace):
    """Fresh restricted connection; no reset/retry/global commit or rollback.

    Native explicit script transactions retain their own SQL semantics. A
    failure stops this script, closes its sqlcmd-equivalent connection and
    preserves already committed effects and the failed attempt resultsets.
    """
    _owned(owner_id, namespace, leased=True)
    if not isinstance(script, PreparedScript) or script.role not in isolation.ROLES:
        raise ValueError('Preflighted canonical SQL script required')
    sql = _compile(_source(script.source_path, script.source_sha256), dict(script.variables))
    if sql != script.sql:
        raise ValueError('Prepared SQL differs from pinned source and explicit variables')
    receipt = dict(source_path=script.source_path, source_sha256=script.source_sha256,
        role=script.role, owner_id=str(UUID(str(owner_id))), status='FAILED', results=[])
    try:
        with _connection(script.role) as connection:
            for batch in GO.split(sql):
                if not batch.strip():
                    continue
                cursor = connection.raw.cursor()
                try:
                    cursor.execute(batch)
                    _, caught = _results(cursor, receipt['results'])
                    if caught:
                        receipt['failure'] = 'canonical_error_resultset'
                        raise SQLScriptFailure(receipt)
                finally:
                    cursor.close()
    except SQLScriptFailure:
        raise
    except Exception as error:
        receipt['failure'] = type(error).__name__
        raise SQLScriptFailure(receipt) from error
    receipt['status'] = 'SUCCEEDED'
    return receipt


def readback(*, owner_id, namespace, role, query):
    """Read committed occurrences from a separate restricted connection."""
    _owned(owner_id, namespace, leased=True)
    if role not in isolation.ROLES:
        raise ValueError('Explicit owned SQL role required')
    query = isolation.bind_sql(query)
    code = re.sub(r"'(?:''|[^'])*'|--[^\r\n]*|/\*[\s\S]*?\*/", ' ', query)
    if (not re.match(r'^\s*;?\s*(?:SELECT|WITH)\b', code, re.I)
            or re.search(r'\b(?:INSERT|UPDATE|DELETE|MERGE|INTO|TRUNCATE|CREATE|ALTER|DROP|EXEC|EXECUTE|DBCC|BEGIN|COMMIT|ROLLBACK)\b', code, re.I)):
        raise ValueError('Readback requires owned read-only SELECT SQL')
    with _connection(role) as connection:
        cursor = connection.raw.cursor()
        try:
            cursor.execute(query)
            results, caught = _results(cursor)
            if caught:
                raise ValueError('Canonical readback returned an error resultset')
            return results
        finally:
            cursor.close()
