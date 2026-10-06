"""SQL clock for native GETDATE consumers, distinct from API-generated IDs."""
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import connection


def database_now():
    """Retain SQL Server datetime's 1/300-second ticks as displayed milliseconds."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT clock_timestamp()')
        stamp=cursor.fetchone()[0].astimezone(ZoneInfo(settings.VF_MTA_ACTION_TIME_ZONE))
    ticks=(stamp.microsecond*300+500000)//1000000
    milliseconds=(ticks*1000+150)//300
    return stamp.replace(microsecond=0)+timedelta(milliseconds=milliseconds)
