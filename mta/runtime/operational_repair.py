"""Linked file repair without rewriting successful historical receipts."""
from django.db import transaction
from mta.application import operational_io as files
from mta.runtime.operational_models import OperationalAttempt,OperationalFile,OperationalRepairTarget
from mta.runtime.operational_lease import require_attempt_lease

EXACT='EXACT_CONTAINER'
MEMBERS='EXACT_ARCHIVE_MEMBERS'
# Only the mapped report archives admitted by the complete runner qualify.
# Backups, traces and other groups retain exact-container requirements.
MEMBER_GROUPS={'O2','O3','O4','O5','O6','O7'}


def receipt(file):
    return dict(relative_path=file.relative_path,sha256=file.sha256,size_bytes=file.size_bytes)


def members(file):
    return list(file.members.order_by('ordinal').values('ordinal','name','sha256','size_bytes'))


def _same_owner(parent,child):
    fields=('run_id','configuration_id','predecessor_id','business_date','run_output_digest','action_digest','source_digest','clock')
    if any(getattr(parent,name)!=getattr(child,name) for name in fields):
        raise ValueError('Repair source/configuration/action/clock identity differs')


def _operation_identity(effect):
    return tuple(getattr(effect,name) for name in ('ordinal','group','name','stage','source_digest'))


def verify_file_direct(file):
    files.verify_file(file.operation.attempt.root,receipt(file))
    expected=members(file)
    if expected and files.zip_members(file.operation.attempt.root,file.relative_path)!=expected:
        raise ValueError('Operational archive members changed')
    return file


def _verify_link(target,*,completed=False):
    owner=target.attempt;original=target.original_file;replacement=target.replacement_file
    if replacement is None or owner.repair_of_id!=original.operation.attempt_id:
        raise ValueError('Repair replacement or original owner is absent')
    if owner.repair_of.status!='SUCCEEDED' or original.operation.status!='SUCCEEDED':
        raise ValueError('Repair original is not a successful historical operation')
    if completed and replacement.operation.status!='SUCCEEDED':
        raise ValueError('Repair replacement operation is incomplete')
    _same_owner(owner.repair_of,owner)
    if (replacement.operation.attempt_id!=owner.pk
            or _operation_identity(original.operation)!=_operation_identity(replacement.operation)
            or replacement.relative_path!=original.relative_path or replacement.role!=original.role):
        raise ValueError('Repair operation/path/role lineage differs')
    if target.equivalence==EXACT:
        if (receipt(original)!=receipt(replacement) or members(original)!=members(replacement)):
            raise ValueError('Repair exact container bytes or members differ')
    elif target.equivalence==MEMBERS:
        if (original.operation.group not in MEMBER_GROUPS or not members(original)
                or members(original)!=members(replacement)):
            raise ValueError('Repair archive equivalence is outside approved member contract')
    else:raise ValueError('Explicit repair equivalence required')


def resolve_operational_file(original,*,_seen=None):
    seen=set() if _seen is None else set(_seen)
    if original.pk in seen:raise ValueError('Cyclic operational repair lineage')
    seen.add(original.pk)
    path=files.owned_path(original.operation.attempt.root,original.relative_path)
    if path.exists():return verify_file_direct(original)
    targets=list(original.repair_targets.filter(attempt__status='SUCCEEDED').select_related(
        'attempt__repair_of','replacement_file__operation__attempt','original_file__operation__attempt'))
    if len(targets)!=1:raise ValueError('Required operational file absent or repair lineage ambiguous: '+original.relative_path)
    target=targets[0]
    from mta.runtime.operational_attempts import configuration_value,_identity
    configuration_value(target.attempt.configuration)
    current=_identity(target.attempt.run)
    if (target.attempt.run_output_digest!=current['output_digest']
            or target.attempt.action_digest!=current['action_digest']
            or target.attempt.source_digest!=current['source_digest']):
        raise ValueError('Repair source/action identity changed')
    _verify_link(target,completed=True)
    return resolve_operational_file(target.replacement_file,_seen=seen)


