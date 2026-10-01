"""BTR-specific SQL, header builder and CsvHelper parity; no engine replay."""
import base64
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import ijson
import pyodbc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from parity.btr_queries import export_query, SOURCE, SOURCE_SHA
from parity.legacy_isolation import connection, exclusive_replay
from parity.output_archive import file_sha
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences
from parity.verify_btr_filters import bound
from parity.verify_rrr_consumer import auth_ctes, supplement_temp_hierarchy, temp_rows, PERMISSION_SHA
from parity.verify_rrr_export import CONFIG, call, typed


def assert_source_failure(case_id, sql_state, message):
    expected = {**{name: ('42000', '4104', 'sla.c') for name in
                  ('raw-null-hasnovalue', 'raw-null-notequal', 'raw-null-negative-like', 'pair-custom')},
                'missing-availability': ('42S22', '207', 'availability'),
                'missing-coverage': ('42S22', '207', 'coverage'),
                'invalid-hierarchy-column': ('42S22', '207', 'sl9'),
                'invalid-operator': ('42000', '102', 'Incorrect syntax'),
                'black-red-invalid-multi-column': ('42000', '102', 'Incorrect syntax')}
    state, code, text = expected[case_id]
    assert sql_state == state and '(' + code + ')' in message and text in message


def terminal_requirements(legacy, provenance, target):
    """Lossless consumer-field projection, not a replay or early-state substitute.

    GenerateRationReqReport's initial INSERT SELECT copies these nine fields
    directly, without a join/filter/distinct. Its later updates and the remaining
    sequence leave them unchanged. Pin the reviewed SQL; corroborate the terminal
    dispatch colour against the separately captured CalculationCheckpoints.
    """
    root = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR')
    pins = {'UpdateDispatchPriority.sql': '1331f5cb21ece8ffce3ac3c9dbd61e6df7c2e636bdd297c6267b6b5595656e90',
            'Ration_Scripts/GenerateRationReqReport.sql': 'eca76c08c57a553c65f3c9bb460434adfbbcc88341a3a607bbe80a84c825f9c3',
            'UpdateBPR.sql': 'fb050b8cb30a8c582dcf8ef5c4a50dff52c5252f82fc6318862fabfa6708722b'}
    for name, expected in pins.items():
        assert file_sha(root / name) == expected
    fields = ('SKUCode', 'WhCode', 'ParentWhCode', 'Norm', 'VirtualNorm', 'Stock', 'GIT',
              'DispatchColor', 'PhysicalInventoryColor')
    rows = [{field: row[field] for field in fields} for row in legacy['late']['vf_RationedReqReport']]
    with gzip.open(provenance['capture'], 'rb') as stream:
        terminal = next(ijson.items(stream, 'output.CalculationCheckpoints.requirements', use_float=True))
    captured = [dict(SKUCode=r['sku_code'], WhCode=r['location_code'], DispatchColor=r['dispatch_colour']) for r in terminal]
    projected = [{field: row[field] for field in ('SKUCode', 'WhCode', 'DispatchColor')} for row in rows]
    assert len(rows) == len(terminal) == 1240 and not differences(captured, projected)
    assert len({(r['SKUCode'], r['WhCode']) for r in rows}) == len(rows)
    path = target / 'terminal-requirement-fields.json.gz'
    with gzip.open(path, 'wt') as stream:
        json.dump(rows, stream)
    return rows, dict(fields=fields, rows=len(rows), source_sql=pins, sha256=file_sha(path),
        terminal_dispatch_capture_equal=True,
        qualification='Terminal consumer fields reconstructed through canonical lossless INSERT SELECT; '
                      'native_inputs is pre-colour and is not the terminal requirement table; no engine replay or state write')


