"""Permissioned whole-file downloads from a selected immutable placement."""
from contextlib import ExitStack
import os
from pathlib import Path

from mta.presentation.context import PublicationUnavailable,scope
from mta.presentation.permissions import _sql_equal
from mta.runtime import runtime_report_publication as publication

SELECTORS={'Spike_Order_Dump':7,'TotalReqReport_YYYY-MM-DD':10}


def _binding(view):
    from mta.presentation.runtime_report_view import applicable_reference
    if not applicable_reference(view.reference):
        raise PublicationUnavailable('runtime_reports_not_configured_for_selected_view')
    row=publication.read(view.run.pk,verify_bytes=False)
    if (row.phase_id!=view.reference.report_generation.phase_id
            or row.configuration_digest!=view.reference.runtime_reports_digest
            or row.scope_request_digest!=view.reference.metadata['scope_request_digest']):
        raise PublicationUnavailable('runtime_report_selected_owner_differs')
    raw,request,config,anchor=publication._configuration(view.run)
    return row,raw,request,config


def report_paths(view):
    from mta.presentation.runtime_report_view import applicable_reference
    if not applicable_reference(view.reference):return {}
    row,_raw,_request,config=_binding(view)
    events={event['report_id']:event for event in row.metadata['candidate']['reports']}
    result={}
    for definition in config['RuntimeReports']:
        selector=definition['ReportName']
        if SELECTORS.get(selector)!=definition['Id']:
            raise PublicationUnavailable('runtime_report_selector_not_qualified')
        event=events[definition['Id']]
        extension='zip' if definition['Compression'] else 'csv'
        result[selector]=dict(path='',downloadName=event['last_generated_file_name']+'.'+extension,
            reportName=selector,fileType='application/zip' if extension=='zip' else 'text/csv')
    return result


def allowed(rows,report_id,products,locations):
    """Deny a partial-file scope; absent nullable parent is not a location code."""
    if not products or not locations:return False
    if report_id not in (7,10):raise ValueError('Unqualified runtime report permission projection')
    parent='FirstServicingWhCode' if report_id==7 else 'ParentWhCode'
    for row in rows:
        if (not any(_sql_equal(row['SKUCode'],code) for code in products)
                or not any(_sql_equal(row['WhCode'],code) for code in locations)
                or row[parent] is not None and not any(_sql_equal(row[parent],code) for code in locations)):
            return False
    return True


def permission_rows(projected,report_id):
    """The real CSV producer yields positional cells, not row dictionaries."""
    parent='FirstServicingWhCode' if report_id==7 else 'ParentWhCode'
    columns=projected['columns'];fields=('SKUCode','WhCode',parent)
    if report_id not in (7,10) or any(columns.count(name)!=1 for name in fields):
        raise PublicationUnavailable('runtime_report_permission_columns_differ')
    positions=[columns.index(name) for name in fields]
    for cells in projected['rows']:
        if len(cells)!=len(columns):
            raise PublicationUnavailable('runtime_report_permission_row_width_differs')
        yield {name:cells[index] for name,index in zip(fields,positions)}


def _open(root,relative,receipt):
    from mta.runtime.scoped_pick_files import _folder,_open as open_member,_stream_metadata
    from mta.application.operational_io import owned_path
    if os.name!='posix' or not hasattr(os,'O_NOFOLLOW'):
        raise PublicationUnavailable('runtime_report_safe_open_unavailable')
    path=owned_path(root,relative)
    with ExitStack() as stack:
        descriptor=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        stack.callback(os.close,descriptor)
        for part in path.parts[1:-1]:descriptor=stack.enter_context(_folder(descriptor,part))
        stream=open_member(descriptor,path.name)
    try:
        if _stream_metadata(stream)!=dict(size=receipt['size_bytes'],sha256=receipt['sha256']):
            raise PublicationUnavailable('runtime_report_changed_before_open')
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def open_file(view,payload,selector):
    from mta.application.runtime_report_projection import project
    identity=SELECTORS.get(selector)
    if identity is None:raise PublicationUnavailable('runtime_report_selector_not_qualified')
    row,raw,request,config=_binding(view)
    _bound,definitions,inputs=publication._sources(row.phase,request,config,
        row.metadata['candidate']['last_generated_before'])
    definition=next(value for value in definitions if value['Id']==identity)
    products,locations=scope(payload,attributes=view.planning.attributes())
    rows=permission_rows(project(definition,inputs[identity]['sources']),identity)
    if not allowed(rows,identity,products,locations):
        raise PermissionError('runtime_report_whole_file_scope_denied')
    published=publication.read(view.run.pk,verify_bytes=True)
    from mta.application.runtime_report_files import layout
    selected=layout(definition,publication._variables(view.run))
    relative=selected['download']
    entry=published.metadata['catalogue'].get(relative)
    if entry is None or entry['candidate_id']!=str(published.pk):
        raise PublicationUnavailable('runtime_report_download_custody_differs')
    root=publication._root(view.run,raw)/str(published.pk)
    return _open(root,relative,entry['file']),Path(relative).name,('application/zip' if definition['Compression'] else 'text/csv')
