"""Explicit human-deferred Guided Excess history for the owned synthetic demo."""
from django.conf import settings
from django.db import connection
from mta.presentation.context import PublicationUnavailable

VERSION = 'guided-excess-history-deferred-v1'
REASON = 'guided_excess_history_deferred_for_3006_synthetic_demo'


def guard(run, kind):
    if kind not in ('excess-sku', 'excess-value'):
        return
    configured = getattr(settings, 'VF_MTA_GUIDED_EXCESS_DISPOSITION', '')
    if not configured:
        return
    if (configured != VERSION or run.kind != 'DAILY_CHAIN' or
            getattr(settings, 'VF_MTA_SYNTHETIC_ROSTER', '') != 'core-without-bor-v1'):
        raise PublicationUnavailable('guided_excess_disposition_scope_mismatch')
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        if cursor.fetchone()[0] != 'daily_3006':
            raise PublicationUnavailable('guided_excess_disposition_owned_database_required')
    # Deliberately no source read, empty result or fallback to another timeline.
    raise PublicationUnavailable(REASON)
