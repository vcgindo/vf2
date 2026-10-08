"""SELECT-only qualification of complete-day scalars in their bounded domain.

No fixture loads, producers, scripts, business days or serving mutations. Actual
registered identifiers/raw percentages and declared edges are retained distinctly.
Failure stops at its first exact typed mismatch. This qualifies the tested ASCII
alphanumeric/colour/date domain only, not arbitrary Unicode collation semantics.
"""
from datetime import date, datetime
from decimal import Decimal
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mta.domain import complete_daily_scalars as scalars
from mta.runtime.offline_scenario import admit, registry
from mta.serialization import digest, storage
from parity.verify_complete_daily_producers import OWNER, DATA, guard_options, quote

PINNED_FULL = 'ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56'
PINNED_CATALOGUE = '2ecf4e079807e00d0f809abedde1303640910ca82faeb5b8e56671b22d5de0ff'
FILES = ('mta/domain/complete_daily_scalars.py', 'parity/verify_complete_daily_scalars.py',
         'parity/verify_complete_daily_producers.py', 'parity/adapters/legacy/complete_daily_sql.py',
         'parity/legacy_isolation.py', 'mta/runtime/offline_scenario.py', 'mta/serialization.py')


def code_pins():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in FILES}


def cell(value):
    if value is None:
        return ['null', None]
    if type(value) is bool:
        return ['bool', value]
    if type(value) is int:
        return ['int', value]
    if type(value) is float:
        return ['float64', value.hex()]
    if isinstance(value, Decimal):
        return ['decimal', format(value, 'f')]
    if isinstance(value, datetime):
        return ['datetime', value.isoformat()]
    if type(value) is date:
        return ['date', value.isoformat()]
    if isinstance(value, str):
        return ['text', value]
    raise TypeError('Unsupported scalar type: ' + type(value).__name__)


def read_only(sql):
    if not re.match(r'^\s*SELECT\b', sql, re.I) or re.search(
            r'\b(?:INTO|INSERT|UPDATE|DELETE|MERGE|TRUNCATE|CREATE|ALTER|DROP|EXEC|EXECUTE|DBCC|COMMIT|ROLLBACK|OPENQUERY|OPENROWSET)\b', sql, re.I):
        raise ValueError('Scalar qualification only permits read-only SELECT expressions')
    return sql


def registered_domain():
    pins = registry()
    full = pins['scenarios']['full']
    if full['sha256'] != PINNED_FULL or pins['catalogue_sha256'] != PINNED_CATALOGUE:
        raise ValueError('Frozen scalar qualification population identity differs')
    artifact = admit(Path(full['path']).read_bytes(), full['sha256'])
    register_path = ROOT / 'baseline/synthetic-rlt-4-7-v1.json'
    registered = json.loads(register_path.read_text())['catalogue_artifact']
    raw = Path(registered['path']).read_bytes()
    if registered['sha256'] != PINNED_CATALOGUE or hashlib.sha256(raw).hexdigest() != PINNED_CATALOGUE:
        raise ValueError('Pinned scalar catalogue differs')
    catalogue = json.loads(raw)['raw_master']
    sku = sorted({r['SKUCode'] for r in catalogue})
    locations = sorted({r[f] for r in catalogue for f in ('WhCode', 'ParentWhCode', 'LogisticsLocation') if r[f] is not None})
    keys = sorted(set(sku + locations))
    if len(sku) != 200 or len(locations) != 20 or any(re.fullmatch(r'[A-Za-z0-9]+ *', key) is None for key in keys):
        raise ValueError('Actual catalogue is outside declared alphanumeric scalar domain')
    masters = artifact['case']['static_day']['raw_master']
    percentages = [dict(ordinal=i, SKUCode=r['SKUCode'], WhCode=r['WhCode'], SKULocAtt02=r['SKULocAtt02'])
                   for i, r in enumerate(masters)]
    if len(percentages) != 1240 or any(r['SKULocAtt02'] is not None for r in percentages):
        raise ValueError('Frozen raw percentage domain no longer equals the qualified NULL population')
    return dict(full_artifact=dict(path=full['path'], sha256=PINNED_FULL),
                catalogue=dict(path=registered['path'], sha256=PINNED_CATALOGUE),
                register_sha256=hashlib.sha256(register_path.read_bytes()).hexdigest(),
                sku_keys=sku, location_keys=locations, all_keys=keys, raw_percentages=percentages,
                actual_business_dates=[r['business_date'] for r in artifact['case']['days']])


