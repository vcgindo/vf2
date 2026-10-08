"""Owned, single-process selection scope; never changes a serving configuration."""
from contextlib import contextmanager
from threading import RLock

from django.conf import settings
from django.test.utils import override_settings
from mta.presentation import admission, qualified_consumption
from mta.presentation.context import PublicationUnavailable

_selection_lock = RLock()


@contextmanager
def selected(run):
    """Verify candidate atomically from the caller's view; restore prior on exit.

    The opt-in is only installed by the owned proof configuration. This is not a
    live-server switch: Django settings and admission are process-wide state.
    """
    if not getattr(settings, 'VF_COHORT3_OWNED_INPROCESS', False):
        raise PublicationUnavailable('qualified_selection_requires_owned_inprocess_config')
    qualified_consumption.owner(run)
    from mta.runtime.models import DailyUiPublication
    publication = DailyUiPublication.objects.get(run=run, status='READY')
    generation = publication.layers['btr']['receipt']['generation']
    with _selection_lock:
        previous = admission._admitted
        with override_settings(VF_MTA_PUBLISHED_RUN=str(run.pk),
                               VF_MTA_PUBLISHED_DIGEST=run.output_digest,
                               VF_BTR_REPORTING_GENERATION=generation):
            try:
                receipt = admission.admit()
                receipt['qualification'] = qualified_consumption.POLICY
                yield receipt
            finally:
                admission._admitted = previous
        # Any exception still restores both configuration and previous admission.
        # The caller verifies the prior binding before using it again.
