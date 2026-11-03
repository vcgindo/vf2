"""One-time typed history adoption inside the existing maintenance upgrade."""
from contextlib import closing

from django.db import connection,transaction

from mta.serialization import digest
from mta.runtime.models import ProductionInitialization
from mta.runtime.state_cut_models import OperationalStateCut
from mta.runtime.dated_history_delta import FAMILIES,TRANSITION_FAMILIES,supports_descriptor,source_table,family_enabled
from mta.runtime.dated_history_reader import read_cut
from mta.runtime.dated_history_writer import opening_path,seal_anchor_rows
from mta.runtime.rationing_adoption import accepted_terminal


def adopt(owner):
    if not connection.in_atomic_block:
        raise ValueError('History adoption requires the existing upgrade transaction')
    from mta.runtime.ingestion_authority import _provisioner
    from mta.runtime.input_reader import read_execution_input
    from mta.runtime.execution_settings import require_snapshot
    from mta.runtime import relational_state,opening_storage
    with transaction.atomic(),connection.cursor() as cursor:
        _provisioner(cursor)
        owner=ProductionInitialization.objects.select_for_update().get(pk=owner.pk)
        run=accepted_terminal(owner)
        if run is None:
            manifest=owner.input_payload
            if digest(manifest)!=owner.input_manifest_digest:
                raise ValueError('History adoption requires the exact initialized manifest')
            manifest_digest=owner.input_manifest_digest
            settings=owner.configuration_digest
            from mta.runtime.input_storage import read_input
            profile=read_input(owner,components=('profile',),image_reader=opening_storage.load_image)['profile']
            if digest(profile)!=settings:
                raise ValueError('History adoption initialized profile differs')
        else:
            manifest=run.production_manifest
            if manifest.get('version') not in (2,3) or digest(manifest)!=run.production_digest:
                raise ValueError('History adoption requires its intact native accepted manifest')
            manifest_digest=run.production_digest
            frozen=read_execution_input(run,components=('profile','execution_settings','initialization_binding'))
            if frozen['initialization_binding']['id']!=str(owner.pk):
                raise ValueError('History adoption captured initialization differs')
            settings=require_snapshot(owner,frozen['profile'],frozen.get('execution_settings'),run.business_date)
            profile=frozen['profile']
        result={}
        for family in FAMILIES:
            existing=OperationalStateCut.objects.filter(initialization=owner,family=family).order_by('-position').first()
            if not family_enabled(family,profile):
                if existing is not None or run is not None and family in manifest['images']:
                    raise ValueError('Disabled complete history has an activated terminal image')
                result[family]=dict(status='FINALIZATION_DISABLED')
                continue
            if existing is not None:
                cut=read_cut(existing.pk)
                if cut.run!=(run.pk if run else None):
                    cut=_adopt_transition(owner,run,existing,cut,manifest,settings)
                    status='ADOPTED_TRANSITION'
                else:
                    status='EXISTING'
                result[family]=dict(status=status,cut_id=str(cut.identity),root_digest=cut.root_digest)
                continue
            path=family if run else opening_path(family)
            item=manifest['images'].get(path)
            if item is None:
                result[family]=dict(status='SOURCE_ABSENT')
                continue
            if item.get('image')!=path or 'storage_format' in item or item.get('table')!=source_table(family):
                raise ValueError('History adoption requires its exact old-format source image')
            if not supports_descriptor(family,item['fields'],item['count']):
                result[family]=dict(status='LEGACY_DESCRIPTOR_RETAINED')
                continue
            cut=OperationalStateCut.objects.create(initialization=owner,family=family,position=0,run=run,
                input_digest=run.input_digest if run else owner.input_digest,settings_digest=settings)
            anchor=dict(owner_kind='RUN' if run else 'INITIALIZATION',owner_id=str(run.pk if run else owner.pk),
                manifest_digest=manifest_digest,image=path,digest=item['digest'],count=item['count'])
            source=relational_state.iter_image(run,item) if run else opening_storage.iter_image(owner,item)
            with closing(source) as rows:
                seal_anchor_rows(cut,item,rows,anchor)
            accepted=read_cut(cut.pk)
            result[family]=dict(status='ADOPTED',cut_id=str(cut.pk),root_digest=accepted.root_digest,
                source_run=str(run.pk) if run else None,rows=accepted.body['count'])
        return result


def _adopt_transition(owner,run,parent_row,parent,manifest,settings):
    """Only a sealed one-day transition that exactly matches the old closing."""
    from mta.row_sequences import RecordRows
    from mta.runtime import phase_state_contract,relational_state
    from mta.runtime.models import DailyPhaseSnapshot
    from mta.runtime.phase_state_schema import TABLES
    from mta.runtime.transition_history_image import FORMAT,iter_image,require_image
    from mta.runtime.dated_history_writer import write_transition

    family=parent.body['family']
    if (run is None or family not in TRANSITION_FAMILIES or parent.run is None
            or parent.run!=run.predecessor_id):
        raise ValueError('History anchor does not cover the current accepted prefix')
    snapshot=DailyPhaseSnapshot.objects.get(run=run,phase='DBM')
    phase_state_contract.require(snapshot)
    if snapshot.input_digest!=run.input_digest or digest(snapshot.manifest)!=snapshot.state_digest:
        raise ValueError('History adoption phase commitment differs')
    item=manifest['images'][family]
    phase=snapshot.manifest['images']['phase/DBM/'+family.removeprefix('closing/')]
    if (item.get('image')!=family or item.get('table')!=source_table(family)
            or 'storage_format' in item or phase.get('storage_format')!=FORMAT
            or any(phase[key]!=item[key] for key in ('table','count','fields','digest'))
            or require_image(run,phase)!=parent):
        raise ValueError('Accepted phase history does not match its legacy closing')
    for _ in iter_image(run,phase,audit=True):pass
    additions=relational_state.load_image(run,phase['additions'])
    changes=relational_state.load_image(run,phase['changes'],table_registry=TABLES)
    transition=dict(opening_count=parent.body['count'],additions=list(additions),
        removed=[row['OpeningOrdinal'] for row in changes if row['OpeningOrdinal'] is not None],
        sorted_prefix=phase['sorted_prefix'])
    cut=OperationalStateCut.objects.create(initialization=owner,family=family,position=parent.position+1,
        run=run,parent=parent_row,input_digest=run.input_digest,settings_digest=settings)
    anchor=dict(owner_kind='RUN',owner_id=str(run.pk),manifest_digest=run.production_digest,
        image=family,digest=item['digest'],count=item['count'])
    rows=RecordRows(item['count'],lambda:relational_state.iter_image(run,item))
    write_transition(cut,parent,rows,today=run.business_date,transition=transition,anchor=anchor)
    return read_cut(cut.pk)
