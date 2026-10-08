"""PostgreSQL-native consistent backup and fresh-target logical verification.

Connection factories and pinned client executables are supplied by the owned
runtime configuration. This module never chooses a database or resets a target.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
from uuid import UUID

from psycopg import sql
from mta.application.operational_io import tool_identity, inspect_file, owned_path


def _value(value):
    if value is None:
        return ['null', None]
    if type(value) in (str, int, bool):
        return [type(value).__name__, value]
    if isinstance(value, float):
        return ['float', value.hex()]
    if isinstance(value, Decimal):
        return ['decimal', str(value)]
    if isinstance(value, (date, datetime, time)):
        return [type(value).__name__, value.isoformat()]
    if isinstance(value, timedelta):
        return ['timedelta', [value.days, value.seconds, value.microseconds]]
    if isinstance(value, UUID):
        return ['uuid', str(value)]
    if isinstance(value, (bytes, memoryview)):
        return ['bytes', bytes(value).hex()]
    if isinstance(value, dict):
        return ['json-object', [[key, _value(value[key])] for key in sorted(value)]]
    if isinstance(value, list):
        return ['array', [_value(item) for item in value]]
    raise ValueError('Unsupported PostgreSQL logical value: ' + type(value).__name__)


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def logical_image(connection):
    """Read all user tables and sequence state, preserving NULLs and duplicates.

    Rows have no physical SQL ordering contract; explicit ordinal columns remain
    ordinary exact values. Sorting complete encoded rows preserves multiplicity.
    This is backup logical equality, not a report-order qualification.
    """
    relations = connection.execute('''SELECT n.nspname,c.relname,c.relkind
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema')
          AND n.nspname NOT LIKE 'pg_toast%%' AND n.nspname NOT LIKE 'pg_temp_%%'
          AND c.relkind IN ('r','p','S') ORDER BY n.nspname,c.relname''').fetchall()
    image = []
    for schema, table, kind in relations:
        name = sql.Identifier(schema, table)
        if kind == 'S':
            row = connection.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(name)).fetchone()
            image.append(dict(schema=schema, name=table, kind=kind, state=[_value(v) for v in row]))
            continue
        columns = connection.execute('''SELECT a.attname,format_type(a.atttypid,a.atttypmod),
            a.attnotnull,a.attidentity,a.attgenerated,pg_get_expr(d.adbin,d.adrelid)
            FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
            WHERE n.nspname=%s AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped
            ORDER BY a.attnum''', (schema, table)).fetchall()
        constraints = connection.execute('''SELECT con.conname,pg_get_constraintdef(con.oid,true)
            FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=%s AND c.relname=%s ORDER BY con.conname''', (schema, table)).fetchall()
        rows = sorted(_encoded([_value(value) for value in row]) for row in
                      connection.execute(sql.SQL('SELECT * FROM ONLY {}').format(name)))
        image.append(dict(schema=schema, name=table, kind=kind, columns=columns,
                          constraints=constraints, rows=[json.loads(row) for row in rows]))
    definitions = {}
    definitions['views'] = connection.execute('''SELECT schemaname,viewname,definition
        FROM pg_views WHERE schemaname NOT IN ('pg_catalog','information_schema')
        ORDER BY schemaname,viewname''').fetchall()
    definitions['indexes'] = connection.execute('''SELECT schemaname,tablename,indexname,indexdef
        FROM pg_indexes WHERE schemaname NOT IN ('pg_catalog','information_schema')
        ORDER BY schemaname,tablename,indexname''').fetchall()
    definitions['triggers'] = connection.execute('''SELECT n.nspname,c.relname,t.tgname,
        pg_get_triggerdef(t.oid,true),t.tgenabled FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE NOT t.tgisinternal AND n.nspname NOT IN ('pg_catalog','information_schema')
        ORDER BY n.nspname,c.relname,t.tgname''').fetchall()
    definitions['routines'] = connection.execute('''SELECT n.nspname,p.proname,
        pg_get_function_identity_arguments(p.oid),pg_get_functiondef(p.oid)
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
        WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND p.prokind IN ('f','p')
        ORDER BY n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)''').fetchall()
    # JSON-normalized sequences make a saved backup receipt recoverable without
    # a tuple/list discrepancy after decoding its external complete row proof.
    from mta.application.operational_restore_qualification import runtime_cast_metadata
    return json.loads(_encoded(dict(relations=image, definitions=definitions,
                                   runtime_cast_metadata=runtime_cast_metadata(connection))))


def image_digest(image):
    return hashlib.sha256(_encoded(image)).hexdigest()


def dump_database(*, connection_factory, database_name, root, relative_path,
                  executable, executable_sha256, client_environment):
    """Keep the exported read-only snapshot open through pg_dump and row audit."""
    target = owned_path(root, relative_path)
    if target.exists():
        raise ValueError('New backup path required; prior backups are retained')
    tool = tool_identity(executable, executable_sha256)
    target.parent.mkdir(parents=True, exist_ok=True)
    with connection_factory(database_name) as connection:
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        actual = connection.execute('SELECT current_database()').fetchone()[0]
        if actual != database_name:
            raise ValueError('Owned backup database binding differs')
        snapshot = connection.execute('SELECT pg_export_snapshot()').fetchone()[0]
        before = logical_image(connection)
        result = subprocess.run([str(tool), '--format=custom', '--no-owner', '--no-privileges',
            '--snapshot=' + snapshot, '--dbname=' + database_name, '--file=' + str(target)],
            env=client_environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=600, check=False)
        if result.returncode:
            raise RuntimeError('PostgreSQL backup failed with exit ' + str(result.returncode))
        if logical_image(connection) != before:
            raise ValueError('Backup sequence/schema state changed during capture')
    return dict(file=inspect_file(root, relative_path), snapshot=snapshot,
                database=database_name, tool_sha256=executable_sha256,
                logical_digest=image_digest(before), logical_image=before)


def restore_database(*, admin_connection_factory, connection_factory, target_database,
                     source_database, root, backup, executable, executable_sha256,
                     client_environment, qualification=None, observe_restore=None):
    """Create only an absent explicitly named owned target; never drop/reset one."""
    import re
    from mta.application.operational_io import verify_file
    if (not re.fullmatch(r'fresh_cohort2_restore_[a-z0-9_]+', target_database)
            or target_database == source_database):
        raise ValueError('New explicit owned restore target required')
    verify_file(root, backup['file'])
    tool = tool_identity(executable, executable_sha256)
    with admin_connection_factory() as admin:
        if not admin.autocommit:
            raise ValueError('Restore setup requires an autocommit administrative connection')
        if admin.execute('SELECT 1 FROM pg_database WHERE datname=%s', (target_database,)).fetchone():
            raise ValueError('Restore target exists; refusing replacement')
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(target_database)))
    result = subprocess.run([str(tool), '--exit-on-error', '--single-transaction',
        '--no-owner', '--no-privileges', '--dbname=' + target_database,
        str(owned_path(root, backup['file']['relative_path']))],
        env=client_environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=600, check=False)
    if result.returncode:
        raise RuntimeError('PostgreSQL restore failed; target retained; exit ' + str(result.returncode))
    with connection_factory(target_database) as restored:
        restored.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        actual = logical_image(restored)
    if observe_restore is not None:
        observe_restore(actual)
    from mta.application.operational_restore_qualification import compare_restore_images
    if image_digest(backup['logical_image']) != backup['logical_digest']:
        raise ValueError('Backup logical receipt identity differs')
    comparison = compare_restore_images(backup['logical_image'], actual, qualification=qualification)
    return dict(target=target_database, source=source_database,
                tool_sha256=executable_sha256, **comparison)
