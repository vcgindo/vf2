"""Explicit physical verification, kept out of routine execution/serving reads.

Three ordered streams verify a selected prefix without per-cut payload queries
or full-history Python bags. Later valid closures do not alter an older cut.
"""
from contextlib import ExitStack,closing

from django.db import connection

from mta.runtime.dated_history_delta import fields
from mta.runtime.dated_history_reader import table,authenticate_cut,require_image,CUT_FIELDS
from mta.runtime.rationing_audit import _Hash,_Groups
from mta.runtime.relational_state import quote,wire_value
from mta.runtime.state_cut_models import OperationalStateCut


def _records(sql,cut):
    with connection.chunked_cursor() as cursor:
        cursor.execute(sql,[cut.initialization,cut.body['family'],cut.position])
        while batch:=cursor.fetchmany(500):
            yield from batch


def _lifetimes(cut):
    with connection.cursor() as cursor:
        cursor.execute('SELECT EXISTS(SELECT FROM '+table(cut.body['family'])+' F'
            ' JOIN mta.fresh_mta_operationalstatecut C ON C.id=F.cut_id'
            ' LEFT JOIN mta.fresh_mta_operationalstatecut Z ON Z.id=F.closing_cut_id'
            ' WHERE ((C.initialization_id=%s AND C.family=%s AND C.position<=%s) OR'
            ' (F.initialization_id=%s AND F.born_position<=%s)) AND ('
            ' F.initialization_id IS DISTINCT FROM C.initialization_id OR F.born_position IS DISTINCT FROM C.position'
            ' OR C.family<>%s OR (F.end_position IS NULL)<>(F.closing_cut_id IS NULL)'
            ' OR F.closing_cut_id IS NOT NULL AND ('
            ' F.end_position IS DISTINCT FROM Z.position OR Z.initialization_id IS DISTINCT FROM C.initialization_id'
            ' OR Z.family IS DISTINCT FROM C.family OR F.end_position<=C.position)))',
            [cut.initialization,cut.body['family'],cut.position,cut.initialization,cut.position,cut.body['family']])
        if cursor.fetchone()[0]:
            raise ValueError('History audit occurrence lifetime ownership differs')


def audit_cut(cut):
    family=cut.body['family'];columns=fields(family);relation=table(family)
    where=' WHERE C.initialization_id=%s AND C.family=%s AND C.position<=%s'
    facts=('SELECT C.position,F.vf_ordinal,'+','.join('F.'+quote(n) for n in columns)+
        ' FROM '+relation+' F JOIN mta.fresh_mta_operationalstatecut C ON C.id=F.cut_id'+where+
        ' ORDER BY C.position,F.vf_ordinal')
    removed=('SELECT C.position,F.born_position,F.vf_ordinal,F.initialization_id,F.end_position'
        ' FROM '+relation+' F JOIN mta.fresh_mta_operationalstatecut C ON C.id=F.closing_cut_id'+where+
        ' ORDER BY C.position,F.born_position,F.vf_ordinal')
    headers=OperationalStateCut.objects.filter(initialization_id=cut.initialization,family=family,
        position__lte=cut.position).order_by('position').values(*CUT_FIELDS).iterator(chunk_size=500)
    totals=dict(cuts=0,facts=0,removals=0);previous=None
    with ExitStack() as stack:
        stack.enter_context(closing(headers))
        streams={name:_Groups(stack.enter_context(closing(_records(sql,cut))))
                 for name,sql in (('facts',facts),('removals',removed))}
        for header in headers:
            current=authenticate_cut(header);body=current.body;position=totals['cuts']
            if (current.position!=position or body['parent']!=(str(previous.identity) if previous else None)
                    or body['parent_root']!=(previous.root_digest if previous else '0'*64)):
                raise ValueError('History audit prefix commitment chain differs')
            checks={name:_Hash() for name in streams};anchor=_Hash() if position==0 else None
            projection=[(n,k,columns.index(n)+2) for n,_,k in body['fields']]
            for record in streams['facts'].at(position):
                if record[1]!=checks['facts'].count:
                    raise ValueError('History audit fact order differs')
                row={n:wire_value(record[index],kind) for n,kind,index in projection}
                checks['facts'].add([record[1],row])
                if anchor is not None:anchor.add(row)
            last=None
            for record in streams['removals'].at(position):
                original=record[1:3]
                if (record[3]!=cut.initialization or record[4]!=position or not 0<=record[1]<position
                        or last is not None and original<=last):
                    raise ValueError('History audit removal ownership/order differs')
                checks['removals'].add(list(original));last=original
            for name,count_key in (('facts','inserted'),('removals','removed')):
                actual=checks[name]
                if actual.count!=body[count_key] or actual.finish()!=body[name+'_digest']:
                    raise ValueError('History audit '+name+' values/type/order differ')
                totals[name]+=actual.count
            if body['count']!=(previous.body['count'] if previous else 0)+body['inserted']-body['removed']:
                raise ValueError('History audit membership transition differs')
            if anchor is not None:
                source=body['anchor']
                if (not isinstance(source,dict) or source.get('count')!=anchor.count
                        or source.get('digest')!=anchor.finish() or body['removed']!=0):
                    raise ValueError('History audit anchor source values/type/order differ')
            elif body['anchor'] is not None:
                raise ValueError('History audit successor has unexpected anchor')
            previous=current;totals['cuts']+=1
        if previous!=cut or any(s.next is not None for s in streams.values()):
            raise ValueError('History audit did not reach the exact selected cut')
    _lifetimes(cut)
    return dict(totals,root_digest=cut.root_digest,count=cut.body['count'])


def audit_image(run,item):
    return audit_cut(require_image(run,item))
