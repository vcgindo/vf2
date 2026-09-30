"""Generate storage column definitions from the verified canonical test schema.

Read-only schema extraction, never a data importer or business-code generator.
"""
import json
from pathlib import Path

from parity.legacy_isolation import exclusive_replay, raw_connection, MAPPING
from parity.provision_legacy import DDL
from parity.adapters.legacy.temporal_support import BINDINGS
from parity.adapters.legacy.temporal_delivery import AUX, OWNERS

ROOT=Path(__file__).resolve().parents[1]


def build():
    roster=json.loads((ROOT/'baseline/temporal-oracle-roster.json').read_text())
    bindings={}
    for section,tables in roster['closing_tables'].items():
        if section=='publication_context':continue  # Bounded version/timezone descriptors, not rows.
        for name in tables:
            if name=='IntermediateTables':continue
            if section=='controls': role,table=BINDINGS[name]
            elif section=='control_aux':role,table=AUX[name]
            elif section=='dbm':role,table=OWNERS.get(name,'DBM'),name
            elif section=='bpr':role,table='BPR',name
            elif section=='btr':role,table={'SKULocStandardAttributes':'Importer','ExpediteDispatches':'BPR'}.get(name,'BTR'),name
            elif section=='importer':role,table='Importer',name
            elif section=='supplier':role,table='BPR',name
            elif section=='orders':
                role,table=({'DBMMaster':'DBM','PSOData':'Importer','OrderIdentity':'SyntheticMetadata'}.get(name,'BPR')),name
            elif section=='consumer_context':
                role,table={'CWH_List':'BPR','CategoryColDescription':'BTR','DistributorList':'Distributor',
                    'GoodsInTransitTransporterMaster':'BPR','NMSAllItems':'Importer'}[name],name
            else:raise ValueError('Unmapped closing section '+section)
            bindings['closing/'+section+'/'+name]=[role,table]
    bindings['closing/importer_settings']=['Importer','ImporterSettingsTbl']
    for name in roster['scratch_tables']:
        bindings['scratch/'+name]=['Intermediate',name.removeprefix('dbo.')]
    bindings.update({'reports/bpr/BPR_Table':['BPR','BPR_Table'],
                     'reports/bpr/vf_RationedReqReport':['BPR','vf_RationedReqReport']})
    for stage in ('norm1-advisory','norm-change-export','norm-change-history','norm0-export','norm1-export','norm2-export'):
        for table in ('Norm0Norm1Norm2Report','Norm0_1_2ReportDetails','Norm1IncreaseSuggestions'):
            bindings['reports/'+stage+'/'+table]=['DBM',table]
    bindings['reports/controls/phase_exceptions']=['DBM','PhaseInPhaseOutExceptionLog']
    bindings['reports/controls/failed_force']=['Projection','FailedForce']
    definitions={}; column_definitions={}
    sources={}
    with exclusive_replay():
        for role in sorted({r for r,_ in bindings.values()}-{'SyntheticMetadata','Projection'}):
            names={t for r,t in bindings.values() if r==role}
            with raw_connection(MAPPING['VFTEST_'+role]) as connection:
                columns=connection.execute("SELECT t.name,c.name,ty.name,c.column_id,c.max_length,c.precision,c.scale,c.is_nullable FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id JOIN sys.columns c ON c.object_id=t.object_id JOIN sys.types ty ON ty.user_type_id=c.user_type_id WHERE s.name='dbo' ORDER BY t.name,c.column_id").fetchall()
            for table,column,kind,ordinal,length,precision,scale,nullable in columns:
                if table in names:
                    definitions.setdefault(role+'/'+table,[]).append([column,kind])
                    column_definitions.setdefault(role+'/'+table,[]).append(dict(name=column,type=kind,
                        ordinal=ordinal,length=length,precision=precision,scale=scale,nullable=bool(nullable)))
            receipt=json.loads((Path('D:/freshvcf-build/sqlserver')/(MAPPING['VFTEST_'+role]+'-schema.json')).read_text())
            sources[role]={k:receipt[k] for k in ('source','source_sha256','schema_sha256')}
    definitions['SyntheticMetadata/OrderIdentity']=[[n,'bigint'] for n in ('Seed','Increment','LastValue')]
    definitions['Projection/FailedForce']=[['SKUCode','nvarchar'],['WhCode','nvarchar'],['VectorFlowNorm','int'],['Reason','nvarchar']]
    missing=sorted({'/'.join(v) for v in bindings.values()}-set(definitions))
    if missing:raise ValueError('Missing canonical table schemas: '+str(missing))
    catalog=dict(schema='fresh-relational-state-v1',sources=sources,bindings=bindings,tables=definitions,
                 canonical_columns=column_definitions)
    (ROOT/'baseline/production-state-schema.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(bindings=len(bindings),tables=len(definitions))))


if __name__=='__main__':build()
