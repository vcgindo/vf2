"""Retain approved BPR policy/files when its owned TEST day reaches terminal.

No producer runs here. The original phase, declarations and physical files
remain their owners; the completed day supplies current permission attributes.
"""
from types import SimpleNamespace
from django.conf import settings
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.request_scope import once_per_request
from mta.runtime.bpr_history_completion import AUTHORITY
from mta.serialization import digest


def applicable(run):
    return str(run.pk) == AUTHORITY['run']


@once_per_request
def binding(run):
    from mta.runtime.receipt_integrity import verify_root
    from mta.runtime.bpr_history_completion import verified
    from mta.runtime.scoped_pick_files import _accepted
    if not applicable(run) or run.status != 'SUCCEEDED':
        raise PublicationUnavailable('terminal_bpr_delivery_owner_required')
    verify_root(run)
    completion = verified(run)
    phase = _accepted(completion.phase_id, completion.phase_digest)
    from mta.presentation.scoped_sources import bind
    from mta.runtime.scoped_actions import revision
    sources = bind(phase.pk, expected_digest=phase.digest, action_revision=revision(run))
    return SimpleNamespace(run=run, run_id=run.pk, phase=phase, bpr=SimpleNamespace(sources=sources))


def output_policy(run, day):
    from mta.presentation.scoped_bor import policy
    if (day.get('production_report_schema') != 'fresh-production-source-inputs-v1'
            or day.get('production_report_policy') != AUTHORITY['policy']):
        raise PublicationUnavailable('terminal_bpr_original_policy_differs')
    return policy(binding(run))['output_contract']


def projected_rows(run, name, fields):
    """Reuse the already qualified BPR projection without editing source images."""
    from django.db import connection
    from mta.presentation.scoped_bor import BorBinding, policy
    from mta.runtime.relational_state import quote
    view = binding(run)
    bound = BorBinding(run, view, view.phase, policy(view)['output_contract'])
    sql, params = bound.source_query(name)
    with connection.cursor() as cursor:
        cursor.execute('SELECT ' + ','.join(quote(field) for field in fields)
                       + ' FROM (' + sql + ') original_bpr ORDER BY vf_ordinal', params)
        return [dict(zip(fields, row)) for row in cursor.fetchall()]


def report_paths(values):
    if str(settings.VF_MTA_PUBLISHED_RUN) != AUTHORITY['run']:
        return values
    from mta.presentation.context import selected_run
    from mta.presentation import scoped_batch_downloads
    view = binding(selected_run())
    if scoped_batch_downloads.selected(view) is not None:
        from mta.presentation.scoped_bor import policy
        policy(view)
        values = dict(values, BOR_OrderAllocation=dict(path='', downloadName='BOR_OrderAllocation.csv',
            reportName='Buyer Order Allocation Report', fileType='text/csv'))
    return values


def open_archive(run):
    from mta.presentation import scoped_artifacts
    values = scoped_artifacts.configured()
    if values is None:
        raise PublicationUnavailable('terminal_bpr_input_archive_not_configured')
    return scoped_artifacts.open_archive(binding(run), *values), 'InputData.zip'


def open_report(run, payload, report_name):
    from mta.presentation import pick_downloads as pick, scoped_batch_downloads
    from mta.presentation.permissions import _sql_equal
    view = binding(run)
    if report_name == 'BOR_OrderAllocation':
        from mta.presentation.scoped_bor import policy
        policy(view)
        from mta.runtime.production_report_storage import read
        rows = read(run, 'BORWithOrderAllocation')
        if digest(rows) != AUTHORITY['sources']['BOR_OrderAllocationHistory']['current_digest']:
            raise PublicationUnavailable('terminal_bpr_allocation_source_changed')
        products, locations = scope(payload, attributes=pick._attributes(run))
        if (not all(any(_sql_equal(row['SKUCode'], code) for code in products) for row in rows)
                or not all(any(_sql_equal(row[field], code) for code in locations)
                           for row in rows for field in ('WhCode', 'SupplierCode'))):
            raise pick.PickDownloadDenied('selected_run_bor_file_scope_denied')
        return scoped_batch_downloads.open_file(view), 'BOR_OrderAllocation.csv'
    if report_name not in pick.REPORTS:
        raise pick.PickDownloadDenied('unknown_pick_report')
    state = pick._complete_state(run)
    if not pick._fully_scoped(run, payload, state, report_name):
        raise pick.PickDownloadDenied('selected_run_pick_scope_denied')
    from mta.runtime.scoped_pick_files import open_file
    sources = view.bpr.sources
    stream = open_file(sources.acceptance_id, pick.REPORTS[report_name], expected_digest=sources.acceptance_digest)
    try:
        # Both owners must describe these same bytes; never copy/regenerate a file.
        for chunk in pick._expected_chunks(state, report_name):
            if stream.read(len(chunk)) != chunk:
                raise pick.PickDownloadDenied('terminal_bpr_pick_population_differs')
        if stream.read(1):
            raise pick.PickDownloadDenied('terminal_bpr_pick_population_differs')
        stream.seek(0)
        return stream, pick.REPORTS[report_name]
    except BaseException:
        stream.close()
        raise
