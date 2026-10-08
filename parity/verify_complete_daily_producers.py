"""Rollback-only small-fixture qualification, never a full-day parity claim.

Only the explicitly approved new complete-day namespace is permitted. Table
boundaries use declared exact typed multisets because canonical table reads have
no ORDER BY; observed sequences and every cell remain in evidence. This does not
change the full31 positional assertions. Modern calls use the retained qualified standalone ASCII scalar adapters;
the native counterpart executes unchanged canonical SQL.
"""
from collections import Counter
from datetime import date, datetime, timedelta
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

from mta.domain.complete_daily_bpr import post_bpr_calculated_attributes, production_order_suggestions
from mta.domain.complete_daily_btr import post_btr_calculated_attributes
from mta.domain import complete_daily_scalars as scalars
from mta.evidence import evidence_mode
from mta.serialization import storage

OWNER = 'fdc5bc5e-4d68-4b3a-b8e6-d2754df0e2f4'
DATA = Path('D:/freshvcf-build/sqlserver') / ('complete-daily-' + OWNER)
OUTPUT_ROOT = Path('D:/freshvcf-build/complete-daily-assessment')
SOURCE = Path('F:/VFlow_Local/local-runtime/mta-engine')
TODAY = date(2026, 6, 6)
PINS = {
    'Scripts/SiteSpecific/GulfOil/BPR/CalculatedAttributes.sql':
        'd0d2036edd71269c514fd0e316889c6923c20f963063fb5f984b81eaaa7c332b',
    'Scripts/BPR/ProdOrderSuggestions.sql':
        'e4e50d327a60e02717183c803303ffa6ae8a731c7fa728a76dfff190d51377db',
    'Scripts/SiteSpecific/GulfOil/BTR/CalculateAttributeBasedonBTR.sql':
        'b2f356c09bdc905f11d33e58de2e47b7bb852db43eed2aceb7dcfe3982058f6b',
}
IMPLEMENTATION_FILES = (
    'mta/domain/complete_daily_bpr.py', 'mta/domain/complete_daily_btr.py',
    'mta/evidence.py', 'mta/serialization.py', 'mta/domain/complete_daily_scalars.py',
    'parity/verify_complete_daily_producers.py',
    'parity/adapters/legacy/temporal_delivery.py',
    'parity/adapters/legacy/complete_daily_sql.py', 'parity/legacy_isolation.py',
)


def implementation_pins():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in IMPLEMENTATION_FILES}


SCALAR_PROOF = OUTPUT_ROOT / 'scalars-qualification-a002.json'
NATIVE_COLLATION = 'SQL_Latin1_General_CP1_CI_AS'
NATIVE_LANGUAGE = 'us_english'


def scalar_binding():
    proof = json.loads(SCALAR_PROOF.read_text())
    module = 'mta/domain/complete_daily_scalars.py'
    module_hash = hashlib.sha256((ROOT / module).read_bytes()).hexdigest()
    if (proof['owner'] != OWNER or proof['status'] != 'PASS'
            or proof.get('code_identity_unchanged') is not True
            or proof['code_pins'][module] != module_hash):
        raise ValueError('Standalone scalar qualification identity differs')
    return dict(kind='standalone Python adapters; no SQL callbacks', module=module,
                module_sha256=module_hash, proof_path=str(SCALAR_PROOF),
                proof_sha256=hashlib.sha256(SCALAR_PROOF.read_bytes()).hexdigest(),
                domain='bounded ASCII identifiers, colours, numeric text and us_english datetime')


def native_context(raw, isolation):
    expression = "SELECT @@LANGUAGE, CONVERT(nvarchar(128),DATABASEPROPERTYEX(DB_NAME(),'Collation'))"
    row = raw.execute(expression).fetchone()
    report = dict(sql=expression, language=row[0], database_collation=row[1], databases=[])
    for role, database in isolation.MAPPING.items():
        value = raw.execute("SELECT CONVERT(nvarchar(128),DATABASEPROPERTYEX(?,'Collation'))", database).fetchval()
        report['databases'].append(dict(role=role, database=database, collation=value))
    if (row[0] != NATIVE_LANGUAGE or row[1] != NATIVE_COLLATION
            or any(d['collation'] != NATIVE_COLLATION for d in report['databases'])):
        raise ValueError('Native language/collation differs from qualified standalone scalar domain')
    return report


