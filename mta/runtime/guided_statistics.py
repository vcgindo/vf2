"""Prepare planner statistics before an unsealed Guided history aggregation.

History rows are committed by the report coordinator immediately before their
consumer runs. Autovacuum may not yet have analysed the new run_id population.
The caller owns admission and coordination; this changes only planner metadata,
never rows, report recipes, database settings or accepted receipts.
"""
from django.db import connection

from mta.runtime.models import ReportAggregateReceipt


SOURCE_TABLES = (
    'mta.fresh_mta_guidedavailabilityhistoryrow',
    'mta.fresh_mta_guidedavailabilitysnapshotreference',
    'mta.fresh_mta_guidedexcesshistoryrow',
)


def refresh_pending(run):
    """Use current source statistics; leave sealed aggregate reuse untouched."""
    if connection.vendor != 'postgresql':
        raise ValueError('Guided aggregate statistics require PostgreSQL')
    if run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED':
        raise ValueError('Guided aggregate statistics require a committed daily run')
    if ReportAggregateReceipt.objects.filter(run=run).exists():
        return False
    with connection.cursor() as cursor:
        for table in SOURCE_TABLES:
            cursor.execute('ANALYZE ' + table)
    return True