def validate_repair_parent(parent,file_ids):
    if parent.status!='SUCCEEDED':raise ValueError('Repair requires a successful historical attempt')
    if not file_ids or len(file_ids)!=len(set(file_ids)):
        raise ValueError('Explicit nonempty unique repair file roster required')
    original=list(OperationalFile.objects.filter(pk__in=file_ids,operation__attempt=parent).select_related('operation__attempt'))
    indexed={row.pk:row for row in original}
    if set(indexed)!=set(file_ids):raise ValueError('Repair file belongs to another attempt')
    for row in original:
        if row.operation.group=='O8':
            raise ValueError('Backup snapshot artifacts cannot be regenerated as report repair')
        path=files.owned_path(parent.root,row.relative_path)
        if path.exists():
            verify_file_direct(row)
            raise ValueError('Repair target already exists; use the verified original')
        if row.repair_targets.filter(attempt__status__in=['RUNNING','SUCCEEDED']).exists():
            raise ValueError('Repair target already has an active/successful lineage')
    from mta.runtime.operational_attempts import _verify_attempt
    _verify_attempt(parent,missing_file_ids=set(file_ids))
    return [indexed[key] for key in file_ids]


def resolve_intent_attachment(attempt,attachment,*,missing_file_ids=()):
    matched=list(OperationalFile.objects.filter(operation__attempt=attempt,
        relative_path=attachment.relative_path,sha256=attachment.sha256,size_bytes=attachment.size_bytes))
    if len(matched)!=1:raise ValueError('Alert attachment lacks an unambiguous operation file receipt')
    original=matched[0]
    if original.pk in missing_file_ids:
        if attempt.status!='SUCCEEDED' or files.owned_path(attempt.root,original.relative_path).exists():
            raise ValueError('Repair admission permits only missing historical attachments')
        return None
    return resolve_operational_file(original)


@transaction.atomic
def bind_repair_file(attempt_id,original_file_id,replacement_file_id):
    owner=OperationalAttempt.objects.select_for_update().get(pk=attempt_id)
    require_attempt_lease(owner)
    if owner.status!='RUNNING' or owner.repair_of_id is None:
        raise ValueError('Running repair attempt required')
    target=owner.repair_targets.select_for_update().get(original_file_id=original_file_id)
    if target.replacement_file_id is not None:raise ValueError('Repair target already bound')
    replacement=OperationalFile.objects.select_related('operation__attempt').get(pk=replacement_file_id)
    verify_file_direct(replacement)
    target.replacement_file=replacement
    original=target.original_file
    target.equivalence=EXACT if receipt(original)==receipt(replacement) else MEMBERS
    _verify_link(target)
    target.save(update_fields=['replacement_file','equivalence'])
    require_attempt_lease(owner)
    return target


def verify_repair_attempt(owner,*,missing_file_ids=()):
    if not owner.repair_of_id:raise ValueError('Repair parent absent')
    if owner.repair_of.status!='SUCCEEDED':raise ValueError('Repair historical parent is not successful')
    _same_owner(owner.repair_of,owner)
    targets=list(owner.repair_targets.order_by('ordinal').select_related('original_file__operation','replacement_file__operation'))
    if not targets or [row.ordinal for row in targets]!=list(range(len(targets))):
        raise ValueError('Complete ordered repair target roster required')
    expected=sorted(set(_operation_identity(row.original_file.operation) for row in targets))
    operations=list(owner.operations.order_by('ordinal'))
    if [_operation_identity(row) for row in operations]!=expected or any(row.status!='SUCCEEDED' for row in operations):
        raise ValueError('Repair operation subset is incomplete or differs')
    from mta.runtime.operational_effects import verify_files
    for effect in operations:verify_files(effect,missing_file_ids=missing_file_ids)
    for target in targets:
        _verify_link(target,completed=True)
        if target.replacement_file_id not in missing_file_ids:
            resolve_operational_file(target.replacement_file)
    return expected


