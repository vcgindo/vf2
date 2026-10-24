"""Exact certified counter ownership for the existing scoped ledger.

The immutable initial capture is retained. Each owned statement stores its
expected next cut; unknown changes remain conflicts, including after fencing.
Normal Full still uses capture_preparation.require_commit without any exception.
"""
import json
from django.db import connection
from mta.serialization import digest


def identity(run,*,retained=False):
    from mta.runtime.capture_preparation import CONTRACT
    from mta.runtime.ingestion_models import InitializationCertification,MasterInputRevision
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    body=run.production_manifest.get('ingestion_preparation')
    if body is None:return None
    if (not connection.in_atomic_block or body.get('contract') != CONTRACT
            or body.get('run_id') != str(run.pk)
            or body.get('predecessor_id') != (str(run.predecessor_id) if run.predecessor_id else None)
            or body.get('receipt_digest') != digest({k:v for k,v in body.items() if k!='receipt_digest'})):
        raise ValueError('Scoped original certified capture identity differs')
    cert=InitializationCertification.objects.filter(initialization_id=body['initialization_id'],
        receipt_digest=body['certification_digest']).values(
            'status','receipt_digest','initialization_id','initialization__source_id').first()
    if cert is None or cert['status']!='CERTIFIED' and not (retained and cert['status']=='INVALIDATED'):
        raise ValueError('Scoped capture certification is unavailable or invalidated')
    captured=MdmDailyInputCapture.objects.filter(run_id=run.pk).values('source_id','source__digest').first()
    if (not MasterInputRevision.objects.filter(pk=body['base_revision_id'],
            initialization_id=cert['initialization_id'],status='ACCEPTED').exists()
            or captured is None or captured['source__digest'] != body['source_digest']
            or cert['initialization__source_id'] != captured['source_id']):
        raise ValueError('Scoped capture certification/source differs')
    return body


def next_cut(value):
    if value is None:return None
    if (not isinstance(value,list) or len(value)!=5
            or any(type(v) is not int or not 0<=v<=9223372036854775807 for v in value)
            or value[3]==9223372036854775807):
        raise ValueError('Scoped revision cut requires five bounded nonnegative integer counters')
    result=list(value);result[3]+=1
    return result


def positions(run,*,retained=False):
    """Lock existing revision state; expected never comes from the live counters."""
    if identity(run,retained=retained) is None:return None,None
    function='scope_retained_cut' if retained else 'scope_native_cut'
    with connection.cursor() as cursor:
        cursor.execute('SELECT mta.scope_expected_cut(%s),mta.'+function+'(%s)',[run.pk,run.pk])
        expected,observed=cursor.fetchone()
    return _decoded(expected),_decoded(observed)


def require_current(run):
    expected,observed=positions(run)
    if observed != expected:
        raise ValueError('Scoped native source/master/configuration/fact/action revision changed')
    return observed


def owned_position(run,*,retained=False):
    """Inside an already fenced unit, read after its actual guarded writers."""
    if identity(run,retained=retained) is None:return None
    function='scope_retained_cut' if retained else 'scope_native_cut'
    with connection.cursor() as cursor:
        cursor.execute('SELECT mta.'+function+'(%s)',[run.pk])
        return _decoded(cursor.fetchone()[0])


def _decoded(value):
    # Django's raw psycopg cursor leaves jsonb as text; model JSONFields have
    # their own decoder. Keep exact integer types rather than coercing cells.
    return json.loads(value) if isinstance(value,str) else value


def verify_write(run,expected,*,retained=False):
    if owned_position(run,retained=retained) != expected:
        raise ValueError('Scoped owned write did not advance exactly its declared revision cut')


def closing(run):
    expected,observed=positions(run,retained=True)
    diagnostics={}
    if expected!=observed:diagnostics['revision_conflict']=dict(expected=expected,observed=observed)
    body=run.production_manifest.get('ingestion_preparation')
    if body is not None:
        from mta.runtime.ingestion_models import InitializationCertification
        status=InitializationCertification.objects.filter(initialization_id=body['initialization_id'],
            receipt_digest=body['certification_digest']).values_list('status',flat=True).get()
        if status!='CERTIFIED':diagnostics['certification_status']=status
    # A conflict records the expected safe cut plus this header write, never
    # the foreign cut. Retry will therefore continue to reject that change.
    # The original watcher updates only CERTIFIED owners. Once invalidated,
    # this retained diagnostic write does not advance that owner's counters.
    after=expected if diagnostics.get('certification_status')=='INVALIDATED' else next_cut(expected)
    return after,observed,diagnostics
