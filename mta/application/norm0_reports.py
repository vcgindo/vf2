"""Native run-owned Norm0 exports; separate from the accepted O6 profile."""
import hashlib
import io
import json
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


def resultsets(*,reports,batch,run_id,output_digest,lineage=None):
    owner=dict(run_id=str(uuid.UUID(str(run_id))),output_digest=sha(output_digest,'report output'))
    horizons=enabled_horizons(batch)
    if not isinstance(reports,list):raise ValueError('Owned typed Reports required')
    result={}
    disposition = (lineage or [{}])[0].get('native_report_disposition')
    from mta.application import occurrence_text_policy as occurrence_policy
    policy = (lineage or [{}])[0].get(occurrence_policy.KEY)
    if policy is not None:
        occurrence_policy.require_binding(policy)
        if policy['owner']['run_id'] != owner['run_id']:
            raise ValueError('Occurrence availability report owner differs')
        if disposition is not None:
            raise ValueError('Conflicting occurrence availability policies')
    if disposition is not None:
        from mta.application.native_report_disposition import require_binding, verify_export, limitation
        require_binding(disposition)
        if 30 not in horizons:
            raise ValueError('Native report disposition requires its enabled 30-day report')
    for horizon in horizons:
        stage=NORM0_EXPORT_STAGES[horizon]
        matches=[r for r in reports if isinstance(r,dict) and r.get('stage')==stage]
        if len(matches)!=1:raise ValueError('Exactly one owned Norm0 horizon family required: '+stage)
        tables=matches[0].get('tables')
        required=('ReportHeader','ReportRows','Norm0Norm1Norm2Report','Norm0_1_2ReportDetails')
        if not isinstance(tables,dict) or any(not isinstance(tables.get(n),list) for n in required):
            raise ValueError('Complete typed Norm0 source required: '+stage)
        if disposition is not None and horizon == 30:
            verify_export(tables, disposition)
        if policy is not None and horizon == 30:
            occurrence_policy.verify_export(tables, policy, norm=0)
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
        if disposition is not None and horizon == 30:
            result[name]['occurrence_classification'] = 'LEGACY_FLAW/NOT_PARITY'
            result[name]['limitations'] = [limitation(disposition)]
        if policy is not None and horizon == 30:
            result[name].update(occurrence_text_policy=policy,
                occurrence_classification=occurrence_policy.CLASSIFICATION,
                occurrence_text_availability=occurrence_policy.summaries(
                    [dict(stage=stage, tables=tables)], policy)[stage],
                affected_groups=list(occurrence_policy.groups(tables, policy, norm=0)))
    receipt = dict(**owner,enabled_horizons=list(horizons),reports=result)
    if disposition is not None:
        receipt['native_report_disposition'] = disposition
        receipt['qualification'] = 'COMPLETE_WITH_LEGACY_FLAWS'
    if policy is not None:
        receipt[occurrence_policy.KEY] = policy
    return receipt


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
        disposition = receipt.get('native_report_disposition')
        metadata = None
        if disposition is not None:
            from mta.application.native_report_disposition import require_binding, limitation, DISPLAY, KEY
            require_binding(disposition)
            if horizon == 30:
                if report.get('limitations') != [limitation(disposition)] or report['occurrence_classification'] != 'LEGACY_FLAW/NOT_PARITY':
                    raise ValueError('Native report download limitation differs')
                affected = [row for row in report['data_result_set'] if (row[0]['value'],row[2]['value']) == KEY]
                if len(affected) != 1 or affected[0][8]['value'] != '"'+DISPLAY+'"':
                    raise ValueError('Native report download disclosure differs')
                metadata = json.dumps(dict(run_id=run_id,output_digest=output_digest,
                    native_report_disposition=disposition,limitations=report['limitations']),
                    sort_keys=True,separators=(',',':')).encode('utf-8')
            elif 'limitations' in report:
                raise ValueError('Native report disposition cannot extend to another horizon')
        elif 'limitations' in report:
            raise ValueError('Native report download lacks disposition binding')
        policy = receipt.get('occurrence_text_policy')
        if policy is not None and horizon == 30:
            from mta.application import occurrence_text_policy as occurrence_policy
            occurrence_policy.require_binding(policy, norm=0, horizon=30)
            if (policy['owner']['run_id'] != run_id or report.get('occurrence_text_policy') != policy
                    or report.get('occurrence_classification') != occurrence_policy.CLASSIFICATION):
                raise ValueError('Occurrence availability download owner differs')
            metadata = json.dumps(dict(run_id=run_id, output_digest=output_digest,
                occurrence_text_policy=policy, occurrence_text_availability=report['occurrence_text_availability'],
                affected_groups=report['affected_groups']), sort_keys=True,separators=(',',':')).encode('utf-8')
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            info=zipfile.ZipInfo(filename,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,payload)
            if metadata is not None:
                meta = zipfile.ZipInfo(filename.removesuffix('.csv')+'.metadata.json',date_time=(1980,1,1,0,0,0))
                meta.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(meta,metadata)
        prefix=f'runs/{run_id}/{output_digest}'
        payloads.append((horizon,prefix+'/output/'+filename,payload,
            prefix+'/download/'+filename.removesuffix('.csv')+'.zip',buffer.getvalue(),metadata))
    # Validate/encode the complete roster before making file effects.
    def write(relative,payload):
        if files.owned_path(root,relative).exists():
            return files.verify_file(root,dict(relative_path=relative,
                sha256=hashlib.sha256(payload).hexdigest(),size_bytes=len(payload)))
        return files.write_file(root,relative,payload)
    artifacts=[]
    for horizon,csv_path,payload,zip_path,zipped,metadata in payloads:
        csv=write(csv_path,payload);archive=write(zip_path,zipped)
        members=files.zip_members(root,zip_path)
        expected_members=[dict(ordinal=0,name=csv_path.rsplit('/',1)[1],sha256=csv['sha256'],size_bytes=csv['size_bytes'])]
        if metadata is not None:
            expected_members.append(dict(ordinal=1,name=csv_path.rsplit('/',1)[1].removesuffix('.csv')+'.metadata.json',
                sha256=hashlib.sha256(metadata).hexdigest(),size_bytes=len(metadata)))
        if members!=expected_members:
            raise ValueError('Norm0 archive member differs from its owned CSV')
        report=receipt['reports'][f'Norm0_{horizon}days']
        artifacts.append(dict(horizon=horizon,source_digest=report['source_digest'],
            occurrence_rule=report['occurrence_rule'],occurrence_classification=report['occurrence_classification'],
            csv=csv,archive=archive,members=members))
        if metadata is not None:
            if disposition is not None:
                artifacts[-1]['limitations']=report['limitations']
                artifacts[-1]['native_report_disposition']=receipt['native_report_disposition']
            if policy is not None and horizon == 30:
                artifacts[-1].update(occurrence_text_policy=policy,
                    occurrence_text_availability=report['occurrence_text_availability'])
    return dict(run_id=run_id,output_digest=output_digest,artifacts=artifacts)
