"""Relational reconstruction of the operational BTR import in producer order.

The caller owns validation of the source run ids, per-day source counts and
the surviving anchor count. This relation does not select or admit a run.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from django.db import connection
from mta.domain.btr_finalization import BPR_SOURCE_FIELDS
from mta.runtime.relational_state import quote, table_sql


HISTORY = 'closing/btr/BPR'
DAILY = 'reports/bpr/vf_RationedReqReport'
FORMAT = 'btr-daily-imports-v1'


@dataclass(frozen=True)
class ImportBlock:
    owner: UUID
    day: date
    count: int


def _source(run, item, path):
    table = 'BTR/BPR' if path==HISTORY else 'BPR/vf_RationedReqReport'
    if (item.get('image')!=path or item.get('table')!=table or type(item.get('count')) is not int
            or item['count']<0 or not isinstance(item.get('digest'),str) or len(item['digest'])!=64):
        raise ValueError('Expected the original BTR import source identity')
    return dict(owner=str(run.pk), day=run.business_date.isoformat(), count=item['count'], digest=item['digest'])


def advance(run, parent, current_image):
    """Advance the accepted parent's directory using only newly excluded anchor dates.

    For a physical predecessor its entire ordered history is the initial anchor.
    A future-dated anchor record can outlive the anchor's own business date by
    more than 90 days. Drop the anchor only when its surviving count is zero.
    The final database seal must independently check these supplied bindings.
    """
    if (not connection.in_atomic_block or run.predecessor_id!=parent.pk or parent.status!='SUCCEEDED'
            or parent.production_manifest.get('version')!=3 or parent.business_date>=run.business_date):
        raise ValueError('BTR import requires the accepted earlier predecessor in its owning transaction')
    prior = parent.production_manifest['images'][HISTORY]
    if 'storage_format' not in prior:
        anchor, days = _source(parent, prior, HISTORY), []
    elif prior['storage_format']==FORMAT:
        anchor, days = prior['sources']['anchor'], prior['sources']['daily']
    else:
        raise ValueError('Unrecognised predecessor BTR import format')
    old_cutoff, cutoff = parent.business_date-timedelta(days=90), run.business_date-timedelta(days=90)
    if anchor:
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM '+table_sql('BTR/BPR')+
                           ' WHERE vf_run_id=%s AND vf_image=%s AND ("ReportDate"=%s OR '
                           '("ReportDate">%s AND "ReportDate"<=%s AND NOT ("ReportDate"=ANY(%s::date[]))))',
                           [anchor['owner'],HISTORY,run.business_date,old_cutoff,cutoff,[b['day'] for b in days]])
            left = anchor['count']-cursor.fetchone()[0]
        if left<0:
            raise ValueError('BTR physical anchor population drift')
        anchor = dict(anchor,count=left) if left else None
    retained = [block for block in days if block['day']>cutoff.isoformat()]
    return dict(anchor=anchor,daily=[*retained,_source(run,current_image,DAILY)])


def source_query(run, sources):
    def block(value):
        return ImportBlock(UUID(value['owner']), date.fromisoformat(value['day']),value['count'])
    anchor = sources['anchor']
    return query(run,anchor=block(anchor) if anchor else None,blocks=[block(b) for b in sources['daily']])


def query(run, *, anchor, blocks):
    """Anchor rows retain their relative order. New rows retain native ordinals.

    A date supplied again displaces that date in the physical anchor. The
    original import retains future-dated anchor rows until supplied or expired.
    Only the optional anchor requires renumbering after its exclusions.
    """
    earlier = run.business_date - timedelta(days=90)
    if len(blocks)>90 or anchor is None and not blocks:
        raise ValueError('Missing or oversized BTR import window')
    owners = set()
    if anchor is not None:
        if (type(anchor.count) is not int or anchor.count<0 or not isinstance(anchor.owner, UUID)
                or type(anchor.day) is not date or anchor.day>run.business_date):
            raise ValueError('Invalid BTR import anchor')
        owners.add(anchor.owner)
    offset = anchor.count if anchor is not None else 0
    previous = max(earlier, anchor.day) if anchor else earlier
    offsets = []
    for block in blocks:
        if (type(block.day) is not date or not previous < block.day <= run.business_date
                or not isinstance(block.owner, UUID) or block.owner in owners
                or type(block.count) is not int or block.count<0):
            raise ValueError('Invalid BTR daily source sequence')
        offsets.append(offset)
        offset += block.count
        previous = block.day
        owners.add(block.owner)
    current = blocks[-1] if blocks else anchor
    if current.day != run.business_date or current.owner != run.pk:
        raise ValueError('BTR import window must end with its owning day')

    pieces, params = [], []
    days = [block.day for block in blocks]
    projected = [field if field != 'WhCode' else 'WHCode' for field in BPR_SOURCE_FIELDS]
    if anchor is not None and anchor.count:
        fields = ','.join('a.'+quote(field) for field in (*projected,'ReportDate'))
        pieces.append('SELECT row_number() OVER (ORDER BY a.vf_ordinal)-1 AS vf_ordinal,'+fields+
                      ' FROM '+table_sql('BTR/BPR')+' a WHERE a.vf_run_id=%s AND a.vf_image=%s'+
                      ' AND a."ReportDate">%s AND NOT (a."ReportDate"=ANY(%s::date[]))')
        params.extend((anchor.owner,HISTORY,earlier,days))
    if blocks:
        fields = ','.join('a.'+quote(field)+' AS '+quote(target)
                          for field,target in zip(BPR_SOURCE_FIELDS, projected, strict=True))
        pieces.append('SELECT d.base+a.vf_ordinal AS vf_ordinal,'+fields+',d.day AS "ReportDate" '+
                      'FROM unnest(%s::uuid[],%s::date[],%s::bigint[]) d(owner,day,base) JOIN '+
                      table_sql('BPR/vf_RationedReqReport')+' a ON a.vf_run_id=d.owner AND a.vf_image=%s')
        params.extend(([block.owner for block in blocks],days,offsets,DAILY))
    if not pieces:
        # Cold empty anchor retains the declared native component types.
        fields = ','.join(quote(field) for field in (*projected,'ReportDate'))
        pieces.append('SELECT vf_ordinal,'+fields+' FROM '+table_sql('BTR/BPR')+' WHERE FALSE')
    return ('SELECT %s::uuid AS vf_run_id,%s::text AS vf_image,b.* FROM ('+
            ' UNION ALL '.join(pieces)+') b', [run.pk,HISTORY,*params])
