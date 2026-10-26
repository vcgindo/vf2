"""Terminal master handoff for the new placement request's accepted phases.

Intake's reuse decision and the actual phase producer are distinct facts. This
adapter preserves both and parents terminal state to its accepted DBM owner.
It neither adopts an old request nor grants cross-release execution authority.
"""
from django.db import connection
from mta.serialization import digest

PROVENANCE='fresh-placement-scoped-master-v1'
KEY='placement_execution_provenance'


def _owner(run,capture):
    from mta.runtime import scoped_final,scope_revisions
    from mta.runtime.models import RunPhaseAcceptance
    from mta.runtime.input_reader import read_input
    from mta.runtime.runtime_report_request import validate_request
    from mta.runtime.scoped_actions import revision
    request=validate_request(read_input(run,components=('scope_request',))['scope_request'])
    continuation={'UptoBPR':'PostBPR','UptoDBM':'PostDBM'}.get(request['scope'])
    if continuation is None:raise ValueError('Placement master requires a scoped request')
    scoped_final.require_pending_final(run)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('fresh.scope_phase',true),current_setting('fresh.scope_worker',true)")
        phase_id,worker=cursor.fetchone()
    final=RunPhaseAcceptance.objects.select_related('attempt').get(pk=phase_id,run=run,
        phase='DAY_FINAL',state_sealed=False,snapshot__isnull=True)
    attempt=final.attempt
    # Publication has consumed its capture and advanced owned counters. The
    # pending SQL owner and locked attempt authenticate that intermediate state.
    prefix,_=scoped_final.accepted_prefix(run)
    if (scope_revisions.identity(run)!=capture or attempt.scope!=continuation
            or attempt.status!='ACTIVE' or str(attempt.worker_token)!=worker
            or attempt.compatibility_digest!=request['compatibility_digest']
            or attempt.input_digest!=run.input_digest
            or attempt.input_manifest_digest!=run.input_manifest_digest
            or attempt.action_revision!=revision(run)
            or attempt.command_key==request['command_key']):
        raise ValueError('Placement master pending owner/capture differs')
    return prefix,final


def _producer(capture,producer,prefix):
    from mta.application.persistent_master import CONTRACT
    # This scoped entry runs prepare_day without prepared_master. Reuse and
    # changed-master producers need their own qualified implementation first.
    expected=dict(contract=CONTRACT,qualified=True,reused=False,
        configuration_digest=capture['configuration_digest'],
        full_master_producer_calls=1,changed_work=None)
    if (producer!=expected or type(producer.get('full_master_producer_calls')) is not int
            or producer.get('reused') is not False or producer.get('qualified') is not True
            or type(capture.get('qualified_master_reuse')) is not bool):
        raise ValueError('Placement master producer differs from its scoped contract')
    for phase in prefix:
        manifest=phase.snapshot.manifest;metadata=manifest['metadata']
        if (manifest['references']['profile']!=capture['configuration_digest']
                or metadata.get('master_reused') is not False
                or metadata.get('master_work') is not None
                or metadata.get('master_outcome')!='APPLIED'):
            raise ValueError('Placement master producer differs from accepted phases')


def _pair_metadata(run,source):
    from mta.runtime import relational_state as typed,phase_state
    rows=typed.load_image(run,source,table_registry=phase_state.REGISTRY)
    projected=[dict(row,NonNMS=None if row['NonNMS'] is None else bool(row['NonNMS'])) for row in rows]
    columns={name.casefold():(name,kind) for name,kind in phase_state.REGISTRY[source['table']]}
    return typed.describe_rows(projected,columns,'closing/importer/SkuLocAttributeData')[0]


def _static_roots(run,dbm):
    from mta.runtime.master_revisions import STATIC_TABLES
    manifest=dbm.snapshot.manifest;roots={}
    for name in STATIC_TABLES:
        source=manifest['images'][manifest['state']['importer'][name]['image']]
        if name=='SkuLocAttributeData':source=_pair_metadata(run,source)
        target=run.production_manifest['images']['closing/importer/'+name]
        if any(source[key]!=target[key] for key in ('count','digest','fields')):
            raise ValueError('Placement terminal master differs from accepted DBM: '+name)
        roots[name]=source['digest']
    return roots


