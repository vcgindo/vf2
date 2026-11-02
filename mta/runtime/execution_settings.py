"""Central control ownership; historical initialization and run inputs stay sealed.

Only the trusted management process writes versions. Resolution is bounded by
the control catalogue, never SKU count. Existing consumers receive their exact
profile projection, not a generic dictionary of loosely typed parameter names.
"""
from datetime import date
from uuid import uuid4
from dataclasses import dataclass
from django.db import connection, transaction
from mta.serialization import digest
from mta.runtime.execution_setting_values import SettingCell, rows_digest

CONTRACT = 'vectorflow-execution-settings-v1'
PARTITION_CONTRACT = 'vectorflow-settings-master-partitions-v1'
CELL_FIELDS = ('path', 'module', 'parameter', 'ordinal', 'value_kind', 'value_text', 'value_state')


@dataclass(frozen=True)
class MasterSettingsBasis:
    previous_profile_digest: str
    cut: tuple
    revision_id: str


def master_basis(owner, parent, parent_profile, current_profile, ref, revision_id, business_date):
    """A DBM-only control edit does not invalidate unchanged accepted masters.

    This returns the actual old producer/cut, rather than rewriting its
    metadata to claim the new settings. All normal input/queue tests still run.
    """
    if ref is None:
        return None
    from mta.runtime.ingestion_models import MasterInputRevision
    previous=parent.production_manifest.get('master_preparation',{})
    if previous.get('configuration_digest')!=digest(parent_profile):
        return None
    cut=previous.get('master_cut')
    if not isinstance(cut,list) or len(cut)!=2:
        return None
    current=MasterInputRevision.objects.get(pk=revision_id,initialization=owner,status='ACCEPTED')
    if current.partitions.get('contract')!=PARTITION_CONTRACT:
        return None
    prior=MasterInputRevision.objects.filter(initialization=owner,status='ACCEPTED',
        master_epoch=cut[0],configuration_epoch=cut[1]).first()
    if prior is None or current.master_epoch!=prior.master_epoch:
        return None
    old_base=prior.partitions.get('base') if prior.partitions.get('contract')==PARTITION_CONTRACT else prior.partitions
    if current.partitions['base']!=old_base:
        return None
    compatible_profiles(owner,parent_profile,current_profile,ref,business_date)
    return MasterSettingsBasis(digest(parent_profile),tuple(cut),str(prior.pk))


def reference(version):
    return dict(contract=CONTRACT, id=str(version.pk), initialization_id=str(version.initialization_id),
        revision=version.revision, effective_date=version.effective_date.isoformat() if version.effective_date else None,
        values_digest=version.values_digest, profile_digest=version.profile_digest)


def _rows(version):
    return tuple(SettingCell(**row) for row in version.values.order_by('position').values(*CELL_FIELDS))


def verify(version, original):
    from mta.runtime.execution_setting_catalogue import project
    if version.status != 'COMMITTED' or version.format_version != 1:
        raise ValueError('Execution settings version is not committed/supported')
    cells = _rows(version)
    if rows_digest(cells) != version.values_digest:
        raise ValueError('Execution settings row digest differs')
    profile = project(original, cells)
    if digest(profile) != version.profile_digest:
        raise ValueError('Execution settings projection differs')
    return profile


def resolve(owner, original, business_date):
    """One SELECT chooses the complete immutable version and ordered cells."""
    from mta.runtime.execution_setting_catalogue import project
    # Two small normalized tables; a statement snapshot cannot expose half an edit.
    with connection.cursor() as cursor:
        cursor.execute('SELECT V.id,V.revision,V.effective_date,V.values_digest,V.profile_digest,'
            'R.path,R.module,R.parameter,R.ordinal,R.value_kind,R.value_text,R.value_state '
            'FROM mta.fresh_mta_executionsettingsversion V '
            'LEFT JOIN mta.fresh_mta_executionsetting R ON R.version_id=V.id '
            'WHERE V.id=(SELECT id FROM mta.fresh_mta_executionsettingsversion '
            "WHERE initialization_id=%s AND status='COMMITTED' "
            'AND (effective_date IS NULL OR effective_date<=%s) ORDER BY revision DESC LIMIT 1) '
            'ORDER BY R.position', [owner.pk, business_date])
        rows = cursor.fetchall()
    if not rows:
        return original, None  # Historical, pre-adoption installation only.
    header = rows[0][:5]
    cells = tuple(SettingCell(*row[5:]) for row in rows if row[5] is not None)
    if not cells or rows_digest(cells) != header[3]:
        raise ValueError('Execution settings atomic row set differs')
    profile = project(original, cells)
    # The immutable header was sealed by the management transaction. The
    # finite projector checks all editable cells against the trusted original;
    # do not rehash excluded master/history populations to obtain a scalar.
    ref = dict(contract=CONTRACT, id=str(header[0]), initialization_id=str(owner.pk),
        revision=header[1], effective_date=header[2].isoformat() if header[2] else None,
        values_digest=header[3], profile_digest=header[4])
    return profile, ref


