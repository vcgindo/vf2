"""Choose existing readers from the selected native daily publication contract.

Prepared switches retain their explicit legacy meaning. A native sealed daily
publication owns a fixed prepared roster independently of those switches; its
original configuration, selection, sources and summary must still validate.
Historical phase/file custody adapters do not decide ordinary reader eligibility.
"""
from dataclasses import dataclass
from django.conf import settings
from mta.presentation.request_scope import once_per_request

LAYERS = {'VF_BPR_PREPARED': 'bpr', 'VF_RRR_PREPARED': 'rrr',
          'VF_HISTORY_REPORTS_PREPARED': 'history',
          'VF_RESEARCH_AVAILABILITY_PREPARED': 'research_availability'}
FLAGS = frozenset(LAYERS)


@dataclass(frozen=True)
class TerminalReaders:
    run_id: object
    publication_seal: str
    configuration_digest: str
    contract: str = 'native-sealed-daily-v1'


@once_per_request
def binding(run):
    """Request-local references only; the existing owners verify all authority."""
    from mta.presentation import native_publication, native_selection, daily_publication
    native_publication.require_mode()
    native_selection.require_selected(run)
    native_publication.require_publication(run)
    publication = daily_publication.require_ready(run)
    # require_ready validates the exact supported roster, sources, recipe,
    # statuses, configuration and seal. Readers additionally verify their own
    # projection receipts and source ordinals before reading any business rows.
    return TerminalReaders(run.pk, publication.seal_digest, publication.configuration_digest)


def prepared(flag, run):
    if flag not in FLAGS:
        raise ValueError('Unknown terminal reader mode')
    if getattr(settings, flag, False):
        return True
    if (not settings.VF_MTA_NATIVE_PUBLICATION or not settings.VF_MTA_DAILY_PUBLICATION
            or getattr(run, 'kind', None) != 'DAILY_CHAIN'
            or getattr(run, 'status', None) != 'SUCCEEDED'):
        return False
    binding(run)
    return True