def guard_options(owner, output):
    if owner != OWNER:
        raise ValueError('Only the explicitly approved complete-day qualification owner is permitted')
    output = Path(output).resolve()
    if not output.is_relative_to(OUTPUT_ROOT.resolve()) or output.suffix != '.json':
        raise ValueError('Qualification output must be a JSON file in its approved evidence directory')
    if output.exists():
        raise FileExistsError('Refusing to overwrite qualification evidence: ' + str(output))
    return output


def quote(value):
    return '[' + value.replace(']', ']]') + ']'


def typed(value, column):
    """Exact cells with explicit lossless ISO reconstruction for native dates."""
    if value is None:
        return ['null', None]
    kind = column['type_name']
    if kind in ('date', 'datetime', 'datetime2', 'smalldatetime'):
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value)
            value = parsed.date() if kind == 'date' else parsed
        if kind == 'date' and type(value) is not date:
            raise ValueError('Native date type differs')
        if kind != 'date' and not isinstance(value, datetime):
            raise ValueError('Native datetime type differs')
        return [kind, value.isoformat()]
    if type(value) is bool:
        return ['bool', value]
    if type(value) is int:
        return ['int', value]
    if isinstance(value, Decimal):
        return ['decimal', format(value, 'f')]
    if type(value) is float:
        return ['float64', value.hex()]
    if isinstance(value, str):
        return ['text', value]
    if isinstance(value, bytes):
        return ['bytes', value.hex()]
    raise TypeError('Unsupported native cell ' + type(value).__name__)


def cells(rows, columns):
    result = []
    for row in rows:
        lookup = {name.casefold(): value for name, value in row.items()}
        if len(lookup) != len(row) or set(lookup) != {c['name'].casefold() for c in columns}:
            raise ValueError('Full native column roster differs')
        result.append([typed(lookup[c['name'].casefold()], c) for c in columns])
    return result


def compare_rows(native, modern, columns):
    a, b = cells(native, columns), cells(modern, columns)
    encode = lambda row: json.dumps(row, separators=(',', ':'), ensure_ascii=False)
    left, right = Counter(map(encode, a)), Counter(map(encode, b))
    report = dict(policy='exact typed multiset; native table has no ORDER BY',
                  fields=[c['name'] for c in columns], native_sequence=a, modern_sequence=b,
                  native_sequence_sha256=hashlib.sha256(json.dumps(a, separators=(',', ':')).encode()).hexdigest(),
                  modern_sequence_sha256=hashlib.sha256(json.dumps(b, separators=(',', ':')).encode()).hexdigest(),
                  native_duplicates=[dict(cells=json.loads(k), count=v) for k, v in left.items() if v > 1],
                  modern_duplicates=[dict(cells=json.loads(k), count=v) for k, v in right.items() if v > 1],
                  missing=[dict(cells=json.loads(k), count=v) for k, v in (left - right).items()],
                  extra=[dict(cells=json.loads(k), count=v) for k, v in (right - left).items()])
    report['status'] = 'PASS' if left == right else 'FAIL'
    return report


