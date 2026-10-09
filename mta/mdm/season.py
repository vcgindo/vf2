"""Pinned Seasonality master configuration and shared current reader."""
from mta.mdm.season_configuration import aliases, fields, configuration as _configuration
from mta.mdm.season_current import read

MASTER_ID = 10
ALIASES = aliases(MASTER_ID)
DRAFT_ALIASES = dict(ALIASES, IsSelected='IsSelected')
FIELDS = fields(MASTER_ID)


def configuration(screen_type):
    return _configuration(MASTER_ID, screen_type)
