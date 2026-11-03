"""Typed transport for already-calculated dated histories.

Only new occurrences and one-time membership closures are written. The caller
owns initialization/capture and the normal day transaction; SQL independently
enforces those owners and requires a run-bound seal before commit.
"""
from contextlib import closing

from django.db import connection, transaction

from mta.serialization import canonical_parts,digest
from mta.runtime.dated_history_delta import changes,Fact,Removal,Counts,Occurrence,fields,supports_descriptor,_tables,FAMILIES,source_table,COMPLETE_REMARKS,family_enabled
from mta.runtime.dated_history_reader import FORMAT,Cut,table,read_cut,iter_occurrences,image_metadata
from mta.runtime.rationing_writer import _Digest
from mta.runtime.relational_state import copy_rows,db_value,quote,wire_type,wire_value
from mta.runtime.state_cut_models import OperationalStateCut
from mta.application.stage_observation import stage,summary


BATCH = 500


class _Shape:
    def __init__(self,rows,family):
        self.rows,self.family = rows,family
        self.order = ()
        self.kinds = {n:set() for n in fields(family)}
        self.count = 0

    def __iter__(self):
        for row in self.rows:
            if set(row) != self.kinds.keys():
                raise ValueError('History produced field roster differs')
            if not self.count:
                self.order = tuple(row)
            for name in self.kinds:
                if row[name] is not None:
                    self.kinds[name].add(wire_type(row[name]))
                    if len(self.kinds[name])>1:
                        raise ValueError('Mixed history wire types')
            self.count += 1
            yield row

    def descriptor(self):
        return [[n,n,next(iter(self.kinds[n]),'str')] for n in self.order]


def _flush(cut,events):
    relation = table(cut.family)
    columns = _tables()[source_table(cut.family)]
    facts = [e for e in events if type(e) is Fact]
    if facts:
        copy_rows(relation,['cut_id','vf_ordinal','initialization_id','born_position',*[n for n,_ in columns]],
            ((cut.pk,e.occurrence.ordinal,cut.initialization_id,cut.position,
              *[db_value(e.values[n],kind) for n,kind in columns]) for e in facts))
    removed = [e.occurrence for e in events if type(e) is Removal]
    if removed:
        with connection.cursor() as cursor:
            cursor.execute('UPDATE '+relation+' F SET end_position=%s,closing_cut_id=%s'
                ' FROM unnest(%s::bigint[],%s::bigint[]) AS X(position,ordinal)'
                ' WHERE F.initialization_id=%s AND F.born_position=X.position AND F.vf_ordinal=X.ordinal'
                ' AND F.end_position IS NULL',
                [cut.position,cut.pk,[o.position for o in removed],[o.ordinal for o in removed],cut.initialization_id])
            if cursor.rowcount != len(removed):
                raise ValueError('History closure did not affect its exact occurrence batch')


def stored_digests(cut,descriptor):
    checks = {k:_Digest() for k in ('facts','removals')}
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT vf_ordinal'+(' ,'+','.join(quote(n) for _,n,_ in descriptor) if descriptor else '')+
                       ' FROM '+table(cut.family)+' WHERE cut_id=%s ORDER BY vf_ordinal',[cut.pk])
        while batch := cursor.fetchmany(BATCH):
            for record in batch:
                if record[0] != checks['facts'].count:
                    raise ValueError('History fact ordinal differs')
                checks['facts'].add([record[0],{n:wire_value(v,kind) for (n,_,kind),v in zip(descriptor,record[1:])}])
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT born_position,vf_ordinal FROM '+table(cut.family)+
            ' WHERE closing_cut_id=%s ORDER BY born_position,vf_ordinal',[cut.pk])
        while batch := cursor.fetchmany(BATCH):
            for record in batch:
                checks['removals'].add(list(record))
    return checks


