"""Rollback-only SQL-derived fullkit proof; external checks are supplied facts.

Never executes BAT/site hooks, resolves files, sanitizes data or sends alerts.
Native NOT NULL fields prohibit artificial NULL setting/type/existence fixtures.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from mta.domain import complete_daily_fullkit as fullkit
from mta.domain.complete_daily_scalars import ascii_equal
from mta.serialization import storage
from parity.adapters.legacy.complete_daily_sql import namespace, data_directory
from parity.verify_complete_daily_producers import (OWNER, SOURCE, FixtureSQL, compare_rows,
    guard_options, native_context, scalar_binding, preflight_fixture_suite)

RUN_DATE = '2026-06-06'
SOURCES = ('Engine/CheckRunStartCriteria.bat', 'Engine/CheckForFilesAvailability.bat',
           'Engine/FullkitCheckForPostRun.bat')
# Exact -Q payloads from the pinned sources, with only EXIT (sqlcmd exit-code
# routing) removed before ordinary ODBC execution. Substitutions are explicit.
STATEMENTS = {
    'initial_flag': (SOURCES[0], "update ImporterSettingsTbl set Value=1 where Parameter='FullkitAvailable'"),
    'initial_date': (SOURCES[0], "update ImporterSettingsTbl set Value=CONVERT(Date,'%Rundate%') where Parameter='FullkitCheckdate'"),
    'initial_files': (SOURCES[0], "EXIT(update CriticalFiles set [Exists]=0, [ResolvedPath]=NULL,[ResolvedFileName]=NULL)"),
    'missing_files': (SOURCES[1], "EXIT(select count(*) from CriticalFiles where [Type]='%FileType%' and [Exists]=0)"),
    'abort_flag': (SOURCES[0], "update ImporterSettingsTbl set Value=0 where Parameter='FullkitAvailable'"),
    'post_count': (SOURCES[2], "EXIT(select count(*) from ImporterSettingsTbl where (Parameter='FullkitAvailable' and Value='1') or (Parameter='FullkitCheckdate' and Value=convert(nvarchar,convert(Date,'%Rundate%'))))"),
}
FILES = ('mta/domain/complete_daily_fullkit.py', 'mta/domain/complete_daily_scalars.py',
         'mta/serialization.py', 'parity/verify_complete_daily_fullkit.py',
         'parity/verify_complete_daily_producers.py', 'parity/adapters/legacy/complete_daily_sql.py',
         'parity/legacy_isolation.py')
TABLES = (('Importer', 'ImporterSettingsTbl'), ('Importer', 'CriticalFiles'))


def code_pins():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in FILES}


def source_preflight():
    manifest = json.loads((ROOT/'baseline/manifest.json').read_text())
    registered = {r['path']: r['sha256'] for r in manifest['engine_sources']}
    pins = {}
    for relative in SOURCES:
        path = SOURCE/relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if registered.get(path.as_posix()) != actual:
            raise ValueError('Fullkit canonical source identity differs: '+relative)
        text = path.read_text(encoding='cp1252')
        for source, statement in STATEMENTS.values():
            if source == relative and ('-Q "'+statement+'"') not in text:
                raise ValueError('Exact native inline SQL absent from pinned BAT: '+statement)
        pins[relative] = actual
    post = (SOURCE/SOURCES[2]).read_text(encoding='cp1252')
    for literal in ('if [%Scope%]==[UptoBPR] goto end:', 'if [%Scope%]==[UptoDBM] goto end:',
                    'if [%Scope%]==[] goto end:', 'if [%ERRORLEVEL%] NEQ [2] ('):
        if literal not in post:
            raise ValueError('Native post-run control branch differs: '+literal)
    return pins


def statement(name, *, file_type=None, run_date=RUN_DATE):
    if run_date not in (RUN_DATE, '2026-06-07'):
        raise ValueError('Undeclared fixture date')
    sql = STATEMENTS[name][1].replace('%Rundate%', run_date)
    if '%FileType%' in sql:
        if file_type not in ('GoAheadFiles', 'DataFiles'):
            raise ValueError('Undeclared fixture file type')
        sql = sql.replace('%FileType%', file_type)
    if sql.startswith('EXIT('):
        sql = sql[5:-1]
    return sql


def fixture_cases():
    settings = [dict(Parameter='FullkitAvailable', Value='0'),
                dict(Parameter='FullkitCheckdate', Value='2026-06-05')]
    files = [dict(Path='owned', FileName='go.txt', Type='GoAheadFiles', Exists=False,
                  ResolvedPath='old', ResolvedFileName='old'),
             dict(Path='owned', FileName='daily.csv', Type='DataFiles', Exists=True,
                  ResolvedPath=None, ResolvedFileName=None)]
    cases = [dict(name='stale-current-cumulative-missing', settings=settings, files=files,
                  checks=(True, False, True)),
             dict(name='duplicate-two-flags-without-date', settings=[dict(Parameter='FullkitAvailable', Value='1')]*2,
                  files=[], checks=(True, True, True)),
             dict(name='duplicate-flags-plus-current-date-count-three',
                  settings=[dict(Parameter='FullkitAvailable', Value='1')]*2+
                           [dict(Parameter='FullkitCheckdate', Value=RUN_DATE)],
                  files=[], checks=(False, True, True)),
             dict(name='missing-settings-daily-hook-failure', settings=[], files=[],
                  checks=(True, True, False))]
    return [case | dict(declared={TABLES[0]: case['settings'], TABLES[1]: case['files']}) for case in cases]


def qualify(raw, isolation, case):
    sql = FixtureSQL(raw, isolation)
    for key, rows in case['declared'].items():
        sql.load(*key, rows)
    before = {key: sql.rows(*key) for key in TABLES}
    report = dict(name=case['name'], status='STARTED', inputs=[dict(role=k[0], table=k[1],
        schema=sql.schema(*k), rows=storage(v)) for k,v in before.items()],
        supplied_checks=dict(zip(('go_ahead','files_available','daily_data_available'),case['checks'])),
        sql_observations=[], checkpoints=[])
    def execute(name, **arguments):
        text = statement(name, **arguments)
        cursor = raw.execute(text)
        value = cursor.fetchval() if name in ('missing_files','post_count') else None
        report['sql_observations'].append(dict(name=name, sql=text, arguments=arguments, result=value))
        return value
    def population(label, wanted):
        checkpoint = dict(name=label, comparisons={})
        report['checkpoints'].append(checkpoint)
        for key, rows in wanted.items():
            value = compare_rows(sql.rows(*key), rows, sql.schema(*key))
            checkpoint['comparisons']['.'.join(key)] = value
            if value['status'] != 'PASS':
                raise ValueError('Full native fullkit population mismatch: '+'.'.join(key))
    def post(settings, label):
        for day in (RUN_DATE, '2026-06-07'):
            count = execute('post_count', run_date=day)
            expected = fullkit.post_run_fullkit(settings, day, scope='PostBPR', equal=ascii_equal)
            actual = dict(checked=True, matching_count=count, AbortPostRun=count != 2)
            report['checkpoints'].append(dict(name=label+'-'+day, actual=actual, expected=expected))
            if actual != expected:
                raise ValueError('Native post-run COUNT=2 outcome differs')
        for scope in ('UptoBPR','UptoDBM',''):
            actual = dict(checked=False, matching_count=None, AbortPostRun=False)
            expected = fullkit.post_run_fullkit(settings,RUN_DATE,scope=scope,equal=ascii_equal)
            report['checkpoints'].append(dict(name=label+'-skipped-'+scope, actual=actual, expected=expected))
            if actual != expected:
                raise ValueError('Pinned skipped post-run branch differs')
    def availability(rows, label):
        previous = True
        for file_type in ('GoAheadFiles','DataFiles'):
            count = execute('missing_files',file_type=file_type)
            expected = fullkit.file_availability(rows,file_type,previous=previous,equal=ascii_equal)
            actual = dict(missing_count=count,files_available=previous and count==0)
            report['checkpoints'].append(dict(name=label+'-'+file_type,actual=actual,expected=expected))
            if actual != expected:
                raise ValueError('Native cumulative availability differs')
            previous = actual['files_available']
    try:
        post(before[TABLES[0]], 'opening')
        availability(before[TABLES[1]], 'supplied-resolution-snapshot')
        modern = fullkit.initialise_fullkit(before[TABLES[0]],before[TABLES[1]],RUN_DATE,equal=ascii_equal)
        for name in ('initial_flag','initial_date','initial_files'):
            execute(name)
        population('initialise',{TABLES[0]:modern['ImporterSettingsTbl'],TABLES[1]:modern['CriticalFiles']})
        availability(modern['CriticalFiles'], 'reset-resolution-snapshot')
        # Resolver/file/hook outcomes are explicit caller inputs; this operation
        # does not claim to execute those external checks or the alert wrapper.
        checks = case['checks']
        modern_outcome = fullkit.fullkit_outcome(modern['ImporterSettingsTbl'],go_ahead=checks[0],
            files_available=checks[1],daily_data_available=checks[2],equal=ascii_equal)
        native_abort = not all(checks)
        if native_abort:
            execute('abort_flag')
        actual = dict(AbortRun=native_abort,daily_unavailability_alert_required=native_abort)
        expected = {key:modern_outcome[key] for key in actual}
        report['checkpoints'].append(dict(name='final-abort',actual=actual,expected=expected))
        if actual != expected:
            raise ValueError('Native final abort branch differs')
        population('outcome',{TABLES[0]:modern_outcome['ImporterSettingsTbl'],TABLES[1]:modern['CriticalFiles']})
        post(modern_outcome['ImporterSettingsTbl'],'closing')
        report['status']='PASS'
    except Exception as error:
        report.update(status='FAIL',failure_type=type(error).__name__,failure=str(error),
            native_after_error=[dict(role=k[0],table=k[1],rows=storage(sql.rows(*k))) for k in TABLES])
    return report


def run(owner, output):
    output = guard_options(owner, output)
    pins = source_preflight()
    from parity import legacy_isolation as isolation
    if isolation._lease is not None:
        raise ValueError('Cannot bind fullkit owner during active lease')
    isolation.MAPPING.clear(); isolation.MAPPING.update(namespace(owner))
    isolation.DATA=data_directory(owner)
    os.environ['VFTEST_PROFILE']='fresh'
    receipt=dict(owner=owner,namespace=namespace(owner),status='STARTED',source_pins=pins,
        implementation_pins=code_pins(),scalar_adapters=scalar_binding(),cases=[],
        scope='small rollback SQL-derived fullkit operations; zero business days',
        limitations=['no actual file existence/resolution/deletion, site hooks, sanitation or alerts executed',
            'NOT NULL settings/type/existence cannot be represented as impossible native NULL fixtures',
            'restoration proves populations and scratch, not SQL IDENTITY allocator state',
            'pinned BAT control branches are compared as supplied boolean decisions, not BAT execution'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as file:
        try:
            with isolation.exclusive_replay(validate_schema=True):
                receipt['schema_receipts']=[json.loads((data_directory(owner)/(db+'-schema.json')).read_text())
                    for db in namespace(owner).values()]
                with isolation.connection('VFTEST_Importer') as raw:
                    receipt['native_context']=native_context(raw,isolation)
                    sql=FixtureSQL(raw,isolation)
                    cases=fixture_cases()
                    receipt['fixture_preflight']=preflight_fixture_suite(sql,
                        [(c['name'],'Importer','pinned inline BAT SQL',c['declared']) for c in cases])
                    if receipt['fixture_preflight']['status']!='PASS':
                        raise ValueError('Entire fixture suite schema preflight failed before mutation')
                    for declared in cases:
                        baseline={k:sql.rows(*k) for k in TABLES}
                        scratch=sql.scratch()
                        identity_before=raw.execute("SELECT IDENT_CURRENT('dbo.CriticalFiles')").fetchval()
                        raw.raw.autocommit=False
                        try:
                            case=qualify(raw,isolation,declared)
                            receipt['cases'].append(case)
                        finally:
                            raw.rollback(); raw.raw.autocommit=True
                        case['identity_allocator']=dict(sql="SELECT IDENT_CURRENT('dbo.CriticalFiles')",
                            before=storage(identity_before),
                            after=storage(raw.execute("SELECT IDENT_CURRENT('dbo.CriticalFiles')").fetchval()),
                            scope='observed allocator; outside population-restoration assertion')
                        case['outer_rollback']=raw.execute('SELECT @@TRANCOUNT').fetchval()==0
                        wanted=baseline | {('Intermediate',k):rows for k,rows in scratch.items()}
                        case['restoration']={'.'.join(k):compare_rows(sql.rows(*k),rows,sql.schema(*k))
                                             for k,rows in wanted.items()}
                        if set(sql.scratch())!=set(scratch):
                            raise ValueError('Scratch roster changed')
                        if (case['status']!='PASS' or not case['outer_rollback']
                                or any(r['status']!='PASS' for r in case['restoration'].values())):
                            raise ValueError('Stopped at first fullkit fixture mismatch: '+declared['name'])
            receipt['status']='PASS'
        except Exception as error:
            receipt.update(status='FAIL',failure_type=type(error).__name__,failure=str(error))
        finally:
            receipt['implementation_identity_unchanged']=receipt['implementation_pins']==code_pins()
            receipt['source_identity_unchanged']=pins==source_preflight()
            if not receipt['implementation_identity_unchanged'] or not receipt['source_identity_unchanged']:
                receipt.update(status='FAIL',failure='Source/implementation drift during qualification')
            json.dump(storage(receipt),file,indent=2,allow_nan=False); file.write('\n')
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=run(args.owner,args.output)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),output=str(args.output))))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
