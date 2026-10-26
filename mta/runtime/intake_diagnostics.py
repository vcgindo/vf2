"""Capture actual pre-success failure facts independently of successful days."""
from contextlib import contextmanager
from datetime import datetime
from importlib import import_module
import inspect
import uuid

from django.db import connection,transaction
from mta.serialization import digest,storage
from mta.application.intake_errors import NativeIntakeRejected
from mta.domain.complete_daily_scalars import parse_datetime
from mta.runtime import intake_diagnostic_models as models

SCHEMA='fresh-intake-diagnostic-v1'
STAGES=('ValidateAndProcessMaster','SupplierValidation','DailyValidation')
ROWS={
    'rejections':(models.IntakeRejection,('SKUCode','WhCode','RejectionDate','ReasonCode','ReasonDescription')),
    'aborts':(models.IntakeAbortReason,('FileId','RunDateTime','Reason','inherited')),
    'observations':(models.IntakeFileObservation,('Id','Path','FileName','Type','initial_exists',
        'initial_resolved_path','initial_resolved_name','Exists','ResolvedPath','ResolvedFileName','member','sha256','size_bytes')),
    'settings':(models.IntakeFullkitSetting,('Parameter','initial_value','final_value')),
}
COUNTS=dict(rejections='rejection_count',aborts='abort_count',observations='observation_count',settings='setting_count')
HEADER=('kind','stage','business_date','clock','input_digest','source_digest','configuration_digest','recipe_digest','metadata')
LINKS=('initialization_id','run_id','scope_attempt_id','feed_attempt_id')


class FullkitUnavailable(ValueError):
    def __init__(self,diagnostic_id):
        self.diagnostic_id=diagnostic_id
        super().__init__('Daily files unavailable; original diagnostic '+str(diagnostic_id))


def fullkit_request(value,*,initialization,business_date,source,input_root):
    """Explicit versioned request; default CSV intake has no inferred policy."""
    from mta.application.production_csv_files import contained
    from mta.application import literal_fullkit
    if (not isinstance(value,dict) or set(value)!={'schema','initialization_id','source_digest',
            'business_date','clock','configuration'} or value['schema']!='fresh-literal-fullkit-request-v1'
            or value['initialization_id']!=str(initialization.pk)
            or value['source_digest']!=initialization.source.digest or value['business_date']!=business_date):
        raise ValueError('Exact initialized fullkit request required')
    config=value['configuration']
    if not isinstance(config,dict) or config.get('input_root')!=str(contained(source,input_root)):
        raise ValueError('Fullkit files must belong to the original intake directory')
    canonical=literal_fullkit.configuration(critical_files=config['CriticalFiles'],settings=config['ImporterSettingsTbl'],
        abort_opening=config['RunAbortReasons'],input_root=config['input_root'],site_root=config['site_root'])
    if canonical!=config or parse_datetime(value['clock']).date().isoformat()!=business_date:
        raise ValueError('Fullkit explicit configuration or clock differs')
    return config,value['clock']


def recipe_digest():
    from mta.application import literal_fullkit,operational_alert_files
    from mta.temporal import entry_preparation
    return digest(dict(schema=SCHEMA,modules={name:inspect.getsource(module) for name,module in (
        ('custody',inspect.getmodule(recipe_digest)),('models',models),('fullkit',literal_fullkit),
        ('native_entry',entry_preparation),('report',operational_alert_files))}))


def verify_guards(cursor):
    guards=import_module('mta.runtime.migrations.0237_intake_diagnostic_guards')
    cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname FROM pg_proc P "
        "JOIN pg_namespace N ON N.oid=P.pronamespace JOIN pg_language L ON L.oid=P.prolang "
        "WHERE N.nspname='mta' AND P.pronargs=0 AND P.proname IN "
        "('guard_intake_diagnostic','check_intake_diagnostic_complete') ORDER BY P.proname")
    if cursor.fetchall()!=[
        ('check_intake_diagnostic_complete',guards.COMPLETE,False,['search_path=pg_catalog, mta'],'plpgsql'),
        ('guard_intake_diagnostic',guards.GUARD,False,['search_path=pg_catalog, mta'],'plpgsql')]:
        raise ValueError('Exact diagnostic guard functions required')
    cursor.execute("SELECT C.relname,T.tgname,T.tgtype,T.tgenabled,T.tgdeferrable,T.tginitdeferred,"
        "P.proname,T.tgnargs,T.tgqual::text FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid "
        "JOIN pg_namespace N ON N.oid=C.relnamespace JOIN pg_proc P ON P.oid=T.tgfoid "
        "JOIN pg_namespace F ON F.oid=P.pronamespace WHERE N.nspname='mta' AND F.nspname='mta' "
        "AND C.relname=ANY(%s) AND T.tgname LIKE 'intake_diagnostic_%%' ORDER BY C.relname,T.tgname",
        [list(guards.TABLES)])
    expected=[(table,name,kind,'O',False,False,'guard_intake_diagnostic',0,None)
        for table in guards.TABLES for name,kind in (('intake_diagnostic_immutable',31),('intake_diagnostic_no_truncate',34))]
    expected.append((guards.TABLES[0],'intake_diagnostic_complete',5,'O',True,True,
        'check_intake_diagnostic_complete',0,None))
    if cursor.fetchall()!=sorted(expected):raise ValueError('Diagnostic trigger coverage differs')


