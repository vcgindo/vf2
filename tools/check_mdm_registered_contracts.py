"""Offline field-boundary proof for a supplied registered MDM case roster.

Never calls a workflow handler or execute_day. Django is configured with an
in-memory database and every attempted SQL connection is denied. This is an
upload/conversion qualification, not permission, persistence or successor proof.
"""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'user-service')]
sys.dont_write_bytecode = True


def normalized(value):
    return json.loads(json.dumps(value, default=str))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roster', type=Path, required=True)
    parser.add_argument('--workbook', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Evidence must be additive'
    from django.conf import settings
    settings.configure(SECRET_KEY='offline-contract-check-only',
        INSTALLED_APPS=['mta.runtime.apps.RuntimeConfig'], USE_TZ=True,
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}})
    import django
    django.setup()
    from django.db.backends.base.base import BaseDatabaseWrapper
    import pandas as pd
    from django.core.files.uploadedfile import SimpleUploadedFile
    from master_validation.utils.read_temporaryfile_to_disk import read_uploaded_master_file
    from master_validation.utils.replace_headers import replace_headers_with_keys_streaming
    from master_validation.validators.commons.master_id_mapping import MASTER_ID_TO_VALIDATION
    from mta.mdm import tasks, location_tasks, skuloc_tasks, supplier_tasks
    from mta.mdm import season_tasks, force_tasks, phase_controls_tasks

    configs = {}
    for path in sorted((ROOT / 'mta/config').glob('mdm_*.json')):
        for row in json.loads(path.read_text()).get('UI_MDMConfig', []):
            configs.setdefault(row['MasterId'], {})[row['Col_Code']] = row
    results, checks = [], []

    def check(name, actual, expected):
        ok = normalized(actual) == normalized(expected)
        checks.append(dict(name=name, pass_=ok, actual=normalized(actual), expected=normalized(expected)))
        return ok

    # Read the actual view's rule assignment. These NMS classes use their own
    # checks; an empty context is NOT evidence of database/scope validation.
    view = (ROOT / 'user-service/master_validation/views/basic_validation.py').read_text()
    check('production NMS context is empty except MOQ destination flag',
          'validation_rules = {}' in view and "master_id == '5' and screen_type == 'add'" in view, True)
    converters = {1: tasks.convert, 2: location_tasks.convert, 3: skuloc_tasks.convert,
        4: lambda r, k: supplier_tasks.convert(4, r, k),
        7: lambda r, k: phase_controls_tasks._convert(7, r, k),
        8: lambda r, k: phase_controls_tasks._convert(8, r, k),
        9: lambda r, k: phase_controls_tasks._convert(9, r, k),
        12: lambda r, k: season_tasks.convert(r, k, 12), 13: force_tasks.convert}

    def validate(mid, action, values):
        frame = pd.DataFrame([values], dtype=object)
        validator = MASTER_ID_TO_VALIDATION[str(mid)](frame)
        headers = {k: v['Header'] for k, v in configs[mid].items()}
        return json.loads(validator.validation(frame.iloc[0].copy(), 0, headers,
                    {1: 'add', 2: 'modify', 3: 'remove'}[action], {}))[0]

    with patch.object(BaseDatabaseWrapper, 'ensure_connection', side_effect=AssertionError('Offline proof forbids database connections')):
        cases = [c for c in json.loads(args.roster.read_text()) if c['index'] not in (6, 8, 9, 10, 18)]
        check('exact remaining roster', [c['index'] for c in cases], [12,14,16,20,22,23,24,25,26,27,29,30,32,34,35,36])
        for case in cases:
            mid, action = case['master_id'], case['action']
            if mid in (6, 10):
                results.append(dict(index=case['index'], status='REQUIRES_OWN_PREDECESSOR_SELECTED_ROW',
                    intended=case['data'], qualification='No invented current row or upload; selection/status/scopes remain held'))
                continue
            fields = {k: r for k, r in configs[mid].items() if r[{1:'IsAdd',2:'IsDownload',3:'IsDelete'}[action]]}
            values = {k: str(case['data'][k]) if case['data'].get(k) is not None else float('nan') for k in fields}
            if case['index'] == 20:
                df = read_uploaded_master_file(SimpleUploadedFile(args.workbook.name, args.workbook.read_bytes()))
                headers = replace_headers_with_keys_streaming(df, [{'key':k,'displayName':r['Header']} for k,r in configs[mid].items()], mid)
                validator = MASTER_ID_TO_VALIDATION[str(mid)](df)
                emitted = json.loads(validator.validation(df.iloc[0].copy(),0,headers,'add',{}))[0]
            else:
                emitted = validate(mid, action, values)
            # Exact normal frontend _.omit(...,'error','warning','users') has
            # its own Node execution proof; no blank/null cleanup is added.
            wire = {k:v for k,v in emitted.items() if k not in ('error','warning','users')}
            check(f'{case["index"]} upload acceptance', emitted['error'], '')
            if mid == 2 and action == 3:
                # This is an inline native Remove branch, not convert().
                converted = dict(WHCode=wire['wc'], WHDescription='', LogisticsLocation='',
                    **{f'LL{i}':wire[f'LL{i}'] for i in range(1,4)})
                boundary = 'inline Remove branch inspected, not executed'
            else:
                converted = converters[mid](wire, list(wire))
                boundary = 'actual production converter executed; no submit handler'
            differences = []
            for key, expected in case['data'].items():
                if key not in fields:
                    continue
                name = fields[key]['TableField'].rstrip()
                if name == 'StockPercentForRationing': name = 'StockPercentForRat'
                # Master3's pinned configuration spells WHCode while its
                # typed task alias is WhCode. This is a field-name boundary,
                # not a missing business value.
                if mid == 3 and name == 'WHCode': name = 'WhCode'
                actual = converted.get(name)
                equivalent = str(actual) == str(expected) or actual == expected
                if isinstance(actual, (int,float)) and not isinstance(actual,bool):
                    try: equivalent = float(actual) == float(expected)
                    except (TypeError, ValueError): pass
                if key == 'da': equivalent = actual is (expected.lower() in ('yes','y','1'))
                if not equivalent: differences.append(dict(alias=key,field=name,intended=expected,converted=normalized(actual)))
            results.append(dict(index=case['index'], master=mid, action=action, intended=case['data'],
                fields=list(fields), emitted=emitted, wire=wire, converted=normalized(converted),
                differences=differences, status=('INTENDED_VALUE_MISMATCH' if differences else
                    'UPLOAD_ADMITTED_INLINE_MAPPING_STATIC' if mid == 2 and action == 3 else
                    'UPLOAD_CONVERSION_QUALIFIED'),
                boundary=boundary, downstream='persisted/reviewer/queue/consumer not certified by this check'))
        check('known substantive mismatch detected, no silent qualification',
              [(r['index'],r.get('differences')) for r in results if r.get('differences')],
              [(20,[dict(alias='ed',field='EndDate',intended=None,converted='1900-01-01')])])
        finite_case = next(r for r in results if r['index']==20)['wire'].copy()
        finite_case['ed']='2026-10-30'
        finite_upload=validate(12,1,finite_case)
        check('proposed finite-date fixture admitted by actual validator',finite_upload['error'],'')
        finite_wire={k:v for k,v in finite_upload.items() if k not in ('error','warning','users')}
        check('proposed finite date survives production conversion',season_tasks.convert(finite_wire,list(finite_wire),12)['EndDate'],date(2026,10,30))
        # Duplicate rejection is the actual upload function, not a synthetic
        # count assertion. It does not claim native submission deduplicates.
        for idx in (20,22,27,36):
            base=next(r for r in results if r['index']==idx)
            frame=pd.DataFrame([base['wire'],base['wire']],dtype=object)
            validator=MASTER_ID_TO_VALIDATION[str(base['master'])](frame)
            headers={k:v['Header'] for k,v in configs[base['master']].items()}
            parts=[validator.validation(frame.iloc[n].copy(),n,headers,{1:'add',2:'modify',3:'remove'}[base['action']],{}) for n in range(2)]
            duplicated=json.loads(''.join(parts))
            check(f'{idx} duplicate upload pair/triple rejected',all(bool(r['error']) for r in duplicated),True)

        # Canonical GetValuesSPF preserves SQL NULL separately from quoted empty;
        # fixed independent expectations intentionally do not come from convert.
        for value, expected in [(None,None),('',date(1900,1,1)),(' ',date(1900,1,1)),('1900-01-01',date(1900,1,1)),('2026-10-30',date(2026,10,30))]:
            check('season EndDate '+repr(value), season_tasks.convert({'ed':value},['ed'],12), {'EndDate':expected})
        for module, alias, field in [(force_tasks,'nn','NewNorm'),(season_tasks,'bd','BuildupDuration'),(phase_controls_tasks,'tn','TargetNorm')]:
            fn = (lambda r,k: season_tasks.convert(r,k,12)) if module is season_tasks else ((lambda r,k: phase_controls_tasks._convert(9,r,k)) if module is phase_controls_tasks else module.convert)
            for value,expected in [(None,None),('',0),(' ',0),('0',0),('24',24),('-1',-1)]:
                check(module.__name__+' '+repr(value),fn({alias:value},[alias]),{field:expected})
            for bad in ['1.5','2147483648','-2147483649']:
                try: fn({alias:bad},[alias]); rejected=False
                except ValueError: rejected=True
                check(module.__name__+' rejects '+bad,rejected,True)
        check('SKU optional decimal blank is NULL', tasks.convert({'wt':'','vm':''},['wt','vm']),{'Weight':None,'Volume':None})
        check('pair blank rationing defaults',skuloc_tasks.convert({'spr':'','npr':''},['spr','npr']),{'StockPercentForRat':100,'NormPercentReservation':0})
        for index,alias,bad in [(20,'dnp','101'),(20,'dnp','-101'),(20,'dnp','1.5'),(20,'ulc','-1'),(22,'nn','-1'),(16,'tn','-1'),(27,'sb','101'),(36,'rcp','0'),(36,'gcp','0')]:
            case=next(c for c in cases if c['index']==index); mid=case['master_id']
            keys={k:r for k,r in configs[mid].items() if r[{1:'IsAdd',2:'IsDownload',3:'IsDelete'}[case['action']]]}
            vals={k:str(case['data'][k]) if case['data'].get(k) is not None else float('nan') for k in keys};vals[alias]=bad
            emitted=validate(mid,case['action'],vals)
            check(f'{index} validator rejects {alias}={bad}',bool(emitted['error']),True)
        for module, fn in [('force',force_tasks.convert),('season',lambda r,k:season_tasks.convert(r,k,12)),('phase',lambda r,k:phase_controls_tasks._convert(9,r,k))]:
            try: fn({'sc':'x'},['sc','wc']); raised=False
            except KeyError: raised=True
            check(module+' first-row schema missing later key raises',raised,True)
            try: fn({'unknown':'x'},['unknown']); unknown_failed=False
            except KeyError: unknown_failed=True
            check(module+' unknown alias rejects',unknown_failed,True)
        from mta.mdm.task_reads import omit_nulls
        check('canonical plain FOR JSON PATH NULL omission',omit_nulls({'ed':None,'tn':0,'sc':'5954'}),{'tn':0,'sc':'5954'})

    sources = {}
    for module in list(sys.modules.values()):
        path = getattr(module,'__file__',None)
        if path:
            p=Path(path)
            if p.suffix=='.py' and p.is_relative_to(ROOT) and p.is_file(): sources[str(p.relative_to(ROOT)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
    result=dict(status='PASS' if all(c['pass_'] for c in checks) else 'FAIL',
        runtime={'python':sys.version,'pandas':pd.__version__},
        check_count=len(checks),checks=checks,cases=results,source_hashes=sources,
        roster_sha256=hashlib.sha256(args.roster.read_bytes()).hexdigest(),
        workbook_sha256=hashlib.sha256(args.workbook.read_bytes()).hexdigest(),
        isolation='No database connections/HTTP/browser/handlers/calculation; production functions only',
        qualification='Known fixture mismatch is detected, not waived. Remaining eligibility/downstream proof stays conditional.')
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','check_count','qualification')}))
    for c in checks:
        if not c['pass_']:print(json.dumps(c))
    return 0 if result['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
