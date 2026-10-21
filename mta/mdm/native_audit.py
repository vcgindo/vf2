"""Immutable native upload inputs and atomic, occurrence-owned retention."""
from datetime import timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection
from mta.serialization import digest, storage
from mta.mdm.native_audit_policy import validate_policy
from mta.runtime.native_audit_models import NativeUploadAudit, BINDINGS


def fields(model):
    return tuple(f.name for f in model._meta.fields if f.name not in ('id','source'))


def identity(capture):
    values = {f.attname: getattr(capture, f.attname) for f in capture._meta.fields
        if f.name not in ('status','frozen_digest','terminal_digest')}
    return storage({key: str(value) if isinstance(value, UUID) else value
                    for key, value in values.items()})


def images(capture, stage):
    return {name: list(model.objects.filter(capture=capture, stage=stage)
        .order_by('ordinal').values('source_pk','ordinal','retained',*fields(source)))
        for name, source, model in BINDINGS}


def image_digest(capture, stage, rows=None):
    return digest(dict(identity=identity(capture), stage=stage,
        rows=images(capture, stage) if rows is None else rows))


def _policy(capture):
    return dict(horizon=capture.horizon, timezone=capture.timezone,
                client_folder=capture.client_folder)


def verify(capture, *, sealed=True):
    from mta.runtime.input_reader import read_input
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    run = capture.run
    profile = read_input(run, components=('profile',))['profile']
    policy = validate_policy(profile)
    daily = MdmDailyInputCapture.objects.get(run=run)
    if (policy != _policy(capture) or run.kind != 'DAILY_CHAIN'
            or capture.source_id != daily.source_id
            or capture.source_id != capture.initialization.source_id
            or capture.configuration_digest != capture.initialization.configuration_digest
            or digest(profile) != capture.configuration_digest
            or capture.business_date != run.business_date
            or capture.predecessor_id != run.predecessor_id
            or capture.origin_id != daily.origin_id
            or image_digest(capture, 'FROZEN') != capture.frozen_digest):
        raise ValueError('Native audit frozen identity/value drift')
    if capture.predecessor_id:
        parent = capture.predecessor
        if (parent.status != 'SEALED' or parent.run.status != 'SUCCEEDED'
                or parent.source_id != capture.source_id
                or parent.initialization_id != capture.initialization_id
                or _policy(parent) != policy):
            raise ValueError('Native audit requires its own sealed predecessor')
    if sealed and (capture.status != 'SEALED'
            or image_digest(capture, 'FINAL') != capture.terminal_digest):
        raise ValueError('Native audit terminal identity/value drift')
    if not sealed and capture.status != 'FROZEN':
        raise ValueError('Native audit capture is not frozen')
    return capture


def bind(run, daily, profile):
    """Called while the daily source lock and REPEATABLE READ are held."""
    policy = validate_policy(profile)
    if policy is None:
        return
    from mta.runtime.initialization_models import ProductionInitialization
    if (run.kind != 'DAILY_CHAIN' or run.status != 'RUNNING'
            or daily.run_id != run.pk
            or daily.source.receipt.get('schema') != 'fresh-production-mdm-source-v1'):
        raise ValueError('Native audit requires an initialized running daily capture')
    if policy['timezone'] != settings.VF_MTA_ACTION_TIME_ZONE:
        raise ValueError('Native audit timezone differs from the workflow clock')
    initialized = ProductionInitialization.objects.get(source=daily.source)
    if initialized.configuration_digest != digest(profile):
        raise ValueError('Native audit policy differs from initialized configuration')
    parent = None
    if run.predecessor_id:
        parent = verify(NativeUploadAudit.objects.select_related('run','initialization','predecessor__run')
                        .get(run_id=run.predecessor_id))
    origin = None
    if daily.origin_id:
        origin = verify(NativeUploadAudit.objects.select_related('run','initialization','predecessor__run')
                        .get(run_id=daily.origin_id), sealed=False)
        from mta.runtime.captured_input import FINITE,TERMINAL,origin as captured_origin
        finite=False
        if run.input_payload.get('schema') in (FINITE,TERMINAL):
            captured_origin(run)
            finite=origin.run.status=='RUNNING' and str(origin.run_id)==run.input_payload['origin_run_id']
        if (origin.run.status != 'FAILED' and not finite or origin.source_id != daily.source_id
                or origin.predecessor_id != run.predecessor_id
                or origin.business_date != run.business_date or _policy(origin) != policy):
            raise ValueError('Native audit retry is not the frozen failed request')
        rows = images(origin, 'FROZEN')
    else:
        rows = {name: [dict(source_pk=row.pop('id'), ordinal=i, retained=None, **row)
            for i, row in enumerate(source.objects.filter(source=daily.source)
                .order_by('id').values('id',*fields(source)), 1)]
            for name, source, _ in BINDINGS}
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.native_audit_run',%s,true)", [str(run.pk)])
    capture = NativeUploadAudit(run=run, source=daily.source, initialization=initialized,
        predecessor=parent, origin=origin, business_date=run.business_date,
        configuration_digest=initialized.configuration_digest, **policy)
    capture.frozen_digest = image_digest(capture, 'FROZEN', rows)
    capture.save(force_insert=True)
    for name, _, model in BINDINGS:
        model.objects.bulk_create([model(capture=capture, stage='FROZEN', **row)
                                   for row in rows[name]], batch_size=500)
    verify(capture, sealed=False)