@contextmanager
def setting(name,value):
    if name not in ('fresh.intake_diagnostic','fresh.diagnostic_publication') or not connection.in_atomic_block:
        raise ValueError('Diagnostic setting requires its atomic owner')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_setting(%s,true)',[name]);previous=cursor.fetchone()[0] or ''
        cursor.execute('SELECT set_config(%s,%s,true)',[name,str(value)])
    try:yield
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:cursor.execute('SELECT set_config(%s,%s,true)',[name,previous])


def _text(value,width,*,nullable=False):
    if value is None and nullable:return value
    if type(value) is not str or len(value.encode('utf-16-le'))//2>width:
        raise ValueError('Native rejection text type/width differs')
    return value


def rejection_rows(error):
    if not isinstance(error,NativeIntakeRejected) or error.stage not in STAGES:
        raise ValueError('Actual qualified native importer rejection required')
    result=[]
    for ordinal,source in enumerate(error.rejections):
        if set(source)!=set(ROWS['rejections'][1]):raise ValueError('Native rejection columns differ')
        reason=source['ReasonCode']
        if type(reason) is not int or not -(2**31)<=reason<2**31:raise ValueError('Native rejection SQL int required')
        result.append(dict(ordinal=ordinal,SKUCode=_text(source['SKUCode'],50),WhCode=_text(source['WhCode'],50),
            RejectionDate=parse_datetime(source['RejectionDate']),ReasonCode=reason,
            ReasonDescription=_text(source['ReasonDescription'],100,nullable=True)))
    return result


def fullkit_rows(config,result):
    """Lossless typed encoding of the actual literal check result."""
    from mta.application.literal_fullkit import POLICY
    if result['policy']!=POLICY or result['AbortRun'] is not True:
        raise ValueError('Actual literal fullkit abort required')
    initial=config['CriticalFiles'];final=result['CriticalFiles'];observed=result['observations']
    if len(initial)!=len(final) or len(initial)!=len(observed):raise ValueError('Fullkit observation roster differs')
    observations=[]
    for ordinal,(old,new,item) in enumerate(zip(initial,final,observed)):
        if (item['ordinal']!=ordinal or item['file_id']!=old['Id'] or old['Id']!=new['Id']
                or any(old[key]!=new[key] for key in ('Path','FileName','Type')) or new['Exists']!=item['exists']):
            raise ValueError('Fullkit observation ownership/order differs')
        observations.append(dict(ordinal=ordinal,**{key:old[key] for key in ('Id','Path','FileName','Type')},
            initial_exists=old['Exists'],initial_resolved_path=old['ResolvedPath'],initial_resolved_name=old['ResolvedFileName'],
            **{key:new[key] for key in ('Exists','ResolvedPath','ResolvedFileName')},
            **{key:item[key] for key in ('member','sha256','size_bytes')}))
    before=config['ImporterSettingsTbl'];after=result['ImporterSettingsTbl']
    if len(before)!=len(after) or any(old['Parameter']!=new['Parameter'] for old,new in zip(before,after)):
        raise ValueError('Fullkit setting roster differs')
    settings=[dict(ordinal=i,Parameter=old['Parameter'],initial_value=old['Value'],final_value=new['Value'])
        for i,(old,new) in enumerate(zip(before,after))]
    opening=config['RunAbortReasons'];reasons=result['RunAbortReasons']
    if reasons[:len(opening)]!=opening:raise ValueError('Fullkit abort history changed')
    aborts=[dict(ordinal=i,FileId=row['FileId'],RunDateTime=parse_datetime(row['RunDateTime']),Reason=row['Reason'],
        inherited=i<len(opening)) for i,row in enumerate(reasons)]
    return dict(rejections=[],aborts=aborts,observations=observations,settings=settings)


def _value(owner,rows):
    return dict(schema=SCHEMA,id=str(owner.pk),**{name:getattr(owner,name) for name in HEADER},
        **{name:str(getattr(owner,name)) if getattr(owner,name) is not None else None for name in LINKS},rows=rows)


