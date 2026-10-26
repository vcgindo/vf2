"""Bind native preparation to the existing capture and atomic finish boundary.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from django.db import connection
from django.db.models import F
from mta.serialization import digest
from mta.runtime.accepted_daily import epochs

CONTRACT='vectorflow-native-capture-cut-v1'


def seed(state, *, reused):
    return dict(contract=CONTRACT, initialization_id=state.initialization_id,
        source_digest=state.source_digest, certification_digest=state.certification_digest,
        base_revision_id=state.master_revision_id, configuration_digest=state.configuration_digest,
        qualified_master_reuse=bool(reused))


def seal(run,*,consumer_snapshot=None):
    body=run.production_manifest.get('ingestion_preparation')
    if body is None:
        return
    cut=epochs(body['initialization_id'],lock=True)
    if consumer_snapshot is not None:
        from mta.runtime.scope_consumers import capture
        body['bpr_consumer_cut']=capture(run,consumer_snapshot,body['initialization_id'])
    cut[3]+=1  # Exactly this single guarded calculation-header UPDATE.
    body.update(run_id=str(run.pk),predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
                capture_cut=cut)
    body['receipt_digest']=digest(body)
    run.save(update_fields=['production_manifest'])
    if epochs(body['initialization_id'])!=cut:
        raise ValueError('Native capture preparation did not seal atomically')


def require_commit(run):
    body=run.production_manifest.get('ingestion_preparation')
    if body is None:
        return None
    if (body.get('contract')!=CONTRACT or body.get('run_id')!=str(run.pk)
            or body.get('predecessor_id')!=(str(run.predecessor_id) if run.predecessor_id else None)
            or body.get('receipt_digest')!=digest({k:v for k,v in body.items() if k!='receipt_digest'})
            or epochs(body['initialization_id'],lock=True)!=body.get('capture_cut')):
        raise ValueError('Native source/master/configuration/fact/action changed during calculation')
    from mta.runtime.ingestion_models import InitializationCertification,MasterInputRevision
    cert=InitializationCertification.objects.get(initialization_id=body['initialization_id'],status='CERTIFIED')
    base=MasterInputRevision.objects.get(pk=body['base_revision_id'],initialization_id=cert.initialization_id,status='ACCEPTED')
    if (cert.receipt_digest!=body['certification_digest']
            or run.mdm_input_capture.source.digest!=body['source_digest']):
        raise ValueError('Native capture certification/source differs')
    return body


def publication_metadata(run, capture, producer, *, _scoped_placement=False):
    if capture is None:
        return
    from mta.runtime.ingestion_models import IngestionRevisionState, MasterInputRevision
    base=MasterInputRevision.objects.get(pk=capture['base_revision_id'],status='ACCEPTED')
    state=IngestionRevisionState.objects.select_for_update().get(initialization_id=capture['initialization_id'])
    if base.run_id is None and (state.master_epoch,state.configuration_epoch)==(base.master_epoch,base.configuration_epoch):
        IngestionRevisionState.objects.filter(pk=state.pk).update(master_epoch=F('master_epoch')+1)
        state.refresh_from_db()
    if not isinstance(producer,dict) or producer.get('configuration_digest')!=capture['configuration_digest']:
        raise ValueError('Native prepared producer result differs')
    if _scoped_placement:
        from mta.runtime.placement_master_publication import publication_master as placement_master
        producer=placement_master(run,capture,producer,state)
    elif producer.get('reused') is not capture['qualified_master_reuse']:
        from mta.runtime.production_post_dbm import AUTHORITY
        if str(run.pk)!=AUTHORITY['run']:
            raise ValueError('Native prepared producer result differs')
        from mta.runtime.scoped_postdbm_recovery import publication_master,promote_master
        producer=publication_master(run,capture,producer)
        producer=promote_master(run,capture,producer,state)
    producer=dict(producer,master_cut=[state.master_epoch,state.configuration_epoch])
    run.production_manifest['master_preparation']=producer
    run.production_manifest['ingestion_preparation']=capture
