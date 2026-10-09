"""Pinned master-8 AddPIPO ADD-only facade."""
from mta.mdm.phase_controls_configuration import (
    ALIASES as SHARED_ALIASES,
    DRAFT_ALIASES as SHARED_DRAFT_ALIASES,
    FIELDS as SHARED_FIELDS,
    configuration as _configuration,
)


MASTER_ID = 8
ALIASES = SHARED_ALIASES[MASTER_ID]
DRAFT_ALIASES = SHARED_DRAFT_ALIASES[MASTER_ID]
FIELDS = SHARED_FIELDS[MASTER_ID]


def configuration(screen_type):
    return _configuration(MASTER_ID, screen_type)


def read(source, payload, *, count=False):
    if int(payload['id']) != MASTER_ID:
        raise ValueError('Wrong phase-control master')
    # Deployed GetData/GetDataCount have no cases for ADD-only masters 7/8/9.
    return '' if count else None