def read(diagnostic_id):
    with connection.cursor() as cursor:verify_guards(cursor)
    owner=models.IntakeDiagnostic.objects.select_related('initialization__source','run','scope_attempt','feed_attempt').get(pk=diagnostic_id)
    if owner.initialization.source.digest!=owner.source_digest:raise ValueError('Diagnostic initialized source differs')
    if owner.recipe_digest!=recipe_digest():raise ValueError('Diagnostic reader recipe differs')
    rows={}
    for name,(model,fields) in ROWS.items():
        rows[name]=list(model.objects.filter(diagnostic=owner).order_by('ordinal').values('ordinal',*fields))
        if (len(rows[name])!=getattr(owner,COUNTS[name])
                or [row['ordinal'] for row in rows[name]]!=list(range(len(rows[name])))):
            raise ValueError('Diagnostic row count/order differs')
    if digest(_value(owner,rows))!=owner.digest:raise ValueError('Diagnostic immutable typed digest differs')
    if owner.kind=='IMPORTER':
        if (owner.run.input_digest!=owner.input_digest or owner.run.business_date!=owner.business_date
                or owner.run.mdm_input_capture.source_id!=owner.initialization.source_id
                or owner.scope_attempt_id is not None and owner.scope_attempt.run_id!=owner.run_id
                or owner.feed_attempt_id is not None and owner.feed_attempt.run_id!=owner.run_id):
            raise ValueError('Diagnostic original importer owner differs')
    return owner,rows


def _insert(owner,rows):
    if not connection.in_atomic_block:raise ValueError('Diagnostic capture requires the original failure transaction')
    with connection.cursor() as cursor:verify_guards(cursor)
    owner.recipe_digest=recipe_digest()
    for name in ROWS:setattr(owner,COUNTS[name],len(rows[name]))
    owner.digest=digest(_value(owner,rows))
    existing=models.IntakeDiagnostic.objects.filter(pk=owner.pk).first()
    if existing is not None:
        found,stored=read(existing.pk)
        if found.digest!=owner.digest or stored!=rows:raise ValueError('Diagnostic retry facts differ')
        return found
    with setting('fresh.intake_diagnostic',owner.pk):
        owner.save(force_insert=True)
        for name,(model,_fields) in ROWS.items():
            model.objects.bulk_create([model(diagnostic=owner,**row) for row in rows[name]])
        found,stored=read(owner.pk)
        if found.digest!=owner.digest or stored!=rows:raise ValueError('Independent diagnostic readback differs')
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS intake_diagnostic_complete IMMEDIATE')
    return found


def capture_importer(run,error,*,scope_attempt=None):
    """Called only at real claimed failure closure, before losing error rows."""
    if not isinstance(error,NativeIntakeRejected):return None
    if run.kind!='DAILY_CHAIN' or run.evidence_mode!='production':return None
    from mta.runtime.models import ProductionInitialization
    from mta.runtime.daily_feed_models import DailyFeedAttempt
    initialization=ProductionInitialization.objects.select_related('source').get(source=run.mdm_input_capture.source)
    if scope_attempt is not None and scope_attempt.run_id!=run.pk:raise ValueError('Diagnostic worker run differs')
    feed=DailyFeedAttempt.objects.filter(run=run).first()
    key='scope:'+str(scope_attempt.pk) if scope_attempt is not None else 'run:'+str(run.pk)
    owner=models.IntakeDiagnostic(id=uuid.uuid5(uuid.NAMESPACE_URL,SCHEMA+':'+key),initialization=initialization,
        run=run,scope_attempt=scope_attempt,feed_attempt=feed,kind='IMPORTER',stage=error.stage,
        business_date=run.business_date,clock=datetime.combine(run.business_date,datetime.min.time()),
        input_digest=run.input_digest,source_digest=initialization.source.digest,
        configuration_digest=initialization.configuration_digest,metadata=dict(
            input_manifest_digest=run.input_manifest_digest,production_digest=run.production_digest,
            capture_revision=run.mdm_input_capture.revision_digest,error_type=type(error).__name__,
            error_message=str(error)[:4000]))
    return _insert(owner,dict(rejections=rejection_rows(error),aborts=[],observations=[],settings=[]))


def capture_fullkit(initialization,config,*,business_date,run_datetime,capture_root):
    """Check first; atomically retain only a real failure, without a fake run."""
    from mta.application import literal_fullkit
    if connection.in_atomic_block:raise ValueError('Fullkit observation precedes its own short transaction')
    result=literal_fullkit.check(config,business_date=business_date,run_datetime=run_datetime,capture_root=capture_root)
    if not result['AbortRun']:return None,result
    from datetime import date
    owner=models.IntakeDiagnostic(initialization=initialization,kind='FULLKIT',stage='CheckRunStartCriteria',
        business_date=date.fromisoformat(business_date),clock=parse_datetime(result['clock']),
        input_digest=digest(dict(policy=literal_fullkit.POLICY,observations=result['observations'])),
        source_digest=initialization.source.digest,configuration_digest=digest(config),
        metadata=dict(abort_run=True,input_root=config['input_root'],site_root=config['site_root'],
            absent_hooks=config['absent_hooks'],capture_root=str(capture_root),policy=literal_fullkit.POLICY))
    with transaction.atomic():
        from mta.mdm.supplier_revisions import lock_transaction
        lock_transaction(initialization.source_id)
        owner=_insert(owner,fullkit_rows(config,result))
    return owner,result
