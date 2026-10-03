"""Measured BTR fixture count plan, scoped to one read transaction."""
from contextlib import contextmanager
from django.db import connection, transaction


@contextmanager
def count_cursor(enabled):
    if not enabled:
        with connection.cursor() as cursor:
            yield cursor
        return
    # At this scale parallel nested loops repeatedly probe each index for every
    # report position. The covering-index merge plan was measured for both
    # admitted scopes. Do not apply this choice to bounded grids or normal runs.
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('max_parallel_workers_per_gather'),current_setting('enable_nestloop')")
        previous = cursor.fetchone()
        cursor.execute('SET LOCAL max_parallel_workers_per_gather=0')
        cursor.execute('SET LOCAL enable_nestloop=off')
        yield cursor
        # Explicit restoration also covers callers already in a transaction.
        # On exceptions the atomic/savepoint rollback restores SET LOCAL.
        cursor.execute("SELECT set_config('max_parallel_workers_per_gather',%s,true),set_config('enable_nestloop',%s,true)", previous)
