"""Native run-owned Norm0 exports; separate from the accepted O6 profile."""
import hashlib
import io
import uuid
import zipfile

from mta.domain.dbm_norm012 import NORM0_EXPORT_STAGES, CHRONOLOGICAL_RULE
from mta.mdm.initialization_contract import sha
from mta.application.operational_norm_reports import _values, _cell, NORM_CELLS
from mta.application.report_encoding import norm_report_bytes
from mta.application import operational_io as files
from mta.serialization import digest


def enabled_horizons(batch):
    if not isinstance(batch,dict):raise ValueError('Owned report configuration required')
    enabled=[]
    for horizon in NORM0_EXPORT_STAGES:
        name=f'ActivateNorm0Report{horizon}Days'
        if type(batch.get(name)) is not int or batch[name] not in (0,1):
            raise ValueError('Explicit Norm0 activation flag required: '+name)
        if batch[name]==1:enabled.append(horizon)
    return tuple(enabled)


def resultsets(*,reports,batch,run_id,output_digest):
    owner=dict(run_id=str(uuid.UUID(str(run_id))),output_digest=sha(output_digest,'report output'))
    horizons=enabled_horizons(batch)
    if not isinstance(reports,list):raise ValueError('Owned typed Reports required')
    result={}
    for horizon in horizons:
        stage=NORM0_EXPORT_STAGES[horizon]
        matches=[r for r in reports if isinstance(r,dict) and r.get('stage')==stage]
        if len(matches)!=1:raise ValueError('Exactly one owned Norm0 horizon family required: '+stage)
        tables=matches[0].get('tables')
        required=('ReportHeader','ReportRows','Norm0Norm1Norm2Report','Norm0_1_2ReportDetails')
        if not isinstance(tables,dict) or any(not isinstance(tables.get(n),list) for n in required):
            raise ValueError('Complete typed Norm0 source required: '+stage)
        headers=_values(tables['ReportHeader'],9,stage+'/ReportHeader')
        if len(headers)!=1:raise ValueError('One owned Norm0 header required')
        values=_values(tables['ReportRows'],9,stage+'/ReportRows')
        if len(values)!=len(tables['Norm0_1_2ReportDetails']):
            raise ValueError('Norm0 detail/export population differs')
        name=f'Norm0_{horizon}days'
        header=tuple(_cell(v,('nvarchar',True,None),name,str(i)) for i,v in enumerate(headers[0]))
        rows=tuple(tuple(_cell(v,kind,name,str(i)) for i,(v,kind) in enumerate(zip(row,NORM_CELLS,strict=True))) for row in values)
        result[name]=dict(**owner,horizon=horizon,stage=stage,source_digest=digest(tables),
            filename=f'Norm_0_Report_{horizon}Days.csv',header_result_set=header,data_result_set=rows,
            occurrence_rule='retained-norm0-30-contract' if horizon==30 else CHRONOLOGICAL_RULE,
            occurrence_classification='EXISTING_30_QUALIFICATION_PRESERVED' if horizon==30 else 'APPROVED_PRODUCTION_CONTRACT_CHANGE')
    return dict(**owner,enabled_horizons=list(horizons),reports=result)


def export_files(*,root,receipt):
    """Serialize verified producer cells under immutable run/digest/horizon paths."""
    run_id=str(uuid.UUID(receipt['run_id']));output_digest=sha(receipt['output_digest'],'report output')
    if receipt['enabled_horizons']!=[h for h in NORM0_EXPORT_STAGES if f'Norm0_{h}days' in receipt['reports']]:
        raise ValueError('Complete enabled Norm0 export roster required')
    expected={f'Norm0_{h}days' for h in receipt['enabled_horizons']}
    if set(receipt['reports'])!=expected:raise ValueError('Norm0 export family roster differs')
    payloads=[]
    for horizon in receipt['enabled_horizons']:
        report=receipt['reports'][f'Norm0_{horizon}days']
        filename=f'Norm_0_Report_{horizon}Days.csv'
        if (report['run_id'],report['output_digest'],report['horizon'],report['stage'],report['filename'])!=(run_id,output_digest,horizon,NORM0_EXPORT_STAGES[horizon],filename):
            raise ValueError('Norm0 export owner/horizon differs')
        payload=norm_report_bytes(report)
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            info=zipfile.ZipInfo(filename,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,payload)
        prefix=f'runs/{run_id}/{output_digest}'
        payloads.append((horizon,prefix+'/output/'+filename,payload,
            prefix+'/download/'+filename.removesuffix('.csv')+'.zip',buffer.getvalue()))
    # Validate/encode the complete roster before making file effects.
    def write(relative,payload):
        if files.owned_path(root,relative).exists():
            return files.verify_file(root,dict(relative_path=relative,
                sha256=hashlib.sha256(payload).hexdigest(),size_bytes=len(payload)))
        return files.write_file(root,relative,payload)
    artifacts=[]
    for horizon,csv_path,payload,zip_path,zipped in payloads:
        csv=write(csv_path,payload);archive=write(zip_path,zipped)
        members=files.zip_members(root,zip_path)
        if members!=[dict(ordinal=0,name=csv_path.rsplit('/',1)[1],sha256=csv['sha256'],size_bytes=csv['size_bytes'])]:
            raise ValueError('Norm0 archive member differs from its owned CSV')
        report=receipt['reports'][f'Norm0_{horizon}days']
        artifacts.append(dict(horizon=horizon,source_digest=report['source_digest'],
            occurrence_rule=report['occurrence_rule'],occurrence_classification=report['occurrence_classification'],
            csv=csv,archive=archive,members=members))
    return dict(run_id=run_id,output_digest=output_digest,artifacts=artifacts)
