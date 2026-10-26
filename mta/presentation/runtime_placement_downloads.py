"""Terminal eight-report downloads from the accepted placement catalogue.

Keep the original endpoint and scoped-reader paths for all prior requests.
This adapter neither prepares a read graph nor activates a serving selection.
"""
from pathlib import Path
from inspect import unwrap

from django.conf import settings
from django.http import FileResponse,JsonResponse

from mta.presentation import views
from mta.presentation.context import PublicationUnavailable,scope,selected_run
from mta.presentation.request_scope import once_per_request
from mta.presentation.runtime_report_downloads import allowed,permission_rows,_open
from mta.runtime import runtime_report_placement_publication as publication
from mta.runtime import runtime_report_stage_storage as images

SELECTORS={'BOR WH Efficiency report':2,'RRR WH Efficiency report':3,
    'BOR_Color_Bandwise':4,'Chennai_BOR_OrderAllocation':5,'Silvasa_BOR_OrderAllocation':6,
    'Spike_Order_Dump':7,'BOR_OrderAllocationHistory':8,'TotalReqReport_YYYY-MM-DD':10}


@once_per_request
def _selected():
    from mta.runtime.models import CalculationRun
    from mta.runtime.runtime_report_request import SCHEMA
    identifier=getattr(settings,'VF_MTA_PUBLISHED_RUN','')
    if not identifier:return None
    run=CalculationRun.objects.filter(pk=identifier).only('id','input_payload').first()
    if run is None:return None
    from mta.runtime.input_reader import read_input
    request=read_input(run,components=('scope_request',)).get('scope_request')
    if not isinstance(request,dict) or request.get('schema')!=SCHEMA:return None
    # Same complete atomic selection/admission as other terminal endpoints.
    selected=selected_run()
    if selected.pk!=run.pk:raise PublicationUnavailable('placement_selected_run_changed')
    from mta.runtime.receipt_integrity import verify_root
    verify_root(selected)
    return selected


@once_per_request
def binding(run):
    raw,request,config,_anchor=publication.configuration(run)
    if run.status!='SUCCEEDED':raise PublicationUnavailable('placement_terminal_owner_required')
    rows={placement:publication.read(run.pk,placement=placement,verify_bytes=False)
          for placement in images.PLACEMENTS}
    definitions={row['ReportName']:row for row in config['RuntimeReports']}
    if {name:row['Id'] for name,row in definitions.items()}!=SELECTORS:
        raise PublicationUnavailable('placement_download_roster_differs')
    return raw,definitions,rows


def descriptors(run):
    _raw,definitions,rows=binding(run)
    result={}
    for selector,definition in definitions.items():
        events=[event for event in rows[definition['Placement']].metadata['candidate']['reports']
                if event['report_id']==definition['Id']]
        if len(events)!=1:raise PublicationUnavailable('placement_download_event_differs')
        extension='zip' if definition['Compression'] else 'csv'
        result[selector]=dict(path='',downloadName=events[0]['last_generated_file_name']+'.'+extension,
            reportName=selector,fileType='application/zip' if definition['Compression'] else 'text/csv')
    return result


def open_file(run,payload,selector):
    from mta.application.runtime_report_projection import describe,project
    from mta.application.runtime_report_files import layout
    from mta.presentation.pick_downloads import _attributes
    if selector not in SELECTORS:raise PublicationUnavailable('placement_download_selector_unqualified')
    raw,definitions,rows=binding(run)
    definition=definitions[selector];row=rows[definition['Placement']]
    manifest=row.metadata['authority']['images']
    logical=set(describe(definition)['sources'].values())
    fields={name:([item[0] for item in manifest['images'][name]['fields']]
                  or [field for field,_kind in images.LOGICAL[name]]) for name in logical}
    sources=images.read(run,manifest,candidate_id=str(row.pk),placement=row.placement,fields=fields)
    products,locations=scope(payload,attributes=_attributes(run))
    projected=project(definition,sources)
    if not allowed(permission_rows(projected,definition['Id']),definition['Id'],products,locations):
        raise PermissionError('runtime_report_whole_file_scope_denied')
    published=publication.read(run.pk,placement=row.placement,verify_bytes=True)
    relative=layout(definition,publication.variables(run))['download']
    entry=rows['Final'].metadata['catalogue'].get(relative)
    if entry is None or entry['candidate_id']!=str(published.pk):
        raise PublicationUnavailable('placement_terminal_file_custody_differs')
    return (_open(publication.root(run,raw)/str(published.pk),relative,entry['file']),
            Path(relative).name,'application/zip' if definition['Compression'] else 'text/csv')


@views.endpoint('GET')
def report_paths(request,payload):
    run=_selected()
    response=unwrap(views.report_paths)(request,payload)
    if run is None:return response
    import json
    value=json.loads(response.content)
    value['data'].update(descriptors(run))
    return JsonResponse(value,status=response.status_code)


@views.endpoint('GET')
def download_report(request,payload,*,report_name):
    if report_name not in SELECTORS:
        return unwrap(views.download_report)(request,payload,report_name=report_name)
    run=_selected()
    if run is None:
        return unwrap(views.download_report)(request,payload,report_name=report_name)
    if views.identity(request).get('entitlements')!=['mta-report-urls']:
        return JsonResponse({'error':'mta_report_download_forbidden'},status=403)
    try:stream,filename,mimetype=open_file(run,payload,report_name)
    except PermissionError:
        return JsonResponse({'error':'runtime_report_whole_file_scope_denied'},status=403)
    except (ValueError,KeyError,OSError) as error:
        raise PublicationUnavailable('runtime_report_download_unavailable') from error
    return FileResponse(stream,as_attachment=True,filename=filename,content_type=mimetype)
