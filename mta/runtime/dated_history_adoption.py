"""One-time typed history adoption inside the existing maintenance upgrade."""
from contextlib import closing

from django.db import connection,transaction

from mta.serialization import digest
from mta.runtime.models import ProductionInitialization
from mta.runtime.state_cut_models import OperationalStateCut
from mta.runtime.dated_history_delta import FAMILIES,supports_descriptor,source_table,family_enabled
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
                    raise ValueError('History anchor does not cover the current accepted prefix')
                result[family]=dict(status='EXISTING',cut_id=str(cut.identity),root_digest=cut.root_digest)
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