def edge_corpus():
    return dict(
        casts=[None, '', ' ', '\t\r\n', '0', '-0', '+0', '1', '-1', '.5', '-.5', '  +12.5  ',
               '1e2', '-1E-2', '1.e2', '1.234565', '123456.5', '123454.5', '999999.5',
               '1e308', '1e309', '1e-308', 'invalid', 'NaN', 'Inf', '1_000', '0x1', '1,000', '$1'],
        floats=[0.0, -0.0, .49, -.49, .5, -.5, 1.5, -1.5, 2.5, -2.5, 2.49, -2.49,
                123456.5, -123456.5, 123454.5, -123454.5, 1.234565, -1.234565,
                999999.5, -999999.5, 999999.49, 1000000.0, .0001, .00009999995,
                .00001, .00001234567, 12345678.0, 2147483647.0, 4503599627370495.0,
                1e20, 1e-20, 1e100, 1e-100],
        sort_keys=['0', '00', '001', '01', '1', '10', '2', '99', 'A', 'A0', 'AA', 'AZ', 'B', 'Z9'],
        equality=[(None, None), (None, 'A'), ('A', None), ('a', 'A'), ('A ', 'a'), ('A\t', 'A'),
                  ('', ' '), ('0', '00'), ('Black', 'BLACK '), ('NA', 'na'), ('0', 'NA')],
        datetimes=[datetime(2026, 6, 6), datetime(2026, 6, 6, 0, 1), datetime(2026, 6, 6, 11, 59),
                   datetime(2026, 6, 6, 12), datetime(2026, 6, 6, 13, 5), datetime(2026, 12, 31, 23, 59),
                   datetime(2026, 6, 6, 0, 0, 1), datetime(2026, 6, 6, 0, 0, 0, 1000)],
        date_texts=['2026-06-06', '2026-06-06T00:00:00', '2026-06-06 13:05:00',
                    'Jun  6 2026 12:00AM', 'Jun  6 2026 12:00PM', 'Dec 31 2026 11:59PM',
                    '2026-06-06T00:00:00.001', '2026-06-06T00:00:00.002',
                    '2026-06-06T00:00:00.003', '2026-06-06T00:00:00.004',
                    '2026-06-06T00:00:00.005', '2026-06-06T23:59:59.999',
                    '1753-01-01T00:00:00', '9999-12-31T23:59:59.997'])


class ScalarProof:
    def __init__(self, raw, receipt):
        self.raw, self.receipt = raw, receipt
        self.cache = {}

    def query(self, sql, parameters):
        sql = read_only(sql)
        record = dict(sql=sql, parameters=[cell(v) for v in parameters], status='STARTED')
        self.receipt['queries'].append(record)
        try:
            cursor = self.raw.execute(sql, tuple(parameters)) if parameters else self.raw.execute(sql)
            columns = [c[0] for c in cursor.description]
            rows = [list(r) for r in cursor.fetchall()]
            record.update(status='PASS', fields=columns, rows=[[cell(v) for v in r] for r in rows])
        except Exception as error:
            record.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
            raise
        return rows

    def compare(self, kind, source, sql, parameters, python):
        # Python considers -0.0 and +0.0 equal; retain their native parameter
        # identities rather than accidentally reusing the other probe's result.
        signature = (sql, tuple(json.dumps(cell(v), separators=(',', ':')) for v in parameters))
        if signature not in self.cache:
            self.cache[signature] = self.query(sql, parameters)[0][0]
        expected = self.cache[signature]
        # CASE returns int in ODBC; explicitly cast the SQL comparison to bit
        # at the query so Python/native booleans retain identical types.
        record = dict(kind=kind, source=source, sql=sql,
                      parameters=[cell(v) for v in parameters], native=cell(expected))
        try:
            record['modern'] = cell(python())
        except Exception as error:
            record.update(status='FAIL', modern_error=dict(type=type(error).__name__, message=str(error)))
            self.receipt['comparisons'].append(record)
            raise ValueError('First Python scalar failure: ' + kind + ' ' + str(source)) from error
        record['status'] = 'PASS' if record['native'] == record['modern'] else 'FAIL'
        self.receipt['comparisons'].append(record)
        if record['status'] != 'PASS':
            raise ValueError('First exact scalar mismatch: ' + kind + ' ' + str(source))
        return record