def stage_surviving_copy(effect,original):
    """Use only another recorded, exact surviving copy from the original owner."""
    from mta.runtime.operational_effects import record_file
    owner=effect.attempt
    require_attempt_lease(owner)
    if owner.repair_of_id!=original.operation.attempt_id:
        raise ValueError('Surviving copy belongs to another repair parent')
    candidates=OperationalFile.objects.filter(operation__attempt_id=owner.repair_of_id,
        sha256=original.sha256,size_bytes=original.size_bytes).exclude(pk=original.pk).order_by('pk')
    for candidate in candidates:
        path=files.owned_path(candidate.operation.attempt.root,candidate.relative_path)
        if not path.exists():continue
        verify_file_direct(candidate)
        if members(candidate)!=members(original):continue
        target=files.owned_path(owner.root,original.relative_path)
        target.parent.mkdir(parents=True,exist_ok=True)
        # Exclusive destination; never overwrite a different staged artifact.
        import shutil,os
        with path.open('rb') as source,target.open('xb') as destination:
            shutil.copyfileobj(source,destination,1024*1024);destination.flush();os.fsync(destination.fileno())
        files.verify_file(owner.root,receipt(original))
        return record_file(effect,relative_path=original.relative_path,role=original.role,archive=bool(members(original)))
    return None


def materialize_repair(attempt_id,*,archive_writer):
    """Repair only the declared files through their existing mapped producer."""
    from mta.runtime.operational_effects import operation
    from mta.runtime.operational_reports import materialize_report_operation,REPORT_OPERATIONS
    owner=OperationalAttempt.objects.select_related('repair_of').get(pk=attempt_id)
    require_attempt_lease(owner)
    if owner.status!='RUNNING' or owner.repair_of_id is None:
        raise ValueError('Running linked repair required')
    targets=list(owner.repair_targets.order_by('ordinal').select_related('original_file__operation'))
    grouped={}
    for target in targets:grouped.setdefault(target.original_file.operation_id,[]).append(target)
    for batch in sorted(grouped.values(),key=lambda rows:rows[0].original_file.operation.ordinal):
        old=batch[0].original_file.operation
        # A recorded surviving copy is preferable to rerunning even a report
        # producer. Check the complete group's candidates before writing.
        all_copies=True
        for target in batch:
            original=target.original_file
            candidates=OperationalFile.objects.filter(operation__attempt=owner.repair_of,
                sha256=original.sha256,size_bytes=original.size_bytes).exclude(pk=original.pk)
            found=False
            for candidate in candidates:
                if not files.owned_path(owner.repair_of.root,candidate.relative_path).exists():continue
                verify_file_direct(candidate)
                if members(candidate)==members(original):found=True;break
            all_copies=all_copies and found
        if all_copies:
            specification={name:getattr(old,name) for name in ('ordinal','group','name','stage','source_digest')}
            with operation(owner,**specification) as effect:
                for target in batch:
                    replacement=stage_surviving_copy(effect,target.original_file)
                    if replacement is None:raise ValueError('Recorded surviving copy disappeared')
                    bind_repair_file(owner.pk,target.original_file_id,replacement.pk)
        else:
            if old.group == 'O7':
                from mta.runtime.operational_alert_sources import read_alert_inputs
                from mta.runtime.operational_alert_runner import write_alert_files
                inputs=read_alert_inputs(owner.repair_of)
                specification={name:getattr(old,name) for name in ('ordinal','group','name','stage','source_digest')}
                with operation(owner,**specification) as effect:
                    write_alert_files(effect,inputs,archive_writer=archive_writer)
            elif old.group not in REPORT_OPERATIONS:
                raise ValueError('Mapped repair producer is not available for '+old.group)
            else:
                effect=materialize_report_operation(owner.pk,group=old.group,archive_writer=archive_writer)
            for target in batch:
                original=target.original_file
                replacement=effect.files.get(relative_path=original.relative_path,role=original.role)
                bind_repair_file(owner.pk,original.pk,replacement.pk)
    return owner
