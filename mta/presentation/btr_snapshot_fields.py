"""Finite typed fields for the retained BTR presentation trial.

Numeric/text alternatives preserve the JS mapper's number-or-string cells without
storing operational rows in JSON. NULL in both alternatives denotes an empty cell;
source filter columns separately retain their actual SQL NULLs and scalar types.
"""
TEXT_FIELDS = ('Source', 'SKUCode', 'SKUDescription', 'WhCode', 'LocationName', 'pc', 'pn')
SCALAR_FIELDS = ('Category', 'Tags', 'Norm', 'VirtualNorm', 'age', 'bc', 'rc', 'yc', 'gc', 'blc', 'wc')
DAILY_FIELDS = tuple(f'D{i}' for i in range(1, 91))
DISPLAY_FIELDS = SCALAR_FIELDS + DAILY_FIELDS + tuple('C' + day for day in DAILY_FIELDS)
FILTER_FIELDS = {
    'A': {'SKUCode': 'text', 'WhCode': 'text'},
    'E': {'ParentWhCode': 'text', 'Norm': 'numeric', 'VirtualNorm': 'numeric'},
    'B': {'Category': 'text', 'Tags': 'text'},
    'btd': {'Age': 'numeric', 'D90': 'text', **{c + 'Count': 'numeric'
            for c in ('Black', 'Red', 'Yellow', 'Green', 'Blue', 'White')}},
    'sa': {'SKUCode': 'text', **{f'SL{i}': 'text' for i in range(1, 6)}, **{f'c{i}': 'text' for i in range(1, 16)}},
    'la': {'WHCode': 'text', 'LocationType': 'text', **{f'LL{i}': 'text' for i in range(1, 6)},
           **{f'c{i}': 'text' for i in range(1, 16)}},
    'sla': {f'c{i}': 'text' for i in range(1, 16)},
}


def filter_field(owner, field):
    return 'filter_' + owner.lower() + '_' + field.lower()


def display_field(field, kind):
    return 'display_' + field.lower() + '_' + kind
