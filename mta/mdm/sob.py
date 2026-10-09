"""Pinned master-4 supplier workflow facade."""
from mta.mdm import supplier

CONFIG = supplier.CONFIG[4]
FIELDS = {row['Col_Code']: row for row in CONFIG['UI_MDMConfig']}
ALIASES = {alias: row['TableField'] for alias, row in FIELDS.items()}
DRAFT_ALIASES = {alias: name for alias, name in ALIASES.items() if FIELDS[alias]['IsDownload']}


def configuration(screen_type):
    return supplier.configuration(4, screen_type)


def read(source, payload, *, count=False):
    if int(payload['id']) != 4:
        raise ValueError('Wrong supplier master')
    return supplier.read(source, payload, count=count)
