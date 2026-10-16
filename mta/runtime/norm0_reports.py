"""Read native Norm0 families only from their actual completed immutable run."""
from mta.application.norm0_reports import resultsets, export_files
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.runtime.validation_storage import read_input
from mta.mdm.initialization_contract import SOURCE_SCHEMA, sha


def read_reports(*,run_id,expected_output_digest):
    run=CalculationRun.objects.get(pk=run_id)
    if run.kind!='DAILY_CHAIN' or run.status!='SUCCEEDED' or run.output_digest!=sha(expected_output_digest,'report output'):
        raise ValueError('Exact completed native Norm0 run/output owner required')
    capture=run.mdm_input_capture
    if capture.status!='CONSUMED' or capture.source.receipt.get('schema')!=SOURCE_SCHEMA:
        raise ValueError('Consumed native Norm0 source required')
    inputs=read_input(run,components=('profile','initialization_binding'))
    binding=inputs.get('initialization_binding')
    if not isinstance(binding,dict) or binding.get('source_digest')!=capture.source.digest:
        raise ValueError('Native Norm0 initialization/source binding differs')
    output=read_outputs(run)  # Existing complete typed receipt/checksum verification.
    from mta.application.native_report_disposition import verify_commit
    disposition=(output['Lineage'] or [{}])[0].get('native_report_disposition')
    verify_commit(disposition,output['Lineage'],run)
    receipt=resultsets(reports=output['Reports'],batch=inputs['profile']['delivery']['batch'],
        run_id=run.pk,output_digest=run.output_digest,lineage=output['Lineage'])
    receipt.update(business_date=run.business_date.isoformat(),initialization_id=binding['id'],source_digest=capture.source.digest)
    return receipt


def export_reports(*,run_id,expected_output_digest,root):
    receipt=read_reports(run_id=run_id,expected_output_digest=expected_output_digest)
    return export_files(root=root,receipt=receipt)