class FixtureSQL:
    def __init__(self, raw, isolation):
        self.raw, self.isolation = raw, isolation
        self.schemas, self.fills = {}, []

    def table(self, role, name):
        return quote(self.isolation.MAPPING['VFTEST_' + role]) + '.dbo.' + quote(name)

    def schema(self, role, name):
        key = (role, name)
        if key not in self.schemas:
            database = quote(self.isolation.MAPPING['VFTEST_' + role])
            cursor = self.raw.execute(
                'SELECT c.name,t.name,c.is_nullable,c.is_identity,c.is_computed,c.max_length,'
                'c.precision,c.scale,c.collation_name FROM ' + database + '.sys.columns c JOIN '
                + database + '.sys.types t ON c.user_type_id=t.user_type_id WHERE c.object_id=OBJECT_ID(?) '
                'ORDER BY c.column_id', self.table(role, name))
            labels = ('name', 'type_name', 'nullable', 'identity', 'computed', 'max_length', 'precision', 'scale', 'collation')
            self.schemas[key] = [dict(zip(labels, r)) for r in cursor.fetchall()]
            if not self.schemas[key]:
                raise ValueError('Required canonical fixture table absent: ' + str(key))
        return self.schemas[key]

    def rows(self, role, name):
        cursor = self.raw.execute('SELECT * FROM ' + self.table(role, name))
        labels = [c[0] for c in cursor.description]
        return [dict(zip(labels, r)) for r in cursor.fetchall()]

    def fill(self, column):
        if column['nullable']:
            return None, 'explicit SQL NULL for unused nullable fixture column'
        kind = column['type_name']
        if kind in ('int', 'bigint', 'smallint', 'tinyint'):
            return 0, 'declared unused required integer fixture value 0'
        if kind == 'bit':
            return False, 'declared unused required bit fixture value false'
        if kind in ('decimal', 'numeric', 'money', 'smallmoney'):
            return Decimal(0), 'declared unused required decimal fixture value 0'
        if kind in ('float', 'real'):
            return 0.0, 'declared unused required floating fixture value 0'
        if kind in ('nvarchar', 'varchar', 'nchar', 'char'):
            return '', 'declared unused required text fixture value empty string'
        if kind == 'date':
            return TODAY, 'declared unused required date fixture business date'
        if kind in ('datetime', 'datetime2', 'smalldatetime'):
            return datetime.combine(TODAY, datetime.min.time()), 'declared unused required datetime fixture midnight'
        raise ValueError('No declared filler for required schema type ' + kind)

    def load(self, role, name, records):
        columns = [c for c in self.schema(role, name) if not c['identity'] and not c['computed']
                   and c['type_name'] not in ('timestamp', 'rowversion')]
        self.raw.execute('DELETE FROM ' + self.table(role, name))
        for ordinal, record in enumerate(records):
            declared = {k.casefold(): v for k, v in record.items()}
            if len(declared) != len(record) or not set(declared) <= {c['name'].casefold() for c in columns}:
                raise ValueError('Declared fixture column differs from native schema: ' + name)
            values = []
            for column in columns:
                if column['name'].casefold() in declared:
                    value = declared[column['name'].casefold()]
                else:
                    value, reason = self.fill(column)
                    self.fills.append(dict(role=role, table=name, ordinal=ordinal, field=column['name'],
                                           value=storage(value), reason=reason))
                values.append(value)
            self.raw.execute('INSERT INTO ' + self.table(role, name) + ' ('
                + ','.join(quote(c['name']) for c in columns) + ') VALUES ('
                + ','.join('?' for _ in columns) + ')', tuple(values))

    def scratch(self):
        database = quote(self.isolation.MAPPING['VFTEST_Intermediate'])
        names = [r[0] for r in self.raw.execute('SELECT t.name FROM ' + database + '.sys.tables t JOIN '
                 + database + ".sys.schemas s ON s.schema_id=t.schema_id WHERE s.name='dbo' "
                 'AND t.is_ms_shipped=0 ORDER BY t.name')]
        return {name: self.rows('Intermediate', name) for name in names}


