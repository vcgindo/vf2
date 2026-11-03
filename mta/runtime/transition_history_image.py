"""Finite phase history overlays on the run's own accepted opening.

Only current additions and actual removed opening ordinals are staged. The
sealed phase owns those typed rows; terminal history cuts retain their existing
successful-run transaction. Full typed ordered comparison remains at writing.
"""
from contextlib import closing
from copy import deepcopy
from itertools import islice
from django.db import connection
from mta.row_sequences import RecordRows
from mta.runtime import relational_state as typed
from mta.runtime.dated_history_delta import SORTED_IMPORTER

FORMAT = 'phase-history-transition-v1'
PROJECTION = 'terminal-history-projection-v1'
FAMILIES = ('closing/importer/RejectedMaster','closing/importer/RetiredNormsTbl',
            'closing/dbm/NormChangeLogTbl')
DBM_CARRIES = ('DailyConsumption', 'OrderData', 'SuspendHistory', 'SpikeReport')
DBM_CARRY_FAMILIES = frozenset('closing/dbm/'+name for name in DBM_CARRIES)
PHASE_FAMILIES = frozenset(FAMILIES) | DBM_CARRY_FAMILIES
BASE = frozenset(('image','table','count','digest','fields','storage_format',
                  'run_id','family','cut_id','cut_digest'))
KEYS = BASE | {'sorted_prefix','additions','changes'}


def family(path):
    parts=path.split('/')
    if parts[:1]==['phase'] and len(parts)>=4:
        if parts[1] not in ('PRE_BPR','BPR','DBM'):return None
        suffix='/'.join(parts[2:])
    else:suffix=path.removeprefix('closing/')
    if suffix=='controls/log':return FAMILIES[2]
    if suffix.startswith('report-facts/'):
        from mta.runtime.relational_state import REPORT_STAGES
        pieces=suffix.split('/')
        if len(pieces)!=3 or pieces[1] not in REPORT_STAGES:return None
        suffix='dbm/'+pieces[2]
    result='closing/'+suffix
    if parts[:2]==['phase','DBM'] and result in DBM_CARRY_FAMILIES:
        return result
    return result if result in FAMILIES else None


def owns(item):return item.get('storage_format') in (FORMAT,PROJECTION)


def _projection(rows,description):
    # Logical control spelling is retained while physical DBM columns stay exact.
    for row in rows:
        yield {name:row[column] for name,column,_ in description['fields']}


def _opening(run,name,frozen=None):
    from mta.runtime.input_reader import read_input
    from mta.runtime.state_cut_models import OperationalStateCut
    from mta.runtime.dated_history_reader import read_cut
    if frozen is None:
        frozen=read_input(run,components=('initialization_binding','lineage'))
    binding=frozen.get('initialization_binding')
    if binding is None:return None
    cut=OperationalStateCut.objects.filter(initialization_id=binding['id'],family=name,run_id=run.predecessor_id).first()
    if cut is None:
        if name not in FAMILIES:return None  # An unqualified legacy source keeps its original image.
        raise ValueError('History transition requires its adopted opening cut')
    accepted=read_cut(cut.pk)
    _owner(run,accepted,frozen)
    return accepted


def _owner(run,cut,frozen=None,terminal=False):
    from mta.runtime.input_reader import read_input
    frozen=read_input(run,components=('initialization_binding','lineage')) if frozen is None else frozen
    binding=frozen.get('initialization_binding')
    if (not isinstance(binding,dict) or str(cut.initialization)!=binding.get('id')
            or cut.body['family'] not in (FAMILIES if terminal else PHASE_FAMILIES)
            or cut.run!=(run.pk if terminal else run.predecessor_id)):
        raise ValueError('History transition opening ownership differs')
    if not terminal and run.predecessor_id:
        lineage=frozen.get('lineage')
        if (run.predecessor.status!='SUCCEEDED' or not isinstance(lineage,dict)
                or lineage.get('run_id')!=str(run.predecessor_id)
                or lineage.get('output_digest')!=run.predecessor.output_digest
                or cut.body['input_digest']!=run.predecessor.input_digest):
            raise ValueError('History transition predecessor acceptance differs')


