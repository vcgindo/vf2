"""Source-bound report operations used by the operational daily runner."""
from mta.application.operational_exceptions import (
    bpr_exception_rows, bpr_exception_resultsets, no_norm_at_parent_rows,
)
from mta.application.operational_norm_reports import norm_report_resultsets
from mta.application.operational_report_files import (
    SOURCES, bpr_exception_report_files, no_norm_parent_report_files, norm_report_files, upload_log_report_files,
)
from mta.application.operational_sqlcmd import resultset_bytes, no_norm_parent_bytes, norm_report_bytes
from mta.domain.complete_daily_scalars import ascii_equal
from mta.runtime.operational_models import OperationalAttempt
from mta.runtime.operational_attempts import configuration_value, _identity
from mta.runtime.operational_effects import operation, record_file
from mta.runtime.operational_native import save_population
from mta.runtime.operational_readers import read_report_inputs
from mta.runtime.operational_opening import upload_inputs
from mta.application.operational_upload_logs import LOG_BINDINGS, clear_ui_upload_log_history, export_ui_upload_log
from mta.application.operational_sqlcmd import upload_log_bytes
from mta.application import operational_bor as bor
from mta.application.operational_sqlcmd import bor_report_bytes
from mta.application.operational_report_files import bor_report_files
from mta.runtime.operational_bor import bor_inputs
from mta.runtime.operational_archive import archive_inputs
from mta.application.operational_input_archive import write_input_archive


REPORT_OPERATIONS = {
    'O1': dict(name='BOROrderAllocation', stage='bor-order-allocation', source_digest=SOURCES['bor'][1]),
    'O2': dict(name='BPRExceptionReport', stage='bpr-exception-files', source_digest=SOURCES['bpr_exceptions'][1]),
    'O3': dict(name='NoNormParentReport', stage='parent-norm', source_digest=SOURCES['parent_norm'][1]),
    'O4': dict(name='InputDataArchive', stage='post-bpr-input-download',
               source_digest='d46ade48ab45823ae3b29a6d6808f33e1802afdccf98f87fc0c81b6050146b52'),
    'O5': dict(name='UIUploadLogs', stage='upload-logs', source_digest=SOURCES['upload_roster'][1]),
    'O6': dict(name='NormReports', stage='dbm-files', source_digest=SOURCES['dbm_change'][1]),
}


def _record_final_files(effect, receipt):
    """Record only surviving files, including actual decompressed ZIP members."""
    paths = {}
    def visit(value):
        if isinstance(value, dict):
            if {'relative_path', 'sha256', 'size_bytes'} <= set(value):
                paths[value['relative_path']] = value
            else:
                for key, item in value.items():
                    # These receipts describe CSVs intentionally removed by their
                    # canonical wrappers, not surviving operation artifacts.
                    if key not in ('source_csv',):
                        visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)
    visit(receipt)
    for path in sorted(paths):
        record_file(effect, relative_path=path, role=path.split('/')[0],
                    archive=path.lower().endswith('.zip'))


