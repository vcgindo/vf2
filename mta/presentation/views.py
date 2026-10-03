"""Preserved MTA HTTP envelopes over the accepted relational publication.

Identity is asserted only by the private authenticated user-service gateway;
the MTA service must not be exposed on a public/host port.
"""
from copy import deepcopy
from datetime import timedelta
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
def ui_config(request, payload):
    name = request.GET.get('reportName')
    if name == 'NormSuggestion':
        return envelope(data=ui_state.dbm_columns())
    if name == 'AdminBPR':
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
def bpr_remark_history(request, payload):
    """Canonical empty terminal history; no remark-write workflow implied."""
    from mta.presentation.terminal_supplement import terminal_ancillary
    rows = terminal_ancillary(selected_run())['BPRReport_RemarkDetails']
    # The admitted supplement proves only initial emptiness. Do not silently
    # extend this reader to populated history or other selected publications.
    if rows != []:
        raise PublicationUnavailable('populated_BPR_remark_history_not_connected')
    return envelope(data=[])


def bpr_selected(payload, *, mode='grid'):
    from mta.presentation.bpr import ReadModel
    from mta.presentation.bpr_read import bpr_context
    from mta.presentation.bpr_filters import BprPredicate
    context = bpr_context()
    model = ReadModel(context.output, context.ancillary)
    importer = context.output['ClosingState'][0]['importer']
    predicate = BprPredicate(payload, importer['LocationAttributeData'], export=mode == 'export')
    source = (model.count_rows() if mode == 'count' else
              list(model.joined(final=True)) if mode == 'export' else model.candidates())
    rows = scoped(source, payload, 'WHCode', attributes=importer, preserve_join_multiplicity=True)
    return model, predicate.select(rows)


@endpoint('POST')
def bpr_analytics(request, payload):
    if payload.get('name') != 'BPR':
        raise PublicationUnavailable('selected_analytics_report_not_connected')
    model, rows = bpr_selected(payload, mode='analytics')
    return envelope(data=model.analytics(rows))


@endpoint('POST')
def bpr_data(request, payload, *, count=False):
    from mta.presentation.bpr_response import response_row
    if not count:
        paging = payload.get('paginationParameter')
        if (not isinstance(paging, dict) or any(type(paging.get(k)) is not int or paging[k] < 1
                for k in ('pageNumber', 'recordsPerPage'))):
            raise ValueError('positive_BPR_pagination_required')
    model, rows = bpr_selected(payload, mode='count' if count else 'grid')
    if count:
        return envelope(record_count=str(len(rows)))
    return envelope(data=[response_row(row) for row in model.page(rows, paging['pageNumber'], paging['recordsPerPage'])])


@endpoint('POST')
def export_data(request, payload):
    from mta.presentation.rrr_sql import read_rrr
    from mta.presentation.rrr_export import FIELDS, selected_headers, csv_chunks
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
        from mta.presentation.expedite_read import expedite_context
        context=expedite_context()
        try:
            rows=context.rows
            pick=read_pick_post(context.run,output=context.native_output)
        except (ExpediteProjection.DoesNotExist,PickPostProjection.DoesNotExist) as exc:
            raise PublicationUnavailable('selected_run_expedite_chart_projection_not_published') from exc
        products,locations=scope(payload,attributes=context.output['ClosingState'][0]['importer'])
        kind=str(payload.get('type','')).casefold()
        tables=expedite_chart_queries(context.output,rows,pick,kind,products=products,locations=locations)
        try:
            # Explicit 3 October presentation exception: parent receiving labels
            # belong to their own persisted location, not the last critical row.
            values=expedite_chart_response(tables,kind,receiving_own_label=kind=='parent')
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
        if not _no_active_filters(payload):
            raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
        from mta.presentation.expedite_read import expedite_context
        context=expedite_context()
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
    if payload.get('category') == 'orderFulfillment':
        from mta.presentation.fulfillment_read import fulfillment_context, custom_grid as fulfillment_custom_grid
        return envelope(data=fulfillment_custom_grid(fulfillment_context(custom=True),payload,paging))
    return envelope(data=custom_grid(excess_context(custom=True), payload, paging))


@endpoint('POST')
def btr_data(request, payload, *, count=False):
    from mta.presentation.btr_sql import read_btr
    run = selected_run()
    paging = _pagination(payload)
    if paging is None:
        raise ValueError('invalid_pagination')
    return envelope(data=read_btr(run, payload, paging=paging, count=count))


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
    context = publication()
    state=context.output['BTRFinal'][0]; products,locations=scope(payload,attributes=state)
    master=context.output['BPRReports'][0]['vf_RationedReqReport']
    return envelope(data=history_native.research_rows(state,master,payload.get('data'),
        products=products,locations=locations),message='')


@endpoint('GET')
def historical_availability(request, payload):
    state=publication().output['BTRFinal'][0]; products,locations=scope(payload,attributes=state)
    return envelope(data=history_native.historical_availability(state,products=products,locations=locations),message='')


@endpoint('POST')
def insight_data(request, payload, *, kind):
    from mta.presentation.insight_read import insight_context
    from mta.presentation.insight_filters import InsightPredicate
    from mta.presentation.insight_response import insight_payload
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