class ReferenceWriter:
    def __init__(self,run,transitions):
        self.run,self.transitions=run,transitions
        self.openings={}

    def prepare_dbm(self,phase):
        from dataclasses import replace
        from mta.runtime.input_reader import read_input
        from mta.runtime.dated_history_delta import Counts, Fact, changes
        from mta.runtime.dated_history_reader import iter_occurrences

        if self.transitions is None:return phase
        frozen=read_input(self.run,components=('initialization_binding','lineage'))
        batch=phase.context.profile['delivery']['batch']
        transitions=dict(self.transitions)
        for name in DBM_CARRIES:
            if name not in phase.final_dbm:continue
            family='closing/dbm/'+name
            cut=self.openings[family]=_opening(self.run,family,frozen)
            if cut is None:continue
            ordinal=-1
            def opening_rows():
                nonlocal ordinal
                with closing(iter_occurrences(cut)) as rows:
                    for ordinal, occurrence in enumerate(rows):
                        yield occurrence
            additions,removed=[],[]
            horizon=batch['DailyConsumptionHorizonDBM'] if name=='DailyConsumption' else None
            unchanged=False
            if name=='SuspendHistory':
                flag=batch['GatherSuspensionHistory']
                if type(flag) is not int:
                    raise ValueError('Frozen suspension gathering control must be an integer')
                unchanged=flag!=1
            with closing(opening_rows()) as rows:
                for event in changes(rows,phase.final_dbm[name],family=family,
                                     today=self.run.business_date,position=cut.position+1,
                                     horizon=horizon,unchanged=unchanged):
                    if isinstance(event,Fact):additions.append(event.values)
                    elif isinstance(event,Counts):
                        if event.prior!=cut.body['count']:
                            raise ValueError('History transition opening count differs')
                    else:removed.append(ordinal)
            transitions[family]=dict(opening_count=cut.body['count'],additions=additions,
                                     removed=removed,sorted_prefix=None)
        self.transitions=transitions
        return replace(phase,context=replace(phase.context,history_changes=transitions))

    def __call__(self,path,table,description,images):
        name=family(path)
        if name is None or self.transitions is None or name not in self.transitions:return None
        from mta.runtime.dated_history_reader import load_cut
        from mta.runtime.dated_history_delta import transition_rows,source_table
        if table!=source_table(name):raise ValueError('History transition table differs')
        if name not in self.openings:self.openings[name]=_opening(self.run,name)
        cut=self.openings[name]
        if cut is None:return None
        change=self.transitions[name]
        prefix='phase/'+path.split('/')[1]
        suffix=name.removeprefix('closing/')
        additions=images[prefix+'/history-additions/'+suffix]
        changes=images[prefix+'/history-changes/'+suffix]
        columns={n.casefold():(n,k) for n,k in typed.STORAGE_TABLES[table]}
        def reconstructed():
            prior=load_cut(cut)
            if name in FAMILIES:
                yield from transition_rows(prior,change,name)
            else:
                removed=set(change['removed'])
                yield from (row for ordinal,row in enumerate(prior) if ordinal not in removed)
                yield from change['additions']
        rows=RecordRows(cut.body['count']-len(change['removed'])+len(change['additions']),
            lambda:_projection(reconstructed(),description[0]))
        actual=typed.describe_rows(rows,columns,path)[0]
        if actual!=description[0]:raise ValueError('History transition differs from complete produced image')
        return dict(deepcopy(description[0]),table=table,storage_format=FORMAT,
            run_id=str(self.run.pk),family=name,cut_id=str(cut.identity),cut_digest=cut.root_digest,
            sorted_prefix=change['sorted_prefix'],additions=additions,changes=changes)


