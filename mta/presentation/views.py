"""Preserved MTA HTTP envelopes over the accepted relational publication.

Identity is asserted only by the private authenticated user-service gateway;
the MTA service must not be exposed on a public/host port.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import wraps
import json
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from mta.presentation import btr, insights
from mta.presentation.context import PublicationUnavailable, permission_catalogue, publication, scope, selected_run
from mta.presentation.insight_filters import InsightFilterUnavailable
from mta.presentation.dbm import dbm_rows, delivery_history
from mta.presentation.dbm_read import dbm_context
from mta.presentation.dbm_filters import dbm_predicate
from mta.presentation.daily_history import daily_graph
from mta.presentation.insight_response import scalar_json_rows,chronic_grid_payload
from mta.presentation import history_native
from mta.presentation.history import _buffer_trend_graph, _colour_counts, _historical_availability
from mta.presentation.legacy_ui import UI_CONFIGS, _filter_rows, _pagination, _no_active_filters
from mta.presentation.permissions import permission_multiplicity
from mta.presentation.pick_storage import read_pick_bands
from mta.presentation.rrr import selected_rows as rrr_rows
from mta.presentation.rrr_types import selected_rrr_response
from mta.presentation.rrr_filters import rrr_predicate
from mta.presentation.btr_filters import BtrPredicate
from mta.runtime.models import PickProjection, ExcessProjection
from mta.presentation.excess_storage import read_excess
from mta.presentation.excess_views import joined_rows as excess_rows
from mta.presentation.excess_views import chart_response as excess_chart_response
from mta.presentation.excess_grid import excess_grid_rows,excess_grid_config
from mta.presentation.fulfillment_storage import read_fulfillment
from mta.presentation.fulfillment_views import joined_rows as fulfillment_rows,detail_aliases
from mta.presentation.fulfillment_grid import fulfillment_grid_rows,fulfillment_grid_config
from mta.presentation.fulfillment_charts import chart_queries as fulfillment_chart_queries,chart_response as fulfillment_chart_response
from mta.runtime.models import FulfillmentProjection
from mta.runtime.models import ExpediteProjection
from mta.presentation.expedite_storage import read_expedite
from mta.presentation.expedite_views import counts as expedite_counts
from mta.presentation.pick_post_storage import read_pick_post
from mta.presentation.expedite_charts import queries as expedite_chart_queries,response as expedite_chart_response
from mta.runtime.models import PickPostProjection
from mta.presentation import ui_state
from mta.presentation import actions

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def envelope(*, data=None, record_count=None, message=None, status=200):
    return JsonResponse(dict(recordCount=record_count, data=data, status=status, msg=message,
        errorCount=None, error=None, conflictErrorCount=None, conflictError=None), status=status)


def identity(request):
    try:
        value = json.loads(request.headers.get(settings.MTA_TRUSTED_GATEWAY_HEADER, ''))
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) and value.get('id') is not None else None


def _require_report(report):
    from mta.presentation.daily_preparation import require_report
    require_report(report)


def endpoint(method, *, public=False):
    def decorate(function):
        @csrf_exempt
        @wraps(function)
        def wrapped(request, *args, **kwargs):
            if request.method != method:
                return JsonResponse({'error': 'method_not_allowed'}, status=405)
            if not public and identity(request) is None:
                return JsonResponse({'error': 'gateway_identity_required'}, status=403)
            try:
                # The existing gateway injects permission lists into GET JSON
                # bodies as well; never discard that authenticated scope.
                payload = json.loads(request.body.decode('utf-8') or '{}')
                if not isinstance(payload, dict):
                    raise ValueError('JSON body must be an object')
                from mta.presentation import fixture
                if fixture.enabled() and not public:
                    if not fixture.actor_allowed(identity(request),payload):
                        return JsonResponse({'error':'fixture_actor_scope_denied'},status=403)
                    if function.__name__ == 'dbm_action':
                        return JsonResponse({'error':'demo_read_only'},status=403)
                return function(request, payload, *args, **kwargs)
            except InsightFilterUnavailable:
                # Canonical Guided controller: HTTP500 and responseMessage null fields.
                return envelope(status=500)
            except PublicationUnavailable as exc:
                return JsonResponse({'error': str(exc)}, status=503)
            except (ValueError, TypeError) as exc:
                return JsonResponse({'error': 'invalid_request', 'detail': str(exc)}, status=400)
        return wrapped
    return decorate


def scoped(rows, payload, location_key, *, attributes, preserve_join_multiplicity=False):
    products, locations = scope(payload, attributes=attributes)
    return [dict(row) for row in rows
        for _ in range((permission_multiplicity(products, row.get('SKUCode')) *
                        permission_multiplicity(locations, row.get(location_key)))
                       if preserve_join_multiplicity else
                       int(row.get('SKUCode') in products and row.get(location_key) in locations))]


@endpoint('GET', public=True)
def all_permissions(request, payload):
    catalogue = permission_catalogue()
    return JsonResponse({kind: [dict(id=r['id'], **{
        field + str(i): r['level_' + str(i)] for i in range(1, 4)}) for r in catalogue[source]['records']]
        for kind, source, field in (('product', 'products', 'product_hierarchy_'),
                                    ('location', 'locations', 'location_heirarchy_'))})


@endpoint('GET')
def location_types(request, payload):
    # Deployed CommonsProcessor.GetLocationType: DISTINCT, NULL exclusion only;
    # response.data is JSON text, not a nested array. No scope predicate/order.
    from mta.presentation.selective import image_field
    rows = image_field(selected_run(), 'closing/importer/LocationAttributeData','LocationType')
    values = list(dict.fromkeys(value for value in rows if value is not None))
    return envelope(data=json.dumps([{'lt': value} for value in values], separators=(',', ':'), ensure_ascii=False))


@endpoint('GET')
def descriptions(request, payload, *, kind):
    from mta.presentation.descriptions import selected_descriptions
    # Deployed permission expansion double-quotes an empty ID list; its SQL
    # membership conversion fails and the processor returns status500/data:null.
    # Preserve that source failure rather than inventing a successful empty list.
    if not payload.get('product_permissions' if kind == 'sku' else 'location_permissions'):
        return envelope(status=500)
    return envelope(data=selected_descriptions(payload, kind))


@endpoint('GET')
def environment(request, payload):
    values = json.loads((CONFIG / 'mta_environment_configuration.json').read_text())
    return envelope(data=[dict(ConfigKey=str(k), ConfigValue=str(v)) for k, v in sorted(values.items())])


@endpoint('GET')
def report_paths(request, payload):
    return envelope(data=json.loads((CONFIG / 'mta_report_paths.json').read_text()))


@endpoint('GET')
def download_report(request, payload, *, report_name):
    from mta.presentation.pick_downloads import PickDownloadDenied, open_report
    if identity(request).get('entitlements') != ['mta-report-urls']:
        return JsonResponse({'error': 'mta_report_download_forbidden'}, status=403)
    from mta.presentation import fixture
    if fixture.enabled():
        return JsonResponse({'error': 'fixture_pick_download_denied'}, status=403)
    try:
        stream, filename = open_report(selected_run(), payload, report_name)
    except PickDownloadDenied as error:
        return JsonResponse({'error': str(error)}, status=403)
    from django.http import FileResponse
    return FileResponse(stream, as_attachment=True, filename=filename, content_type='text/csv')


@endpoint('GET')
def ui_config(request, payload):
    name = request.GET.get('reportName')
    if name == 'BOR_OA':
        _require_report('boroa')
        from mta.presentation.boroa_sources import admitted_sources
        from mta.presentation.boroa_configuration import configuration, ui_columns
        admitted_sources()
        return envelope(data=ui_columns(configuration()))
    if name == 'BuyerOrderReport':
        _require_report('bor')
        from mta.presentation.bor_sources import admitted_sources
        from mta.presentation.bor_configuration import configuration, ui_columns
        admitted_sources()
        return envelope(data=ui_columns(configuration()))
    if name == 'NormSuggestion':
        return envelope(data=ui_state.dbm_columns())
    if name == 'AdminBPR':
        from mta.presentation.fixture import enabled as fixture_enabled
        if fixture_enabled() and settings.VF_BPR_PREPARED:
            from mta.presentation.fixture import bpr_ui_columns
            return envelope(data=bpr_ui_columns())
        from mta.presentation.legacy_ui import bpr_ui_columns
        return envelope(data=bpr_ui_columns())
    if name not in UI_CONFIGS:
        return JsonResponse({'error': 'legacy_ui_config_not_migrated', 'reportName': name}, status=404)
    return envelope(data=UI_CONFIGS[name])


@endpoint('POST')
def user_layout(request, payload, *, operation):
    # Never accept an impersonated payload.user on the private service either.
    username = identity(request)['id']
    arguments = [username, payload.get('reportname')]
    if operation == 'save':
        arguments.append(payload.get('state'))
    function = {'get': ui_state.get_layout, 'save': ui_state.save_layout,
                'reset': ui_state.reset_layout}[operation]
    return envelope(data=function(*arguments))


@endpoint('POST')
def dbm_action(request, payload, *, operation):
    try:
        _, response = actions.submit(payload, identity(request)['id'], operation)
    except actions.ActionDenied as exc:
        return JsonResponse({'error': str(exc)}, status=403)
    return envelope(**response)


@endpoint('GET')
def last_run_date(request, payload):
    value = selected_run().business_date
    return envelope(data=[dict(formatted=value.strftime('%d %b %Y'), rawDate=value.isoformat())])


def dbm_filtered(context, payload):
    reader=dbm_rows
    if getattr(getattr(context,'run',None),'kind',None)=='LEGACY_UI_FIXTURE':
        from mta.presentation.fixture import dbm_grid_rows
        reader=dbm_grid_rows
    rows = reader(context.dbm, predicate=dbm_predicate(payload,context.dbm))
    rows = [dict(r, WHCode=r['LocCode'], WhCode=r['LocCode'], WHName=r['LocName'],
                 ParentWhCode=r.get('PWhCode')) for r in rows]
    rows = scoped(rows, payload, 'LocCode',
                  attributes=context.dbm,preserve_join_multiplicity=True)
    return [dict({k: v for k, v in r.items() if k not in ('WHCode', 'WhCode', 'WHName', 'ParentWhCode')}, RN=i)
            for i, r in enumerate(rows, 1)]


@endpoint('POST')
def dbm_data(request, payload, *, count=False):
    paging = _pagination(payload)
    if paging is None:
        raise ValueError('invalid_pagination')
    rows = dbm_filtered(dbm_context(payload=payload), payload)
    if count:
        return envelope(record_count=str(len(rows)))
    page, size = paging
    return envelope(data=scalar_json_rows([{k:v for k,v in r.items() if v is not None}
        for r in rows[(page-1)*size:page*size]]))


@endpoint('POST')
def rrr_data(request, payload, *, count=False):
    paging = _pagination(payload)
    if paging is None:
        raise ValueError('invalid_pagination')
    from mta.presentation.rrr_sql import read_rrr
    rows = read_rrr(selected_run(), payload, paging=paging, count=count)
    if count:
        return envelope(record_count=str(rows))
    return envelope(data=[selected_rrr_response(row) for row in rows])


@endpoint('POST')
def rrr_colour_data(request, payload, *, count=False):
    from mta.presentation.daily_rrr_read import read
    from django.db import DatabaseError
    try:
        rows = read(selected_run(), payload, count=count)
        return envelope(data=[{'count': rows}]) if count else envelope(data=rows if rows else '')
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return envelope(status=500)


@endpoint('POST')
def bpr_remark_history(request, payload):
    """Read the retained remark bag; no remark-write workflow implied."""
    run = selected_run()
    daily = (getattr(run, 'kind', None) == 'DAILY_CHAIN' and
             getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False))
    if getattr(run, 'kind', None) == 'LEGACY_UI_FIXTURE' or daily:
        from mta.presentation.fixture import bpr_ancillary
        from mta.presentation.selective import image_rows
        from mta.presentation.rrr import sql_key
        if not daily:
            rows = bpr_ancillary(run)['BPRReport_RemarkDetails']
        else:
            from mta.presentation import ancillary_live
            rows = ancillary_live.image_rows(
                run, ancillary_live.PATHS[ancillary_live.BPR], include_live=True)
        attributes = {name: image_rows(run, 'closing/importer/' + name)
                      for name in ('SkuAttributeData', 'LocationAttributeData')}
        products, locations = scope(payload, attributes=attributes)
        selected = sql_key(payload.get('skucode', ''), payload.get('whcode', ''))
        rows = [row for row in rows if sql_key(row['SKUCode'], row['WhCode']) == selected
                and row['SKUCode'] in products and row['WhCode'] in locations]
        # Deployed BPRProcessor.GetRemarkDetails: RemarkDate DESC, NULL omission.
        # Stable source occurrence order is retained for equal dates.
        rows.sort(key=lambda row: (row['RemarkDate'] is not None, row['RemarkDate']), reverse=True)
        if daily:
            for row in rows:
                if row['RemarkDate'] is not None:
                    stamp = datetime.fromisoformat(row['RemarkDate'])
                    row['RemarkDate'] = stamp.astimezone(timezone.utc).replace(
                        tzinfo=None).isoformat(
                            timespec='milliseconds' if stamp.microsecond else 'seconds')
        return envelope(data=[{alias: (value.isoformat() if field == 'RemarkDate' and
                                        hasattr(value, 'isoformat') else value)
            for alias, field in (('r', 'Remark'), ('rd', 'RemarkDate'), ('un', 'Username'))
            if (value := row[field]) is not None} for row in rows])
    from mta.presentation.terminal_supplement import terminal_ancillary
    rows = terminal_ancillary(run)['BPRReport_RemarkDetails']
    # The admitted supplement proves only initial emptiness. Do not silently
    # extend this reader to populated history or other selected publications.
    if rows != []:
        raise PublicationUnavailable('populated_BPR_remark_history_not_connected')
    return envelope(data=[])


@endpoint('POST')
def bpr_remark(request, payload):
    """Canonical AddRemark for the explicitly initialized daily live owner."""
    from django.db import DatabaseError
    from mta.presentation import bpr_remarks
    try:
        return envelope(data=bpr_remarks.append(payload, identity(request)))
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return envelope(status=500)


def bpr_selected(payload, *, mode='grid'):
    from mta.presentation.bpr import ReadModel
    from mta.presentation.bpr_read import bpr_context
    from mta.presentation.bpr_filters import BprPredicate
    context = bpr_context()
    if (getattr(context.run, 'kind', None) == 'DAILY_CHAIN' and
            getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False)):
        from mta.presentation import ancillary_live
        context.ancillary = {**context.ancillary,
            'BPRReport_RemarkDetails': ancillary_live.image_rows(
                context.run, ancillary_live.PATHS[ancillary_live.BPR], include_live=True)}
    fixture=getattr(context.run,'kind',None)=='LEGACY_UI_FIXTURE'
    model = ReadModel(context.output, context.ancillary, bounded_page=fixture)
    importer = context.output['ClosingState'][0]['importer']
    predicate = BprPredicate(payload, importer['LocationAttributeData'], export=mode == 'export')
    if fixture:
        # Keep the exact native join/filter/scope multiplicities without holding
        # three copied full-population display bags in each concurrent reader.
        from mta.presentation.bpr import sort_rows
        products,locations=scope(payload,attributes=importer)
        source=model.joined(count=mode=='count',final=mode=='export')
        def weight(row):
            return (permission_multiplicity(products,row.get('SKUCode')) *
                    permission_multiplicity(locations,row.get('WHCode')) * predicate(row))
        if mode=='count':
            # The count caller only asks len(); no display rows are needed.
            return model,range(sum(weight(row) for row in source))
        rows=[row for row in source for _ in range(weight(row))]
        return model,rows if mode=='export' else sort_rows(rows)
    source = (model.count_rows() if mode == 'count' else
              list(model.joined(final=True)) if mode == 'export' else model.candidates())
    rows = scoped(source, payload, 'WHCode', attributes=importer, preserve_join_multiplicity=True)
    return model, predicate.select(rows)


@endpoint('POST')
def bpr_analytics(request, payload):
    if payload.get('name') != 'BPR':
        raise PublicationUnavailable('selected_analytics_report_not_connected')
    from django.conf import settings
    from mta.presentation.fixture import enabled as fixture_enabled
    if fixture_enabled() and settings.VF_BPR_PREPARED:
        from mta.presentation.bpr_prepared import read_bpr
        return envelope(data=read_bpr(selected_run(), payload, analytics=True))
    model, rows = bpr_selected(payload, mode='analytics')
    return envelope(data=model.analytics(rows))


@endpoint('GET')
def bor_ui_config(request, payload):
    _require_report('bor')
    from mta.presentation.bor_sources import admitted_sources
    from mta.presentation.bor_configuration import configuration, ui_columns
    admitted_sources()
    return envelope(data=ui_columns(configuration()))


@endpoint('POST')
def bor_data(request, payload, *, count=False):
    _require_report('bor')
    from mta.presentation.bor_sql import read_bor
    from mta.presentation.bor_configuration import configuration, wire_rows
    from django.db import DatabaseError
    try:
        rows = read_bor(payload, count=count)
        return envelope(record_count=str(rows)) if count else envelope(data=wire_rows(rows, configuration()))
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return envelope(status=500)


@endpoint('POST')
def boroa_data(request, payload, *, count=False):
    _require_report('boroa')
    from mta.presentation.boroa_sql import read_boroa
    from django.db import DatabaseError
    try:
        rows = read_boroa(payload, count=count)
        # Getresponse returns an empty string for SQL's NULL JSON scalar.
        return envelope(data=[{'count': rows}]) if count else envelope(data=rows if rows else '')
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return envelope(status=500)


@endpoint('POST')
def boroa_remark(request, payload, *, history=False):
    _require_report('boroa')
    from mta.presentation import boroa_remarks
    from django.db import DatabaseError
    try:
        return envelope(data=boroa_remarks.history(payload) if history else boroa_remarks.append(payload, identity(request)))
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return envelope(status=500)


@endpoint('GET')
def bor_analytics(request, payload):
    _require_report('bor')
    from mta.presentation.bor_sql import read_bor
    from django.db import DatabaseError
    try:
        return envelope(data=read_bor(payload, analytics=True))
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return envelope(status=500)


@endpoint('POST')
def bor_remark(request, payload, *, history=False):
    _require_report('bor')
    from mta.presentation import bor_remarks
    from django.db import DatabaseError
    try:
        return envelope(data=bor_remarks.history(payload) if history else bor_remarks.append(payload, identity(request)))
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return envelope(status=500)


@endpoint('POST')
def bpr_data(request, payload, *, count=False):
    from mta.presentation.bpr_response import response_row
    if not count:
        paging = payload.get('paginationParameter')
        if (not isinstance(paging, dict) or any(type(paging.get(k)) is not int or paging[k] < 1
                for k in ('pageNumber', 'recordsPerPage'))):
            raise ValueError('positive_BPR_pagination_required')
    from mta.presentation.fixture import enabled as fixture_enabled
    if fixture_enabled():
        if settings.VF_BPR_PREPARED:
            from mta.presentation.bpr_prepared import read_bpr
        else:
            from mta.presentation.bpr_sql import read_bpr
        rows = read_bpr(selected_run(), payload, count=count,
            paging=None if count else (paging['pageNumber'], paging['recordsPerPage']))
        if count:
            return envelope(record_count=str(rows))
        return envelope(data=[response_row(row) for row in rows])
    model, rows = bpr_selected(payload, mode='count' if count else 'grid')
    if count:
        return envelope(record_count=str(len(rows)))
    daily = settings.VF_MTA_DAILY_PUBLICATION and selected_run().kind == 'DAILY_CHAIN'
    return envelope(data=[response_row(row, daily_transit=daily)
        for row in model.page(rows, paging['pageNumber'], paging['recordsPerPage'])])


@endpoint('POST')
def export_data(request, payload):
    from mta.presentation.rrr_sql import read_rrr
    from mta.presentation.rrr_export import FIELDS, selected_headers, csv_chunks
    if payload.get('reportName') == 'RRROA':
        from mta.presentation.daily_rrr_read import read, projection
        from mta.presentation.legacy_ui import RRR_OA_UI_CONFIG
        from django.db import DatabaseError
        try:
            rows = read(selected_run(), payload, export=True)
        except PublicationUnavailable:
            raise
        except (ValueError, KeyError, TypeError, DatabaseError):
            return envelope(status=500)
        state = ui_state.get_layout(identity(request)['id'], 'RRRColorBandWise')
        headers = selected_headers(state, ['RN', *[n for n, _ in projection()]],
                                   configuration=RRR_OA_UI_CONFIG)
        response = StreamingHttpResponse(csv_chunks(rows, headers), content_type='text/csv')
        response['Content-Disposition'] = 'attachment'
        return response
    if payload.get('reportName') == 'BOROA':
        _require_report('boroa')
        from mta.presentation.boroa_sql import read_boroa, projection
        from mta.presentation.boroa_configuration import configuration
        from django.db import DatabaseError
        try:
            rows = read_boroa(payload, export=True)
        except PublicationUnavailable:
            raise
        except (ValueError, KeyError, TypeError, DatabaseError):
            return envelope(status=500)
        state = ui_state.get_layout(identity(request)['id'], 'BORColorBandwise')
        headers = selected_headers(state, ['RN', *[n for n, _ in projection()]], configuration=configuration()['columns'])
        response = StreamingHttpResponse(csv_chunks(rows, headers), content_type='text/csv')
        response['Content-Disposition'] = 'attachment'
        return response
    if payload.get('reportName') == 'BOR':
        _require_report('bor')
        from mta.presentation.bor_sql import read_bor, projection, BorQueryError
        from mta.presentation.bor_configuration import configuration
        try:
            rows = read_bor(payload, export=True)
        except PublicationUnavailable:
            raise
        except (BorQueryError, ValueError, KeyError, TypeError):
            return envelope(status=500)
        state = ui_state.get_layout(identity(request)['id'], 'BOR')
        headers = selected_headers(state, [n for n, _ in projection()],
                                   configuration=configuration()['columns'])
        response = StreamingHttpResponse(csv_chunks(rows, headers), content_type='text/csv')
        response['Content-Disposition'] = 'attachment'
        return response
    if payload.get('reportName') not in ('RRR', 'BTR', 'BPR'):
        raise PublicationUnavailable('selected_report_export_not_connected')
    run = selected_run()
    if payload['reportName'] == 'BTR':
        from mta.presentation.btr_sql import read_btr
        from mta.presentation.btr_export import selected_headers as btr_headers
        rows, dates = read_btr(run, payload, paging=None, export=True)
        report = 'BTRon-hand' if payload.get('name') == 'tech' else 'BTRpipeline'
        state = ui_state.get_layout(identity(request)['id'], report)
        headers = btr_headers(state, dates)
    elif payload['reportName'] == 'BPR':
        from mta.presentation.bpr_export import selected_headers as bpr_headers
        model, selected = bpr_selected(payload, mode='export')
        rows = model.export(selected)
        state = ui_state.get_layout(identity(request)['id'], 'BPR')
        headers = bpr_headers(state)
    else:
        rows = read_rrr(run, payload, paging=None)
        state = ui_state.get_layout(identity(request)['id'], 'RRR')
        headers = selected_headers(state, FIELDS)
    response = StreamingHttpResponse(csv_chunks(rows, headers), content_type='text/csv')
    response['Content-Disposition'] = 'attachment'
    return response


@endpoint('POST')
def planning_overview(request, payload):
    import os
    if os.environ.get('VF_PLANNING_SUMMARY') == '1':
        from mta.presentation.planning_summary import admitted, identity_value, counts
        claimed = payload.pop('_report_read_identity', None)
        receipt, resolved = admitted(selected_run(), payload)
        token = identity_value(receipt, payload, identity(request), resolved)
        if claimed is not None and claimed != token:
            return JsonResponse({'error': 'report_read_identity_changed'}, status=409)
        response = envelope(data=counts(receipt, resolved), message='')
        response['X-Planning-Business-Date'] = receipt.business_date.isoformat()
        response['X-Planning-Identity'] = token
        return response
    return planning_overview_reference(request, payload)


def planning_overview_reference(request, payload):
    from mta.presentation.daily_planning_extension import enabled
    if enabled(selected_run()):
        from mta.presentation.daily_planning.dispatch import read
        return envelope(data=read(selected_run(),payload,'overview'),message='')
    from mta.presentation import fixture
    if fixture.enabled():
        from mta.presentation.planning_overview_sql import counts as prepared_counts
        return envelope(data=prepared_counts(selected_run(),payload),message='')
    from mta.presentation.planning_read import planning_overview_context
    from mta.presentation.planning_overview import counts
    if not _no_active_filters(payload):
        raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
    context = planning_overview_context()
    products, locations = scope(payload, attributes=context.attributes)
    return envelope(data=counts(context.attributes, context.standards, context.reports,
        context.run.business_date, products=products, locations=locations), message='')


def planning_context(payload):
    category=str(payload.get('category','')).casefold()
    if category not in ('excessinventory','orderfulfillment') or payload.get('type')=='custom':
        raise PublicationUnavailable('selected_planning_branch_not_yet_connected')
    if category == 'excessinventory':
        from mta.presentation.excess_read import excess_context
        context = excess_context()
        return context, context.rows
    from mta.presentation.fulfillment_read import fulfillment_context
    context = fulfillment_context()
    return context,context.rows


@endpoint('POST')
def planning_graph(request,payload):
    from mta.presentation.daily_planning_extension import enabled
    if enabled(selected_run()):
        from mta.presentation.daily_planning.dispatch import read
        return envelope(data=read(selected_run(),payload,'graph'),message='')
    category = str(payload.get('category', '')).casefold()
    if category in ('excessinventory', 'orderfulfillment'):
        from mta.presentation import fixture
        if fixture.enabled():
            from mta.presentation.planning_chart_sql import graph
            return envelope(data=graph(selected_run(), payload,
                                       'excess' if category == 'excessinventory' else 'fulfillment'), message='')
    if payload.get('category') == 'git':
        from mta.presentation.git_read import graph
        return envelope(data=graph(payload), message='')
    if str(payload.get('category', '')).casefold() == 'excessinventory':
        from mta.presentation.excess_read import excess_context
        context = excess_context()
        products, locations = scope(payload, attributes=context.output['ClosingState'][0]['importer'])
        # The deployed Excess graph processor never reads request filters.
        return envelope(data=excess_chart_response(context.output, context.rows, context.business_date,
            products=products, locations=locations), message='')
    if str(payload.get('category','')).casefold()=='expedite':
        if not _no_active_filters(payload):
            raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
        kind=str(payload.get('type','')).casefold()
        from mta.presentation import fixture
        if fixture.enabled():
            from mta.presentation.planning_expedite_chart_sql import queries
            tables=queries(selected_run(),payload,kind)
        else:
            from mta.presentation.expedite_read import expedite_context
            context=expedite_context()
            try:
                rows=context.rows
                pick=read_pick_post(context.run,output=context.native_output)
            except (ExpediteProjection.DoesNotExist,PickPostProjection.DoesNotExist) as exc:
                raise PublicationUnavailable('selected_run_expedite_chart_projection_not_published') from exc
            products,locations=scope(payload,attributes=context.output['ClosingState'][0]['importer'])
            tables=expedite_chart_queries(context.output,rows,pick,kind,products=products,locations=locations)
        try:
            # Parent (3 October) and child (5 October) presentation corrections:
            # receiving labels belong to their own verified joined location.
            values=expedite_chart_response(tables,kind,receiving_own_label=True)
        except ValueError as exc:
            if str(exc)!='Legacy Expedite receiving LogisticsLocation depends on unordered critical rows': raise
            raise PublicationUnavailable('LEG-EXPEDITE-UNORDERED-LABEL: chart response unavailable; no legacy repair applied') from exc
        return envelope(data=values,message='')
    context,rows=planning_context(payload)
    products,locations=scope(payload,attributes=context.output['ClosingState'][0]['importer'])
    if str(payload.get('category','')).casefold()=='orderfulfillment':
        return envelope(data=fulfillment_chart_response(fulfillment_chart_queries(context.output,rows,
            products=products,locations=locations)),message='')
    return envelope(data=excess_chart_response(context.output,rows,context.business_date,
        products=products,locations=locations),message='')


@endpoint('POST')
def planning_grid(request, payload, *, count=False):
    from mta.presentation.daily_planning_extension import enabled
    if enabled(selected_run()):
        from mta.presentation.daily_planning.dispatch import read
        return envelope(data=read(selected_run(),payload,'grid',count=count))
    if payload.get('category') == 'expedite' and payload.get('type') == 'child' and not count:
        from mta.presentation.expedite_read import child_grid
        return envelope(data=child_grid(payload))
    if payload.get('category') == 'expedite' and payload.get('type') == 'parent' and not count:
        from mta.presentation.expedite_read import parent_grid
        return envelope(data=parent_grid(payload))
    if payload.get('category') == 'git':
        from mta.presentation.git_read import grid
        return envelope(data=grid(payload, count=count))
    if str(payload.get('category','')).casefold()=='expedite' and count:
        from mta.presentation import fixture
        if fixture.enabled():
            from mta.presentation.planning_expedite_sql import counts as prepared_counts
            return envelope(data=prepared_counts(selected_run(),payload))
        if not _no_active_filters(payload):
            raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
        from mta.presentation.expedite_read import expedite_context
        context=expedite_context(include_master=False)
        rows=context.rows
        products,locations=scope(payload,attributes=context.output['ClosingState'][0]['importer'])
        return envelope(data=expedite_counts(context.output,rows,str(payload.get('type','')).casefold(),
                         products=products,locations=locations))
    excess = str(payload.get('category', '')).casefold() == 'excessinventory'
    fulfillment = str(payload.get('category', '')).casefold() == 'orderfulfillment'
    if excess or fulfillment:
        from mta.presentation.excess_read import pagination
        paging = pagination(payload)
    else:
        paging = _pagination(payload)
    if paging is None and not (excess or fulfillment):
        raise ValueError('invalid_pagination')
    if excess or fulfillment:
        from mta.presentation import fixture
        if fixture.enabled():
            from mta.presentation.planning_grid_sql import read_grid
            projected = read_grid(selected_run(), payload,
                                  family='excess' if excess else 'fulfillment',
                                  paging=paging, count=count)
            if count:
                return envelope(data=projected)
            return envelope(data={'data': projected,
                                  'uiConfig': fulfillment_grid_config() if fulfillment else excess_grid_config()})
    context,rows=planning_context(payload)
    details=detail_aliases(rows['details']) if fulfillment else []
    if fulfillment:
        from mta.presentation.fulfillment_filters import predicate
        selected = predicate(payload, context.output['ClosingState'][0]['importer'])
        rows = fulfillment_rows(context.output, rows['summary'], predicate=selected)
    else:
        from mta.presentation.excess_filters import predicate
        selected = predicate(payload, context.output['ClosingState'][0]['importer'])
        rows = excess_rows(context.output, rows, context.business_date, predicate=selected)
    rows=scoped(rows,payload,'WHCode',attributes=context.output['ClosingState'][0]['importer'],
                preserve_join_multiplicity=True)
    if count:
        return envelope(data=len(rows))
    projected = fulfillment_grid_rows(rows, details) if fulfillment else excess_grid_rows(rows)
    if paging is not None:
        page, size = paging
        projected = [row for row in projected if (page-1)*size+1 <= row['rn'] <= page*size]
    # Both normal branches call GenericFunction.ExecuteScalar<object>, which deserializes
    # SQL JSON into List<object> before the controller serializes its response.
    return envelope(data={'data':projected,
                          'uiConfig':fulfillment_grid_config() if fulfillment else excess_grid_config()})


@endpoint('POST')
def planning_custom(request, payload):
    from mta.presentation.daily_planning_extension import enabled
    if enabled(selected_run()):
        from mta.presentation.daily_planning.dispatch import read
        return envelope(data=read(selected_run(),payload,'custom'))
    if payload.get('category') == 'expedite':
        from mta.presentation.expedite_read import custom_grid as expedite_custom_grid
        return envelope(data=expedite_custom_grid(payload))
    if payload.get('category') == 'git':
        from mta.presentation.git_read import custom
        return envelope(data=custom(payload))
    # Deployed custom dispatch is case sensitive and does not inspect type.
    if payload.get('category') not in ('excessInventory','orderFulfillment'):
        raise PublicationUnavailable('selected_planning_custom_branch_not_yet_connected')
    from mta.presentation.excess_read import excess_context, custom_grid, pagination
    paging = pagination(payload)
    from mta.presentation import fixture
    if fixture.enabled():
        from mta.presentation.planning_custom_sql import custom_grid as prepared_custom_grid
        return envelope(data=prepared_custom_grid(selected_run(), payload, paging,
                        family='fulfillment' if payload['category'] == 'orderFulfillment' else 'excess'))
    if payload.get('category') == 'orderFulfillment':
        from mta.presentation.fulfillment_read import fulfillment_context, custom_grid as fulfillment_custom_grid
        return envelope(data=fulfillment_custom_grid(fulfillment_context(custom=True),payload,paging))
    return envelope(data=custom_grid(excess_context(custom=True), payload, paging))


@endpoint('POST')
def btr_data(request, payload, *, count=False):
    from mta.presentation.btr_sql import read_btr
    from mta.presentation.btr_display import display_horizon, prepare_display
    horizon = None if count else display_horizon(payload)
    run = selected_run()
    paging = _pagination(payload)
    if paging is None:
        raise ValueError('invalid_pagination')
    data = read_btr(run, payload, paging=paging, count=count)
    if horizon is not None and data.get('displayPrepared') is not True:
        data = prepare_display(data, horizon)
    return envelope(data=data)


@endpoint('POST')
def history_graph(request, payload):
    sku, location = payload.get('SKUCode'), payload.get('WHCode')
    if not isinstance(sku, str) or not isinstance(location, str):
        raise ValueError('SKUCode_and_WHCode_required')
    if not payload.get('product_permissions') or not payload.get('location_permissions'):
        return envelope(data=[])
    context = dbm_context(history=True,pair=(sku,location))
    products, locations = scope(payload, attributes=context.output['ClosingState'][0]['importer'])
    if sku not in products or location not in locations:
        return envelope(data=[])
    return envelope(data=daily_graph(context.dbm, sku, location))


def history_rows(context, payload, horizon):
    rows = delivery_history(context.output, context.business_date, horizon)
    return _filter_rows(scoped(rows, payload, 'WHCode', attributes=context.output['BTRFinal'][0],
                              preserve_join_multiplicity=True), payload)


@endpoint('POST')
def buffer_trends(request, payload):
    from mta.presentation.buffer_trends_sql import read_graph
    return envelope(data=read_graph(selected_run(),payload),message='')


@endpoint('POST')
def research_insights(request, payload):
    from mta.presentation.research_read import read_research
    return envelope(data=read_research(selected_run(), payload), message='')


@endpoint('GET')
def historical_availability(request, payload):
    from mta.presentation.research_read import read_historical_availability
    return envelope(data=read_historical_availability(selected_run(), payload), message='')


@endpoint('POST')
def insight_data(request, payload, *, kind):
    if kind in ('excess-sku', 'excess-value') and settings.VF_MTA_GUIDED_EXCESS_DISPOSITION:
        from mta.presentation.daily_history_disposition import guard
        guard(selected_run(), kind)
    from mta.presentation.insight_read import insight_context
    from mta.presentation.insight_filters import InsightPredicate
    from mta.presentation.insight_response import insight_payload
    from mta.presentation import fixture
    from mta.presentation.chronic_sql import native_fixture
    if fixture.enabled() and settings.VF_GUIDED_PREPARED and kind in (
            'loc', 'sku', 'pie', 'ageing', 'chronic-loc', 'chronic-sku', 'chronic-grid') and native_fixture(selected_run()):
        run = selected_run()
        if kind == 'chronic-grid':
            from mta.presentation.guided_chronic import read_guided_chronic
            values = read_guided_chronic(run, payload)
        elif kind.startswith('chronic-'):
            from mta.presentation.chronic_sql import read_chronic
            values = read_chronic(run, payload, kind)
        else:
            from mta.presentation.guided_dbm import read_guided_dbm
            from mta.presentation.selective import image_rows
            attributes = {name: image_rows(run, 'closing/btr/' + name)
                          for name in ('SkuAttributeData', 'LocationAttributeData')}
            values = read_guided_dbm(run, payload, kind, attributes)
        return envelope(data=insight_payload(values, kind))
    if fixture.enabled() and (kind.startswith('availability-') or kind.startswith('excess-')):
        run = selected_run()
        from mta.presentation.insight_history_sql import read_history
        try:
            return envelope(data=scalar_json_rows(read_history(run, payload, kind)))
        except OverflowError:
            if kind.startswith('excess-'):
                return envelope(status=500)
            raise
    context = insight_context(kind)
    state = context.state
    predicate = InsightPredicate(payload, state['LocationAttributeData'], kind=kind)
    if kind in ('excess-sku', 'excess-value'):
        from mta.presentation.excess_insights import project
        try:
            horizon = int(payload.get('horison', 0))
            cutoff = (context.business_date - timedelta(days=horizon)).isoformat()
            rows = insights.availability_rows({**state, 'BPR': context.history}, filter_owners=True)
            rows = [r for r in rows if r['ReportDate'] > cutoff]
            rows = predicate.select(scoped(rows, payload, 'WHCode', attributes=state,
                                           preserve_join_multiplicity=True))
            return envelope(data=scalar_json_rows(project(rows, value=kind == 'excess-value')))
        except OverflowError:
            return envelope(status=500)
    if kind == 'chronic-grid':
        rows = insights.chronic_grid(state, context.nms, filter_owners=True)
        rows = predicate.select(scoped(rows, payload, 'WHCode', attributes=state,
                                       preserve_join_multiplicity=True))
        return envelope(data=chronic_grid_payload([
            {k: v for k, v in row.items() if not k.startswith('_')} for row in rows]))
    if kind in ('availability-trend', 'availability-ageing'):
        horizon = int(payload.get('horizon', payload.get('horison', 90 if kind == 'availability-trend' else 30)))
        if not 1 <= horizon <= 90:
            raise ValueError('horizon must be between 1 and 90 days')
        cutoff = (context.business_date - timedelta(days=horizon)).isoformat()
        rows = [r for r in insights.availability_rows(state, filter_owners=True) if r['ReportDate'] > cutoff]
        rows = scoped(rows, payload, 'WHCode', attributes=state, preserve_join_multiplicity=True)
        values = (insights.availability_trend(predicate.select(rows)) if kind == 'availability-trend' else
                  insights.availability_ageing(rows, state['BTRSnapshotForUI'],
                      int(payload.get('ageing',1)), predicate=predicate))
    else:
        # Insight tables are producer-owned daily outputs. Later Apply/Sleep
        # changes the DBM action overlay, not these already-produced tables.
        rows = insights.joined_rows(state, context.dbm, kind, filter_owners=True)
        rows = predicate.select(scoped(rows, payload, 'WHCode', attributes=state,
                                       preserve_join_multiplicity=True))
        values = insights.project(rows, kind)
    return envelope(data=insight_payload(values, kind))


@endpoint('POST')
def report_read_identity(request,payload):
    if payload.pop('report', None) == 'planning':
        from mta.presentation.planning_summary import admitted, identity_value
        receipt, resolved = admitted(selected_run(), payload)
        return envelope(data=dict(identity=identity_value(receipt,payload,identity(request),resolved),
            businessDate=receipt.business_date.isoformat()))
    from mta.presentation.report_cache import read_identity
    return envelope(data={'identity':read_identity(selected_run(),payload,identity(request))})
