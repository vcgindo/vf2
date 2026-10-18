"""Pinned master-5 supplier workflow facade."""
from mta.mdm import supplier

CONFIG = supplier.CONFIG[5]
FIELDS = {row['Col_Code']: row for row in CONFIG['UI_MDMConfig']}
ALIASES = {alias: row['TableField'] for alias, row in FIELDS.items()}
DRAFT_ALIASES = {alias: name for alias, name in ALIASES.items() if FIELDS[alias]['IsDownload']}


def configuration(screen_type, *, source=None):
    result = supplier.configuration(5, screen_type)
    if source is not None and supplier.setting(source) == 'WithDestLoc':
        for master in result:
            for field in master['fields']:
                if field['key'] == 'wc':
                    field['visible'] = True
                    if screen_type == 'add':
                        field['isAdd'] = True
    return result


def read(source, payload, *, count=False):
    if int(payload['id']) != 5:
        raise ValueError('Wrong supplier master')
    return supplier.read(source, payload, count=count)
