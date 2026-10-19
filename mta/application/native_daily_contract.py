"""Shared native feed names; extraction from production_daily, without ORM imports."""
SCHEMA = 'fresh-production-day-input-v1'
FEED_SCHEMA = 'fresh-production-day-input-v2'
SOURCE_SCHEMA = 'fresh-production-day-input-v3'
STOCK_FEED_SCHEMA = 'fresh-production-day-input-v4'
STOCK_TABLE = 'Intermediate/AdditionalDataStockForReqCalc'
SUPPLIER_TABLES = dict(SOBDataRaw='Intermediate/TempSOBDataRaw',
    MOQDataRaw1='Intermediate/TempMOQDataRaw1', MOQDataRaw2='Intermediate/TempMOQDataRaw2')
DAY_TABLES = dict(raw_daily='Intermediate/DailyData', raw_non_nms='Importer/MasterDataRaw',
    raw_no_norm='Intermediate/NoNormMasterRaw', accepted_feed='Importer/AcceptedNorms',
    order_raw='DBM/OrderData', new_force_requests='Importer/ForceNormChange',
    order_feed='Intermediate/PSODataInput',
    distributor_transactions='input/production_transaction',
    vendor_transactions='input/production_transaction')
CONTROL_TABLES = dict(phase_requests='Importer/PhaseOut', phase_stops='Importer/PhaseOutStop',
    phase_in_requests='Importer/PhaseInNorms', season_requests='Importer/Seasonality')
DAY_FIELDS = {*DAY_TABLES, 'business_date', 'order_feed_status', 'control_requests',
    'phase_controls_input_validation', 'seasonality_input_validation'}


def day_tables(intake):
    return {**DAY_TABLES, **({'requirement_stock':STOCK_TABLE} if intake==STOCK_FEED_SCHEMA else {})}


def day_fields(intake):
    return DAY_FIELDS | ({'raw_master','supplier_feeds'} if intake in (FEED_SCHEMA,STOCK_FEED_SCHEMA) else set()) | (
        {'requirement_stock'} if intake==STOCK_FEED_SCHEMA else set())
