"""Atomic immutable facts required by derived reports after the day commits.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from itertools import islice
from django.db import connection,transaction
from mta.runtime.report_generation_models import DailyReportOrderRouteSource
from mta.serialization import digest,storage

ROUTE_FIELDS=('OrderKey','SrcWhCode','DestWhCode','DueDate')
SCHEMA='fresh-report-route-facts-v1'


def read_routes(run,metadata):
    if set(metadata)!={'schema','row_count','rows_digest'} or metadata['schema']!=SCHEMA:
        raise ValueError('Report route source identity differs')
    result=[]
    for ordinal,row in enumerate(DailyReportOrderRouteSource.objects.filter(run=run)
            .order_by('ordinal').values('ordinal',*ROUTE_FIELDS).iterator(chunk_size=500)):
        if row.pop('ordinal')!=ordinal:raise ValueError('Report route source ordinal differs')
        result.append(storage(row))
    if len(result)!=metadata['row_count'] or digest(result)!=metadata['rows_digest']:
        raise ValueError('Report route source full values/order differ')
    return result


def write_routes(run,calculated,orders):
    if transaction.get_autocommit() or run.status!='RUNNING':
        raise ValueError('Report route facts require atomic operational publication')
    from mta.presentation.fulfillment import routes_for_orders
    rows=routes_for_orders(calculated,orders)
    metadata=dict(schema=SCHEMA,row_count=len(rows),rows_digest=digest(rows))
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('fresh.report_route_source',%s,true)",[str(run.pk)])
    try:
        records=(DailyReportOrderRouteSource(run=run,ordinal=i,**row) for i,row in enumerate(rows))
        while batch:=list(islice(records,500)):
            DailyReportOrderRouteSource.objects.bulk_create(batch,batch_size=500)
        if read_routes(run,metadata)!=storage(rows):raise ValueError('Report route source readback differs')
    finally:
        if not connection.needs_rollback:
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.report_route_source','',true)")
    return metadata