def preflight_fixture_suite(sql, cases):
    """Read-only full-suite schema audit, before any DELETE/INSERT/script call.

    Checks every declared field/null, and that every unused column has an
    explicit supported filler. Empty populations still require their real table.
    The loader protocol is unchanged and remains independently guarded.
    """
    report = dict(status='PASS', scope='entire fixture suite before first mutation',
                  populations=[], errors=[])
    for case, _, path, declared in cases:
        expanded = dict(declared)
        expanded[('Intermediate', 'GulfOil_TechColorData')] = [
            dict(ReportDate=TODAY, SKUCode='SCRATCH', WhCode='W', TechColor='NA')]
        for (role, table), rows in expanded.items():
            try:
                columns = sql.schema(role, table)
                writable = {c['name'].casefold(): c for c in columns
                            if not c['identity'] and not c['computed']
                            and c['type_name'] not in ('timestamp', 'rowversion')}
                checked = []
                for ordinal, row in enumerate(rows):
                    names = {name.casefold(): name for name in row}
                    if len(names) != len(row) or not set(names) <= set(writable):
                        raise ValueError('Unknown or repeated native fixture field: ' + str(sorted(set(names) - set(writable))))
                    declarations = []
                    for key, column in writable.items():
                        if key in names:
                            value, reason = row[names[key]], 'explicit fixture declaration'
                        else:
                            value, reason = sql.fill(column)
                        if value is None and not column['nullable']:
                            raise ValueError('NULL supplied for native NOT NULL field: ' + column['name'])
                        if value is not None:
                            kind = column['type_name']
                            if kind in ('nvarchar', 'nchar', 'varchar', 'char'):
                                if not isinstance(value, str):
                                    raise ValueError('Native text fixture type differs: ' + column['name'])
                                length = len(value.encode('utf-16-le')) if kind in ('nvarchar', 'nchar') else len(value.encode('cp1252'))
                                if column['max_length'] != -1 and length > column['max_length']:
                                    raise ValueError('Native text fixture length exceeds schema: ' + column['name'])
                            elif kind in ('int', 'bigint', 'smallint', 'tinyint'):
                                ranges = {'int': (-2**31, 2**31-1), 'bigint': (-2**63, 2**63-1),
                                          'smallint': (-2**15, 2**15-1), 'tinyint': (0, 255)}
                                lo, hi = ranges[kind]
                                if type(value) is not int or not lo <= value <= hi:
                                    raise ValueError('Native integer fixture type/range differs: ' + column['name'])
                            elif kind == 'bit' and type(value) is not bool:
                                raise ValueError('Native bit fixture type differs: ' + column['name'])
                            elif kind in ('decimal', 'numeric'):
                                if not isinstance(value, Decimal) or not value.is_finite():
                                    raise ValueError('Native decimal fixture type differs: ' + column['name'])
                                if abs(value) >= Decimal(10) ** (column['precision'] - column['scale']):
                                    raise ValueError('Native decimal fixture precision differs: ' + column['name'])
                            typed(value, column)
                        declarations.append(dict(field=column['name'], value=storage(value),
                                                 nullable=bool(column['nullable']), reason=reason))
                    checked.append(dict(ordinal=ordinal, fields=declarations))
                report['populations'].append(dict(case=case, source_path=path, role=role,
                                                  table=table, schema=columns, rows=checked))
            except Exception as error:
                report['errors'].append(dict(case=case, role=role, table=table,
                                             failure_type=type(error).__name__, failure=str(error)))
    if report['errors']:
        report['status'] = 'FAIL'
    return report


