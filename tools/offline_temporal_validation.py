"""Finite human-operated offline trial; calculation and comparison stay in their owners."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OWNER = Path('D:/freshvcf-build/daily-3006')
PYTHON = Path('D:/freshvcf-build/venv/Scripts/python.exe')
REGISTRY = ROOT/'baseline/offline-temporal-scenarios-v1.json'


class ComparisonFailure(RuntimeError):
    pass


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, default=str)


def sources():
    files = [p for folder in ('mta','parity','vectorflow') for p in (ROOT/folder).rglob('*.py')]
    files += list((ROOT/'baseline').glob('*.json'))
    files += list((ROOT/'mta/config').glob('*.json'))
    files += [Path(__file__), ROOT/'tools/offline_windows_worker.py', *ROOT.glob('tools/*TemporalValidation*.ps1')]
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}


def owned(execution_id):
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,39}', execution_id):
        raise ValueError('Execution ID must be 3–40 lowercase letters, digits or hyphens')
    return OWNER/'runtime'/('offline-'+execution_id)


def require_package_sources(folder, package):
    current = sources()
    approved = readiness_package(folder, package)
    if approved is not None:
        if current != approved['sources']:
            raise ValueError('Readiness candidate source files differ')
        return os.environ['VF_OFFLINE_READINESS_SHA256']
    if current == package['sources']:
        return None
    transition = load(folder/'runner-transition.json')
    name = 'tools/offline_temporal_validation.py'
    approved_after = transition.get('after')
    recovery_path = folder/'runner-recovery-transition.json'
    if recovery_path.exists():
        recovery = load(recovery_path)
        if (recovery.get('approval') != '01a115f2-5d87-7c73-a163-e1012432582c'
                or recovery.get('prior_transition_sha256') != sha(folder/'runner-transition.json')
                or recovery.get('before') != approved_after
                or recovery.get('package_sha256') != sha(folder/'package.json')):
            raise ValueError('Approved recovery runner transition differs')
        approved_after = recovery.get('after')
    publication_path = folder/'runner-publication-transition.json'
    if publication_path.exists():
        publication = load(publication_path)
        if (publication.get('approval') != 'publication-readiness-restoration-v1'
                or publication.get('prior_transition_sha256') != sha(recovery_path)
                or publication.get('before') != approved_after
                or publication.get('package_sha256') != sha(folder/'package.json')):
            raise ValueError('Approved publication runner transition differs')
        approved_after = publication.get('after')
    reporting_path = folder/'runner-reporting-transition.json'
    if reporting_path.exists():
        reporting = load(reporting_path)
        if (reporting.get('approval') != 'publication-status-output-v1'
                or reporting.get('prior_transition_sha256') != sha(publication_path)
                or reporting.get('before') != approved_after
                or reporting.get('package_sha256') != sha(folder/'package.json')):
            raise ValueError('Approved reporting runner transition differs')
        approved_after = reporting.get('after')
    retry_path = folder/'runner-selection-retry-transition.json'
    if retry_path.exists():
        retry = load(retry_path)
        if (retry.get('approval') != 'publication-selection-receipt-reuse-v1'
                or retry.get('prior_transition_sha256') != sha(reporting_path)
                or retry.get('before') != approved_after
                or retry.get('package_sha256') != sha(folder/'package.json')):
            raise ValueError('Approved selection retry transition differs')
        approved_after = retry.get('after')
    changed = {key for key in current.keys() | package['sources'].keys()
               if current.get(key) != package['sources'].get(key)}
    if (changed != {name} or package['execution_id'] != 'temporal-smoke-001'
            or transition.get('schema') != 'fresh-approved-runner-transition-v1'
            or transition.get('approval') != 'call_YuWeGF0oMf7XIT15hu0ZnYmU'
            or transition.get('execution_id') != package['execution_id']
            or transition.get('package_sha256') != sha(folder/'package.json')
            or transition.get('path') != name
            or transition.get('before') != package['sources'][name]
            or transition.get('before') != '3c3f6d083d72734ccf22d68128fed829f2803fd1128dfb94a7b25b60fc2a7718'
            or approved_after != current[name]
            or sha(folder/'frozen-runner-001.py') != transition['before']):
        raise ValueError('Frozen execution source differs from approved runner transition')
    return sha(folder/'runner-transition.json')


def readiness_package(folder, package):
    from mta.runtime.offline_transition import transition
    value = transition()
    if value is None:
        return None
    if (package['execution_id'] != value['execution_id']
            or sha(folder/'package.json') != value['package_sha256']
            or package['sources'] != value['before_sources']
            or package['image'] != value['before_image']
            or package['databases'] != value['databases']
            or package['input']['sha256'] != value['input_sha256']
            or sha(folder/value['worker_compose']['path']) != value['worker_compose']['sha256']):
        raise ValueError('Readiness original package or worker identity differs')
    expected = load(folder/'worker-compose.json')
    expected['services']['mta']['image'] = value['after_image']
    if load(folder/value['worker_compose']['path']) != expected:
        raise ValueError('Readiness worker must preserve original isolation and resources')
    for index in range(len(value['modern_retained'])):
        retained_modern(folder,index)
    return {**package, 'image':value['after_image'], 'sources':value['after_sources']}


def retained_modern(folder, index):
    from mta.runtime.offline_transition import transition
    value = transition()
    if value and index < len(value['modern_retained']):
        anchor = value['modern_retained'][index]
        path = Path(anchor['execution']['path']).resolve().parent
        if (Path(anchor['execution']['path']).resolve() != path/'execution.json'
                or Path(anchor['sources']['path']).resolve() != path/'source.json'):
            raise ValueError('Retained modern counterpart paths differ')
        for name in ('execution','sources'):
            item = anchor[name]
            if sha(item['path']) != item['sha256']:
                raise ValueError('Retained modern identity changed')
        if load(path/'execution.json')['days'][-1]['day_index'] != index:
            raise ValueError('Retained modern counterpart differs')
        return path
    return latest(folder,'modern-%03d-*'%index,'execution.json',
        passing=lambda r:r['days'][-1]['status']=='COMPUTED_NOT_YET_PARITY')


def require_release(options, kind):
    from mta.runtime.offline_transition import transition
    if transition() and not getattr(options,'release_'+kind,False):
        raise ValueError('Readiness hold: subsequent human release required for '+kind)


def retained_legacy(folder, index):
    from mta.runtime.offline_transition import transition
    value = transition()
    if value and index < len(value['legacy_retained']):
        anchor = value['legacy_retained'][index]
        path = Path(anchor['path'])
        if sha(path) != anchor['sha256']:
            raise ValueError('Retained legacy receipt changed')
        return path.parent
    return latest(folder,'legacy-%03d-*'%index,'receipt.json',passing=lambda r:r.get('status')=='CAPTURED')


def prefix_receipts(folder, through):
    from mta.runtime.offline_transition import transition
    value = transition()
    result = []
    for index in range(through):
        path = latest(folder,'compare-%03d-*'%index,'accepted.json',passing=lambda r:r.get('status')=='PASS')
        if path is None:
            raise ValueError('Accepted prefix has a gap')
        def bound(file):
            return dict(path=str(file.resolve()),sha256=sha(file))
        accepted = bound(path/'accepted.json')
        if value and index < len(value['accepted_prefix']):
            anchor = value['accepted_prefix'][index]
            if accepted != anchor:
                raise ValueError('Original accepted prefix anchor changed')
        item = load(path/'accepted.json')
        if value and index >= len(value['accepted_prefix']):
            from mta.runtime.offline_transition import SHA_ENV
            if item.get('transition_sha256') != os.environ[SHA_ENV]:
                raise ValueError('New accepted receipt lacks matching readiness transition')
        result.append(dict(day_index=index,accepted=accepted,replay=bound(path/'replay.json'),
            rrr=bound(path/'rrr-source.json'),execution=bound(Path(item['modern'])/'execution.json')))
    return result


def protected_baseline(folder):
    original = load(folder/'protected-before.json')
    from mta.runtime.offline_transition import transition
    approved = transition()
    if approved:
        anchor = approved['protected_baseline']
        path = folder/anchor['path']
        if sha(path) != anchor['sha256'] or approved['original_protected_sha256'] != sha(folder/'protected-before.json'):
            raise ValueError('Readiness protected baseline changed')
        current = load(path)
        if any(current.get(name) != row for name,row in original.items()):
            raise ValueError('Readiness baseline changed an originally protected service')
        return current
    path = folder/'approved-recovery-baseline.json'
    if not path.exists():
        return original
    receipt = load(path)
    recovered_path = folder/'external-recovery-snapshot-001.json'
    recovered = load(recovered_path)
    if (receipt.get('approval') != '01a115f2-5d87-7c73-a163-e1012432582c'
            or receipt.get('original_sha256') != sha(folder/'protected-before.json')
            or receipt.get('recovered_sha256') != sha(recovered_path)
            or original.keys() != recovered.keys()
            or any({k:v for k,v in original[n].items() if k != 'started'} !=
                   {k:v for k,v in recovered[n].items() if k != 'started'} for n in original)):
        raise ValueError('Recovery qualification exceeds approved start-time-only boundary')
    return recovered


def container_path(path):
    return '/runtime/'+Path(path).resolve().relative_to((OWNER/'runtime').resolve()).as_posix()


def command(args, log):
    with Path(log).open('x', encoding='utf-8') as stream:
        result = subprocess.run([str(a) for a in args], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        if result.returncode==4:
            raise ComparisonFailure(f'Comparison failed; retained log: {log}')
        raise RuntimeError(f'Command failed ({result.returncode}); retained log: {log}')


def bounded_legacy_command(args,log):
    from tools.offline_windows_worker import run
    with Path(log).open('x',encoding='utf-8') as stream:
        result=run(args,stdout=stream,cwd=ROOT)
    save(Path(log).with_suffix('.resources.json'),result)
    if result['returncode']:
        if result['returncode']==4:
            raise ComparisonFailure(f'Comparison failed; retained log: {log}')
        raise RuntimeError(f"Bounded legacy worker failed ({result['returncode']}); retained log: {log}")


def worker(folder, args, log, *, extra_env=None):
    from mta.runtime.offline_transition import transition, PATH_ENV, SHA_ENV
    approved = transition()
    compose = folder/(approved['worker_compose']['path'] if approved else 'worker-compose.json')
    if approved and sha(compose) != approved['worker_compose']['sha256']:
        raise ValueError('Readiness worker compose changed')
    env = dict(extra_env or {})
    if approved:
        env.update({PATH_ENV:container_path(os.environ[PATH_ENV]),SHA_ENV:os.environ[SHA_ENV]})
    cmd = ['docker','compose','-f',compose,'run','--rm','--no-deps','-T']
    for key,value in env.items():
        cmd += ['-e',key+'='+value]
    command([*cmd,'--entrypoint','python','mta','manage.py',*args], log)


def bind_namespace(execution_id):
    from parity import legacy_isolation as isolation
    suffix = hashlib.sha256(execution_id.encode()).hexdigest()[:16]
    isolation.MAPPING.clear()
    isolation.MAPPING.update({'VFTEST_'+r:'VFTEST_Fresh_Offline_'+suffix+'_'+r for r in isolation.ROLES})
    isolation.DATA = Path('D:/freshvcf-build/sqlserver')/('offline-'+execution_id)
    os.environ['VFTEST_PROFILE']='fresh'
    return isolation


def preflight(options):
    from mta.runtime.offline_scenario import admit
    from parity.temporal_ledger import validate
    pins = load(options.scenario_manifest)
    if Path(options.scenario_manifest).resolve()!=REGISTRY.resolve():
        raise ValueError('Use the registered scenario manifest')
    item = pins['scenarios'][options.scenario]
    artifact = admit(Path(item['path']).read_bytes(),item['sha256'])
    validation = validate(artifact)
    for name,expected in pins['generator_dependencies'].items():
        if sha(ROOT/name)!=expected:
            # The registered artifact was not regenerated. The approved
            # refinement only appended rows_digest to this shared module;
            # all original generator functions remain byte-identical.
            folder=owned(options.execution_id)
            original=load(folder/'package.json') if (folder/'package.json').exists() else None
            effective=readiness_package(folder,original) if original else None
            if (name!='mta/serialization.py' or effective is None
                    or original['sources'].get(name)!=expected
                    or sha(ROOT/name)!=effective['sources'].get(name)):
                raise ValueError('Frozen generator dependency changed: '+name)
    compose = load(OWNER/'compose.json')
    svc = compose['services']['mta']
    if (compose['name']!='freshvcf-daily3006' or svc.get('restart')!='no'
            or svc.get('mem_limit')!='4g' or svc.get('memswap_limit')!='4g'
            or svc.get('cpus')!=2 or svc.get('ports')
            or svc['environment'].get('VF_DB_NAME')!='daily_3006'):
        raise ValueError('Owned worker/resource configuration differs')
    image = json.loads(subprocess.check_output(['docker','image','inspect',options.image]))[0]['Id']
    runtime_pins={k:v for k,v in sources().items() if k.startswith(('mta/','parity/','vectorflow/','baseline/'))}
    check_code=("import json,sys,hashlib; from pathlib import Path; pins=json.load(sys.stdin); "
        "bad=[n for n,h in pins.items() if not Path('/app',n).is_file() or "
        "hashlib.sha256(Path('/app',n).read_bytes()).hexdigest()!=h]; "
        "print(json.dumps(bad)); sys.exit(bool(bad))")
    checked=subprocess.run(['docker','run','--rm','-i','--network','none','--memory','512m','--cpus','1',
        '--entrypoint','python',image,'-c',check_code],input=json.dumps(runtime_pins),capture_output=True,text=True)
    if checked.returncode:
        raise ValueError('Candidate image differs from frozen runtime source: '+checked.stdout[:1500])
    postgres = json.loads(subprocess.check_output(['docker','inspect','freshvcf-daily3006-postgres-1']))[0]
    if postgres['State'].get('Health',{}).get('Status')!='healthy':
        raise ValueError('Owned PostgreSQL is not healthy')
    # A query against master checks actual SQL storage, not merely process presence.
    isolation = bind_namespace(options.execution_id)
    with isolation.exclusive_replay(validate_schema=False), isolation.raw_connection('master') as db:
        if db.execute('SELECT COUNT(*) FROM sys.databases').fetchval()<1:
            raise ValueError('SQL catalogue unavailable')
        existing = [name for name in isolation.MAPPING.values()
                    if db.execute('SELECT DB_ID(?)',name).fetchval()]
        prior = owned(options.execution_id)/'package.json'
        if existing and not prior.exists():
            raise ValueError('SQL namespace already exists without this execution owner')
    free = shutil.disk_usage(OWNER).free
    # Frozen full inputs are 57 MB; reserve 2 GiB per executed day plus 4 GiB workspace.
    required = (item['execution_through']+1)*2*1024**3+4*1024**3
    if free<required:
        raise ValueError(f'Insufficient evidence storage: {free} bytes free; {required} required')
    master=artifact['case']['static_day']['raw_master']
    result = dict(status='PASS',scenario=options.scenario,input=item,image=image,
        population=dict(pairs=len(master),skus=len({r['SKUCode'] for r in master}),locations=len({r['WhCode'] for r in master})),
        requested_dates=[d['business_date'] for d in artifact['case']['days'][:item['execution_through']+1]],
        registry_sha256=sha(REGISTRY),sources=sources(),compose_sha256=sha(OWNER/'compose.json'),
        execution_id=options.execution_id,databases=dict(isolation.MAPPING),
        storage_free_bytes=free,storage_required_bytes=required,ledger=validation)
    folder = owned(options.execution_id)
    if (folder/'package.json').exists():
        original = load(folder/'package.json')
        effective = readiness_package(folder,original) or original
        require_package_sources(folder,original)
        for key in ('scenario','input','image','registry_sha256','compose_sha256','execution_id','databases'):
            if effective[key] != result[key]:
                raise ValueError('Preflight retained package identity differs: '+key)
        result['continuation'] = summary(folder)
        if readiness_package(folder,original):
            count=len(result['continuation']['accepted_dates'])
            if not count:raise ValueError('Readiness requires the retained accepted prefix')
            previous=retained_modern(folder,count-1)
            source=load(folder/'mdm-source.json')
            log=next_attempt(folder,'readiness-prefix-check').with_suffix('.log')
            if count==len(result['requested_dates']):
                args=['verify_offline_terminal','--execution',container_path(previous),
                    '--input',container_path(folder/'input.json'),'--scenario',effective['scenario'],
                    '--owner',options.execution_id]
            else:
                args=['run_temporal',container_path(folder/'input.json'),'--sha256',item['sha256'],
                    '--revision','readiness-check-only','--evidence',container_path(folder/'unused-preflight-target'),
                    '--through',str(count),'--continue-from',container_path(previous),
                    '--automatic-actions','--bounded-one-day','--verify-prefix-only',
                    '--mdm-source',str(source['id']),'--mdm-source-digest',source['digest'],
                    '--bpr-remark-horizon','90']
            worker(folder,args,log)
            result['persisted_prefix_proof']=dict(log=str(log),sha256=sha(log),result=last_json(log))
            from tools.daily_stack_setup import snapshot
            if snapshot()!=protected_baseline(folder):raise ValueError('Readiness protected services changed')
    return result


def initialize(options):
    folder = owned(options.execution_id)
    result = preflight(options)
    if folder.exists():
        if not options.resume:
            raise ValueError('Execution exists: inspect summary and use explicit -Resume')
        original = load(folder/'package.json')
        prior = readiness_package(folder,original) or original
        for key in ('scenario','input','image','registry_sha256','sources','compose_sha256','execution_id','databases'):
            if prior[key]!=result[key]:
                if key == 'sources':
                    require_package_sources(folder, original)
                    continue
                raise ValueError('Resume frozen identity differs: '+key)
        return folder,prior
    if options.resume:
        raise ValueError('Resume owner does not exist')
    folder.mkdir()
    save(folder/'package.json',result)
    from tools.daily_stack_setup import snapshot
    save(folder/'protected-before.json',snapshot())
    compose = deepcopy(load(OWNER/'compose.json'))
    svc = compose['services']['mta']
    svc['image']=result['image']
    env=svc['environment']
    for key in ('VF_MTA_PUBLISHED_RUN','VF_MTA_PUBLISHED_DIGEST','VF_MTA_HIERARCHY_FILE','VF_MTA_HIERARCHY_SHA256','VF_BTR_REPORTING_GENERATION'):
        env.pop(key,None)
    env.update(VF_EVIDENCE_ROOT=container_path(folder/'state'),
        VF_MTA_PERMISSIONS_FILE='',VF_MTA_PERMISSIONS_SHA256='',
        VF_MTA_ALLOW_UNSELECTED_STARTUP='1',VF_MTA_PLANNING_EXTENSION='daily-planning-offline-v1',
        VF_MTA_RRR_COLOUR_EXTENSION='daily-rrr-offline-v1')
    save(folder/'worker-compose.json',compose)  # Private existing credentials remain outside Git.
    shutil.copyfile(result['input']['path'],folder/'input.json')
    return folder,result


def last_json(log):
    for line in reversed(Path(log).read_text(encoding='utf-8').splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            pass
    raise ValueError('Command did not emit its structured receipt: '+str(log))


def modern_day(folder, package, index, previous, mode):
    existing=retained_modern(folder,index)
    if existing:
        if load(existing/'execution.json').get('computation_only',False)!=(mode=='modern-only'):
            raise ValueError('Existing modern verification mode differs')
        return existing
    source_path=folder/'mdm-source.json'
    if not source_path.exists():
        log=next_attempt(folder,'install-source').with_suffix('.log')
        worker(folder,['install_offline_input_source',container_path(folder/'input.json'),
            '--sha256',package['input']['sha256'],'--owner',package['execution_id']],log)
        save(source_path,last_json(log))
    source=load(source_path)
    if source.get('owner')!=package['execution_id'] or source.get('artifact_sha256')!=package['input']['sha256']:
        raise ValueError('Saved MDM source belongs to another execution or artifact')
    target=next_attempt(folder,'modern-%03d'%index)
    args=['run_temporal',container_path(folder/'input.json'),'--sha256',package['input']['sha256'],
        '--revision',package['execution_id']+'-'+target.name,'--evidence',container_path(target),
        '--through',str(index),'--automatic-actions','--bounded-one-day',
        '--mdm-source',str(source['id']),'--mdm-source-digest',source['digest'],'--bpr-remark-horizon','90']
    if previous:
        args+=['--continue-from',container_path(previous)]
    if mode=='modern-only':
        args+=['--computation-only']
    worker(folder,args,target.with_suffix('.log'))
    return target


def legacy_step(options):
    require_release(options,'calculations')
    folder=owned(options.execution_id); package=load(folder/'package.json')
    require_package_sources(folder, package)
    isolation=bind_namespace(options.execution_id)
    from parity.provision_legacy import build
    build()  # New names only; verified schemas are reused, never reset.
    initialize_order_identity(folder,package,isolation)
    from parity.offline_temporal import capture_one
    previous=None
    for index in range(options.day+1):
        prior=retained_legacy(folder,index)
        if prior:
            previous=prior/'receipt.json'
            continue
        if index!=options.day:
            raise ValueError('Legacy predecessor capture is missing')
        with isolation.exclusive_replay():
            capture_one(Path(package['input']['path']),package['input']['sha256'],Path(options.destination),index,previous)


def initialize_order_identity(folder,package,isolation):
    """Represent the supplied used counter in a new empty owned SQL table.

    SQL's virgin identity has last_value NULL even after RESEED. Allocate its
    declared first value in a rolled-back setup transaction; retain no order.
    Never change canonical scripts, a used counter, or a nonempty table.
    """
    artifact=load(package['input']['path'])
    if sha(package['input']['path'])!=package['input']['sha256']:
        raise ValueError('Counter setup input changed')
    opening=artifact['case']['opening']['orders']
    expected=opening['OrderIdentity']
    if expected!=[dict(Seed=1,Increment=1,LastValue=1)] or opening['SpikeOrderData']:
        raise ValueError('Counter setup is restricted to the registered empty used-counter opening')
    receipt_path=folder/'sql-opening-identity.json'
    table='dbo.SpikeOrderData'
    query=("SELECT CONVERT(bigint,seed_value),CONVERT(bigint,increment_value),CONVERT(bigint,last_value) "
           "FROM sys.identity_columns WHERE object_id=OBJECT_ID('dbo.SpikeOrderData')")
    with isolation.exclusive_replay(),isolation.connection('VFTEST_BPR') as db:
        before=list(db.execute(query).fetchone())
        count=db.execute('SELECT count(*) FROM dbo.SpikeOrderData').fetchval()
        if before[:2]!=[1,1] or count!=0:
            raise ValueError('New owned counter schema/population differs')
        if receipt_path.exists():
            prior=load(receipt_path)
            if (prior['artifact_sha256']!=package['input']['sha256']
                    or prior['database']!=isolation.MAPPING['VFTEST_BPR']
                    or prior['expected']!=expected or before[2] is None):
                raise ValueError('Retained SQL counter setup identity differs')
            return
        if before[2] is not None:
            raise ValueError('Used counter lacks this execution setup receipt; refuse adoption')
        master=artifact['case']['static_day']['raw_master'][0]
        db.execute('BEGIN TRANSACTION')
        try:
            allocated=db.execute('INSERT INTO dbo.SpikeOrderData '
                '(CustomerOrderId,PartId,IsSpike,IsElephant,OriginalQty,Qty,SKUCode,WhCode,IntroDate) '
                'OUTPUT inserted.OrderKey VALUES (?,1,0,0,0,0,?,?,?)',
                'VFTEST-COUNTER-SETUP-ROLLED-BACK',master['SKUCode'],master['WhCode'],
                artifact['case']['opening_date']).fetchval()
            if allocated!=1:
                raise ValueError('Fresh declared counter allocation differs')
        finally:
            db.execute('IF @@TRANCOUNT>0 ROLLBACK TRANSACTION')
        after=list(db.execute(query).fetchone())
        remaining=db.execute('SELECT count(*) FROM dbo.SpikeOrderData').fetchval()
        if after!=[1,1,1] or remaining!=0:
            raise ValueError('Rolled-back counter setup did not reproduce declared opening')
    save(receipt_path,dict(artifact_sha256=package['input']['sha256'],
        database=isolation.MAPPING['VFTEST_BPR'],table=table,expected=expected,
        before=before,after=after,retained_order_rows=remaining,
        scope='Physical used-counter initialization only; rolled-back row never enters an engine input'))


def compare_step(options):
    folder=owned(options.execution_id); package=load(folder/'package.json')
    require_package_sources(folder, package)
    isolation=bind_namespace(options.execution_id)
    from parity.offline_temporal import compare_retained
    modern=Path(options.modern); legacy=Path(options.legacy)
    target=Path(options.destination)
    day = load(modern/'execution.json')['days'][-1]
    if (modern.resolve() != retained_modern(folder,day['day_index']).resolve()
            or legacy.resolve() != (retained_legacy(folder,day['day_index'])/'receipt.json').resolve()):
        raise ValueError('Comparison counterpart differs from retained target')
    compare_retained(Path(package['input']['path']),package['input']['sha256'],modern,legacy,target,
                    accepted_prefix=prefix_receipts(folder,day['day_index']))
    replay=load(target/'replay.json')
    if replay['status'] not in ('PASS','COMPLETE_WITH_LEGACY_FLAWS'):
        raise ComparisonFailure('Independent temporal comparison failed')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    os.environ.setdefault('VF_SECRET_KEY','offline-proof-no-serving')
    import django
    django.setup()
    from parity.verify_daily_rrr_colour import verify
    day=load(modern/'execution.json')['days'][-1]
    with isolation.exclusive_replay():
        proof=verify(modern/day['output_archive'],day['output_digest'],validation_digest=day.get('validation_digest'),offline_context=dict(
            artifact_sha256=package['input']['sha256'],scenario_sha256=load(REGISTRY)['scenario_sha256']))
    save(target/'rrr-source.json',proof)
    if proof['status']!='PASS':
        raise ComparisonFailure('Independent RRR daily source comparison failed')


def execute(options):
    require_release(options,'calculations')
    started=time.monotonic()
    folder,package=initialize(options)
    with execution_lock(folder):
        failure=None
        try:
            return execute_locked(options,folder,package)
        except Exception as error:
            failure=dict(type=type(error).__name__,message=str(error))
            raise
        finally:
            from tools.daily_stack_setup import snapshot
            result=summary(folder)
            result['failure']=failure
            result['elapsed_invocation_seconds']=round(time.monotonic()-started,3)
            result['protected_services_unchanged']=snapshot()==protected_baseline(folder)
            target=next_attempt(folder,'summary')
            save(target.with_suffix('.json'),result)
            with target.with_suffix('.md').open('x',encoding='utf-8') as stream:
                stream.write('# Offline temporal validation\n\n'+
                    f"Execution: {package['execution_id']}\n\n"+
                    f"Scenario: {package['scenario']}; required days: {result['required_days']}\n\n"+
                    f"Failure: {failure or 'none'}\n\n"+
                    f"Protected services unchanged: {result['protected_services_unchanged']}\n\n"+
                    f"Population: {result['population']}\n\n"+
                    f"Requested dates: {result['requested_dates']}; accepted dates: {result['accepted_dates']}\n\n"+
                    f"Publication: {result['publication']}\n\n"+
                    f"Exceptions and deferred reports: {result['dispositions']}\n\n"+
                    f"Next safe command: `{result['next_safe_command']}`\n\n"+
                    'Calculation, comparison and serving selection remain separate.\n\n'+
                    '| Attempt | Day | Calculation |\n|---|---:|---|\n'+
                    ''.join(f"| {r['attempt']} | {r['day_index']+1} | {r['calculation']} |\n" for r in result['attempts']))
            print('Summary: '+str(target.with_suffix('.json')),flush=True)


@contextmanager
def execution_lock(folder):
    import msvcrt
    with (folder/'execution.lock').open('a+b') as stream:
        if stream.tell()==0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError as error:
            raise ValueError('This execution already has an active runner') from error
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)


def execute_locked(options,folder,package):
    require_release(options,'calculations')
    mode_path=folder/'mode.json'
    if mode_path.exists():
        if load(mode_path)['mode']!=options.mode:
            # Independent captures may subsequently be compared; never change how they ran.
            if options.mode!='compare-retained' and {load(mode_path)['mode'],options.mode}!={'modern-only','legacy-only'}:
                raise ValueError('Execution mode differs; use compare-retained for independent captures')
    else:
        save(mode_path,dict(mode=options.mode))
    previous=None
    for index in range(package['input']['execution_through']+1):
        modern=retained_modern(folder,index)
        if options.mode in ('combined','modern-only'):
            modern=modern_day(folder,package,index,previous,options.mode)
        legacy=retained_legacy(folder,index)
        if options.mode in ('combined','legacy-only') and legacy is None:
            legacy=next_attempt(folder,'legacy-%03d'%index)
            bounded_legacy_command([PYTHON,__file__,'legacy-step','--execution-id',options.execution_id,
                '--day',str(index),'--destination',legacy,'--release-calculations'],legacy.with_suffix('.log'))
        if options.mode in ('combined','compare-retained'):
            if modern is None or legacy is None:
                raise ValueError('Both independently retained captures are required')
            accepted=latest(folder,'compare-%03d-*'%index,'accepted.json',passing=lambda r:r.get('status')=='PASS')
            if accepted is not None:
                from parity.accepted_prefix import verify_prefix
                from parity.offline_temporal import _capture_lineage
                verify_prefix(prefix_receipts(folder,index+1),load(modern/'execution.json'),
                    _capture_lineage(legacy/'receipt.json',sha(legacy/'receipt.json')),require_next=False)
                saved=load(accepted/'accepted.json')
                if (saved['replay_sha256']!=sha(accepted/'replay.json')
                        or saved['rrr_sha256']!=sha(accepted/'rrr-source.json')
                        or saved['modern']!=str(modern) or saved['legacy']!=str(legacy)):
                    raise ValueError('Accepted comparison files or counterpart identity changed')
            if accepted is None:
                target=next_attempt(folder,'compare-%03d'%index)
                bounded_legacy_command([PYTHON,__file__,'compare-step','--execution-id',options.execution_id,
                    '--modern',modern,'--legacy',legacy/'receipt.json','--destination',target],target.with_suffix('.log'))
                worker(folder,['record_parity','--replay',container_path(target/'replay.json'),
                    '--modern-execution',container_path(modern/'execution.json'),'--preserve-existing',
                    '--daily-source-proof',container_path(target/'rrr-source.json')],target/'accept.log')
                accept_comparison(target,modern,legacy)
        previous=modern
        print(json.dumps(dict(day=index+1,mode=options.mode,status='COMPLETE')),flush=True)
    if options.mode in ('combined','compare-retained'):
        worker(folder,['verify_offline_terminal','--execution',container_path(previous),
            '--input',container_path(folder/'input.json'),'--scenario',package['scenario'],'--owner',package['execution_id']],
            next_attempt(folder,'complete-prefix').with_suffix('.log'))
    from tools.daily_stack_setup import snapshot
    if snapshot()!=protected_baseline(folder):
        raise ValueError('Protected service snapshot changed')
    print(json.dumps(summary(folder),indent=2))


def accept_comparison(target,modern,legacy):
    from mta.runtime.offline_transition import transition,SHA_ENV
    value=dict(status='PASS',modern=str(modern),legacy=str(legacy),
        replay_sha256=sha(target/'replay.json'),rrr_sha256=sha(target/'rrr-source.json'))
    if transition():value['transition_sha256']=os.environ[SHA_ENV]
    save(target/'accepted.json',value)


def compare_next(options):
    """Exactly one already-calculated counterpart; never starts either engine."""
    from mta.runtime.offline_transition import transition
    value=transition()
    if value is None:raise ValueError('Comparison-only readiness requires a pinned transition')
    folder=owned(options.execution_id)
    with execution_lock(folder):
        package=load(folder/'package.json');require_package_sources(folder,package)
        index=len(value['accepted_prefix'])
        state=summary(folder)
        if len(state['accepted_dates'])!=index:
            raise ValueError('Comparison-only target is not the anchored next unaccepted day')
        if index>=len(value['modern_retained']) or index>=len(value['legacy_retained']):
            raise ValueError('Comparison-only target has no pinned retained counterparts')
        modern=retained_modern(folder,index);legacy=retained_legacy(folder,index)
        target=next_attempt(folder,'compare-%03d'%index)
        bounded_legacy_command([PYTHON,__file__,'compare-step','--execution-id',options.execution_id,
            '--modern',modern,'--legacy',legacy/'receipt.json','--destination',target],target.with_suffix('.log'))
        worker(folder,['record_parity','--replay',container_path(target/'replay.json'),
            '--modern-execution',container_path(modern/'execution.json'),'--preserve-existing',
            '--daily-source-proof',container_path(target/'rrr-source.json')],target/'accept.log')
        accept_comparison(target,modern,legacy)
        from tools.daily_stack_setup import snapshot
        if snapshot()!=protected_baseline(folder):raise ValueError('Protected service snapshot changed')
        print(json.dumps(summary(folder),indent=2))


def readiness(log):
    code="""import json,time,urllib.request,urllib.error