def main():
    target = Path(sys.argv[1]).resolve()
    assert target.parent == Path('D:/freshvcf-build/evidence').resolve()
    target.mkdir(exist_ok=False)
    result = dict(status='FAILED', engine_replays=0, persistent_writes=False, serving_changes=False)
    try:
        assert file_sha(SOURCE) == SOURCE_SHA
        parent = Path('D:/freshvcf-build/evidence/f3-btr-filters-modern-001')
        roster = json.loads((parent / 'cases.json').read_text())['cases']
        cases = [dict(id=case['id'], payload=deepcopy(case['payload']), layout='') for case in roster]
        for i, case in enumerate(cases):
            case['payload'].update(name='tech' if i % 2 == 0 else 'eco', reportName='BTR', user={'id': 'btr-export-proof'})
        root = deepcopy(cases[0]); root['id'] = 'root-pipeline'; root['payload']['name'] = 'eco'; cases.append(root)
        for name, layout in (
                ('saved-layout', {'columns': [{'colId': 'D90'}, {'colId': 'SKUCode', 'pinned': 'left'},
                    {'colId': 'Norm', 'hide': True}, {'colId': 'WhCode'}, {'colId': 'D79'},
                    {'colId': 'D90'}, {'colId': 'unknown'}]}),
                ('empty-layout', {'columns': []}), ('invalid-layout', 'bad-json')):
            case = deepcopy(cases[1]); case['id'] = name
            case['layout'] = layout if isinstance(layout, str) else json.dumps(layout)
            case['payload']['paginationParameter'] = {'recordsPerPage': 1, 'pageNumber': 9}
            cases.append(case)
        (target / 'requests.json').write_text(json.dumps(dict(cases=cases), indent=2))
        runtime = json.loads(subprocess.check_output(['docker', 'inspect', 'freshvcf-preview-mta-1'], text=True))[0]
        args = ['docker', 'run', '--rm', '--name', 'freshvcf-stage2-btr-export', '--network', 'freshvcf-test_default',
                '--memory', '4g', '--memory-swap', '4g', '--cpus', '2', '-v', 'F:/freshvcf:/app:ro',
                '-v', 'D:/freshvcf-build/evidence:/evidence:ro', '-e', 'PYTHONPATH=/app']
        for value in runtime['Config']['Env']:
            if value.startswith(('VF_', 'MTA_')):
                args += ['-e', value]
        for mount in runtime['Mounts']:
            if mount['Destination'] != '/app':
                args += ['-v', mount['Source'] + ':' + mount['Destination'] + ':ro']
        args += [runtime['Image'], 'python', 'tools/btr_export_probe.py', '/evidence/' + target.name + '/requests.json']
        modern = json.loads(call(args, target / 'modern.log'))
        observed = {row['id']: row for row in modern['observations']}
        for mode, script, output in (('filters', 'invoke_legacy_rrr_filters.ps1', 'filters.json'),
                                      ('headers', 'invoke_legacy_rrr_export.ps1', 'headers.json')):
            command = ['pwsh', '-NoProfile', '-File', str(ROOT / 'parity' / script), '-InputPath', str(target / 'requests.json'),
                       '-OutputPath', str(target / output)]
            command += ['-Report', 'BTR'] if mode == 'filters' else ['-Mode', 'headers']
            call(command, target / (mode + '.log'))
        filters = {row['id']: row for row in json.loads((target / 'filters.json').read_text())['cases']}
        headers = {row['id']: row['query'] for row in json.loads((target / 'headers.json').read_text())['cases']}
        assert file_sha(CONFIG) == '4b248637cd659bdf05730964513bf555103d83521a268e93cddb24bc8c6f34da'
        permission = Path('D:/freshvcf-build/inputs/permission-input-v1.json'); assert file_sha(permission) == PERMISSION_SHA
        catalogue = json.loads(permission.read_text())
        legacy, provenance = terminal_inputs()
        requirements, requirement_proof = terminal_requirements(legacy, provenance, target)
        result['requirement_input'] = requirement_proof
        assert modern['run'] == provenance['modern_run'] and modern['output_digest'] == provenance['modern_output_digest']
        checks, oracle = [], []
        os.environ['VFTEST_PROFILE'] = 'fresh'
        with exclusive_replay(), connection('VFTEST_BTR') as db:
            closing = legacy['closing']
            for table in ('BPPTrendDispatch', 'BPPTrendPhysicalInv', 'BufferTrendDispatch', 'BufferTrendPhysicalInv',
                          'SkuAttributeData', 'LocationAttributeData', 'CategoryColDescription'):
                alias = '#Sku' if table == 'SkuAttributeData' else '#Loc' if table == 'LocationAttributeData' else '#' + table
                temp_rows(db, alias, 'dbo.' + table, closing['btr'].get(table, closing['consumer_context'].get(table)))
            supplement_temp_hierarchy(db, catalogue)
            # Only the nine consumed fields are reconstructed. Preserve their
            # native SQL types without fabricating unrelated NOT NULL columns.
            req_fields = ','.join('[' + field + ']' for field in requirement_proof['fields'])
            db.execute('SELECT TOP 0 ' + req_fields + ' INTO #Req FROM VFTEST_BPR.dbo.vf_ReqCalculation')
            db.cursor().executemany('INSERT INTO #Req (' + req_fields + ') VALUES (' +
                ','.join('?' for _ in requirement_proof['fields']) + ')',
                [tuple(row[field] for field in requirement_proof['fields']) for row in requirements])
            temp_rows(db, '#Standard', 'VFTEST_Importer.dbo.SKULocStandardAttributes', closing['dbm']['SKULocStandardAttributes'])
            for table in ('SKUDescriptionTbl', 'SiteDescriptionTbl'):
                temp_rows(db, '#' + table, 'VFTEST_Importer.dbo.' + table, closing['importer'][table])
            temp_rows(db, '#Dates', 'dbo.BufferTrendDates', closing['btr']['BufferTrendDates'])
            db.execute('SELECT TOP 0 * INTO #Config FROM VFTEST_BPR.dbo.ui_ReportConfigurations; '
                       'SELECT TOP 0 * INTO #Layouts FROM VFTEST_BPR.dbo.Userwise_UiReportConfiguration')
            lines = [line.strip().replace('[dbo].[ui_ReportConfigurations]', '#Config') for line in CONFIG.read_text(encoding='utf-8-sig').splitlines()
                     if line.startswith('INSERT') and "VALUES (N'BufferTrendReport'," in line]
            assert lines
            db.execute('\n'.join(lines))
            for case in cases:
                db.execute('DROP TABLE IF EXISTS #ProductPermissions; DROP TABLE IF EXISTS #LocationPermissions; DELETE FROM #Layouts')
                if case['layout']:
                    db.execute('INSERT INTO #Layouts (username,reportname,state) VALUES (?,?,?)', 'btr-export-proof',
                               'BTRon-hand' if case['payload']['name'] == 'tech' else 'BTRpipeline', case['layout'])
                f = filters[case['id']]
                query = bound(export_query(case['payload']['name'], sql_filter=f['sql_filter'], sql_join_filter=f['sql_join_filter'],
                                           auth_cte=auth_ctes(db, catalogue, case['payload'])))
                try:
                    cursor = db.execute(query)
                except pyodbc.Error as exc:
                    assert_source_failure(case['id'], exc.args[0], str(exc))
                    assert observed[case['id']]['status'] == 503, (case['id'], repr(exc), observed[case['id']])
                    checks.append(dict(id=case['id'], status='LEGACY_FLAW_NOT_PARITY',
                                       legacy_error=str(exc), modern=observed[case['id']]))
                    (target / (case['id'] + '-legacy.sql')).write_text(query)
                    continue
                assert observed[case['id']]['status'] == 200, (case['id'], observed[case['id']])
                fields = [c[0] for c in cursor.description]
                rows = [dict(zip(fields, row)) for row in cursor.fetchall()]
                header_query = headers[case['id']].replace('VFTEST_BINDING.dbo.[Userwise_UiReportConfiguration]', '#Layouts').replace(
                    'VFTEST_BINDING.dbo.ui_ReportConfigurations', '#Config').replace('VFTEST_BINDING.dbo.BufferTrendDates', '#Dates')
                cursor = db.execute(header_query)
                while cursor.description is None:
                    assert cursor.nextset()
                mapping = sorted([(row[0] or '', row[1], row[2]) for row in cursor.fetchall()], key=lambda row: row[2])
                effective = [(header, code) for header, code, _ in mapping if code and code.strip() and code in fields]
                typed_rows = [{k: typed(v) for k, v in row.items()} for row in rows]
                delta = differences(typed_rows, observed[case['id']]['rows'], '/' + case['id'])
                check = dict(id=case['id'], status='PASS', row_count=len(rows),
                             raw_typed_equal=not delta, ordered_rows_equal=typed_rows == observed[case['id']]['rows'],
                             headers_equal=[list(pair) for pair in effective] == observed[case['id']]['headers'], differences=delta)
                checks.append(check)
                oracle.append(dict(id=case['id'], records=[[typed(header) for header, _ in effective]] +
                                  [[typed(row[code]) for _, code in effective] for row in rows]))
                (target / (case['id'] + '-legacy.sql')).write_text(query + ';\n' + header_query)
        (target / 'oracle-cells.json').write_text(json.dumps(dict(cases=oracle)))
        result.update(checks=checks, provenance=provenance, source_sha256=SOURCE_SHA)
        call(['pwsh', '-NoProfile', '-File', str(ROOT / 'parity/invoke_legacy_rrr_export.ps1'), '-InputPath',
              str(target / 'oracle-cells.json'), '-OutputPath', str(target / 'legacy-csv.json'), '-Mode', 'csv'], target / 'csv.log')
        encoded = json.loads((target / 'legacy-csv.json').read_text())
        assert encoded['csvhelper_sha256'] == '20101c398654a14bfd42bd78d7281f43197d19b7b3cf41c7aae93f1eaba65a61'
        for case in encoded['cases']:
            expected, actual = base64.b64decode(case['base64']), base64.b64decode(observed[case['id']]['base64'])
            (target / (case['id'] + '-legacy.csv')).write_bytes(expected)
            (target / (case['id'] + '-modern.csv')).write_bytes(actual)
            next(row for row in checks if row['id'] == case['id']).update(csv_bytes_equal=expected == actual,
                legacy_sha256=hashlib.sha256(expected).hexdigest(), modern_sha256=hashlib.sha256(actual).hexdigest())
        strict = [row for row in checks if row['status'] == 'PASS']
        assert all(row['raw_typed_equal'] and row['ordered_rows_equal'] and row['headers_equal'] and row['csv_bytes_equal'] for row in strict), 'BTR export mismatch'
        result.update(status='PASS_BTR_EXPORT_SQL_HEADERS_TYPES_AND_CSV_WITH_DECLARED_FLAWS',
                      strict_pass=len(strict), declared_flaws=len(checks) - len(strict),
                      csvhelper_sha256=encoded['csvhelper_sha256'])
    except Exception as exc:
        result['error'] = repr(exc)
        raise
    finally:
        result['source_hashes'] = {str(p.relative_to(ROOT)).replace('\\', '/'): file_sha(p) for p in
            [ROOT / 'mta/presentation/btr_sql.py', ROOT / 'mta/presentation/btr_export.py', ROOT / 'mta/presentation/views.py',
             ROOT / 'parity/btr_queries.py', ROOT / 'tools/btr_export_probe.py']}
        (target / 'receipt.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(dict(status=result['status'], error=result.get('error'))), flush=True)


if __name__ == '__main__':
    main()
