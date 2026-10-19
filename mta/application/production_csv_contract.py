"""Versioned CSV projections of existing native daily inputs; no business defaults.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
import json
from pathlib import Path

from mta.application.native_daily_contract import DAY_TABLES, SUPPLIER_TABLES, SCHEMA, FEED_SCHEMA, SOURCE_SCHEMA
from mta.runtime.relational_state import STORAGE_TABLES
from mta.application.production_source_inputs import RAW_TABLE, DIRECTORY_TABLE

SCHEMA_VERSION = 'vectorflow-daily-csv-v1'
FILES = {
    'raw_daily': 'DailyDataRaw.csv', 'raw_non_nms': 'MasterDataRawNonNMS.csv',
    'raw_no_norm': 'NoNormMasterRaw.csv', 'accepted_feed': 'AcceptedNorms.csv',
    'order_raw': 'OrderData.csv', 'order_feed': 'OrderFeed.csv',
    'distributor_transactions': 'DistributorTransactions.csv',
    'vendor_transactions': 'VendorTransactions.csv',
}


def feeds(intake):
    if intake not in (SCHEMA, FEED_SCHEMA):
        raise ValueError('Explicit supported native intake schema required')
    physical = json.loads((Path(__file__).resolve().parents[2] /
        'baseline/cohort2-native-source-schema.json').read_bytes())['tables']
    result = {}

    def add(filename, path, table, physical_table=None):
        columns = []
        metadata = {c['name']: c for c in physical.get(physical_table or table, [])}
        fields = dict(STORAGE_TABLES[table])
        if path == 'day/order_feed':
            fields.pop('Type')
        if path in ('day/distributor_transactions', 'day/vendor_transactions'):
            fields['ReportDate'] = 'date'
        for name, kind in fields.items():
            column = deepcopy(metadata.get(name, {}))
            # The native table contract wins over a similarly named physical source.
            if column.get('type') != kind:
                column = dict(name=name, type=kind, nullable=True)
            column['name'] = name
            columns.append(column)
        result[filename] = dict(path=path, table=table, columns=columns)

    for name, filename in FILES.items():
        add(filename, 'day/' + name, DAY_TABLES[name],
            'Importer/DailyDataRaw' if name == 'raw_daily' else
            'Importer/MasterDataRaw' if name == 'raw_no_norm' else None)
    if intake == FEED_SCHEMA:
        add('MasterDataRaw.csv', 'day/raw_master', 'Importer/MasterDataRaw')
        for name, table in SUPPLIER_TABLES.items():
            add(name + '.csv', 'day/supplier_feeds/' + name, table,
                'Importer/' + name)
    add('InTransitRaw.csv', 'producer_sources/shipments/rows', RAW_TABLE)
    add('Transporters.csv', 'producer_sources/transporters/rows', DIRECTORY_TABLE)
    return result


def describe(intake):
    return dict(schema=SCHEMA_VERSION, native_schema=SOURCE_SCHEMA, intake_schema=intake,
        encoding='UTF-8; optional initial BOM', delimiter=',', null_token='\\N',
        newline='LF or CRLF', empty_population='header only; never missing', feeds=feeds(intake))