def _seal(cut,parent,descriptor,counts,checks,anchor=None):
    if not supports_descriptor(cut.family,descriptor,counts.closing):
        raise ValueError('Unqualified history descriptor')
    stored = stored_digests(cut,descriptor)
    if any((stored[k].count,stored[k].value()) != (v.count,v.value()) for k,v in checks.items()):
        raise ValueError('History persisted delta values/type/order differ')
    body = dict(format=FORMAT,cut=str(cut.pk),initialization=str(cut.initialization_id),family=cut.family,
        position=cut.position,run=str(cut.run_id) if cut.run_id else None,parent=str(cut.parent_id) if cut.parent_id else None,
        parent_root=parent.root_digest if parent else '0'*64,input_digest=cut.input_digest,settings_digest=cut.settings_digest,
        fields=descriptor,count=counts.closing,inserted=counts.inserted,removed=counts.removed,
        facts_digest=checks['facts'].value(),removals_digest=checks['removals'].value(),anchor=anchor)
    cut.root_body = b''.join(canonical_parts(body)).decode('utf8')
    cut.root_digest = digest(body)
    cut.save(update_fields=['root_body','root_digest'])
    summary('dated_history_delta_work',family=cut.family,logical_prior_rows=counts.prior,logical_closing_rows=counts.closing,
        inserted_facts=counts.inserted,removed_occurrences=counts.removed,
        canonical_delta_hash_bytes=sum(v.canonical_bytes for v in checks.values()),
        canonical_readback_hash_bytes=sum(v.canonical_bytes for v in stored.values()),root_bytes=len(cut.root_body.encode()))
    return image_metadata(Cut(cut.pk,cut.initialization_id,cut.run_id,cut.position,cut.root_digest,body))


@stage('dated_history_delta_write')
def write_delta(cut,parent,rows,*,today,horizon=None,unchanged=False):
    """Private adapter. Caller creates a guarded pending cut inside day commit.

    SQL independently checks capture/settings and predecessor binding. Runtime
    activation must derive horizon from that same frozen profile, not live state.
    This savepoint contains all writes, including late classification failures.
    """
    if not connection.in_atomic_block or cut.parent_id != parent.identity or cut.family != parent.body['family']:
        raise ValueError('History delta requires its owning day transaction and parent')
    with transaction.atomic():
        observed = _Shape(rows,cut.family)
        checks = {k:_Digest() for k in ('facts','removals')}
        batch = []
        counts = None
        with closing(iter_occurrences(parent)) as prior:
            with closing(changes(prior,observed,family=cut.family,today=today,position=cut.position,horizon=horizon,unchanged=unchanged)) as events:
                for event in events:
                    if type(event) is Counts:
                        counts = event
                        continue
                    if type(event) is Fact:
                        checks['facts'].add([event.occurrence.ordinal,event.values])
                    elif type(event) is Removal:
                        checks['removals'].add([event.occurrence.position,event.occurrence.ordinal])
                    else:
                        raise ValueError('Unknown history storage event')
                    batch.append(event)
                    if len(batch)==BATCH:
                        _flush(cut,batch)
                        batch=[]
        if counts is None or counts.prior != parent.body['count'] or counts.closing != observed.count or observed.count != len(rows):
            raise ValueError('History classification did not complete')
        if batch:
            _flush(cut,batch)
        return _seal(cut,parent,observed.descriptor(),counts,checks)


def seal_anchor_rows(cut,item,rows,anchor):
    """One-time exact old-image transport, inside existing initialization/upgrade."""
    if not connection.in_atomic_block or cut.position != 0 or not supports_descriptor(cut.family,item['fields'],item['count']):
        raise ValueError('History anchor requires a qualified image and owner transaction')
    with transaction.atomic():
        checks = {k:_Digest() for k in ('facts','removals')}
        source = _Digest()
        batch=[]
        for ordinal,row in enumerate(rows):
            source.add(row)
            checks['facts'].add([ordinal,row])
            batch.append(Fact(Occurrence(0,ordinal),row))
            if len(batch)==BATCH:
                _flush(cut,batch)
                batch=[]
        if batch:
            _flush(cut,batch)
        if source.count != item['count'] or source.value() != item['digest']:
            raise ValueError('History anchor source values/type/order/count differ')
        return _seal(cut,None,item['fields'],Counts(0,0,item['count'],0,item['count']),checks,anchor)


def opening_path(family):
    if family not in FAMILIES:
        raise ValueError('Unqualified dated history family')
    return 'input/opening/state/'+family.removeprefix('closing/')+'/values'


