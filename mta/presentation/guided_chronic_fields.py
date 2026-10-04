"""Finite output and source contract for the prepared Chronic grid bag."""
import hashlib
import json


SOURCES = {
    'A': 'closing/btr/ChronicUnavalabilityData',
    'N': 'closing/consumer_context/NMSAllItems',
    'L': 'closing/btr/LocationAttributeData',
    'S': 'closing/btr/SkuAttributeData',
    'P': 'closing/btr/SkuLocAttributeData',
}

OUTPUTS = {
    'skucode': 'text', 'skudesc': 'text', 'location': 'text',
    'parentloc': 'text', 'RLT': 'bigint', 'BlackRedAgeing': 'bigint',
    'PhysicalInventoryPen': 'text', 'Techcolor': 'text',
    'PipelineInventoryPen': 'text', 'ecocolor': 'text',
    'RationedStockatparent': 'bigint',
}


def schema_digest():
    value = {'sources': SOURCES, 'outputs': OUTPUTS,
             'ordinals': ['a', 'n', 'l', 's', 'p']}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