def fixture_cases():
    """Declared small contract cases, not frozen full-day or catalogue inputs."""
    attr = lambda sku, loc: dict(SKUCode=sku, LocCode=loc, c3='old3', c9='old9', c10='old10', c12='old12', c13='old13')
    post, attributes, raw = [], [], []
    for sku, percent, norm, pack, available, raw_parent in (
            ('ROUND', '50', 15, 4, 19, 'P'), ('DOWN', '100', 15, 4, 14, 'P'),
            ('CAP', '100', 15, 4, 2, 'P'), ('BADCAST', 'invalid', 15, 4, 19, 'P'),
            ('NULLVN', '50', None, 4, 19, 'P'), ('NULLPACK', '50', 15, None, 19, 'P'),
            ('NOMATCH', '50', 15, 4, 19, None)):
        post.append(dict(SKUCode=sku, WhCode='W', ParentWhCode='P', RationedReq=3,
                         VirtualNorm=norm, Stock=0, GIT=0, ParentPackSize=pack, ParentStockForRationing=available))
        attributes.append(attr(sku, 'W'))
        raw.append(dict(SKUCode=sku, WhCode='W', ParentWhCode='P', SKULocAtt01=raw_parent, SKULocAtt02=percent))
    attributes.append(dict(attributes[0]))
    post.append(dict(post[0])); raw.append(dict(raw[0]))
    attributes.append(attr('SELF', 'P'))
    post.append(dict(post[0], SKUCode='SELF', WhCode='P'))
    common_post = {('BPR', 'SkuLocAttributeData'): attributes, ('BPR', 'vf_PickListReport'): post,
                   ('Importer', 'MasterDataRaw'): raw, ('Importer', 'SkuLocAttributeData'): attributes,
                   ('BPR', 'BPR_Table'): [dict(SKUCode=r['SKUCode'], WhCode=r['LocCode']) for r in attributes],
                   ('Importer', 'NMSAllItems'): [dict(SKUCode=r['SKUCode'], WhCode=r['LocCode'], ParentWhCode='P') for r in attributes]}
    prod = {('BPR', 'SupplierDispatchReq'): [dict(SKUCode='PROD', WHCode='W', SupplierCode='P',
             ReqTopOfRed=3, ReqTopOfYellow=4, ReqTopOfGreen=5)] * 2,
            ('BPR', 'Plants'): [dict(PlantCode='P')] * 2,
            ('BPR', 'vf_RationedReqReport'): [dict(SKUCode='PROD', WhCode='W', Norm=10, Stock=0, GIT=0)],
            ('BPR', 'DailyConsumption'): [dict(SKUCode='PROD', WHCode='P', ReportDate=TODAY, Stock=None, GIT=5)],
            ('BPR', 'LastBatchRunTbl'): [dict(LastRunDate=datetime.combine(TODAY, datetime.min.time()))],
            ('BPR', 'ProdOrderSuggestions'): [dict(SKUCode='OLD', PlantCode='P', ReportDate=TODAY)],
            ('Importer', 'ScriptExecutedFlag'): [dict(ScriptName='ProdOrderSuggestions.sql', IsScriptExecuted=False,
             IsScriptCritical=True, ModuleName='BPR')]}
    rm = dict(SKUCode='RM', WhCode='R', **{f'D{i}': 'Green' for i in range(61, 91)})
    rm.update(D85='Black', D86=None, D87=None, D88=None, D89=None, D90='Black')
    current = attr('FG', 'P'); current['FGRMFlag'] = 'FG'
    rm_attr = attr('RM', 'R'); rm_attr['FGRMFlag'] = 'RM'
    histories = [dict(CurrentNodeSKU='FG', CurrentNodeWhCode='P', ChildNodeSKU='FG', ChildNodeWhCode='C',
                     CurrentNodeStock=0, CurrentNodeGIT=0, ChildStock=0, ChildGIT=0, ChildVN=3,
                     CurrentNodeNorm=2, TechPen=Decimal('100.000'), EcoPen=Decimal('100.000'),
                     TechColor='Black', EcoColor='Black', ReportDate=TODAY - timedelta(days=d)) for d in (0, 1, 2, 30, 31)]
    btr = {('BTR', 'LastBatchRunTbl'): prod[('BPR', 'LastBatchRunTbl')],
           ('BTR', 'BufferTrendDates'): [{f'D{i}': TODAY - timedelta(days=90-i) for i in range(61, 91)}],
           ('BTR', 'BufferTrendReport'): [rm, dict(rm)], ('BTR', 'BufferTrendReportEcon'): [dict(rm, D89='Red')],
           ('BTR', 'SkuLocAttributeData'): [current, dict(current), rm_attr],
           ('BTR', 'LocationAttributeData'): [dict(WHCode='P', c1='C')] * 2,
           ('Importer', 'SkuLocAttributeData'): [current, rm_attr],
           ('BPR', 'vf_ReqCalculation'): [dict(SKUCode='FG', WhCode='P', ParentWhCode='P', Norm=2,
             VirtualNorm=2, Stock=0, GIT=1), dict(SKUCode='FG', WhCode='C', ParentWhCode='P', Norm=3,
             VirtualNorm=3, Stock=0, GIT=0)],
           ('Interface', 'FGTrendData'): histories,
           # FG has NO BOR row: the LEFT JOIN generates SQL NULL. Stored
           # DispatchColor is NOT NULL in the canonical table.
           ('BPR', 'BORWithOrderAllocation'): [],
           ('BPR', 'BPR_Table'): [dict(SKUCode=a['SKUCode'], WhCode=a['LocCode']) for a in (current, rm_attr)],
           ('BPR', 'SkuLocAttributeData'): [current, rm_attr], ('DBM', 'SkuLocAttributeData'): [current, rm_attr],
           ('BPR', 'SupplierDispatchReq'): [dict(SKUCode=a['SKUCode'], WHCode=a['LocCode'], SupplierCode='P') for a in (current, rm_attr)],
           ('Importer', 'NMSAllItems'): [dict(SKUCode=a['SKUCode'], WhCode=a['LocCode'], ParentWhCode='P') for a in (current, rm_attr)]}
    # Additional independent FG pair exercises repeating decimal division and
    # the 66.67 threshold after decimal(13,3) assignment, not an integer ratio.
    fractional = attr('FGROUND', 'P'); fractional['FGRMFlag'] = 'FG'
    for key in (('BTR', 'SkuLocAttributeData'), ('Importer', 'SkuLocAttributeData'),
                ('BPR', 'SkuLocAttributeData'), ('DBM', 'SkuLocAttributeData')):
        btr[key].append(dict(fractional))
    btr[('BPR', 'vf_ReqCalculation')].extend([
        dict(SKUCode='FGROUND', WhCode='P', ParentWhCode='P', Norm=2, VirtualNorm=2, Stock=0, GIT=1),
        dict(SKUCode='FGROUND', WhCode='C', ParentWhCode='P', Norm=4, VirtualNorm=4, Stock=1, GIT=0)])
    btr[('BPR', 'BPR_Table')].append(dict(SKUCode='FGROUND', WhCode='P'))
    btr[('BPR', 'SupplierDispatchReq')].append(dict(SKUCode='FGROUND', WHCode='P', SupplierCode='P'))
    btr[('Importer', 'NMSAllItems')].append(dict(SKUCode='FGROUND', WhCode='P', ParentWhCode='P'))
    btr[('BPR', 'BORWithOrderAllocation')] = [dict(SKUCode='FGROUND', WhCode='P', DispatchColor='Black')] * 2
    return [('post-bpr-round-cap-null-duplicates', 'BPR', list(PINS)[0], common_post),
            ('production-color-netting-null-stock-duplicates', 'BPR', list(PINS)[1], prod),
            ('post-btr-fg-history-na-gaps-null-bor-duplicates', 'BTR', list(PINS)[2], btr)]


