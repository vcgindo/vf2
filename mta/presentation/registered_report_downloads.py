"""The two existing PostBPR selectors under registered intermediate custody.

Terminal-only reports remain unavailable at early stops. No new URL, selector,
producer or file repair is introduced; permissions cover the whole stored file.
"""
from pathlib import Path

from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation import registered_report_view as attachment
from mta.presentation.runtime_report_downloads import SELECTORS, allowed, permission_rows, _open
from mta.runtime import runtime_report_placement_publication as publication
from mta.runtime import runtime_report_stage_storage as images


def binding(view):
    config, request_digest = attachment.configuration(view.run)
    if (not attachment.applicable_reference(view.reference)
            or view.reference.metadata['runtime_reports'] != config
            or view.reference.metadata['scope_request_digest'] != request_digest):
        raise PublicationUnavailable('registered_download_read_reference_differs')
    if hasattr(view, 'dbm_phase'):
        attachment.require_dbm(view, view.dbm_phase)
    raw, _request, definitions, _anchor = publication.configuration(view.run)
    row = publication.read(view.run.pk, placement='PostBPR', verify_bytes=False)
    if (dict(id=str(row.pk),digest=row.digest) != config['post_bpr']
            or row.phase_id != view.bpr.sources.acceptance_id):
        raise PublicationUnavailable('registered_download_publication_differs')
    selected = {item['ReportName']:item for item in definitions['RuntimeReports']
                if item['Placement']=='PostBPR' and item['Active']}
    if {name:item['Id'] for name,item in selected.items()} != SELECTORS:
        raise PublicationUnavailable('registered_download_selector_roster_differs')
    return raw, selected, row


def report_paths(view):
    _raw, definitions, row = binding(view)
    result = {}
    for selector, definition in definitions.items():
        events = [event for event in row.metadata['candidate']['reports']
                  if event['report_id']==definition['Id']]
        if len(events)!=1:
            raise PublicationUnavailable('registered_download_event_differs')
        extension = 'zip' if definition['Compression'] else 'csv'
        result[selector] = dict(path='',downloadName=events[0]['last_generated_file_name']+'.'+extension,
            reportName=selector,fileType='application/zip' if extension=='zip' else 'text/csv')
    return result


def open_file(view, payload, selector):
    from mta.application.runtime_report_projection import describe, project
    from mta.application.runtime_report_files import layout
    if selector not in SELECTORS:
        raise PublicationUnavailable('registered_download_selector_unqualified')
    raw, definitions, row = binding(view)
    definition = definitions[selector]
    manifest = row.metadata['authority']['images']
    logical = set(describe(definition)['sources'].values())
    fields = {name:([item[0] for item in manifest['images'][name]['fields']]
        or [field for field,_kind in images.LOGICAL[name]]) for name in logical}
    sources = images.read(view.run, manifest, candidate_id=str(row.pk), placement='PostBPR',fields=fields)
    products, locations = scope(payload, attributes=view.planning.attributes())
    if not allowed(permission_rows(project(definition,sources),definition['Id']),
                   definition['Id'],products,locations):
        raise PermissionError('runtime_report_whole_file_scope_denied')
    published = publication.read(view.run.pk, placement='PostBPR', verify_bytes=True)
    if published.pk != row.pk or published.digest != row.digest:
        raise PublicationUnavailable('registered_download_publication_changed')
    relative = layout(definition,publication.variables(view.run))['download']
    entry = published.metadata['catalogue'].get(relative)
    if entry is None or entry['candidate_id'] != str(published.pk):
        raise PublicationUnavailable('registered_download_file_custody_differs')
    return (_open(publication.root(view.run,raw)/str(published.pk),relative,entry['file']),
            Path(relative).name,'application/zip' if definition['Compression'] else 'text/csv')
