"""Statement-scoped authorization for native synchronous Location Add publication."""
from contextlib import contextmanager

from django.db import connection, transaction


@contextmanager
def publication_statement(source, task):
    # Each native INSERT still commits separately. A surrounding recovery/day
    # transaction, when present, retains ownership of its own atomic boundary.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('fresh.location_add_source',true), "
                           "current_setting('fresh.location_add_task',true)")
            prior = cursor.fetchone()
            cursor.execute("SELECT set_config('fresh.location_add_source',%s,true), "
                           "set_config('fresh.location_add_task',%s,true)",
                           [str(source.pk), str(task.pk)])
        try:
            yield
        finally:
            if not connection.needs_rollback:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('fresh.location_add_source',%s,true), "
                                   "set_config('fresh.location_add_task',%s,true)",
                                   [prior[0] or '', prior[1] or ''])
