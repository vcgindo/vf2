"""Explicit post-BPR producer projection, before DBM can change working state."""
from copy import deepcopy
from mta.application.operational_inputs import PHYSICAL_TABLES, typed_value
from mta.application.operational_upload_logs import _schema, SCHEMA_SHA256

INPUT_CAPTURE_POLICY = 'cohort2-input-tables-v1'


def capture_input_tables(*, controls, daily, supplier):
    bindings = dict(MasterDataRaw=(controls, 'raw_master'), DailyDataRaw=(daily, 'DailyDataRaw'),
                    SOBDataRaw=(supplier, 'SOBDataRaw'), MOQDataRaw1=(supplier, 'MOQDataRaw1'))
    populations={}
    for name in PHYSICAL_TABLES:
        owner,key=bindings[name]
        if not isinstance(owner,dict) or not isinstance(owner.get(key),list):
            raise ValueError('Explicit processed input-table source absent: '+name)
        columns=_schema['tables']['Importer/'+name]
        fields={column['name'] for column in columns}
        for row in owner[key]:
            if not isinstance(row,dict) or set(row)!=fields:
                raise ValueError('Processed input-table fields differ: '+name)
            for column in columns:
                typed_value(row[column['name']],column,reserve_null_token=False)
        populations[name]=deepcopy(owner[key])
    return populations