def materialize_report_operation(attempt_id, *, group, archive_writer):
    """One durable report operation; never declares whole-attempt completion."""
    if group not in REPORT_OPERATIONS:
        raise ValueError('Supported report operation required')
    owner = OperationalAttempt.objects.select_related('run', 'configuration').get(pk=attempt_id)
    if owner.status != 'RUNNING':
        raise ValueError('Report operation requires a running attempt')
    configuration = configuration_value(owner.configuration)
    current = _identity(owner.run)
    if (current['output_digest'] != owner.run_output_digest or current['action_digest'] != owner.action_digest
            or current['source_digest'] != owner.source_digest):
        raise ValueError('Report attempt source/action identity drift')
    specification = REPORT_OPERATIONS[group]
    roster = configuration['bindings'].get('operation_roster', [])
    matches = [row for row in roster if row.get('group') == group]
    if len(matches) != 1 or {k: matches[0].get(k) for k in specification} != specification:
        raise ValueError('Canonical report operation roster differs')
    source_owner = (OperationalAttempt.objects.select_related('run', 'configuration').get(pk=owner.repair_of_id)
                    if owner.repair_of_id is not None else owner)
    inputs = (bor_inputs(source_owner) if group == 'O1' else archive_inputs(source_owner) if group == 'O4' else
              upload_inputs(source_owner) if group == 'O5' else
              read_report_inputs(run_id=owner.run_id, expected_output_digest=owner.run_output_digest)['sources'][group])
    with operation(owner, **matches[0]) as effect:
        if group == 'O1':
            rows = bor.collect_bor_order_allocation(**inputs['collect'], equal=ascii_equal)
            save_population(owner, 'BORWithOrderAllocation', 'BPR/BORWithOrderAllocation', rows)
            report = bor.generate_bor_order_allocation(bor_rows=rows, **inputs['report'], equal=ascii_equal)
            receipt = bor_report_files(root=owner.root, report_bytes=bor_report_bytes(report))
            history = bor.collect_bor_order_allocation_history(opening_history=inputs['bor_history'],
                current_bor=rows, business_date=owner.business_date.isoformat(), horizon=90)
            save_population(owner, 'closing/BOR_OrderAllocationHistory', 'BPR/BOR_OrderAllocationHistory', history)
            save_population(owner, 'closing/RRR_OrderAllocation', 'BPR/RRR_OrderAllocation', inputs['current_rrr'])
            history = bor.collect_rrr_order_allocation_history(opening_history=inputs['rrr_history'],
                current_rrr=inputs['current_rrr'], business_date=owner.business_date.isoformat(), horizon=90)
            save_population(owner, 'closing/RRR_OrderAllocationHistory', 'BPR/RRR_OrderAllocationHistory', history)
        elif group == 'O2':
            rows = bpr_exception_rows(**{name: inputs[name] for name in
                ('bpr_master', 'daily_consumption', 'business_date')}, equal=ascii_equal)
            save_population(owner, 'BPRExceptions', 'BPR/BPRExceptions', rows)
            payload = resultset_bytes(bpr_exception_resultsets(exceptions=rows,
                sku_descriptions=inputs['sku_descriptions'], site_descriptions=inputs['site_descriptions'],
                equal=ascii_equal)) if rows else None
            receipt = bpr_exception_report_files(root=owner.root, exception_count=len(rows),
                report_bytes=payload, archive_writer=archive_writer)
        elif group == 'O3':
            rows = no_norm_at_parent_rows(**inputs, equal=ascii_equal)
            save_population(owner, 'NoNormAtParentReport', 'Intermediate/NoNormAtParentReport', rows)
            receipt = no_norm_parent_report_files(root=owner.root, report_bytes=no_norm_parent_bytes(rows),
                                                  archive_writer=archive_writer)
        elif group == 'O4':
            receipt=write_input_archive(owner.root,**inputs,archive_writer=archive_writer)
        elif group == 'O5':
            payloads = {}
            save_population(owner, 'closing/UIUploadLogActionType', 'Importer/UIUploadLogActionType', inputs['actions'])
            for table, report_name in LOG_BINDINGS:
                rows = clear_ui_upload_log_history(table_name=table, rows=inputs['logs'][table],
                    today=owner.business_date.isoformat(), history_horizon=inputs['horizon'])
                save_population(owner, 'closing/' + table, 'Importer/' + table, rows)
                payloads[report_name] = upload_log_bytes(export_ui_upload_log(
                    table_name=table, rows=rows, action_types=inputs['actions']))
            receipt = upload_log_report_files(root=owner.root, payloads=payloads,
                archive_writer=archive_writer, client_folder=inputs['client_folder'])
        else:
            reports = norm_report_resultsets(**inputs)
            receipt = norm_report_files(root=owner.root,
                payloads={name: norm_report_bytes(report) for name, report in reports.items()},
                archive_writer=archive_writer)
        _record_final_files(effect, receipt)
    return effect
