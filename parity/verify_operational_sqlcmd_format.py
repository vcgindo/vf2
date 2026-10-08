"""Bounded read-only SQLCMD format fixtures in the already owned SQL namespace."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parity import legacy_isolation as isolation
from parity.verify_complete_daily_pick_files import prepare
from parity.verify_complete_daily_producers import OWNER, native_context


SQLCMD = Path('C:/Program Files/Microsoft SQL Server/Client SDK/ODBC/180/Tools/Binn/SQLCMD.EXE')
EVIDENCE = Path('D:/freshvcf-build/evidence/cohort2-20261008-001')
QUERY = '''SET NOCOUNT ON;
SELECT CAST('Header,Second' AS nvarchar(4000));
SELECT CAST('Text ' AS nvarchar(50)) AS [Text], CAST(NULL AS nvarchar(50)) AS [Nullable],
 CAST(3 AS int) AS [Integer], CAST(1.230 AS decimal(10,3)) AS [Decimal],
 CAST('2026-06-06' AS date) AS [Date], CAST('2026-06-06T13:04:05.123' AS datetime) AS [Stamp],
 CAST(1 AS bit) AS [Bit], CAST(1.25 AS float) AS [Float];
SELECT REPLICATE(CAST('X' AS nvarchar(4000)),300) AS [LongText];
SELECT CAST('' AS nvarchar(50)) AS [Empty], CAST('  both  ' AS nvarchar(50)) AS [Spaces],
 CAST('a,b' AS nvarchar(50)) AS [Comma], CAST('a'+CHAR(13)+CHAR(10)+'b' AS nvarchar(50)) AS [Lines];
SELECT CAST(0.120 AS decimal(10,3)), CAST(-0.120 AS decimal(10,3)), CAST(0 AS decimal(10,3)),
 CONVERT(nvarchar(256),CAST(0.120 AS decimal(10,3))),
 CONVERT(nvarchar(256),CAST('2026-06-06T13:04:05.123' AS datetime)),
 CONVERT(nvarchar(256),CAST('2026-06-06' AS date)), CAST(NULL AS int), NCHAR(233);
SELECT CAST('S' AS nvarchar(50)) AS SKUCode, CAST('W' AS nvarchar(50)) AS WhCode,
 CAST(12 AS int) AS Norm, CAST('P' AS nvarchar(50)) AS ParentWhCode;
'''


def run(directory):
    directory = Path(directory).resolve()
    if not directory.is_relative_to(EVIDENCE.resolve()):
        raise ValueError('Owned Cohort2 evidence directory required')
    directory.mkdir(exist_ok=False)
    prepare(OWNER, isolation)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    receipt = dict(scope='SQL scalar/file formatting only; no business-day or table mutation',
        owner=OWNER, tool_sha256=hashlib.sha256(SQLCMD.read_bytes()).hexdigest(), cases=[])
    with isolation.exclusive_replay(validate_schema=True):
        with isolation.connection('VFTEST_Importer') as connection:
            receipt['context'] = native_context(connection, isolation)
        # SQLCMD is a separate connection: apply the same no-revert restricted
        # principal before any fixture SELECT; it never modifies shared tables.
        source = "EXECUTE AS LOGIN = '" + isolation.PRINCIPAL + "' WITH NO REVERT;\n" + QUERY
        script = directory / 'scalar-fixture.sql'
        script.write_text(source, encoding='ascii')
        receipt['fixture_sha256'] = hashlib.sha256(script.read_bytes()).hexdigest()
        for name, flags in (('trimmed-nohead', ['-h-1','-W','-s', ',']),
                            ('trimmed-head', ['-W', '-s', ',']),
                            ('default-head', [])):
            target = directory / (name + '.txt')
            result = subprocess.run([str(SQLCMD), '-C', '-E', '-S', 'localhost',
                '-d', isolation.MAPPING['VFTEST_Importer'], '-b', '-i', str(script),
                '-o', str(target), *flags], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=60, check=False)
            if result.returncode:
                raise RuntimeError('Native SQLCMD format fixture failed: ' + str(result.returncode))
            raw = target.read_bytes()
            receipt['cases'].append(dict(name=name, flags=flags, bytes=len(raw),
                sha256=hashlib.sha256(raw).hexdigest(), latin1=raw.decode('latin1')))
    (directory / 'native-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


if __name__ == '__main__':
    result = run(sys.argv[1])
    print(json.dumps([{key: value for key, value in row.items() if key != 'latin1'}
                      for row in result['cases']], indent=2))
