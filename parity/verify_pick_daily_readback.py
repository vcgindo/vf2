"""Read-only real-route proof. Never invokes a daily or Pick calculation."""
import argparse, hashlib, json, os
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.runtime.validation_storage import read_input
from mta.application.complete_daily_inputs import pick_report
from mta.application.complete_daily_batch_files import PICK_NAMES,reports_from_pick_state,sqlcmd_bytes
from mta.serialization import storage,digest
from parity.output_archive import OutputArchive

def run(execution, destination):
    execution=Path(execution);destination=Path(destination)
    e=json.loads(execution.read_text())
    results=[]
    for receipt in e['days']:
        row=CalculationRun.objects.get(pk=receipt['run_id'])
        output=read_outputs(row);raw=read_input(row)
        archive=OutputArchive(execution.parent/receipt['output_archive'])
        archive.verify(row.output_digest,row.validation_digest)
        calculations={r['capability']:r['rows'] for r in archive.iter_rows('CalculationOutputs')}
        closing=output['ClosingState'][0]
        traced_closing=list(archive.iter_rows('ClosingState'))[0]
        assert closing==traced_closing,'Exact operational ordinal reconstruction differs'
        assert digest(output['ClosingState'])==receipt['closing_digest']
        logistics=raw['profile']['calculation']['logistics']
        sources=dict(pick_rows=pick_report(rationed=output['BPRReports'][0]['vf_RationedReqReport'],
                    bands=calculations['r1_ration_bifurcation']),
            sku_attributes=closing['importer']['SkuAttributeData'],
            location_attributes=closing['importer']['LocationAttributeData'],
            vehicles=[dict(VehicleID=v['vehicle_id'],VehicleName=v['name'],Weight=v['weight_capacity'],Volume=v['volume_capacity']) for v in logistics['vehicles']],
            location_vehicles=[dict(LocationID=v['location_code'],VehicleID=v['vehicle_id']) for v in logistics['location_vehicles']])
        assert {n:digest(v) for n,v in sources.items()}==output['Lineage'][0]['pick_source_digests'],'Actual Pick input source reconstruction differs'
        complete=closing['complete'];reports=reports_from_pick_state(complete);files=[]
        for kind,filename in PICK_NAMES.items():
            expected=sqlcmd_bytes(reports[kind]['resultsets'])
            for folder in ('output','download'):
                path=Path(raw['pick_output_root'])/str(row.pk)/folder/filename
                assert path.read_bytes()==expected,'Own persisted rows/file bytes differ'
                files.append(dict(path=str(path),sha256=hashlib.sha256(expected).hexdigest(),bytes=len(expected)))
        if row.predecessor_id:
            assert raw['opening'] is None
            assert output['Lineage'][0]['run_id']==str(row.predecessor_id)
            assert output['Lineage'][0]['output_digest']==row.predecessor.output_digest
        results.append(dict(run_id=str(row.pk),date=row.business_date.isoformat(),predecessor_id=str(row.predecessor_id) if row.predecessor_id else None,
            input_digest=row.input_digest,output_digest=row.output_digest,production_digest=row.production_digest,
            source_digests=output['Lineage'][0]['pick_source_digests'],sources=storage(sources),modern_state=complete,
            file_copies=files,actions=receipt['commands'],operational_ordinal_readback='PASS'))
    result=dict(schema='pick-real-route-readback-v1',status='PASS',scope='actual modern daily route; native Pick-stage comparison is separate',
        execution_sha256=hashlib.sha256(execution.read_bytes()).hexdigest(),days=results,business_day_calls=0)
    with destination.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(dict(status='PASS',days=len(results),path=str(destination))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execution',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.execution,a.output)