def qualify(raw, receipt, domain):
    proof = ScalarProof(raw, receipt)
    # Do not set LANGUAGE or change the environment to make a comparison pass.
    context = proof.query("SELECT @@LANGUAGE AS Language, CONVERT(nvarchar(128),DATABASEPROPERTYEX(DB_NAME(),'Collation')) AS Collation", [])[0]
    receipt['native_context'] = dict(language=context[0], database_collation=context[1])
    if context[0] != 'us_english' or not isinstance(context[1], str) or not context[1].endswith('_CI_AS'):
        raise ValueError('Native language/collation differs from the declared scalar domain')
    corpus = edge_corpus()
    receipt['declared_edge_corpus'] = storage(corpus)
    equality_sql = 'SELECT CAST(CASE WHEN CONVERT(nvarchar(4000),?)=CONVERT(nvarchar(4000),?) THEN 1 ELSE 0 END AS bit) AS Value'
    for ordinal, key in enumerate(domain['all_keys']):
        for left, right in ((key, key), (key, key.lower()), (key, key + '  '),
                            (key, domain['all_keys'][(ordinal + 1) % len(domain['all_keys'])])):
            proof.compare('ascii_equal', dict(domain='actual-identifiers', ordinal=ordinal), equality_sql,
                          [left, right], lambda a=left, b=right: scalars.ascii_equal(a, b))
    for ordinal, (left, right) in enumerate(corpus['equality']):
        proof.compare('ascii_equal', dict(domain='declared-edge', ordinal=ordinal), equality_sql,
                      [left, right], lambda a=left, b=right: scalars.ascii_equal(a, b))
    sort_values = list(dict.fromkeys(domain['all_keys'] + corpus['sort_keys']))
    # Reject collation ties instead of inventing a deterministic SQL winner.
    if len({scalars.identifier_sort_key(v) for v in sort_values}) != len(sort_values):
        raise ValueError('Declared scalar ordering corpus contains collation-key ties')
    sort_sql = ('SELECT Value FROM (VALUES ' + ','.join('(CONVERT(nvarchar(50),?))' for _ in sort_values)
                + ') A(Value) ORDER BY Value')
    native_order = [r[0] for r in proof.query(sort_sql, sort_values)]
    modern_order = sorted(sort_values, key=scalars.identifier_sort_key)
    order = dict(kind='identifier_sort_key', source='all actual keys plus declared alphanumeric edges',
                 native=[[cell(v)] for v in native_order], modern=[[cell(v)] for v in modern_order],
                 status='PASS' if native_order == modern_order else 'FAIL')
    receipt['comparisons'].append(order)
    if order['status'] != 'PASS':
        raise ValueError('First exact scalar mismatch: identifier_sort_key')
    cast_sql = 'SELECT TRY_CAST(CONVERT(nvarchar(4000),?) AS FLOAT) AS Value'
    for row in domain['raw_percentages']:
        value = row['SKULocAtt02']
        proof.compare('try_cast_float', dict(domain='actual-frozen-raw', **row), cast_sql,
                      [value], lambda v=value: scalars.try_cast_float(v))
    for ordinal, value in enumerate(corpus['casts']):
        proof.compare('try_cast_float', dict(domain='declared-edge', ordinal=ordinal), cast_sql,
                      [value], lambda v=value: scalars.try_cast_float(v))
    for ordinal, value in enumerate(corpus['floats']):
        proof.compare('round_float_zero', dict(domain='declared-edge', ordinal=ordinal),
                      'SELECT ROUND(CAST(? AS FLOAT),0) AS Value', [value],
                      lambda v=value: scalars.round_float_zero(v))
        proof.compare('float_to_nvarchar', dict(domain='declared-edge', ordinal=ordinal),
                      'SELECT CONVERT(nvarchar(50),CAST(? AS FLOAT)) AS Value', [value],
                      lambda v=value: scalars.float_to_nvarchar(v))
    for ordinal, value in enumerate(corpus['datetimes']):
        proof.compare('datetime_to_nvarchar', dict(domain='declared-edge', ordinal=ordinal),
                      'SELECT CONVERT(nvarchar(50),CAST(? AS datetime)) AS Value', [value],
                      lambda v=value: scalars.datetime_to_nvarchar(v))
    for ordinal, when in enumerate(domain['actual_business_dates']):
        text = when + 'T00:00:00'
        value = datetime.fromisoformat(text)
        proof.compare('datetime_to_nvarchar', dict(domain='actual-frozen-run-date', ordinal=ordinal),
                      'SELECT CONVERT(nvarchar(50),CAST(? AS datetime)) AS Value', [value],
                      lambda v=value: scalars.datetime_to_nvarchar(v))
        proof.compare('parse_datetime', dict(domain='actual-frozen-run-date', ordinal=ordinal),
                      'SELECT CONVERT(datetime,CONVERT(nvarchar(50),?)) AS Value', [text],
                      lambda v=text: scalars.parse_datetime(v))
    for ordinal, value in enumerate(corpus['date_texts']):
        proof.compare('parse_datetime', dict(domain='declared-edge', ordinal=ordinal),
                      'SELECT CONVERT(datetime,CONVERT(nvarchar(50),?)) AS Value', [value],
                      lambda v=value: scalars.parse_datetime(v))