def require_snapshot(owner, profile, ref, business_date):
    """Authenticate a frozen version; never select current management values."""
    if ref is None:
        if digest(profile) != owner.configuration_digest:
            raise ValueError('Historical initialization configuration differs')
        return
    from mta.runtime.execution_setting_models import ExecutionSettingsVersion
    version = ExecutionSettingsVersion.objects.get(pk=ref.get('id'), initialization=owner, status='COMMITTED')
    if (reference(version) != ref or digest(profile) != version.profile_digest
            or (version.effective_date and version.effective_date > date.fromisoformat(str(business_date)))):
        raise ValueError('Frozen execution settings ownership/date/profile differs')


def compatible_profiles(owner, previous, current, ref, business_date):
    """Allow only an authenticated catalogue projection; no root rebinding."""
    from mta.runtime.execution_setting_catalogue import extract, project
    require_snapshot(owner, current, ref, business_date)
    # Projecting previous from current, and conversely, checks every nonmanaged
    # field without copying any master/history population.
    if digest(project(previous, extract(current))) != digest(current):
        raise ValueError('Execution settings transition changes nonmanaged configuration')


def daily_frame(owner, frame, business_date, retry_capture_id=None):
    if retry_capture_id is not None:
        from mta.runtime.models import CalculationRun
        from mta.runtime.input_reader import read_execution_input
        frozen=CalculationRun.objects.get(pk=retry_capture_id)
        raw=read_execution_input(frozen,components=('profile','execution_settings'))
        profile,ref=raw['profile'],raw.get('execution_settings')
        require_snapshot(owner,profile,ref,business_date)
    else:
        profile,ref=resolve(owner,frame['profile'],business_date)
    return {**frame,'profile':profile,'execution_settings':ref}


def _stable(owner, effective_date):
    from mta.runtime.daily_feed import unresolved_attempts
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from release.upgrade_database import require_finished_work
    with connection.cursor() as cursor:
        require_finished_work(cursor,owner)
    if unresolved_attempts(owner).exists():
        raise ValueError('Finish or diagnose the retained daily operation before editing settings')
    captures = MdmDailyInputCapture.objects.filter(source=owner.source)
    native_only=captures.filter(run__csv_attempt__isnull=True,run__status__in=('RUNNING','FAILED'))
    if native_only.exclude(retries__status='CONSUMED',retries__run__status='SUCCEEDED').exists():
        raise ValueError('Frozen/scoped/failed work retains its original settings')
    last = captures.order_by('-run__business_date').values_list('run__business_date', flat=True).first()
    if effective_date is not None and last is not None and effective_date <= last:
        raise ValueError('Settings require an unadmitted future business date')


def _append(owner, cells, profile, parent, effective_date, actor, reason):
    from mta.runtime.execution_setting_models import ExecutionSettingsVersion, ExecutionSetting
    if not actor or len(actor)>128 or not reason or len(reason)>512:
        raise ValueError('Bounded settings actor and reason required')
    value = ExecutionSettingsVersion.objects.create(initialization=owner, parent=parent,
        revision=1 if parent is None else parent.revision+1, effective_date=effective_date,
        values_digest=rows_digest(cells), profile_digest=digest(profile), actor=actor, reason=reason)
    ExecutionSetting.objects.bulk_create([ExecutionSetting(version=value, position=i, **cell.as_dict())
        for i, cell in enumerate(cells)])
    value.status='COMMITTED'; value.save(update_fields=('status',))
    return value


def _publish_revision(owner, parent, version):
    """Account for configuration watches without rewriting any old receipt."""
    from mta.runtime.ingestion_models import IngestionRevisionState, MasterInputRevision
    from mta.runtime.ingestion_admission import receipt
    state=IngestionRevisionState.objects.select_for_update().get(initialization=owner)
    # Exactly the header INSERT, one bounded values INSERT and header commit
    # UPDATE fired existing configuration watches. Other work cannot be
    # laundered into a current revision by this metadata-only publication.
    if (state.master_epoch!=parent.master_epoch
            or state.configuration_epoch!=parent.configuration_epoch+3):
        raise ValueError('Settings commit changed a different master/configuration basis')
    base=parent.partitions
    base_master_epoch=parent.master_epoch
    base_configuration_epoch=parent.configuration_epoch
    if base.get('contract')==PARTITION_CONTRACT:
        base_master_epoch=base['base_master_epoch']
        base_configuration_epoch=base['base_configuration_epoch']
        base=base['base']  # Single direct immutable partition, never a chain.
    partitions=dict(contract=PARTITION_CONTRACT, base=base, settings=reference(version),
        base_master_epoch=base_master_epoch, base_configuration_epoch=base_configuration_epoch)
    body=dict(id=uuid4(), initialization_id=owner.pk, parent_id=parent.pk, run_id=parent.run_id,
        master_epoch=state.master_epoch, configuration_epoch=state.configuration_epoch, partitions=partitions)
    new=MasterInputRevision.objects.create(**body,receipt_digest=receipt(body))
    new.status='ACCEPTED';new.save(update_fields=('status',))
    return new