def begin_initial_anchors(owner, *, profile):
    """After opening storage, before its existing immutable initialization seal."""
    if not connection.in_atomic_block:
        raise ValueError('History anchors require the existing initialization transaction')
    if digest(profile)!=owner.configuration_digest:
        raise ValueError('History anchor profile differs from initialized configuration')
    cuts={}
    for family in FAMILIES:
        if not family_enabled(family,profile):continue
        item=owner.input_payload['images'].get(opening_path(family))
        if item is not None and supports_descriptor(family,item['fields'],item['count']):
            cuts[family]=OperationalStateCut.objects.create(initialization=owner,family=family,position=0,
                input_digest=owner.input_digest,settings_digest=owner.configuration_digest)
    return cuts


def seal_initial_anchors(cuts,owner):
    from mta.runtime.opening_storage import iter_image as opening_rows
    for family,cut in cuts.items():
        if cut.family!=family or cut.initialization_id!=owner.pk or cut.run_id is not None:
            raise ValueError('History opening anchor owner differs')
        item=owner.input_payload['images'][opening_path(family)]
        anchor=dict(owner_kind='INITIALIZATION',owner_id=str(owner.pk),manifest_digest=owner.input_manifest_digest,
            image=item['image'],digest=item['digest'],count=item['count'])
        with closing(opening_rows(owner,item)) as rows:
            seal_anchor_rows(cut,item,rows,anchor)


def write_day(run,family,rows):
    from mta.runtime.input_reader import read_execution_input
    frozen=read_execution_input(run,components=('profile','execution_settings','initialization_binding'))
    return write_frozen_day(run,family,rows,frozen=frozen,profile_digest=digest(frozen['profile']))


def write_frozen_day(run,family,rows,*,frozen,profile_digest):
    """Transport unchanged output using only this run's authenticated controls.

    Like the rationing adapter, finish_run supplies its once-decoded input and
    just-computed profile hash. SQL independently binds the cut to that capture.
    None is the explicit legacy codec disposition for an unqualified old source;
    a missing anchor for a qualified source is an error, never a daily backfill.
    """
    if family not in FAMILIES or not connection.in_atomic_block:
        raise ValueError('History requires its qualified owning day transaction')
    from mta.runtime.models import ProductionInitialization
    from mta.runtime.execution_settings import _check_snapshot_digest
    with transaction.atomic():
        owner=ProductionInitialization.objects.select_for_update().get(pk=frozen['initialization_binding']['id'])
        _check_snapshot_digest(owner,profile_digest,frozen.get('execution_settings'),run.business_date)
        if not family_enabled(family,frozen['profile']):
            raise ValueError('Disabled complete history has no terminal image')
        parent_row=OperationalStateCut.objects.filter(initialization=owner,family=family,run_id=run.predecessor_id).first()
        if parent_row is None:
            source=(run.predecessor.production_manifest['images'].get(family) if run.predecessor_id
                    else owner.input_payload['images'].get(opening_path(family)))
            if source is not None and 'storage_format' not in source and not supports_descriptor(family,source['fields'],source['count']):
                return None
            raise ValueError('Qualified history requires its initialized or adopted predecessor anchor')
        parent=read_cut(parent_row.pk)
        batch=frozen['profile']['delivery']['batch']
        horizon=batch['DailyConsumptionHorizonDBM'] if family=='closing/dbm/DailyConsumption' else None
        if family=='closing/bpr/DailyConsumption':
            from mta.application.daily_finalization import configuration
            finalization=configuration(frozen['profile'])
            horizon=finalization['consumption_days'] if finalization is not None else None
        if family in COMPLETE_REMARKS:
            from mta.application.daily_finalization import configuration
            horizon=configuration(frozen['profile'])['remark_days']
        unchanged=False
        if family=='closing/dbm/SuspendHistory':
            flag=batch['GatherSuspensionHistory']
            if type(flag) is not int:
                raise ValueError('Frozen suspension gathering control must be an integer')
            unchanged=flag!=1  # Exact existing producer predicate, not a new flag domain.
        cut=OperationalStateCut.objects.create(initialization=owner,family=family,position=parent.position+1,
            run=run,parent=parent_row,input_digest=run.input_digest,settings_digest=profile_digest)
        return write_delta(cut,parent,rows,today=run.business_date,horizon=horizon,unchanged=unchanged)
