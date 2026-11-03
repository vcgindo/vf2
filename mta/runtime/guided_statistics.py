"""Prepare planner statistics before an unsealed Guided history aggregation.

History rows are committed by the report coordinator immediately before their
consumer runs. Autovacuum may not yet have analysed the new run_id population.
The caller owns admission and coordination; this changes only planner metadata,
never rows, report recipes, database settings or accepted receipts.
"""
from django.db import connection

SOURCE_TABLES = (
    'mta.fresh_mta_guidedavailabilityhistoryrow',
    'mta.fresh_mta_guidedavailabilitysnapshotreference',
    'mta.fresh_mta_guidedexcesshistoryrow',
)


def refresh_sources(run):
    """Refresh sources for the command's locked, unsealed build."""
    if connection.vendor != 'postgresql':
        raise ValueError('Guided aggregate statistics require PostgreSQL')
    if run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED':
        raise ValueError('Guided aggregate statistics require a committed daily run')
    with connection.cursor() as cursor:
        # PostgreSQL can skip ANALYZE with a warning and still return success.
        # Capture only notices from these statements on this connection.
        warnings = []

        def record_warning(notice):
            if notice.severity_nonlocalized == 'WARNING':
                warnings.append(notice.message_primary)

        physical = connection.connection
        physical.add_notice_handler(record_warning)
        try:
            for table in SOURCE_TABLES:
                cursor.execute('ANALYZE ' + table)
                if warnings:
                    raise ValueError(f'Guided statistics refresh failed for {table}: {warnings[0]}')
        finally:
            physical.remove_notice_handler(record_warning)
