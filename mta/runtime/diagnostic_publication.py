"""Canonical diagnostic ZIPs and explicit source-local publication order."""
from hashlib import sha256
import inspect
from pathlib import Path
import uuid

from django.db import connection,transaction
from mta.serialization import digest
from mta.application import operational_io as files,operational_alert_files as reports,operational_report_files as writers
from mta.runtime import intake_diagnostics as custody
from mta.runtime.intake_diagnostic_models import IntakeDiagnosticArchive,DiagnosticPublication

ARCHIVE_FIELDS=('root','relative_path','sha256','size_bytes','member','member_sha256','member_size_bytes','recipe_digest')


def recipe_digest():
    from mta.runtime.runtime_report_publication import _archive
    return digest(dict(schema='fresh-intake-diagnostic-zip-v1',modules={
        name:inspect.getsource(module) for name,module in (
            ('publication',inspect.getmodule(recipe_digest)),('reports',reports),('writers',writers),('files',files))},
        archive=inspect.getsource(_archive)))


def selector(owner):
    if owner.kind not in ('IMPORTER','FULLKIT'):raise ValueError('Unqualified diagnostic kind')
    return 'InvalidDataReport' if owner.kind=='IMPORTER' else 'DailyDataUnavailabilityReport'


def _archive_body(row,owner):
    return dict(diagnostic_id=str(owner.pk),diagnostic_digest=owner.digest,
        **{name:getattr(row,name) for name in ARCHIVE_FIELDS})


def _publication_body(row,owner_digest):
    return dict(initialization_id=str(row.initialization_id),selector=row.selector,
        failure_archive_id=str(row.failure_archive_id) if row.failure_archive_id is not None else None,
        operational_file_id=row.operational_file_id,owner_digest=owner_digest)


def read_archive(diagnostic_id,*,verify_bytes=True):
    owner,rows=custody.read(diagnostic_id)
    row=IntakeDiagnosticArchive.objects.get(pk=diagnostic_id)
    name=selector(owner)
    if (row.recipe_digest!=recipe_digest() or row.relative_path!='download/'+name+'.zip'
            or row.member!=name+'.csv' or row.digest!=digest(_archive_body(row,owner))):
        raise ValueError('Diagnostic archive source/recipe/member differs')
    if verify_bytes:
        files.verify_file(row.root,dict(relative_path=row.relative_path,sha256=row.sha256,size_bytes=row.size_bytes))
        if files.zip_members(row.root,row.relative_path)!=[dict(ordinal=0,name=row.member,
                sha256=row.member_sha256,size_bytes=row.member_size_bytes)]:
            raise ValueError('Diagnostic archive member bytes differ')
    return owner,row


def _publish(initialization,*,name,owner_digest,failure_archive=None,operational_file=None):
    """Caller owns initialization lock; duplicate acknowledgement is readback."""
    if not connection.in_atomic_block:raise ValueError('Diagnostic publication requires source lock transaction')
    query={'failure_archive':failure_archive} if failure_archive is not None else {'operational_file':operational_file}
    row=DiagnosticPublication(initialization=initialization,selector=name,
        failure_archive=failure_archive,operational_file=operational_file)
    row.digest=digest(_publication_body(row,owner_digest))
    previous=DiagnosticPublication.objects.filter(**query).first()
    if previous is not None:
        if previous.digest!=row.digest or _publication_body(previous,owner_digest)!=_publication_body(row,owner_digest):
            raise ValueError('Original diagnostic publication differs')
        return previous
    with custody.setting('fresh.diagnostic_publication',initialization.pk):row.save(force_insert=True)
    return row


def _payload(owner,rows):
    clock=owner.clock.isoformat(timespec='milliseconds')
    if owner.kind=='IMPORTER':
        records=[{key:(value.isoformat(timespec='milliseconds') if key=='RejectionDate' else value)
            for key,value in row.items() if key!='ordinal'} for row in rows['rejections']]
        return reports.invalid_data_bytes(records,clock)
    reasons=[{key:(value.isoformat(timespec='milliseconds') if key=='RunDateTime' else value)
        for key,value in row.items() if key not in ('ordinal','inherited')} for row in rows['aborts']]
    return reports.unavailable_daily_bytes(reasons,clock)


