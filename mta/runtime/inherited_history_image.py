"""A finite unchanged history projection from this run's own accepted opening.

The closing DBM SuggestionsLog has a different producer from the control carry.
Only that control carry may reference the predecessor (or initialization) cut.
Full typed ordered comparison remains at the writer; this removes payload copy,
not the outstanding producer/read/hash work. No current or pending cut is used.
"""
from copy import deepcopy
import hashlib
import re

from mta.row_sequences import RecordRows
from mta.serialization import canonical_parts

FORMAT='inherited-control-history-v1'
FAMILY='closing/dbm/SuggestionsLog'
TABLE='DBM/SuggestionsLog'
PATHS=frozenset(['closing/controls/suggestions_log']+[
    'phase/'+phase+'/controls/suggestions_log' for phase in ('PRE_BPR','BPR','DBM')])
KEYS=frozenset(('image','table','count','digest','fields','storage_format',
                'run_id','cut_id','cut_digest'))


def owns(item):
    return item.get('storage_format')==FORMAT


def _frozen(run):
    from mta.runtime.input_reader import read_input
    return read_input(run,components=('initialization_binding','lineage'))


def _owner(run,cut,frozen):
    binding=frozen.get('initialization_binding')
    if (not isinstance(binding,dict) or str(cut.initialization)!=binding.get('id')
            or cut.run!=run.predecessor_id or cut.body['family']!=FAMILY):
        raise ValueError('Inherited control history opening owner differs')
    if run.predecessor_id is not None:
        parent=run.predecessor
        lineage=frozen.get('lineage')
        if (parent.status!='SUCCEEDED' or not isinstance(lineage,dict)
                or lineage.get('run_id')!=str(parent.pk)
                or lineage.get('output_digest')!=parent.output_digest
                or cut.body['input_digest']!=parent.input_digest):
            raise ValueError('Inherited control history accepted predecessor differs')
    elif cut.position!=0:
        raise ValueError('Inherited control history initialization anchor differs')


def opening_cut(run,*,frozen=None):
    """None retains the old codec for nonnative or not-yet-adopted histories."""
    from mta.runtime.state_cut_models import OperationalStateCut
    from mta.runtime.dated_history_reader import read_cut
    frozen=_frozen(run) if frozen is None else frozen
    binding=frozen.get('initialization_binding')
    if binding is None:return None
    row=OperationalStateCut.objects.filter(initialization_id=binding['id'],
        family=FAMILY,run_id=run.predecessor_id)
    if run.predecessor_id is None:row=row.filter(position=0)
    identity=row.values_list('pk',flat=True).first()
    if identity is None:return None
    cut=read_cut(identity)
    _owner(run,cut,frozen)
    return cut


class ReferenceWriter:
    """One owning encode/write call; no cross-call cache or identity shortcut."""
    def __init__(self,run,*,frozen=None):
        self.run,self.frozen=run,frozen
        self.loaded=False
        self.cut=None
        self.description=None

    def __call__(self,path,table,description):
        if path not in PATHS or table!=TABLE:return None
        if not self.loaded:
            from mta.runtime import dated_history_reader as history,relational_state as typed
            self.cut=opening_cut(self.run,frozen=self.frozen)
            if self.cut is not None:
                rows=history.load_cut(self.cut)
                columns={n.casefold():(n,k) for n,k in typed.STORAGE_TABLES[TABLE]}
                self.description=typed.describe_rows(rows,columns,FAMILY)[0]
            self.loaded=True
        if self.cut is None:return None
        meta=description[0]
        if any(meta[k]!=self.description[k] for k in ('count','digest','fields')):
            return None
        return dict(deepcopy(meta),table=TABLE,storage_format=FORMAT,
            run_id=str(self.run.pk),cut_id=str(self.cut.identity),cut_digest=self.cut.root_digest)


def require_image(run,item):
    """Caller already authenticated the sealed manifest containing this item."""
    from mta.runtime.dated_history_reader import read_cut
    if (type(item) is not dict or set(item)!=KEYS or not owns(item)
            or item['image'] not in PATHS or item['table']!=TABLE
            or item['run_id']!=str(run.pk) or type(item['count']) is not int
            or item['count']<0 or type(item['digest']) is not str
            or re.fullmatch('[0-9a-f]{64}',item['digest']) is None):
        raise ValueError('Inherited control history descriptor differs')
    cut=read_cut(item['cut_id'])
    _owner(run,cut,_frozen(run))
    if (item['cut_digest']!=cut.root_digest or item['count']!=cut.body['count']
            or item['fields']!=cut.body['fields']):
        raise ValueError('Inherited control history cut identity differs')
    return cut


def iter_image(run,item,*,audit=False):
    yield from _iter_cut(require_image(run,item),item,audit=audit)


def _iter_cut(cut,item,*,audit):
    from mta.runtime import dated_history_reader as history
    if audit:
        from mta.runtime.dated_history_audit import audit_cut
        audit_cut(cut)
    checksum=hashlib.sha256(b'[') if audit else None
    count=0
    for _,row in history.iter_occurrences(cut):
        if checksum is not None:
            if count:checksum.update(b',')
            for part in canonical_parts(row):checksum.update(part)
        count+=1
        yield row
    if checksum is not None:
        checksum.update(b']')
        if count!=item['count'] or checksum.hexdigest()!=item['digest']:
            raise ValueError('Inherited control history typed content differs')


def load_image(run,item,*,audit=False):
    cut=require_image(run,item)
    item=deepcopy(item)
    def rows():return _iter_cut(cut,item,audit=audit)
    return RecordRows(item['count'],rows) if item['count']>10000 else list(rows())


def image_relation(run,item,*,required_fields=None):
    from mta.runtime import dated_history_reader as history
    from mta.runtime.relational_state import quote
    cut=require_image(run,item)
    names=None
    if required_fields is not None:
        by_column={column:name for name,column,_ in cut.body['fields']}
        if not set(required_fields)<=by_column.keys():
            raise ValueError('Unknown inherited history projection column')
        names=[by_column[c] for c in dict.fromkeys(required_fields)]
    sql,params,fields=history.occurrence_relation(cut,names)
    projection=''.join(','+quote(column) for _,column,_ in fields)
    return ('SELECT row_number() OVER (ORDER BY born_position,vf_ordinal)-1 AS vf_ordinal'+
            projection+' FROM ('+sql+') inherited_history'),params
