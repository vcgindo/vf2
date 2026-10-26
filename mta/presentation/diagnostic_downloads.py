"""Finite diagnostic names and original operational-file custody checks."""
from pathlib import PurePosixPath

from django.core.exceptions import ObjectDoesNotExist
from mta.presentation.context import PublicationUnavailable
from mta.presentation.runtime_report_downloads import _open


UPLOAD_SELECTORS = {
    'NMSAddNewSKULoc':'NMSAddNewSKULocLog',
    'NMSModifySKULoc':'NMSModifySKULocLog',
    'NMSRemoveSKULoc':'NMSRemoveSKULocLog',
    'NMSLocMaster':'NMSLocMasterLog',
    'NMSSKUMaster':'NMSSKUMasterLog',
    'NMSSOBMaster':'NMSSOBMasterLog',
    'NMSMOQMaster':'NMSMOQMasterLog',
    'ForceNormChangeUpload':'ForceNormChangeUploadLog',
}
SELECTORS = {
    **{name:dict(group='O5',path='download/UIUploadLogs/'+basename+'.zip',member=basename+'.csv')
       for name,basename in UPLOAD_SELECTORS.items()},
    **{name:dict(group='O7',path='download/'+name+'.zip',member=name+'.csv')
       for name in ('InvalidDataReport','DailyDataUnavailabilityReport')},
}


def require_entitlement(identity):
    if not isinstance(identity,dict) or identity.get('entitlements')!=['mta-report-urls']:
        raise PermissionError('mta_report_download_forbidden')


def open_file(run,identity,selector):
    """Read the latest explicitly published file for the admitted source.

    Publication order replaces the legacy single download file. It does not
    choose a calculation day or promote a failed day into serving selection.
    """
    require_entitlement(identity)
    if selector not in SELECTORS:raise PublicationUnavailable('diagnostic_selector_unqualified')
    from django.db import connection
    from mta.runtime.models import ProductionInitialization
    from mta.runtime.intake_diagnostic_models import DiagnosticPublication
    from mta.runtime import intake_diagnostics as custody,diagnostic_publication as publication
    from mta.serialization import digest
    try:
        with connection.cursor() as cursor:custody.verify_guards(cursor)
        initial=ProductionInitialization.objects.get(source_id=run.mdm_input_capture.source_id)
        selected=DiagnosticPublication.objects.filter(initialization=initial,selector=selector).select_related(
            'operational_file__operation__attempt__run').order_by('-pk').first()
        if selected is None:raise PublicationUnavailable('diagnostic_not_published_for_source')
        if selected.failure_archive_id is not None:
            owner,archive=publication.read_archive(selected.failure_archive_id)
            if owner.initialization_id!=initial.pk or publication.selector(owner)!=selector:
                raise PublicationUnavailable('diagnostic_failure_source_differs')
            owner_digest=archive.digest
        else:
            row=selected.operational_file
            if row.operation.attempt.run.mdm_input_capture.source_id!=initial.source_id:
                raise PublicationUnavailable('diagnostic_operational_source_differs')
            owner_digest=publication.operational_digest(row)
        if selected.digest!=digest(publication._publication_body(selected,owner_digest)):
            raise PublicationUnavailable('diagnostic_publication_identity_differs')
        if selected.failure_archive_id is None:
            return open_operational_file(row.operation.attempt.run,selector,row.pk)
        stream=_open(archive.root,archive.relative_path,dict(sha256=archive.sha256,size_bytes=archive.size_bytes))
        return stream,PurePosixPath(archive.relative_path).name,'application/zip'
    except (ObjectDoesNotExist,OSError,ValueError,KeyError,TypeError) as error:
        if isinstance(error,PublicationUnavailable):raise
        raise PublicationUnavailable('diagnostic_publication_unavailable') from error


def open_operational_file(run,selector,file_id):
    """Read an explicitly selected existing receipt, never infer a latest file.

    The caller supplies the source-qualified diagnostic owner. Failed intake
    custody is a different owner and cannot enter this successful-run path.
    """
    from mta.runtime.operational_models import OperationalFile
    from mta.runtime.operational_attempts import configuration_value, _identity
    from mta.runtime.operational_repair import resolve_operational_file
    from mta.runtime.operational_reports import REPORT_OPERATIONS
    from mta.runtime.operational_alert_runner import ALERT_OPERATION
    from mta.application.operational_input_archive import archive_clock
    if selector not in SELECTORS:
        raise PublicationUnavailable('diagnostic_selector_unqualified')
    expected=SELECTORS[selector]
    try:
        row=OperationalFile.objects.select_related('operation__attempt__configuration','operation__attempt__run').get(pk=file_id)
        effect=row.operation;owner=effect.attempt
        if (owner.run_id!=run.pk or owner.run.status!='SUCCEEDED' or owner.run.kind!='DAILY_CHAIN'
                or owner.status!='SUCCEEDED' or effect.status!='SUCCEEDED'
                or owner.business_date!=owner.run.business_date
                or owner.clock!=archive_clock(owner.business_date)['clock']
                or row.role!='download' or row.relative_path!=expected['path']
                or effect.group!=expected['group']):
            raise PublicationUnavailable('diagnostic_operational_owner_differs')
        specification=REPORT_OPERATIONS['O5'] if expected['group']=='O5' else ALERT_OPERATION
        if any(getattr(effect,key)!=value for key,value in specification.items()):
            raise PublicationUnavailable('diagnostic_producer_differs')
        config=configuration_value(owner.configuration)
        roster=[item for item in config['bindings'].get('operation_roster',[]) if item.get('group')==effect.group]
        if (len(roster)!=1 or roster[0].get('ordinal')!=effect.ordinal
                or any(roster[0].get(key)!=value for key,value in specification.items())):
            raise PublicationUnavailable('diagnostic_configuration_differs')
        current=_identity(owner.run)
        if any(current[key]!=getattr(owner,'run_output_digest' if key=='output_digest' else key) for key in current):
            raise PublicationUnavailable('diagnostic_source_changed')
        actual=resolve_operational_file(row)
        members=list(actual.members.order_by('ordinal').values('ordinal','name','sha256','size_bytes'))
        if len(members)!=1 or members[0]['ordinal']!=0 or members[0]['name']!=expected['member']:
            raise PublicationUnavailable('diagnostic_archive_member_differs')
        stream=_open(actual.operation.attempt.root,actual.relative_path,
            dict(size_bytes=actual.size_bytes,sha256=actual.sha256))
        return stream,PurePosixPath(expected['path']).name,'application/zip'
    except (ObjectDoesNotExist,ValueError,KeyError,TypeError) as error:
        if isinstance(error,PublicationUnavailable): raise
        raise PublicationUnavailable('diagnostic_operational_file_unavailable') from error
