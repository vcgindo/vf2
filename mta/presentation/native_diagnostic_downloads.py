"""Diagnostic exports from existing custody or admitted immutable daily facts.

Absent upload audit is unavailable, never an invented empty log. The sole new
projection is InvalidDataReport over the existing selected RejectedMaster.
"""
import json
from inspect import unwrap
from tempfile import SpooledTemporaryFile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from django.db import connection, transaction, DatabaseError
from django.http import FileResponse, JsonResponse

from mta.presentation import views, diagnostic_downloads as original, runtime_placement_downloads
from mta.presentation.context import selected_run, PublicationUnavailable
from mta.presentation.selective import image_query, image_metadata
from mta.application.operational_input_archive import archive_clock
from mta.application.operational_alert_files import invalid_data_bytes
from mta.application.operational_sqlcmd import resultset_bytes
from mta.runtime.relational_state import quote

PATH = 'closing/importer/RejectedMaster'
FIELDS = ('SKUCode', 'WarehouseCode', 'RunDatetime', 'ReasonDescription')
SOURCE_FIELDS = ('SKUCode', 'WhCode', 'RejectionDate', 'ReasonDescription')
TYPES = ('nvarchar(50)', 'nvarchar(50)', 'datetime', 'nvarchar(100)')


def published_names(run):
    from mta.runtime.intake_diagnostic_models import DiagnosticPublication
    from mta.runtime import intake_diagnostics as custody
    try:
        with connection.cursor() as cursor:
            custody.verify_guards(cursor)
    except (ValueError, DatabaseError) as error:
        raise PublicationUnavailable('diagnostic_publication_unavailable') from error
    return set(DiagnosticPublication.objects.filter(
        initialization__source_id=run.mdm_input_capture.source_id).values_list('selector', flat=True))


def native_full():
    from mta.presentation.installation_metadata import publication_configured
    from mta.presentation import native_publication
    return publication_configured() and native_publication.enabled()


def unavailable_reason(run, name):
    if name in original.UPLOAD_SELECTORS:
        from mta.runtime.native_audit_models import NativeUploadAudit
        return ('upload_log_file_not_published' if NativeUploadAudit.objects.filter(run=run).exists()
                else 'upload_log_audit_not_captured')
    from mta.runtime.intake_diagnostic_models import IntakeDiagnostic
    return ('fullkit_abort_file_not_published' if IntakeDiagnostic.objects.filter(
        initialization__source_id=run.mdm_input_capture.source_id, kind='FULLKIT').exists()
        else 'fullkit_abort_not_captured')


def invalid_archive(run):
    relation, params = image_query(run, PATH)
    # SQL datetime stores the approved local wall clock, not its UTC instant.
    clock = archive_clock(run.business_date)['clock'].replace(tzinfo=None)
    sql = ('SELECT ' + ','.join(quote(name) for name in SOURCE_FIELDS) +
           ' FROM (' + relation + ') rejected WHERE "RejectionDate"=%s'
           ' ORDER BY "ReasonCode" DESC NULLS LAST')
    output = SpooledTemporaryFile(max_size=4 * 1024 * 1024, mode='w+b')
    try:
        info = ZipInfo('InvalidDataReport.csv', (run.business_date.year,
            run.business_date.month, run.business_date.day, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        with ZipFile(output, 'w') as archive, archive.open(info, 'w') as member:
            member.write(invalid_data_bytes([], clock.isoformat()))
            with transaction.atomic(), connection.chunked_cursor() as cursor:
                cursor.execute(sql, [*params, clock])
                while rows := cursor.fetchmany(500):
                    member.write(resultset_bytes([dict(fields=FIELDS, types=TYPES, rows=rows)]))
        output.seek(0)
        return output, 'InvalidDataReport.zip', 'application/zip'
    except BaseException:
        output.close()
        raise


@views.endpoint('GET')
def report_paths(request, payload):
    response = unwrap(runtime_placement_downloads.report_paths)(request, payload)
    if not native_full():
        return response
    run = selected_run()
    names = published_names(run)
    # Present qualified source image permits a real header-only export too.
    image_metadata(run, PATH)
    names.add('InvalidDataReport')
    body = json.loads(response.content)
    for name in original.SELECTORS:
        if name not in names:
            body['data'].pop(name, None)
    return JsonResponse(body, status=response.status_code)


@views.endpoint('GET')
def download_report(request, payload, *, report_name):
    if report_name not in original.SELECTORS or not native_full():
        return unwrap(runtime_placement_downloads.download_report)(request, payload, report_name=report_name)
    identity = views.identity(request)
    try:
        original.require_entitlement(identity)
    except PermissionError as error:
        return JsonResponse({'error': str(error)}, status=403)
    run = selected_run()
    try:
        # The original reader authenticates custody BEFORE resolving absence.
        stream, filename, content_type = original.open_file(run, identity, report_name)
    except PublicationUnavailable as absence:
        if str(absence) != 'diagnostic_not_published_for_source':
            # Broken guards, receipts or files can never enter the fallback.
            raise
        if report_name != 'InvalidDataReport':
            return JsonResponse(dict(error='diagnostic_not_available', reportName=report_name,
                reason=unavailable_reason(run, report_name)), status=404)
        try:
            stream, filename, content_type = invalid_archive(run)
        except PublicationUnavailable:
            raise
        except (DatabaseError, ValueError, OSError, KeyError, TypeError) as error:
            raise PublicationUnavailable('native_invalid_data_report_unavailable') from error
    return FileResponse(stream, as_attachment=True, filename=filename, content_type=content_type)
