"""Bounded master-3 approved-input adapter for pinned NMSImportData.sql."""
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
import hashlib
import json

from django.db import connection

from mta.mdm.task_reads import sql_key
from mta.runtime.mdm_skuloc_models import (MdmSkuLocAddApproved,
    MdmSkuLocModifyApproved, MdmSkuLocPair, MdmSkuLocRemoveApproved)

SQL_DIGEST='c86d014b1f7ee921821f83936a53d1d4da566ba9b2558db9252853260c3c3801'
ATTRIBUTES=('PackSize','SpikeThreshold','PSOThreshold','FGRMFlag',
    'StockPercentForRationing','NormPercentReservation',*('c%d'%i for i in range(1,16)))
ADD_FIELDS=('SKUCode','WhCode','ParentWhCode','Norm','MinNorm','RLT','RCP','GCP','OCP',
    'PackSize','SpikeThreshold','PSOThreshold','FGRMFlag','DBMActive','StockPercentForRat',
    'NormPercentReservation','MinOrderCount',*('SKULocAtt%02d'%i for i in range(1,16)),'Approved')
MODIFY_FIELDS=tuple(name for name in ADD_FIELDS if name not in ('Norm','DBMActive'))
REMOVE_FIELDS=('SKUCode','WhCode','Approved')


@dataclass(frozen=True)
class SkuLocInputRevision:
    digest:str
    source_digest:str
    attributes:tuple
    additions:tuple
    modifications:tuple
    removals:tuple


def select_revision(source,expected_digest=None):
    expressions=[];params=[]
    for label,model,columns,owner in (
        ('attributes',MdmSkuLocPair,('SKUCode','LocCode',*ATTRIBUTES),True),
        ('additions',MdmSkuLocAddApproved,ADD_FIELDS,False),
        ('modifications',MdmSkuLocModifyApproved,MODIFY_FIELDS,False),
        ('removals',MdmSkuLocRemoveApproved,REMOVE_FIELDS,False)):
        table=connection.ops.quote_name(model._meta.db_table)
        selected=','.join(connection.ops.quote_name(name) for name in columns)
        where=" AND owner='Importer'" if owner else ''
        expressions.append("%s,(SELECT coalesce(json_agg(row_to_json(r)),'[]'::json) FROM (SELECT "+selected+
            ' FROM '+table+' WHERE source_id=%s'+where+' ORDER BY id) r)')
        params.extend([label,source.pk])
    with connection.cursor() as cursor:
        cursor.execute('SELECT json_build_object('+','.join(expressions)+')::text',params)
        raw=cursor.fetchone()[0]
    digest=hashlib.sha256((source.digest+'\n'+SQL_DIGEST+'\n'+raw).encode()).hexdigest()
    if expected_digest is not None and digest!=expected_digest:
        raise ValueError('approved SKU-location input revision changed')
    rows=json.loads(raw,parse_float=Decimal)
    return SkuLocInputRevision(digest,source.digest,*(tuple(MappingProxyType(row) for row in rows[name])
        for name in ('attributes','additions','modifications','removals')))


def _pair(row,wh='WhCode'):
    return sql_key(row.get('SKUCode')),sql_key(row.get(wh))


def _unique(rows,pair,wh='WhCode'):
    matches=[row for row in rows if _pair(row,wh)==pair]
    if matches and any(row!=matches[0] for row in matches[1:]):
        raise ValueError('canonical SKU-location UPDATE has incomparable duplicate source values')
    return matches[0] if matches else None


def consumer_input(revision,master_rows,master_columns,*,nms_active,last_run_date):
    """Apply only master-3 add/remove/attribute/modify statements to raw rows."""
    result=deepcopy(list(master_rows))
    if not nms_active:return result
    def blank():return dict.fromkeys(master_columns)
    existing={_pair(row) for row in result}
    additions=[row for row in revision.additions if row['Approved'] and _pair(row) not in existing]
    for staged in additions:
        row=blank()
        for name in ('SKUCode','WhCode','Norm','MinNorm','RLT','RCP','GCP','OCP','ParentWhCode',
                     'PackSize','SpikeThreshold','PSOThreshold','FGRMFlag','NormPercentReservation','MinOrderCount'):
            row[name]=staged[name]
        row['SKUIntroDate']=last_run_date
        row['StockPercentForRationing']=staged['StockPercentForRat']
        result.append(row)
    removed={_pair(row) for row in revision.removals if row['Approved']}
    result=[row for row in result if _pair(row) not in removed]
    core=('ParentWhCode','MinNorm','RLT','RCP','GCP','OCP','MinOrderCount')
    by_pair={}
    for row in result:
        pair=_pair(row)
        if None in pair:continue
        values=tuple(row.get(name) for name in core)
        if pair in by_pair and by_pair[pair]!=values:
            raise ValueError('canonical SKULocMaster DISTINCT join is incomparable')
        by_pair[pair]=values
    approved_add=[row for row in additions]
    approved_modify=[row for row in revision.modifications if row['Approved']]
    for row in result:
        pair=_pair(row)
        attr=_unique(revision.attributes,pair,'LocCode')
        added=_unique(approved_add,pair)
        # Existing attributes populate SKULocMaster first; approved additions
        # then overwrite the same fields from NMSData.
        if attr is not None:
            row['PackSize']=attr['PackSize'];row['SpikeThreshold']=attr['SpikeThreshold']
            row['PSOThreshold']=attr['PSOThreshold'];row['FGRMFlag']=attr['FGRMFlag']
            row['StockPercentForRationing']=attr['StockPercentForRationing']
            row['NormPercentReservation']=attr['NormPercentReservation']
            for i in range(1,16):row['SKULocAtt%02d'%i]=attr['c%d'%i]
        if added is not None:
            for name in ('PackSize','SpikeThreshold','PSOThreshold','FGRMFlag','NormPercentReservation',
                         *('SKULocAtt%02d'%i for i in range(1,16))):row[name]=added[name]
            row['StockPercentForRationing']=added['StockPercentForRat']
        modified=_unique(approved_modify,pair)
        if modified is not None:
            for name in ('ParentWhCode','MinNorm','RLT','RCP','GCP','PackSize','FGRMFlag',
                         'NormPercentReservation','MinOrderCount','OCP',
                         *('SKULocAtt%02d'%i for i in range(1,16))):
                if modified[name] is not None:row[name]=modified[name]
            # Canonical statements deliberately clear these on NULL.
            row['SpikeThreshold']=modified['SpikeThreshold']
            row['PSOThreshold']=modified['PSOThreshold']
            if modified['StockPercentForRat'] is not None:
                row['StockPercentForRationing']=modified['StockPercentForRat']
    return result
