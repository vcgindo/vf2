"""Authenticated BOR append/history overlay, separate from immutable snapshot rows."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import connection,transaction,DatabaseError
from mta.presentation.bor_sources import admitted_sources
from mta.presentation.bor_sql import remark_query
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr_sql import equal
from mta.runtime.models import BorLiveRemark


def _literal(value, *, nullable=False):
    if value is None and nullable: return ''
    if not isinstance(value,str): raise ValueError('native string dictionary required')
    if "'" in value:
        raise PublicationUnavailable('LEG-BOR-UNESCAPED-LITERAL: NOT_PARITY')
    return value


def append(payload,actor):
    run,_=admitted_sources()
    rows=payload.get('data')
    if not isinstance(rows,list) or not rows or not isinstance(rows[0],dict):
        raise ValueError('native BOR batch invalid')
    username=_literal(actor['name'])
    keys=list(rows[0])
    # The deployed method builds columns from the first dictionary. Missing values
    # fail construction (500); invalid column names fail PostQuery (empty/200).
    for row in rows:
        if not isinstance(row,dict): raise ValueError('native BOR row invalid')
        for k in keys: _literal(row[k])
    columns=[k.replace('skucode','SKUCode').replace('whcode','WhCode')
             .replace('remark','Remark').replace('spc','SupplierCode').casefold() for k in keys]
    if (len(set(columns))!=len(columns) or not {'skucode','whcode','suppliercode'}<=set(columns)
            or set(columns)-{'skucode','whcode','suppliercode','remark'} or len(username)>100):
        return ''
    values=[{column:_literal(row[k]) for column,k in zip(columns,keys)} for row in rows]
    if any(len(row[k])>50 for row in values for k in ('skucode','whcode','suppliercode')):
        return ''
    # getValues concatenates DateTime.Now using the culture's general format:
    # the resulting SQL literal has whole-second precision. Store wall time in
    # UTC-labelled rows so wire history retains that legacy naive timestamp.
    now=datetime.now(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).replace(microsecond=0,tzinfo=timezone.utc)
    try:
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute("SELECT set_config('fresh.bor_actor',%s,true)",[str(actor['id'])])
            BorLiveRemark.objects.bulk_create([BorLiveRemark(run=run,actor_id=str(actor['id']),
                SKUCode=row['skucode'],WhCode=row['whcode'],SupplierCode=row['suppliercode'],
                Remark=row.get('remark'),Username=username,RemarkDate=now) for row in values])
    except DatabaseError:
        # Deployed GenericFunction.PostQuery catches provider failures and returns
        # empty string; AddBORRemark's OR check still emits status200.
        return ''
    return str(len(rows))


def history(payload):
    run,_=admitted_sources()
    values=[_literal(payload.get(n),nullable=True) for n in ('skucode','whcode','spc')]
    sql,params=remark_query(run)
    sql='SELECT "Remark","RemarkDate","Username" FROM ('+sql+') M WHERE '+ ' AND '.join(
        equal('M."'+n+'"','%s') for n in ('SKUCode','WhCode','SupplierCode'))+' ORDER BY "RemarkDate" DESC'
    with connection.cursor() as c:
        c.execute(sql,[*params,*values]);rows=c.fetchall()
    return [{k:v for k,v in dict(r=remark,rd=stamp.astimezone(timezone.utc).replace(tzinfo=None)
                               .isoformat(timespec='milliseconds' if stamp.microsecond else 'seconds'),un=user).items()
             if v is not None} for remark,stamp,user in rows]
