"""Approved atomic, server-scoped operational logistics commands."""
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import connection, transaction
from mta.presentation import logistics_live as live, logistics_read as reader
from mta.presentation.rrr import sql_key
from mta.runtime.models import (TransitAnnotation, TransitRemarkHistory,
    ExpediteRemarkHistory, DailyOpenRequest)

TRANSIT_FIELDS = frozenset(('OrderNo','SKUCode','WhCode','ParentWHCode','Remarks','CurrentLocation','ETA'))
ACTION_FIELDS = frozenset(('SKUCode','WHCode','Remark','ETA'))


def _text(value, *, width=None):
    # C# quoted string interpolation turns null string values into empty text.
    if value is None:
        value = ''
    if not isinstance(value,str) or (width is not None and len(value)>width):
        raise ValueError('Native logistics text/width required')
    return value


def _datetime(value, *, optional=False, transit=False):
    if value is None or value == '':
        if optional:
            return None
        if transit:
            # Exact SQL Server CONVERT(date,'') behavior of the matched writer.
            return datetime(1900,1,1)
        raise ValueError('Expedite action ETA must be a valid native date')
    value = _text(value).replace('/','-')
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is not None:
        raise ValueError('Native ETA is a wall date, without a timezone')
    if not transit and stamp.year < 1753:
        raise ValueError('Native SQL datetime date out of range')
    if transit:
        return stamp
    from mta.domain.complete_daily_scalars import _datetime_storage
    return _datetime_storage(stamp)


def _batch(payload, fields):
    rows = payload.get('data')
    if not isinstance(rows,list) or not rows or any(not isinstance(r,dict) or set(r)!=fields for r in rows):
        raise ValueError('Exact native logistics batch shape required')
    return rows


def _now():
    return datetime.now(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE)).replace(microsecond=0,tzinfo=timezone.utc)


def _write_context():
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.logistics_command',%s,true)",[live.OWNER])
        cursor.execute("SELECT set_config('fresh.daily_request_owner',%s,true)",['OpenExpediteRequests'])


def _finish(owner, count):
    owner.next_ordinal += count
    owner.revision += 1
    owner.save(update_fields=['next_ordinal','revision'])


@transaction.atomic
def submit_transit(run,payload,actor):
    owner = live.history_owner(lock=True)
    generation = live.generation(run,lock=True)
    rows = _batch(payload,TRANSIT_FIELDS)
    actor_id = actor.get('id')
    if isinstance(actor_id,bool) or str(actor_id) != str(int(actor_id)) or not -(2**31)<=int(actor_id)<2**31:
        raise ValueError('Native transit actor integer required')
    raw = live.transit_rows(run,include_live=False)
    values=[]
    for row in rows:
        text={k:_text(row[k],width=50 if k not in ('Remarks','CurrentLocation','ETA') else None) for k in row}
        text['ETA']=_datetime(row['ETA'],transit=True).date()
        # Current importer CurrentLocationCode is nvarchar(50), even though its
        # history CurrentLocation is nvarchar(max). A failed current write must
        # roll back its corresponding history too.
        _text(text['CurrentLocation'],width=50)
        reader.authorize_order(run,payload,text['OrderNo'])
        reader.authorize_pair(run,payload,text['SKUCode'],text['WhCode'])
        ordinals=[i for i,r in enumerate(raw) if sql_key(r['OrderNo'])==sql_key(text['OrderNo'])]
        values.append((text,ordinals))
    _write_context(); stamp=_now()
    for i,(row,ordinals) in enumerate(values):
        TransitRemarkHistory.objects.create(owner=owner,ordinal=owner.next_ordinal+i,
            generation=generation,**row,UserId=int(actor_id),RemarksDate=stamp)
        for ordinal in ordinals:
            TransitAnnotation.objects.update_or_create(generation=generation,source_ordinal=ordinal,
                defaults=dict(CurrentLocationCode=row['CurrentLocation'],ETA=row['ETA'],Remark=row['Remarks']))
    generation.revision += 1
    generation.save(update_fields=['revision'])
    _finish(owner,len(values))


@transaction.atomic
def add_expedite_remark(run,payload,actor):
    history=live.history_owner(lock=True)
    owner, requests=live.current_requests(lock=True)
    values=[]
    for row in _batch(payload,ACTION_FIELDS):
        sku=_text(row['SKUCode'],width=50); location=_text(row['WHCode'],width=50)
        reader.authorize_pair(run,payload,sku,location)
        eta=_datetime(row['ETA'])
        values.append(dict(SKUCode=sku,WHCode=location,Remark=_text(row['Remark']),
            ETA=eta.replace(tzinfo=timezone.utc)))
    _write_context();stamp=_now(); affected=0
    from mta.mdm.clock import database_now
    for i,row in enumerate(values):
        ExpediteRemarkHistory.objects.create(owner=history,ordinal=history.next_ordinal+i,
            **row,UserId=_text(actor.get('name')),RemarkDate=stamp)
        selected=[r.pk for r in requests if sql_key(r.SKUCode,r.WhCode)==sql_key(row['SKUCode'],row['WHCode'])]
        affected += DailyOpenRequest.objects.filter(pk__in=selected).update(Action=row['Remark'],
            ActionDate=database_now().replace(tzinfo=timezone.utc),
            ETA=datetime.combine(row['ETA'].date(),time.min,tzinfo=timezone.utc))
    owner.revision+=1;owner.save(update_fields=['revision'])
    _finish(history,len(values))
    return str(affected+len(values))
