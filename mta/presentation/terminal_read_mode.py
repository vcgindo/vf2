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
            or getattr(run, 'status', None) != 'SUCCEEDED'):
        return False
    if applicable(run):
        binding(run)
        return True
    if flag == 'VF_BPR_PREPARED' and getattr(run, 'kind', None) == 'DAILY_CHAIN':
        from mta.presentation import registered_report_view, native_publication, native_selection
        if registered_report_view.applicable_run(run):
            # Select the existing terminal projection only after validating its
            # captured registration, own phase chain and sealed selected day.
            # The flag stays part of the original immutable configuration.
            native_publication.require_mode()
            registered_report_view.configuration(run)
            native_selection.require_selected(run)
            native_publication.require_publication(run)
            return True
    return False