def require_image(run,item):
    from mta.runtime.dated_history_reader import read_cut,source_table
    terminal=item.get('storage_format')==PROJECTION
    if (type(item) is not dict or set(item)!=(BASE if terminal else KEYS)
            or not owns(item) or item['run_id']!=str(run.pk)
            or family(item['image'])!=item['family'] or item['table']!=source_table(item['family'])):
        raise ValueError('History transition descriptor differs')
    cut=read_cut(item['cut_id'])
    _owner(run,cut,terminal=terminal)
    if cut.body['family']!=item['family'] or cut.root_digest!=item['cut_digest']:
        raise ValueError('History transition cut commitment differs')
    if terminal:
        if item['count']!=cut.body['count']:raise ValueError('History projection count differs')
        return cut
    for label,table in (('additions',item['table']),('changes','phase/HistoryChange')):
        part=item[label]
        suffix=item['family'].removeprefix('closing/')
        namespace='history-additions' if label=='additions' else 'history-changes'
        if (type(part) is not dict or set(part)!={'image','table','count','digest','fields'}
                or part['table']!=table or part['image'].split('/')[1] not in ('PRE_BPR','BPR','DBM')
                or part['image']!='phase/'+part['image'].split('/')[1]+'/'+namespace+'/'+suffix):
            raise ValueError('History transition typed staging owner differs')
    n=item['sorted_prefix']
    if (item['family'] not in SORTED_IMPORTER and n is not None or item['family'] in SORTED_IMPORTER
            and (type(n) is not int or not 0<=n<=item['additions']['count'])):
        raise ValueError('History transition sort boundary differs')
    return cut


def _raw(run,item):
    fields=item['fields']
    columns=','.join(typed.quote(column) for _,column,_ in fields)
    return ('SELECT vf_ordinal'+(','+columns if columns else '')+' FROM '+typed.table_sql(item['table'])+
        ' WHERE vf_run_id=%s AND vf_image=%s'),[run.pk,item['image']]


def image_relation(run,item,*,required_fields=None):
    from mta.runtime import dated_history_reader as history
    cut=require_image(run,item)
    fields=item['fields']
    if required_fields is not None:
        requested=set(required_fields)
        if not requested<=set(d[1] for d in fields):raise ValueError('Unknown history transition column')
        fields=[d for d in fields if d[1] in requested]
    # Include all canonical columns for a common physical union, project last.
    prior,params,canonical=history.occurrence_relation(cut)
    column_names=[column for _,column,_ in canonical]
    names=','.join(typed.quote(n) for n in column_names)
    order=history.occurrence_order(cut)
    sorted_importer=item['family'] in SORTED_IMPORTER
    prior='SELECT row_number() OVER (ORDER BY '+order+')-1 AS opening_ordinal,'+names+        (',history_sort_key' if sorted_importer else '')+' FROM ('+prior+') opening'
    projection=','.join(typed.quote(column) for _,column,_ in fields)
    # Empty predecessor descriptors have no scalar columns. Typed NULLs use
    # the existing physical table's columns even when the image is empty.
    if not column_names:
        columns=typed.STORAGE_TABLES[item['table']]
        names=','.join(typed.quote(n) for n,_ in columns)
        prior='SELECT vf_ordinal AS opening_ordinal,'+names+            (',NULL::text AS history_sort_key' if sorted_importer else '')+            ' FROM '+typed.table_sql(item['table'])+' WHERE false'
        params=[]
    if item['storage_format']==PROJECTION:
        return 'SELECT opening_ordinal AS vf_ordinal'+(','+projection if projection else '')+' FROM ('+prior+') projected',params
    additions,ap=_raw(run,item['additions']);changes,cp=_raw(run,item['changes'])
    if item['additions']['count']==0:
        additions='SELECT vf_ordinal,'+names+' FROM '+typed.table_sql(item['table'])+' WHERE false';ap=[]
    if item['changes']['count']==0:
        changes='SELECT vf_ordinal,"OpeningOrdinal","AdditionOrdinal","SortKey" FROM mta_state.phase_historychange WHERE false';cp=[]
    if not sorted_importer:
        body=('SELECT 0 AS part,P.opening_ordinal AS ord,'+','.join('P.'+typed.quote(n) for n in (column_names or [n for n,_ in typed.STORAGE_TABLES[item['table']]]))+
            ' FROM prior P WHERE NOT EXISTS (SELECT 1 FROM changes C WHERE C."OpeningOrdinal"=P.opening_ordinal) UNION ALL SELECT 1,A.vf_ordinal,'+names+' FROM additions A')
        ordering='part,ord'
    else:
        body=('SELECT 0 AS part,history_sort_key AS sort_key,0 AS origin,opening_ordinal AS ord,'+names+
            ' FROM prior UNION ALL SELECT CASE WHEN A.vf_ordinal<%s THEN 0 ELSE 1 END,C."SortKey",1,A.vf_ordinal,'+
            ','.join('A.'+typed.quote(n) for n in (column_names or [n for n,_ in typed.STORAGE_TABLES[item['table']]]))+
            ' FROM additions A JOIN changes C ON C."AdditionOrdinal"=A.vf_ordinal')
        ordering='part,CASE WHEN part=0 THEN sort_key END COLLATE "C",origin,ord'
    sql='WITH prior AS ('+prior+'), additions AS ('+additions+'), changes AS ('+changes+') SELECT row_number() OVER (ORDER BY '+ordering+')-1 AS vf_ordinal'+(','+projection if projection else '')+' FROM ('+body+') history'
    return sql,params+ap+cp+([item['sorted_prefix']] if sorted_importer else [])


