"""Fail closed on removed historical serving configuration, without loading it."""
from django.conf import settings


REMOVED_SETTINGS = (
    'VF_MTA_FIXTURE_FILE', 'VF_MTA_FIXTURE_SHA256',
    'VF_MTA_OPERATIONAL_POLICY', 'VF_MTA_OPERATIONAL_RECEIPT',
    'VF_MTA_CONSUMPTION_POLICY', 'VF_MTA_SYNTHETIC_ROSTER',
    'VF_MTA_PLANNING_EXTENSION', 'VF_MTA_RRR_COLOUR_EXTENSION',
    'VF_MTA_PREACCEPTANCE_FILE', 'VF_MTA_PREACCEPTANCE_SHA256',
    'VF_MTA_TERMINAL_FILE', 'VF_MTA_TERMINAL_SHA256',
    'VF_MTA_EXCESS_HISTORY_FILE', 'VF_MTA_EXCESS_HISTORY_SHA256',
    'VF_MTA_GUIDED_EXCESS_DISPOSITION', 'VF_MTA_PREVIEW_EMPTY_EXPEDITE_HISTORY',
    'VF_MTA_FORCE_HISTORY_FIXTURE',
)


def removed_mode(name):
    from mta.presentation.context import PublicationUnavailable
    raise PublicationUnavailable('removed_historical_mode:' + name)


def require_configuration():
    for name in REMOVED_SETTINGS:
        if getattr(settings, name, ''):
            removed_mode(name)
