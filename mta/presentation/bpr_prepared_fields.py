"""Finite native BPR candidate contract; no permissions or display coercions."""
import hashlib
import json
import re


SOURCES = {
    'A': 'reports/bpr/BPR_Table',
    'V': 'reports/bpr/vf_RationedReqReport',
    'S': 'closing/dbm/SKULocStandardAttributes',
    'C': 'closing/importer/SkuAttributeData',
    'D': 'closing/importer/LocationAttributeData',
    'B': 'closing/importer/SkuLocAttributeData',
}

FIELDS = {
    'A': {
        **{name: 'text' for name in ('SKUCode', 'SKUName', 'WhCode', 'WhName',
                                    'ParentWhCode', 'ParentName')},
        **{name: 'bigint' for name in ('Stock', 'Norm', 'GIT', 'TechColorSequence',
                                     'EcoColorSequence')},
        'EcoColor': 'text',
        **{name: 'bigint' for name in ('Req', 'RationedQTY', 'LeftoverParentStock',
                                     'PhaseIn-Out', 'ResidualSnP', 'NormReq', 'BlueReq')},
        **{f'SKULocAttr{i}': 'text' for i in range(1, 16)},
    },
    'V': {'PhysicalInventoryColorSequence': 'bigint',
          'PhysicalInventoryPen': 'numeric', 'DispatchPen': 'numeric',
          'PhysicalInventoryColor': 'text', 'DispatchColor': 'text',
          'VirtualNorm': 'bigint'},
    'S': {'Tags': 'text'},
    'C': {**{f'SL{i}': 'text' for i in range(1, 6)},
          **{f'c{i}': 'text' for i in range(1, 16)}},
    'D': {**{f'LL{i}': 'text' for i in range(1, 6)},
          **{f'c{i}': 'text' for i in range(1, 16)}, 'LocationType': 'text'},
    'B': {f'c{i}': 'text' for i in range(1, 16)},
}


def field_name(owner, name):
    return owner.lower() + '_' + re.sub(r'[^a-z0-9_]', '_', name.casefold())


def schema_digest():
    contract = {'version': 'bpr-prepared-native-v1', 'sources': list(SOURCES.items()),
                'fields': [(owner, list(fields.items())) for owner, fields in FIELDS.items()],
                'ordinals': ['A', 'V', 'S', 'C', 'D', 'B'],
                'key': "lower(rtrim(code::text,' '))", 'joins': 'native-left-candidate-bag'}
    return hashlib.sha256(json.dumps(contract, separators=(',', ':'),
                                     sort_keys=True).encode()).hexdigest()
