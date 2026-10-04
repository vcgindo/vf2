"""Finite typed fields for the daily Guided DBM occurrence relation."""
import hashlib
import json


SOURCES = {
    'A': 'closing/btr/DBMNormSuggestionsData',
    'S': 'closing/btr/SkuAttributeData',
    'L': 'closing/btr/LocationAttributeData',
    'P': 'closing/btr/SkuLocAttributeData',
    'M': 'closing/dbm/DBMMaster',
}

FIELDS = {
    'A': {
        'SKUCode': 'text', 'WhCode': 'text', 'Suggestion': 'text',
        'SuggestionGenerationAge': 'bigint',
    },
    'S': {
        'SKUCode': 'text', 'ElephantOrderCapping': 'bigint',
        # Both are physical numeric columns but the accepted image wire is str.
        # Text retains the exact native serialization and Python MAX ordering.
        'Weight': 'text', 'Volume': 'text',
        **{f'SL{i}': 'text' for i in range(1, 6)},
        **{f'c{i}': 'text' for i in range(1, 16)},
    },
    'L': {
        'WHCode': 'text', 'LocationType': 'text', 'LogisticsLocation': 'text',
        **{f'LL{i}': 'text' for i in range(1, 6)},
        **{f'c{i}': 'text' for i in range(1, 16)},
    },
    'P': {
        'SKUCode': 'text', 'LocCode': 'text',
        **{f'c{i}': 'text' for i in range(1, 16)},
    },
    'M': {
        'SKUCode': 'text', 'WhCode': 'text', 'Norm': 'bigint',
        'ParentWhCode': 'text',
    },
}


def field_name(owner, name):
    return owner.lower() + '_' + name.lower()


def schema_digest():
    value = {'sources': SOURCES, 'fields': FIELDS}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