def finalize(run):
    """Run after force OldNorm publication, inside the daily commit transaction."""
    from mta.runtime.input_reader import read_input
    policy = validate_policy(read_input(run, components=('profile',))['profile'])
    if policy is None:
        if NativeUploadAudit.objects.filter(run=run).exists():
            raise ValueError('Native audit capture without its initialized policy')
        return
    capture = verify(NativeUploadAudit.objects.select_for_update(of=('self',)).select_related(
        'run','initialization','predecessor__run').get(run=run), sealed=False)
    cutoff = capture.business_date - timedelta(days=capture.horizon + 1)
    zone = ZoneInfo(capture.timezone)
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.native_audit_run',%s,true)", [str(run.pk)])
    frozen = images(capture, 'FROZEN')
    for name, source, model in BINDINGS:
        rows = frozen[name]
        current = {row['id']: row for row in source.objects.select_for_update()
            .filter(source=capture.source, pk__in=[r['source_pk'] for r in rows])
            .values('id',*fields(source))}
        terminal = []
        for row in rows:
            live = current.get(row['source_pk'])
            if live is None or any(live[key] != row[key] for key in fields(source)
                    if not (name == 'UIUploadLogFNC' and key == 'OldNorm')):
                raise ValueError('Captured native audit occurrence changed: '+name)
            stamp = live['ActionTimeStamp']
            if stamp.tzinfo is None:
                raise ValueError('Native audit requires an aware producer timestamp')
            terminal.append(dict(source_pk=row['source_pk'], ordinal=row['ordinal'],
                retained=stamp.astimezone(zone).date() > cutoff,
                **{key: live[key] for key in fields(source)}))
        model.objects.bulk_create([model(capture=capture, stage='FINAL', **row)
                                   for row in terminal], batch_size=500)
        # Exact source occurrence identity, never business-key or date-only delete.
        source.objects.filter(source=capture.source,
            pk__in=[r['source_pk'] for r in terminal if not r['retained']]).delete()
    capture.terminal_digest = image_digest(capture, 'FINAL')
    capture.status = 'SEALED'
    capture.save(update_fields=['status','terminal_digest'])
    verify(capture)


def receipt(run):
    from mta.runtime.input_reader import read_input
    policy = validate_policy(read_input(run, components=('profile',)).get('profile', {}))
    capture = NativeUploadAudit.objects.select_related('run','initialization','predecessor__run').filter(run=run).first()
    if policy is None and capture is None:
        return None
    if capture is None:
        raise ValueError('Missing required native audit capture')
    verify(capture)
    return dict(**identity(capture), status=capture.status,
        frozen_digest=capture.frozen_digest, terminal_digest=capture.terminal_digest)


def native_rows(capture, rows):
    """Expose the native wall clock and column roster without metadata columns."""
    result = {}
    zone = ZoneInfo(capture.timezone)
    for name, source, _ in BINDINGS:
        result[name] = []
        for row in rows[name]:
            value = {key: row[key] for key in fields(source)}
            value['ActionTimeStamp'] = value['ActionTimeStamp'].astimezone(zone).replace(tzinfo=None)
            result[name].append(storage(value))
    return result


def read_images(run):
    """Complete cumulative audit evidence plus this run's retained export inputs."""
    run.refresh_from_db()
    if run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED':
        raise ValueError('Native audit reader requires a successful daily run')
    capture = verify(NativeUploadAudit.objects.select_related('run','initialization','predecessor__run').get(run=run))
    current = images(capture, 'FINAL')
    retained = {name: [r for r in rows if r['retained']] for name, rows in current.items()}
    # Walk immutable own ancestors, taking the most recent terminal value per PK.
    full = {name: {} for name, _, _ in BINDINGS}
    owner = capture
    while owner is not None:
        verify(owner)
        for name, rows in images(owner, 'FINAL').items():
            for row in rows:
                full[name].setdefault(row['source_pk'], row)
        owner = owner.predecessor
    ordered = {name: [rows[pk] for pk in sorted(rows)] for name, rows in full.items()}
    expired = {name: [r for r in rows if r['source_pk'] not in
        {v['source_pk'] for v in retained[name]}] for name, rows in ordered.items()}
    return dict(full_source_audit=native_rows(capture, ordered),
        retained=native_rows(capture, retained), expired=native_rows(capture, expired))