def iter_image(run,item,*,audit=False):
    from mta.serialization import canonical_parts
    import hashlib
    if audit:
        from mta.runtime.dated_history_audit import audit_cut
        from mta.runtime.phase_state_schema import TABLES
        cut=require_image(run,item);audit_cut(cut)
        if item['storage_format']==FORMAT:
            for part in ('additions','changes'):
                for _ in typed.iter_image(run,item[part],table_registry={**typed.STORAGE_TABLES,**TABLES}):pass
    sql,params=image_relation(run,item)
    checksum=hashlib.sha256(b'[');count=0
    with connection.chunked_cursor() as cursor:
        cursor.execute(sql+' ORDER BY vf_ordinal',params)
        while batch:=cursor.fetchmany(500):
            for record in batch:
                if record[0]!=count:raise ValueError('History transition logical order differs')
                row={name:typed.wire_value(v,kind) for (name,_,kind),v in zip(item['fields'],record[1:])}
                if audit:
                    if count:checksum.update(b',')
                    for part in canonical_parts(row):checksum.update(part)
                count+=1;yield row
    if count!=item['count']:raise ValueError('History transition count differs')
    if audit:
        checksum.update(b']')
        if checksum.hexdigest()!=item['digest']:raise ValueError('History transition typed content differs')


def load_image(run,item,*,audit=False):
    def rows():return iter_image(run,item,audit=audit)
    return RecordRows(item['count'],rows) if item['count']>10000 else list(rows())


def terminal_projection(run,path,table,rows,cut):
    from mta.runtime.dated_history_reader import load_cut
    columns={n.casefold():(n,k) for n,k in typed.STORAGE_TABLES[table]}
    description=typed.describe_rows(rows,columns,path)[0]
    check=RecordRows(cut.body['count'],lambda:_projection(load_cut(cut),description))
    if typed.describe_rows(check,columns,path)[0]!=description:
        raise ValueError('Terminal history alias differs from canonical owner')
    return dict(description,table=table,storage_format=PROJECTION,run_id=str(run.pk),
        family=cut.body['family'],cut_id=str(cut.identity),cut_digest=cut.root_digest)