def qualify_case(raw, isolation, name, role, path, declared):
    from parity.adapters.legacy.temporal_delivery import DeliverySQL
    sql = FixtureSQL(raw, isolation)
    for (owner, table), records in declared.items():
        sql.load(owner, table, records)
    sql.load('Intermediate', 'GulfOil_TechColorData', [dict(ReportDate=TODAY, SKUCode='SCRATCH', WhCode='W', TechColor='NA')])
    before = {key: sql.rows(*key) for key in declared}
    scratch = sql.scratch()
    collations = {c['collation'] for key in before for c in sql.schema(*key) if c['collation']}
    if collations != {NATIVE_COLLATION}:
        raise ValueError('Fixture column collation differs from qualified scalar domain: ' + str(collations))
    equal, cast = scalars.ascii_equal, scalars.try_cast_float
    rounding, text = scalars.round_float_zero, scalars.float_to_nvarchar
    probes = []
    read = lambda owner, table: before[(owner, table)]
    if path.endswith('CalculatedAttributes.sql'):
        params = dict(sku_loc_attributes=read('BPR', 'SkuLocAttributeData'), pick_list_report=read('BPR', 'vf_PickListReport'),
                      master_data_raw=read('Importer', 'MasterDataRaw'), bpr_table=read('BPR', 'BPR_Table'),
                      importer_sku_loc_attributes=read('Importer', 'SkuLocAttributeData'), nms_all_items=read('Importer', 'NMSAllItems'),
                      intermediate_tables=scratch, equal=equal, try_cast_float=cast, round_float=rounding, float_to_nvarchar=text)
        producer = post_bpr_calculated_attributes
        bindings = {'SkuLocAttributeData': ('BPR', 'SkuLocAttributeData'), 'BPR_Table': ('BPR', 'BPR_Table'),
                    'ImporterSkuLocAttributeData': ('Importer', 'SkuLocAttributeData'), 'NMSAllItems': ('Importer', 'NMSAllItems')}
    elif path.endswith('ProdOrderSuggestions.sql'):
        params = dict(supplier_dispatch_req=read('BPR', 'SupplierDispatchReq'), plants=read('BPR', 'Plants'),
                      rationed_req_report=read('BPR', 'vf_RationedReqReport'), daily_consumption=read('BPR', 'DailyConsumption'),
                      last_batch_run=read('BPR', 'LastBatchRunTbl'), prod_order_suggestions=read('BPR', 'ProdOrderSuggestions'),
                      intermediate_tables=scratch, equal=equal, sort_key=scalars.identifier_sort_key)
        producer, bindings = production_order_suggestions, {'ProdOrderSuggestions': ('BPR', 'ProdOrderSuggestions')}
    else:
        params = dict(buffer_trend_report=read('BTR', 'BufferTrendReport'), buffer_trend_report_econ=read('BTR', 'BufferTrendReportEcon'),
                      buffer_trend_dates=read('BTR', 'BufferTrendDates'), last_batch_run=read('BTR', 'LastBatchRunTbl'),
                      sku_loc_attributes=read('BTR', 'SkuLocAttributeData'), location_attributes=read('BTR', 'LocationAttributeData'),
                      req_calculation=read('BPR', 'vf_ReqCalculation'), importer_sku_loc_attributes=read('Importer', 'SkuLocAttributeData'),
                      fg_trend_data=read('Interface', 'FGTrendData'), bor_with_order_allocation=read('BPR', 'BORWithOrderAllocation'),
                      bpr_table=read('BPR', 'BPR_Table'), bpr_sku_loc_attributes=read('BPR', 'SkuLocAttributeData'),
                      supplier_dispatch_req=read('BPR', 'SupplierDispatchReq'), dbm_sku_loc_attributes=read('DBM', 'SkuLocAttributeData'),
                      nms_all_items=read('Importer', 'NMSAllItems'), intermediate_tables=scratch, equal=equal)
        producer = post_btr_calculated_attributes
        bindings = {'SkuLocAttributeData': ('BTR', 'SkuLocAttributeData'), 'FGTrendData': ('Interface', 'FGTrendData'),
                    'BPR_Table': ('BPR', 'BPR_Table'), 'BPRSkuLocAttributeData': ('BPR', 'SkuLocAttributeData'),
                    'SupplierDispatchReq': ('BPR', 'SupplierDispatchReq'), 'DBMSkuLocAttributeData': ('DBM', 'SkuLocAttributeData'),
                    'ImporterSkuLocAttributeData': ('Importer', 'SkuLocAttributeData'), 'NMSAllItems': ('Importer', 'NMSAllItems')}
    result = dict(name=name, source_path=path, source_sha256=PINS[path], status='STARTED',
                  declaration='small synthetic unit contract fixtures, not frozen full-day inputs',
                  fixtures=[dict(role=k[0], table=k[1], rows=storage(v)) for k, v in declared.items()],
                  native_inputs=[dict(role=k[0], table=k[1], schema=sql.schema(*k), rows=storage(v),
                                      typed_sequence=cells(v, sql.schema(*k))) for k, v in before.items()],
                  filler_policy=sql.fills, probes=probes, scalar_adapters=scalar_binding(), comparisons={})
    try:
        with evidence_mode('production'):
            modern = producer(**params)
        delivery = DeliverySQL(raw, sql.load, sql.rows, None, sql.scratch, PINS, TODAY.isoformat(), {})
        delivery.execute(role, path)
        result['sql_receipts'] = delivery.receipts
        expected = {bindings[key]: rows for key, rows in modern.items() if key in bindings}
        # Script execution flag is a separately declared canonical side effect,
        # not a claim that the production-suggestion pure producer owns flags.
        if path.endswith('ProdOrderSuggestions.sql'):
            expected[('Importer', 'ScriptExecutedFlag')] = [r | {'IsScriptExecuted': True}
                                                            for r in before[('Importer', 'ScriptExecutedFlag')]]
        for key, original in before.items():
            expected.setdefault(key, original)
        for key, wanted in expected.items():
            report = compare_rows(sql.rows(*key), wanted, sql.schema(*key))
            result['comparisons']['.'.join(key)] = report
            if report['status'] != 'PASS':
                raise ValueError('Full native population mismatch: ' + '.'.join(key))
        native_scratch = sql.scratch()
        if set(native_scratch) != set(modern['IntermediateTables']):
            raise ValueError('Intermediate table roster differs')
        for table, wanted in modern['IntermediateTables'].items():
            report = compare_rows(native_scratch[table], wanted, sql.schema('Intermediate', table))
            result['comparisons']['Intermediate.' + table] = report
            if report['status'] != 'PASS':
                raise ValueError('Scratch mismatch: ' + table)
        result['status'] = 'PASS'
    except Exception as error:
        result.update(status='FAIL', failure_type=type(error).__name__, failure=str(error),
                      native_after_error=[dict(role=k[0], table=k[1], rows=storage(sql.rows(*k))) for k in before])
    return result


