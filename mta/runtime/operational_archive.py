"""Separate immutable intake files from captured post-BPR table exports."""
from mta.application.daily_transit import RAW_FIELDS
from mta.application.operational_inputs import PHYSICAL_TABLES, physical_files
from mta.application.operational_sqlcmd import input_table_bytes
from mta.application.operational_upload_logs import _schema
from mta.runtime.operational_input_source import read_input_source
from mta.runtime.operational_attempts import configuration_value
from mta.runtime.input_reader import read_input

# The declared daily-transit-raw-v1 physical reproduction interface follows the
# retained typed shipment model; it does not infer rows from aggregate GIT.
TRANSIT_COLUMNS=[dict(name=name, nullable=True,
    type='date' if name in ('CreationDate','GateOutDate','ReportDate') else
         'int' if name=='InTransitQty' else 'nvarchar',
    parameters=None if name in ('CreationDate','GateOutDate','ReportDate','InTransitQty') else
               'max' if name=='Remark' else '50') for name in RAW_FIELDS]


def archive_inputs(owner):
    config=configuration_value(owner.configuration)
    label=config['bindings'].get('input_export_database')
    expected=[dict(ordinal=i,database_name=label,table_name=name,condition=None)
              for i,name in enumerate(PHYSICAL_TABLES)]
    if not isinstance(label,str) or config['tables']!=expected:
        raise ValueError('Exact four-table input-export roster and database label required')
    if config['bindings'].get('input_archive_clock')!='business-midnight-Asia-Kolkata':
        raise ValueError('Explicit approved archive clock required')
    if owner.run.input_payload.get('schema')!='fresh-daily-input-manifest-v2':
        raise ValueError('Typed intake source required')
    day=read_input(owner.run,components=('day',))['day']
    shipment=day.get('shipment_input')
    if (not isinstance(shipment,dict) or shipment.get('schema')!='daily-transit-raw-v1'
            or shipment.get('business_date')!=owner.business_date.isoformat()
            or not isinstance(shipment.get('rows'),list)):
        raise ValueError('Explicit date-bound raw shipment population required')
    physical=dict(MasterDataRaw=day.get('raw_master'),DailyDataRaw=day.get('raw_daily'),
        SOBDataRaw=day.get('supplier_feeds',{}).get('SOBDataRaw'),
        MOQDataRaw1=day.get('supplier_feeds',{}).get('MOQDataRaw1'),InTransitRaw=shipment['rows'])
    if any(not isinstance(rows,list) for rows in physical.values()):
        raise ValueError('Complete explicit physical intake populations required')
    tables=read_input_source(owner.run)
    return dict(physical=physical_files(_schema,physical,TRANSIT_COLUMNS),
        table_exports={label+'_'+name+'.CSV':input_table_bytes(_schema['tables']['Importer/'+name],tables[name])
                       for name in PHYSICAL_TABLES}, importer_database=label,
        business_date=owner.business_date.isoformat())