def _parent(run,capture,prefix):
    from mta.runtime.ingestion_models import MasterInputRevision
    from mta.runtime.master_revisions import _validate_phase,PHASE_CONTRACT
    from mta.runtime.ingestion_admission import receipt,REVISION_FIELDS
    dbm=prefix[-1];cut=dbm.metadata['revision_after'][:2]
    parent=MasterInputRevision.objects.get(initialization_id=capture['initialization_id'],
        master_epoch=cut[0],configuration_epoch=cut[1],status='ACCEPTED')
    if (parent.run_id!=run.pk or parent.partitions.get('contract')!=PHASE_CONTRACT
            or parent.partitions.get('phase_id')!=str(dbm.pk)
            or parent.partitions.get('phase_digest')!=dbm.digest):
        raise ValueError('Placement accepted DBM master parent differs')
    expected={str(p.pk):p.digest for p in prefix};ancestor=parent;seen=set()
    while True:
        if (ancestor.pk in seen or str(ancestor.initialization_id)!=capture['initialization_id']
                or ancestor.status!='ACCEPTED'
                or ancestor.receipt_digest!=receipt({k:getattr(ancestor,k) for k in REVISION_FIELDS})):
            raise ValueError('Placement master ancestor receipt differs')
        if str(ancestor.pk)==capture['base_revision_id']:break
        seen.add(ancestor.pk)
        if (ancestor.run_id!=run.pk or ancestor.partitions.get('contract')!=PHASE_CONTRACT
                or expected.get(ancestor.partitions.get('phase_id'))!=ancestor.partitions.get('phase_digest')
                or _validate_phase(ancestor.partitions,capture['initialization_id']).pk!=run.pk
                or ancestor.parent_id is None):
            raise ValueError('Placement master phase ancestry differs')
        ancestor=ancestor.parent
    return parent


def configuration_writes(run):
    """Statement deltas from the existing typed writer, including COPY's cut."""
    from mta.runtime.relational_state import table_name
    from mta.runtime.ingestion_ownership import domain
    images=[]
    for path,item in run.production_manifest['images'].items():
        table=table_name(item['table'])
        if domain('mta_state',table)!='configuration':continue
        count=item['count']
        if (table not in ('dbm_dbmsettingstbl','importer_importersettingstbl',
                'bpr_ui_reportconfigurations','importer_vfsettings',
                'complete_importer_emailalertsettings')
                or type(count) is not int or count<0):
            raise ValueError('Placement configuration image/transport differs')
        # insert_image uses one COPY at >=500 rows; otherwise executemany
        # issues one INSERT per row. Empty images issue no statement.
        images.append(dict(image=path,table=item['table'],count=count,digest=item['digest'],
                           statements=1 if count>=500 else count))
    return sorted(images,key=lambda item:item['image'])


def _promotion(run,capture,prefix,state):
    from mta.runtime.ingestion_models import MasterInputRevision
    parent=_parent(run,capture,prefix);images=configuration_writes(run)
    before=[parent.master_epoch,parent.configuration_epoch]
    after=[before[0],before[1]+sum(item['statements'] for item in images)]
    if (not connection.in_atomic_block or str(state.pk)!=capture['initialization_id']
            or [state.master_epoch,state.configuration_epoch]!=after):
        raise ValueError('Placement terminal master configuration cut differs')
    if MasterInputRevision.objects.filter(initialization_id=state.pk,
            master_epoch=after[0],configuration_epoch=after[1]).exists():
        raise ValueError('Placement terminal master cut is already occupied')
    return parent,dict(parent_id=str(parent.pk),captured_base_id=capture['base_revision_id'],
        before=before,after=after,parent_receipt=parent.receipt_digest,
        configuration_writes=images,additional_master_increment=0)


def publication_master(run,capture,producer,state):
    prefix,final=_owner(run,capture)
    _producer(capture,producer,prefix)
    roots=_static_roots(run,prefix[-1])
    _,promotion=_promotion(run,capture,prefix,state)
    return dict(producer,**{KEY:dict(schema=PROVENANCE,capture_receipt=capture['receipt_digest'],
        capture_selected_reuse=capture['qualified_master_reuse'],accepted_master_reused=False,
        pending_final_id=str(final.pk),accepted_phases=[dict(id=str(p.pk),digest=p.digest) for p in prefix],
        terminal_static_roots=roots,master_promotion=promotion)})


def terminal_master_parent(run,initialization_id,base_id,state):
    from mta.runtime.receipt_integrity import verify_root
    capture=run.production_manifest['ingestion_preparation']
    producer=run.production_manifest['master_preparation']
    if (str(initialization_id)!=capture['initialization_id'] or str(base_id)!=capture['base_revision_id']
            or producer.get('master_cut')!=[state.master_epoch,state.configuration_epoch]):
        raise ValueError('Placement terminal master acceptance identity differs')
    raw={key:value for key,value in producer.items() if key not in (KEY,'master_cut')}
    expected=publication_master(run,capture,raw,state)
    if producer!={**expected,'master_cut':producer['master_cut']}:
        raise ValueError('Placement terminal master provenance differs')
    prefix,_=_owner(run,capture)
    parent=_parent(run,capture,prefix)
    verify_root(run)
    return parent