def run(owner, output):
    output = guard_options(owner, output)
    from parity import legacy_isolation as isolation
    from parity.adapters.legacy.complete_daily_sql import namespace, data_directory
    binding = namespace(owner)
    if data_directory(owner).resolve() != DATA.resolve():
        raise ValueError('Complete-day data-directory convention differs')
    isolation.MAPPING.clear()
    isolation.MAPPING.update(binding)
    isolation.DATA = data_directory(owner)
    import os
    os.environ['VFTEST_PROFILE'] = 'fresh'
    for path, pin in PINS.items():
        if hashlib.sha256((SOURCE / path).read_bytes()).hexdigest() != pin:
            raise ValueError('Pinned canonical source drift: ' + path)
    receipt = dict(owner=owner, namespace=binding, owned_data_directory=str(DATA), status='STARTED',
                   source_pins=PINS, implementation_pins=implementation_pins(), scalar_adapters=scalar_binding(), cases=[],
                   scope='rollback small-fixture producer qualification only',
                   limitations=['small fixture proof with qualified bounded standalone adapters; not full-day parity',
                                'no change to full31 positional comparison contract',
                                'worker 4GiB/2CPU limits are externally enforced by the primary'])
    output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve evidence before the first lease or mutation. Never overwrite.
    with output.open('x', encoding='utf-8') as file:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                receipt['schema_receipts'] = [json.loads((DATA / (db + '-schema.json')).read_text()) for db in binding.values()]
                with isolation.connection('VFTEST_BPR') as raw:
                    receipt['native_context'] = native_context(raw, isolation)
                    cases = fixture_cases()
                    receipt['fixture_preflight'] = preflight_fixture_suite(FixtureSQL(raw, isolation), cases)
                    if receipt['fixture_preflight']['status'] != 'PASS':
                        raise ValueError('Entire fixture suite failed native schema audit before mutation')
                    for name, role, path, declared in cases:
                        baseline = FixtureSQL(raw, isolation)
                        originals = {key: baseline.rows(*key) for key in declared}
                        original_scratch = baseline.scratch()
                        # Connection delegates reads, not Python attribute
                        # assignments: set autocommit on its actual ODBC handle.
                        raw.raw.autocommit = False
                        try:
                            case = qualify_case(raw, isolation, name, role, path, declared)
                        except Exception as error:
                            case = dict(name=name, source_path=path, source_sha256=PINS[path], status='FAIL',
                                        failure_type=type(error).__name__, failure=str(error),
                                        fixtures=[dict(role=k[0], table=k[1], rows=storage(v)) for k, v in declared.items()])
                        finally:
                            raw.rollback()
                            raw.raw.autocommit = True
                        receipt['cases'].append(case)
                        case['outer_rollback'] = raw.execute('SELECT @@TRANCOUNT').fetchval() == 0
                        case['rollback_populations'] = {
                            '.'.join(key): compare_rows(originals[key], baseline.rows(*key), baseline.schema(*key))
                            for key in originals}
                        restored_scratch = baseline.scratch()
                        case['rollback_scratch'] = {name: compare_rows(rows, restored_scratch[name],
                                                    baseline.schema('Intermediate', name))
                                                    for name, rows in original_scratch.items()}
                        restored = all(r['status'] == 'PASS' for r in (
                            *case['rollback_populations'].values(), *case['rollback_scratch'].values()))
                        if case['status'] != 'PASS' or not case['outer_rollback'] or not restored:
                            raise ValueError('Stopped at first qualification failure: ' + name)
            receipt['status'] = 'PASS'
        except Exception as error:
            receipt.update(status='FAIL', failure_type=type(error).__name__, failure=str(error))
        finally:
            receipt['implementation_identity_unchanged'] = implementation_pins() == receipt['implementation_pins']
            if not receipt['implementation_identity_unchanged']:
                receipt.update(status='FAIL', failure='Modern implementation changed during qualification')
            json.dump(storage(receipt), file, indent=2, ensure_ascii=False, allow_nan=False)
            file.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args()
    result = run(options.owner, options.output)
    print(json.dumps(dict(status=result['status'], cases=len(result['cases']), output=str(options.output))))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
