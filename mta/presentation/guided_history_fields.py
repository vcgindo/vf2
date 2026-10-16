"""Pinned source and row contracts for fixture history preparation."""
from mta.serialization import digest

SOURCES = {
    'availability': ('closing/btr/BPR', 'closing/btr/SkuAttributeData',
                     'closing/btr/LocationAttributeData',
                     'closing/btr/SkuLocAttributeData',
                     'closing/btr/BTRSnapshotForUI'),
    'excess': ('projection/ExcessInventoryRow',
               'closing/importer/SkuAttributeData',
               'closing/importer/LocationAttributeData',
               'closing/importer/SkuLocAttributeData'),
}

ROW_FIELDS = {
    'availability': ('ordinal', 'fact_ordinal', 'sku_ordinal', 'location_ordinal',
                     'pair_ordinal', 'snapshot_anchor_ordinal', 'report_date',
                     'sku_code', 'location_code', 'parent_location_code',
                     'location_type', 'physical_inventory_color'),
    'snapshot': ('snapshot_anchor_ordinal', 'snapshot_ordinal',
                 'age_physical_inventory'),
    'excess': ('ordinal', 'fact_ordinal', 'sku_ordinal', 'location_ordinal',
               'pair_ordinal', 'report_date', 'sku_code', 'location_code',
               'parent_location_code', 'location_type',
               'physical_inventory_color', 'amount'),
}


def schema_digest():
    return digest({'sources': SOURCES, 'rows': ROW_FIELDS})


NATIVE_EXCESS_FIELDS = ('ordinal', 'fact_run_id') + ROW_FIELDS['excess'][1:]


def native_excess_schema_digest():
    """Native owner-bound schema; retained fixture receipts remain unchanged."""
    return digest({'sources': SOURCES, 'rows': {
        **ROW_FIELDS, 'excess': NATIVE_EXCESS_FIELDS}})
