"""Bounded SKU approved-input adapter; never executes or publishes a day.

Selection is one PostgreSQL statement over typed application rows. Its digest
identifies the exact source revision; callers cannot silently substitute a newer
revision. The consumer boundary is the SKU-only portion of NMSImportData.sql,
after construction of MasterDataRaw from the existing item inputs. Other family
processors, archive/clear/status processing and execute_day remain separate.
"""
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from decimal import Decimal
import hashlib
import json

from django.db import connection
from mta.mdm.sku import ALIASES
from mta.mdm.task_reads import sql_key
from mta.runtime.mdm_models import MdmSkuAttributes, MdmSkuDescription, MdmSkuApproved

SQL_DIGEST = 'c86d014b1f7ee921821f83936a53d1d4da566ba9b2558db9252853260c3c3801'
SKU_FIELDS = tuple(name for name in ALIASES.values() if name!='SKUCode')


@dataclass(frozen=True)
class SkuInputRevision:
    digest: str
    source_digest: str
    attributes: tuple
    descriptions: tuple
    approved: tuple


def select_revision(source, expected_digest=None):
    expressions=[]
    params=[]
    for label,model,columns,owner in (
        ('attributes',MdmSkuAttributes,[n for n in ALIASES.values() if n!='SKUDescription'],True),
        ('descriptions',MdmSkuDescription,['SKUCode','SKUDescription'],True),
        ('approved',MdmSkuApproved,[*ALIASES.values(),'ActionType','Approved','Reverted'],False)):
        table=connection.ops.quote_name(model._meta.db_table)
        selected=','.join(connection.ops.quote_name(n) for n in columns)
        where=" AND owner='Importer'" if owner else ''
        expressions.append("%s,(SELECT coalesce(json_agg(row_to_json(r)),'[]'::json) FROM (SELECT "+selected+
            ' FROM '+table+' WHERE source_id=%s'+where+' ORDER BY id) r)')
        params.extend([label,source.pk])
    with connection.cursor() as cursor:
        cursor.execute('SELECT json_build_object('+','.join(expressions)+')::text',params)
        raw=cursor.fetchone()[0]
    digest=hashlib.sha256((source.digest+'\n'+SQL_DIGEST+'\n'+raw).encode()).hexdigest()
    if expected_digest is not None and digest!=expected_digest:
        raise ValueError('approved SKU input revision changed')
    rows=json.loads(raw,parse_float=Decimal)
    return SkuInputRevision(digest,source.digest,*(tuple(MappingProxyType(row) for row in rows[name])
        for name in ('attributes','descriptions','approved')))


def unique_update(rows, code):
    matches=[row for row in rows if sql_key(row['SKUCode'])==sql_key(code)]
    if matches and any(row!=matches[0] for row in matches[1:]):
        raise ValueError('canonical SKU UPDATE has incomparable duplicate source values')
    return matches[0] if matches else None


def consumer_input(revision, master_rows, master_columns, *, nms_active):
    """Return SKU-transformed input occurrences, without mutating any owner.

The caller supplies the complete native MasterDataRaw columns and item rows.
New standalone SKU records have SQL NULL in every non-SKU column. Existing
location/item fields are preserved exactly. This function does not normalize,
validate or compute downstream master/calculation state.
"""
    result=deepcopy(list(master_rows))
    if not nms_active:
        return result
    def blank(): return dict.fromkeys(master_columns)
    codes={sql_key(row.get('SKUCode')) for row in result}
    additions=[]
    for description in revision.descriptions:
        if sql_key(description['SKUCode']) not in codes:
            row={**blank(),**description}
            if row not in additions: additions.append(row)
    result+=additions
    codes={sql_key(row.get('SKUCode')) for row in result}
    additions=[]
    for staged in revision.approved:
        if staged['Approved'] and staged['ActionType']==1 and sql_key(staged['SKUCode']) not in codes:
            # Canonical standalone insert omits c1..15; the later overlay fills them.
            row={**blank(),**{k:staged[k] for k in ('SKUCode','SKUDescription','ElephantOrderCapping','Weight','Volume',*('SL'+str(i) for i in range(1,6)))}}
            if row not in additions: additions.append(row)
    result+=additions
    deleted={sql_key(row['SKUCode']) for row in revision.approved if row['Approved'] and row['ActionType']==0}
    result=[row for row in result if row.get('SKUCode') is None or sql_key(row['SKUCode']) not in deleted]
    overlay=[row for row in revision.approved if row['Approved'] and row['ActionType']==1]
    for row in result:
        code=row.get('SKUCode')
        if code is None: continue  # SQL NULL never joins NULL.
        attr=unique_update(revision.attributes,code)
        description=unique_update(revision.descriptions,code)
        approved=unique_update(overlay,code)
        for name in SKU_FIELDS:
            target='SKUAtt'+name[1:].zfill(2) if name.startswith('c') else name
            if approved is not None:
                row[target]=approved[name]
            elif name=='SKUDescription':
                row[target]=description[name] if description is not None else None
            elif attr is not None:
                row[target]=attr[name]
            elif name.startswith('c'):
                row[target]=None
    return result
