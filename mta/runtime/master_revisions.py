"""Accepted static-master generations reference existing committed typed owners.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from uuid import uuid4
from django.db import connection
from django.db.models import F
from mta.serialization import digest
from mta.runtime.ingestion_admission import receipt, REVISION_FIELDS

CONTRACT = 'vectorflow-static-master-partitions-v1'
STATIC_TABLES = ('MasterData','SKUDescriptionTbl','SiteDescriptionTbl',
                 'SkuAttributeData','LocationAttributeData','SkuLocAttributeData')


def validate(value, initialization_id):
    """Validate bounded roots without reconstructing any population."""
    from mta.runtime.models import CalculationRun
    from mta.runtime.receipt_integrity import verify_root
    if (not isinstance(value,dict) or set(value) != {'contract','run_id','source_digest',
            'output_digest','input_manifest_digest','production_digest','roots'}
            or value['contract'] != CONTRACT or set(value['roots']) != set(STATIC_TABLES)):
        raise ValueError('Static master revision partition contract differs')
    run=CalculationRun.objects.select_related('mdm_input_capture__source').get(pk=value['run_id'])
    verify_root(run)
    from mta.runtime.models import ProductionInitialization
    owner=ProductionInitialization.objects.get(pk=initialization_id)
    if (run.mdm_input_capture.source_id != owner.source_id
            or value['source_digest'] != owner.source.digest
            or run.output_digest != value['output_digest']
            or run.input_manifest_digest != value['input_manifest_digest']
            or run.production_digest != value['production_digest']):
        raise ValueError('Static master revision source/run differs')
    for name in STATIC_TABLES:
        image=run.production_manifest['images']['closing/importer/'+name]
        expected=dict(image=image['image'], count=image['count'], digest=image['digest'],
            fields=[field for field, *_ in image['fields'] if field != 'Norm'])
        if value['roots'][name] != expected:
            raise ValueError('Static master immutable partition differs: '+name)
    return run


def accept(run, initialization_id, parent_id):
    """Called after successful typed publication, inside the SAME day commit."""
    if not connection.in_atomic_block or run.status != 'SUCCEEDED':
        raise ValueError('Static master acceptance requires atomic successful publication')
    from mta.runtime.ingestion_models import IngestionRevisionState, MasterInputRevision
    state=IngestionRevisionState.objects.select_for_update().get(initialization_id=initialization_id)
    old=MasterInputRevision.objects.get(pk=parent_id,initialization_id=initialization_id,status='ACCEPTED')
    if (state.master_epoch,state.configuration_epoch)==(old.master_epoch,old.configuration_epoch):
        if old.run_id is not None:
            return old
        # First canonical producer qualification establishes a new immutable
        # input representation. This metadata generation is not business DML.
        IngestionRevisionState.objects.filter(pk=initialization_id).update(master_epoch=F('master_epoch')+1)
        state.refresh_from_db()
    from mta.runtime.models import ProductionInitialization
    owner=ProductionInitialization.objects.select_related('source').get(pk=initialization_id)
    roots={}
    for name in STATIC_TABLES:
        image=run.production_manifest['images']['closing/importer/'+name]
        roots[name]=dict(image=image['image'],count=image['count'],digest=image['digest'],
            fields=[field for field,*_ in image['fields'] if field!='Norm'])
    partitions=dict(contract=CONTRACT,run_id=str(run.pk),source_digest=owner.source.digest,
        output_digest=run.output_digest,input_manifest_digest=run.input_manifest_digest,
        production_digest=run.production_digest,roots=roots)
    body=dict(id=uuid4(),initialization_id=owner.pk,parent_id=old.pk,run_id=run.pk,
        master_epoch=state.master_epoch,configuration_epoch=state.configuration_epoch,partitions=partitions)
    candidate=MasterInputRevision.objects.create(**body,receipt_digest=receipt(body))
    candidate.status='ACCEPTED'
    candidate.save(update_fields=['status'])
    return candidate
