"""Read routing for the qualified terminal TEST delivery, not configuration repair.

The original flags/configuration receipt stay unchanged. Native startup still
requires the entire READY roster; each chosen reader verifies its own receipt.
"""
from django.conf import settings

FLAGS = frozenset(('VF_BPR_PREPARED', 'VF_RRR_PREPARED',
                   'VF_HISTORY_REPORTS_PREPARED', 'VF_RESEARCH_AVAILABILITY_PREPARED'))


def prepared(flag, run):
    if flag not in FLAGS:
        raise ValueError('Unknown terminal reader mode')
    if getattr(settings, flag, False):
        return True
    from mta.presentation.terminal_bpr_delivery import applicable, binding
    if (not settings.VF_MTA_NATIVE_PUBLICATION or not settings.VF_MTA_DAILY_PUBLICATION
            or not applicable(run)
            or getattr(run, 'status', None) != 'SUCCEEDED'):
        return False
    binding(run)
    return True