deadline=time.monotonic()+180
while True:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/readyz',timeout=10) as response:
            result=json.load(response)
        if result.get('ready') is True:
            print(json.dumps(result)); break
    except (urllib.error.URLError,TimeoutError) as error:
        print('Readiness pending: '+str(error),flush=True)
    if time.monotonic()>=deadline:
        raise RuntimeError('Selected application did not become ready within 180 seconds')
    time.sleep(2)
"""
    command(['docker','compose','-f',OWNER/'compose.json','exec','-T','mta','python','-c',code],log)
    if last_json(log).get('ready') is not True:
        raise ValueError('Selected application is not ready')


def replace_owned_config(value):
    target=OWNER/'compose.json'
    temporary=OWNER/'compose-offline-pending.json'
    with temporary.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)
    os.replace(temporary,target)


def retain_selection(path, value):
    if path.exists():
        if load(path) != value:
            raise ValueError('Existing selection receipt differs; preserve and reconcile')
    else:
        save(path,value)


def prepare_terminal(folder, args):
    """One ordinary retry only for the known RRR prerequisite ordering failure."""
    log = next_attempt(folder,'prepare').with_suffix('.log')
    try:
        worker(folder,['prepare_daily_ui',*args],log)
    except RuntimeError:
        before = last_json(log)
        failed = {k for k,v in before.get('layers',{}).items() if v.get('status')!='READY'}
        allowed = {'planning_expedite_transit','planning_expedite_charts'}
        if (before.get('status')!='INCOMPLETE' or not failed or not failed <= allowed
                or before['layers'].get('rrr',{}).get('status')!='READY'
                or any(before['layers'][k].get('error_type')!='DoesNotExist'
                       or before['layers'][k].get('error')!='RrrPreparedProjection matching query does not exist.'
                       for k in failed)):
            raise
        retry = next_attempt(folder,'prepare').with_suffix('.log')
        worker(folder,['prepare_daily_ui',*args],retry)
        after = last_json(retry)
        if (after.get('status')!='READY' or any(after['layers'].get(k)!=v
                for k,v in before['layers'].items() if v['status']=='READY')):
            raise ValueError('Terminal preparation retry changed successful layers')
        return after
    result = last_json(log)
    if result.get('status')!='READY':raise ValueError('Terminal preparation is incomplete')
    return result


def publish(options):
    if not options.restore:require_release(options,'publication')
    folder=owned(options.execution_id); package=load(folder/'package.json')
    require_package_sources(folder, package)
    package = readiness_package(folder,package) or package
    if options.restore:
        selected=load(folder/'selection.json')
        if sha(OWNER/'compose.json')!=selected['selected_compose_sha256']:
            raise ValueError('Serving config changed after trial; refuse to overwrite it')
        replace_owned_config(load(folder/'previous-compose.json'))
        log=next_attempt(folder,'restore').with_suffix('.log')
        command(['docker','compose','-f',OWNER/'compose.json','up','-d','--no-deps','mta'],log)
        readiness(next_attempt(folder,'restored-ready').with_suffix('.log'))
        save(next_attempt(folder,'restoration').with_suffix('.json'),dict(
            status='RESTORED',selection_sha256=sha(folder/'selection.json'),
            restored_compose_sha256=sha(OWNER/'compose.json')))
        return
    if sha(OWNER/'compose.json')!=package['compose_sha256']:
        raise ValueError('Prior serving tuple changed; explicit reconciliation required')
    terminal_index=package['input']['execution_through']
    modern=latest(folder,'modern-%03d-*'%terminal_index,'execution.json',
        passing=lambda r:r['days'][-1]['status']=='COMPUTED_NOT_YET_PARITY')
    if modern is None:
        raise ValueError('Terminal modern capture is missing')
    prooflog=next_attempt(folder,'terminal-proof').with_suffix('.log')
    worker(folder,['verify_offline_terminal','--execution',container_path(modern),
        '--input',container_path(folder/'input.json'),'--scenario',package['scenario'],'--owner',package['execution_id']],prooflog)
    terminal=last_json(prooflog)
    args=['--run-id',terminal['run_id'],'--output-digest',terminal['output_digest']]
    prepared=prepare_terminal(folder,args)
    original=load(OWNER/'compose.json')
    oldenv=original['services']['mta']['environment']
    hierarchy=load(OWNER/'inputs'/Path(oldenv['VF_MTA_HIERARCHY_FILE']).name)
    hierarchy['publications']=[{k:terminal[k] for k in ('run_id','business_date','output_digest')}]
    hierarchy['authorization']='Approved offline 21-day package; exact retained catalogue and six read-time hierarchy fields only.'
    hierarchy_path=folder/'terminal-hierarchy.json'
    if hierarchy_path.exists():
        if load(hierarchy_path)!=hierarchy:
            raise ValueError('Terminal hierarchy retry identity differs')
    else:
        save(hierarchy_path,hierarchy)
    access={key:oldenv[key] for key in ('VF_MTA_PERMISSIONS_FILE','VF_MTA_PERMISSIONS_SHA256')}
    access.update(VF_MTA_HIERARCHY_FILE=container_path(hierarchy_path),VF_MTA_HIERARCHY_SHA256=sha(hierarchy_path))
    worker(folder,['activate_daily_ui',*args,'--publication-seal',prepared['seal_digest']],
        next_attempt(folder,'activate').with_suffix('.log'),extra_env=access)
    worker(folder,['activate_offline_readers',*args,'--publication-seal',prepared['seal_digest']],
        next_attempt(folder,'readers').with_suffix('.log'),extra_env=access)
    selectionlog=next_attempt(folder,'selection-check').with_suffix('.log')
    worker(folder,['check_daily_selection',*args],selectionlog,extra_env=access)
    selection=last_json(selectionlog)
    candidate=deepcopy(original)
    candidate['services']['mta']['image']=package['image']
    env=candidate['services']['mta']['environment']
    from mta.runtime.offline_transition import transition
    approved = transition()
    env.update(load(folder/(approved['worker_compose']['path'] if approved else 'worker-compose.json'))['services']['mta']['environment'])
    env.update(access)
    env.update({key:value for key,value in selection.items() if key.startswith('VF_')})
    if not (folder/'previous-compose.json').exists():
        save(folder/'previous-compose.json',original)
    selection_receipt=dict(**terminal,publication_seal=prepared['seal_digest'],
        selected_compose_sha256=hashlib.sha256(json.dumps(candidate,indent=2).replace('\n',os.linesep).encode('utf-8')).hexdigest(),
        previous_compose_sha256=package['compose_sha256'])
    if (folder/'selection.json').exists() and load(folder/'selection.json')!=selection_receipt:
        raise ValueError('Existing selection receipt differs; refuse serving change')
    replace_owned_config(candidate)
    try:
        command(['docker','compose','-f',OWNER/'compose.json','up','-d','--no-deps','mta'],
            next_attempt(folder,'select').with_suffix('.log'))
        readiness(next_attempt(folder,'selected-ready').with_suffix('.log'))
    except Exception:
        replace_owned_config(original)
        command(['docker','compose','-f',OWNER/'compose.json','up','-d','--no-deps','mta'],
            next_attempt(folder,'failure-restore').with_suffix('.log'))
        readiness(next_attempt(folder,'failure-restored-ready').with_suffix('.log'))
        raise
    if sha(OWNER/'compose.json')!=selection_receipt['selected_compose_sha256']:
        raise ValueError('Selected configuration changed before recording selection')
    retain_selection(folder/'selection.json',selection_receipt)
    from tools.daily_stack_setup import snapshot
    if snapshot()!=protected_baseline(folder):
        raise ValueError('Protected services changed during terminal selection')
    print(json.dumps({**terminal, 'status':'SELECTED'}))


def next_attempt(folder, stem):
    for index in range(1,10000):
        value=folder/(stem+'-a%03d'%index)
        if not value.exists() and not any(value.with_suffix(suffix).exists() for suffix in ('.log','.json','.md')):
            return value
    raise ValueError('Attempt limit reached')


def latest(folder, pattern, receipt, *, passing):
    result=None
    for path in sorted(folder.glob(pattern)):
        candidate=path/receipt
        if candidate.exists() and passing(load(candidate)):
            result=path
    return result


def summary(folder):
    package=load(folder/'package.json')
    rows=[]
    for path in sorted(folder.glob('modern-*/execution.json')):
        record=load(path); day=record['days'][-1]
        rows.append(dict(attempt=path.parent.name,day_index=day['day_index'],date=day['date'],
            calculation=day['status'],run_id=day.get('run_id'),error=day.get('error')))
    accepted=[]
    for index in range(package['input']['execution_through']+1):
        value=latest(folder,'compare-%03d-*'%index,'accepted.json',passing=lambda r:r.get('status')=='PASS')
        if value is None:
            break
        proof=load(value/'accepted.json')
        if proof['replay_sha256']!=sha(value/'replay.json') or proof['rrr_sha256']!=sha(value/'rrr-source.json'):
            raise ValueError('Accepted summary proof changed')
        accepted.append(package['requested_dates'][index])
    captures=[dict(path=str(p),status=load(p)['status'],error=load(p).get('error'))
              for p in sorted(folder.glob('legacy-*/receipt.json'))]
    mode=load(folder/'mode.json')['mode'] if (folder/'mode.json').exists() else 'combined'
    from mta.runtime.offline_transition import transition, PATH_ENV, SHA_ENV
    approved=transition()
    suffix=(f" -Image {approved['after_image']} -TransitionFile {os.environ[PATH_ENV]} -TransitionSha256 {os.environ[SHA_ENV]}"
            if approved else '')
    if accepted:
        from parity.accepted_prefix import verify_prefix
        from parity.offline_temporal import _capture_lineage
        descriptors=prefix_receipts(folder,len(accepted))
        capture=retained_legacy(folder,len(accepted)-1)/'receipt.json'
        bind_namespace(package['execution_id'])
        verify_prefix(descriptors,load(descriptors[-1]['execution']['path']),
            _capture_lineage(capture,sha(capture)),require_next=False)
    later=[i for i in range(len(accepted),package['input']['execution_through']+1)
           if latest(folder,'compare-%03d-*'%i,'accepted.json',passing=lambda r:r.get('status')=='PASS')]
    if later:raise ValueError('Accepted summary has a gap')
    return dict(execution_id=package['execution_id'],scenario=package['scenario'],
        runner_transition_sha256=sha(folder/'runner-transition.json') if (folder/'runner-transition.json').exists() else None,
        population=package['population'],requested_dates=package['requested_dates'],accepted_dates=accepted,
        legacy_captures=captures,
        action_coverage=[dict(path=str(p),days=[dict(day=d['day_index'],**d.get('action_coverage',{}))
            for d in load(p)['days']]) for p in sorted(folder.glob('modern-*/execution.json'))],
        dispositions=['RRR MTO=0 synthetic gate exception; formula proof separate',
            'BOR/BOROA and Guided Excess rolling history deferred',
            'Retained GIT SQL207 and native ordering limitations remain; no new exclusions'],
        publication=publication_state(folder),
        next_safe_command=(f"./tools/Test-TemporalValidationPreflight.ps1 -ExecutionId {package['execution_id']} -Scenario {package['scenario']}"+suffix if approved else
            f"./tools/Invoke-TemporalValidation.ps1 -ExecutionId {package['execution_id']} -Scenario {package['scenario']} -Mode {mode} -Resume"+suffix),
        after_human_release_command=f"./tools/Invoke-TemporalValidation.ps1 -ExecutionId {package['execution_id']} -Scenario {package['scenario']} -Mode {mode} -Resume -ReleaseCalculations"+suffix,
        next_day_index=len(accepted) if len(accepted)<len(package['requested_dates']) else None,
        calculated_only_dates=sorted({r['date'] for r in rows if r['calculation']=='COMPUTED_NOT_YET_PARITY'}-set(accepted)),
        execution_hold='Requires subsequent direct human release; preflight does not release calculation or publication',
        required_days=package['input']['execution_through']+1,attempts=rows,
        comparisons=[dict(path=str(p),status=load(p)['status']) for p in sorted(folder.glob('compare-*/replay.json'))],
        selection='No selection implied; terminal publication is a separate command')


def publication_state(folder):
    selection=folder/'selection.json'
    if not selection.exists():
        return 'unselected; terminal command required'
    current=sha(OWNER/'compose.json')
    selected=load(selection)
    if current==selected['selected_compose_sha256']:
        return 'selected terminal'
    for path in folder.glob('restoration-a*.json'):
        receipt=load(path)
        if (receipt.get('status')=='RESTORED' and receipt.get('selection_sha256')==sha(selection)
                and receipt.get('restored_compose_sha256')==current
                and current==selected['previous_compose_sha256']):
            return 'trial verified; previous selection restored'
    return 'selection differs; reconciliation required'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['preflight','run','summary','legacy-step','compare-step','compare-next','publish'])
    parser.add_argument('--scenario-manifest',type=Path,default=REGISTRY)
    parser.add_argument('--scenario',choices=['trial','full'],default='trial')
    parser.add_argument('--execution-id',required=True)
    parser.add_argument('--image',default='freshvcf-daily3006-mta:offline-temporal-003')
    parser.add_argument('--mode',choices=['combined','modern-only','legacy-only','compare-retained'],default='combined')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--day',type=int)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--modern',type=Path)
    parser.add_argument('--legacy',type=Path)
    parser.add_argument('--restore',action='store_true')
    parser.add_argument('--release-calculations',action='store_true')
    parser.add_argument('--release-publication',action='store_true')
    parser.add_argument('--transition-file',type=Path)
    parser.add_argument('--transition-sha256')
    options=parser.parse_args()
    if bool(options.transition_file)!=bool(options.transition_sha256):
        raise ValueError('Transition file and trusted SHA256 must be supplied together')
    if options.transition_file:
        from mta.runtime.offline_transition import PATH_ENV,SHA_ENV,transition
        os.environ[PATH_ENV]=str(options.transition_file.resolve())
        os.environ[SHA_ENV]=options.transition_sha256
        transition()
    if options.operation=='preflight':
        result=preflight(options)
        folder=owned(options.execution_id)
        if folder.exists():save(next_attempt(folder,'preflight').with_suffix('.json'),result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('sources','databases','ledger')},indent=2))
    elif options.operation=='summary':
        print(json.dumps(summary(owned(options.execution_id)),indent=2))
    elif options.operation=='legacy-step':
        legacy_step(options)
    elif options.operation=='compare-step':
        compare_step(options)
    elif options.operation=='compare-next':
        compare_next(options)
    elif options.operation=='publish':
        with execution_lock(owned(options.execution_id)):
            publish(options)
    else:
        execute(options)


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        target=Path('D:/freshvcf-build/evidence/offline-runner-failures')
        target.mkdir(exist_ok=True)
        stamp=str(time.time_ns())
        record=dict(status='FAILED',error_type=type(error).__name__,error=str(error),
            operation=sys.argv[1] if len(sys.argv)>1 else None,
            next_safe_action='Inspect the retained error/log, restore matching pins or resolve the failure, then explicitly resume. No failed check authorizes recomputation or selection.')
        save(target/(stamp+'.json'),record)
        (target/(stamp+'.md')).write_text('# Offline invocation failed\n\n'+str(error)+'\n\n'+record['next_safe_action'],encoding='utf-8')
        print(json.dumps(record),file=sys.stderr)
        raise SystemExit(4 if isinstance(error,ComparisonFailure) else 2 if isinstance(error,ValueError) else 3)