def commit(owner, original, *, cells=None, base_revision=None, effective_date=None,
           actor, reason):
    """Trusted atomic adoption/apply under the existing source/capture lock."""
    from mta.runtime.production_scope import authorize
    from mta.runtime.execution_setting_models import ExecutionSettingsVersion
    from mta.runtime.execution_setting_catalogue import extract, project
    from mta.runtime.ingestion_models import InitializationCertification, MasterInputRevision
    from mta.runtime.ingestion_admission import _admit
    from mta.mdm.supplier_revisions import source_lock
    from release.native_identity import require_current
    authorize()
    if connection.in_atomic_block:
        raise ValueError('Settings management owns its atomic transaction')
    if digest(original)!=owner.configuration_digest:
        raise ValueError('Settings adoption requires the exact original initialized profile')
    if effective_date is not None:
        effective_date=date.fromisoformat(str(effective_date))
    with source_lock(owner.source_id), transaction.atomic(), connection.cursor() as cursor:
        # The current watcher is database-wide. Do not silently invalidate a
        # second certified installation in a shared database.
        if InitializationCertification.objects.filter(status='CERTIFIED').exclude(initialization=owner).exists():
            raise ValueError('Settings management requires its exclusive certified installation database')
        admitted=_admit(cursor,owner.pk,require_current())
        parent=ExecutionSettingsVersion.objects.select_for_update().filter(initialization=owner,
            status='COMMITTED').order_by('-revision').first()
        _stable(owner,effective_date)
        if parent is None:
            if cells is not None or base_revision is not None or effective_date is not None:
                raise ValueError('Adopt current values before applying a settings edit')
            cells=extract(original); profile=project(original,cells)
        else:
            if cells is None:
                verify(parent,original)
                return parent
            if base_revision!=parent.revision:
                raise ValueError('Stale settings export; export the current revision again')
            if effective_date is None or (parent.effective_date and effective_date<=parent.effective_date):
                raise ValueError('Settings changes require a strictly increasing explicit effective date')
            profile=project(original,cells)
            if rows_digest(cells)==parent.values_digest:
                return parent
        revision=MasterInputRevision.objects.get(pk=admitted.master_revision_id)
        version=_append(owner,cells,profile,parent,effective_date,actor,reason)
        _publish_revision(owner,revision,version)
        # Reads of the original selected publication must remain admitted after
        # the configuration watches have advanced.
        _admit(cursor,owner.pk,require_current())
        return version


def validate_partition(value, initialization_id):
    from mta.runtime.execution_setting_models import ExecutionSettingsVersion
    from mta.runtime import master_revisions
    if set(value)!={'contract','base','settings','base_master_epoch','base_configuration_epoch'}:
        raise ValueError('Settings master partition fields differ')
    ref=value['settings']
    version=ExecutionSettingsVersion.objects.get(pk=ref.get('id'),initialization_id=initialization_id,status='COMMITTED')
    if reference(version)!=ref or value['base'].get('contract')==PARTITION_CONTRACT:
        raise ValueError('Settings master partition owner differs')
    if (value['base'].get('contract')==master_revisions.PHASE_CONTRACT
            and value['base']['revision_cut'][:2]!=[value['base_master_epoch'],value['base_configuration_epoch']]):
        raise ValueError('Settings master base phase counters differ')
    if set(value['base'])=={'opening_master_root'}:
        from mta.runtime.ingestion_admission import sha
        sha(value['base']['opening_master_root'])
        return None
    return master_revisions.validate(value['base'],initialization_id)


def validate_revision(revision, initialization_id):
    """A wrapper owns only its three settings writes over an accepted parent."""
    from mta.runtime.ingestion_models import MasterInputRevision
    from mta.runtime.ingestion_admission import receipt, REVISION_FIELDS
    parent=MasterInputRevision.objects.values(*REVISION_FIELDS,'receipt_digest').get(
        pk=revision['parent_id'],initialization_id=initialization_id,status='ACCEPTED')
    if (parent['receipt_digest']!=receipt({key:parent[key] for key in REVISION_FIELDS})
            or revision['master_epoch']!=parent['master_epoch']
            or revision['configuration_epoch']!=parent['configuration_epoch']+3):
        raise ValueError('Settings revision does not own its exact configuration cut')
    prior=parent['partitions']
    expected_base=prior['base'] if prior.get('contract')==PARTITION_CONTRACT else prior
    if revision['partitions']['base']!=expected_base:
        raise ValueError('Settings revision replaced its accepted master partition')
    validate_partition(revision['partitions'],initialization_id)