def _verify_originals(owner,rows):
    if owner.kind!='FULLKIT':return
    root=owner.metadata['capture_root']
    for row in rows['observations']:
        if row['Exists']:
            files.verify_file(root,dict(relative_path=row['member'],sha256=row['sha256'],size_bytes=row['size_bytes']))
        elif any(row[key] is not None for key in ('member','sha256','size_bytes')):
            raise ValueError('Absent fullkit file cannot acquire invented original bytes')


def publish_failure(diagnostic_id,*,output_root):
    """Publish committed failure facts; never rerun a producer or mutate a run."""
    if not transaction.get_autocommit():raise ValueError('Diagnostic files follow committed failure custody')
    from mta.runtime.production_scope import authorize
    from mta.runtime.daily_feed import job_lock
    from mta.runtime.models import ProductionInitialization
    from mta.runtime.runtime_report_publication import _archive
    authorize()
    owner,rows=custody.read(diagnostic_id)
    with job_lock(owner.initialization):
        _verify_originals(owner,rows)
        existing=IntakeDiagnosticArchive.objects.filter(pk=owner.pk).first()
        if existing is not None:
            _,archive=read_archive(owner.pk)
        else:
            root=files.owned_path(output_root,str(uuid.uuid4()))
            root.mkdir(parents=True,exist_ok=False)
            payload=_payload(owner,rows);name=selector(owner)
            if owner.kind=='IMPORTER':
                # Attachment mode affects output copies only. Existing download
                # is always the same ZIP; retain ZIP as the original custody.
                writers.invalid_data_report_files(root=root,report_bytes=payload,attach_zip=True,archive_writer=_archive)
            else:
                writers.unavailable_daily_report_files(root=root,report_bytes=payload,archive_writer=_archive)
            receipt=files.inspect_file(root,'download/'+name+'.zip')
            members=files.zip_members(root,receipt['relative_path'])
            expected=dict(ordinal=0,name=name+'.csv',sha256=sha256(payload).hexdigest(),size_bytes=len(payload))
            if members!=[expected]:raise ValueError('Canonical diagnostic CSV bytes differ')
            archive=IntakeDiagnosticArchive(diagnostic=owner,root=str(root),**receipt,
                member=expected['name'],member_sha256=expected['sha256'],member_size_bytes=expected['size_bytes'],
                recipe_digest=recipe_digest())
            archive.digest=digest(_archive_body(archive,owner))
        with transaction.atomic():
            initial=ProductionInitialization.objects.select_for_update().get(pk=owner.initialization_id)
            current,_=custody.read(owner.pk)
            if current.digest!=owner.digest:raise ValueError('Failure source changed before file publication')
            if existing is None:
                with custody.setting('fresh.intake_diagnostic',owner.pk):archive.save(force_insert=True)
            return _publish(initial,name=selector(owner),owner_digest=archive.digest,failure_archive=archive)


def publish_importer(owner):
    from mta.runtime.input_reader import read_input
    raw=read_input(owner.run,components=('pick_output_root',))
    root=files.owned_path(raw['pick_output_root'],str(owner.run_id)+'/intake-diagnostics')
    root.mkdir(parents=True,exist_ok=True)
    return publish_failure(owner.pk,output_root=root)


def operational_digest(row):
    return digest(dict(file_id=row.pk,attempt_id=str(row.operation.attempt_id),
        path=row.relative_path,sha256=row.sha256,size_bytes=row.size_bytes))


def publish_operational(file_id):
    """Explicit original custody attachment; no most-recent run/file inference."""
    from mta.runtime.operational_models import OperationalFile
    from mta.runtime.models import ProductionInitialization
    from mta.runtime.production_scope import authorize
    from mta.presentation.diagnostic_downloads import SELECTORS,open_operational_file
    if not transaction.get_autocommit():raise ValueError('Operational diagnostic attachment owns its transaction')
    authorize()
    row=OperationalFile.objects.select_related('operation__attempt__run').get(pk=file_id)
    names=[name for name,spec in SELECTORS.items() if spec['path']==row.relative_path]
    if len(names)!=1:raise ValueError('Operational diagnostic selector differs')
    run=row.operation.attempt.run
    # Use the same verified original-or-linked-repair byte path as the reader.
    stream,_,_=open_operational_file(run,names[0],row.pk)
    stream.close()
    owner_digest=operational_digest(row)
    with transaction.atomic():
        initial=ProductionInitialization.objects.select_for_update().get(source=run.mdm_input_capture.source)
        with connection.cursor() as cursor:custody.verify_guards(cursor)
        return _publish(initial,name=names[0],owner_digest=owner_digest,operational_file=row)