def run(owner, output):
    output = guard_options(owner, output)
    domain = registered_domain()
    from parity import legacy_isolation as isolation
    from parity.adapters.legacy.complete_daily_sql import namespace, data_directory
    binding = namespace(owner)
    if data_directory(owner).resolve() != DATA.resolve():
        raise ValueError('Owned data directory differs')
    isolation.MAPPING.clear()
    isolation.MAPPING.update(binding)
    isolation.DATA = data_directory(owner)
    import os
    os.environ['VFTEST_PROFILE'] = 'fresh'
    receipt = dict(owner=owner, namespace=binding, status='STARTED', code_pins=code_pins(),
                   domain=domain, queries=[], comparisons=[],
                   scope='SELECT-only scalar qualification; no fixture/business-day invocation',
                   limitations=['ASCII alphanumeric identifiers and declared colours/text/date corpus only',
                                'not all Unicode collations or full-day parity',
                                '4GiB/2CPU worker limits are externally enforced by primary'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as file:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                receipt['schema_receipts'] = [json.loads((DATA / (db + '-schema.json')).read_text()) for db in binding.values()]
                with isolation.connection('VFTEST_BPR') as raw:
                    probes = ScalarProof(raw, receipt)
                    receipt['all_database_collations'] = [dict(role=role,
                        collation=probes.query('SELECT CONVERT(nvarchar(128),DATABASEPROPERTYEX(?,\'Collation\'))', [database])[0][0])
                        for role, database in binding.items()]
                    if len({r['collation'] for r in receipt['all_database_collations']}) != 1:
                        raise ValueError('Owned database collations differ; no blanket adapter qualification')
                    qualify(raw, receipt, domain)
                    receipt['transaction_count'] = probes.query('SELECT @@TRANCOUNT', [])[0][0]
                    if receipt['transaction_count'] != 0:
                        raise ValueError('Read-only scalar qualification left a transaction')
            receipt['status'] = 'PASS'
        except Exception as error:
            receipt.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
        finally:
            receipt['code_identity_unchanged'] = receipt['code_pins'] == code_pins()
            if not receipt['code_identity_unchanged']:
                receipt.update(status='FAIL', failure='Scalar implementation/harness changed during proof')
            receipt['comparisons_sha256'] = digest(receipt['comparisons'])
            json.dump(storage(receipt), file, indent=2, ensure_ascii=False, allow_nan=False)
            file.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', required=True, type=Path)
    options = parser.parse_args()
    result = run(options.owner, options.output)
    print(json.dumps(dict(status=result['status'], comparisons=len(result['comparisons']), output=str(options.output))))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
