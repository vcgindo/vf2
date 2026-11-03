"""Relational reconstruction of the operational BTR import in producer order.

The caller owns validation of the source run ids, per-day source counts and
the surviving anchor count. This relation does not select or admit a run.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from mta.domain.btr_finalization import BPR_SOURCE_FIELDS
from mta.runtime.relational_state import quote, table_sql


HISTORY = 'closing/btr/BPR'
DAILY = 'reports/bpr/vf_RationedReqReport'


@dataclass(frozen=True)
class ImportBlock:
    owner: UUID
    day: date
    count: int


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
