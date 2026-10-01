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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from mta.presentation import btr, insights
from mta.presentation.context import PublicationUnavailable, permission_catalogue, publication, scope, selected_run
from mta.presentation.dbm import dbm_rows, delivery_history
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
                return function(request, payload, *args, **kwargs)
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
    rows = dbm_rows(context.dbm, predicate=dbm_predicate(payload,context.dbm))
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
    rows = dbm_filtered(publication(), payload)
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


def planning_context(payload):
    category=str(payload.get('category','')).casefold()
    if category not in ('excessinventory','orderfulfillment') or payload.get('type')=='custom':
        raise PublicationUnavailable('selected_planning_branch_not_yet_connected')
    # Explicit incomplete contract, never silently ignore or invent a filter.
    # Canonical filter/flaw handling is part of the pending F3.2 obligation.
    if not _no_active_filters(payload):
        raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
    context=publication()
    try:
        rows=(read_excess(context.run,output=context.storage_output) if category=='excessinventory' else
              read_fulfillment(context.run,output=context.storage_output))
    except (ExcessProjection.DoesNotExist,FulfillmentProjection.DoesNotExist) as exc:
        raise PublicationUnavailable('selected_run_'+category+'_projection_not_published') from exc
    return context,rows


@endpoint('POST')
def planning_graph(request,payload):
    if str(payload.get('category','')).casefold()=='expedite':
        if not _no_active_filters(payload):
            raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
        context=publication()
        try:
            rows=read_expedite(context.run,output=context.storage_output)
            pick=read_pick_post(context.run,output=context.storage_output)
        except (ExpediteProjection.DoesNotExist,PickPostProjection.DoesNotExist) as exc:
            raise PublicationUnavailable('selected_run_expedite_chart_projection_not_published') from exc
        products,locations=scope(payload,attributes=context.output['ClosingState'][0]['importer'])
        kind=str(payload.get('type','')).casefold()
        tables=expedite_chart_queries(context.output,rows,pick,kind,products=products,locations=locations)
        try:
            values=expedite_chart_response(tables,kind)
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
    if str(payload.get('category','')).casefold()=='expedite' and count:
        if not _no_active_filters(payload):
            raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
        context=publication()
        try:
            rows=read_expedite(context.run,output=context.storage_output)
        except ExpediteProjection.DoesNotExist as exc:
            raise PublicationUnavailable('selected_run_expedite_projection_not_published') from exc
        products,locations=scope(payload,attributes=context.output['ClosingState'][0]['importer'])
        return envelope(data=expedite_counts(context.output,rows,str(payload.get('type','')).casefold(),
                         products=products,locations=locations))
    paging=_pagination(payload)
    if paging is None:
        raise ValueError('invalid_pagination')
    context,rows=planning_context(payload)
    fulfillment=str(payload.get('category','')).casefold()=='orderfulfillment'
    details=detail_aliases(rows['details']) if fulfillment else []
    rows=(fulfillment_rows(context.output,rows['summary']) if fulfillment else
          excess_rows(context.output,rows,context.business_date))
    rows=scoped(rows,payload,'WHCode',attributes=context.output['ClosingState'][0]['importer'],
                preserve_join_multiplicity=True)
    if count:
        return envelope(data=len(rows))
    # Deployed PlanningProcessor returns SQL FOR JSON as a STRING in data.data.
    page,size=paging
    projected=(fulfillment_grid_rows(rows,details) if fulfillment else excess_grid_rows(rows))[(page-1)*size:page*size]
    return envelope(data={'data':json.dumps(projected,ensure_ascii=False,separators=(',',':')),
                          'uiConfig':fulfillment_grid_config() if fulfillment else excess_grid_config()})


@endpoint('POST')
def btr_data(request, payload, *, count=False):
    context = publication()
    columns = btr.horizon_columns(context.business_date.isoformat(), payload)
    paging = _pagination(payload)
    if paging is None:
        raise ValueError('invalid_pagination')
    page, size = paging
    filters = deepcopy(payload)
    if isinstance(filters.get('filters'), dict):
        filters['filters'].pop('horizonFilter', None)
    predicate = BtrPredicate(filters, context.output['BTRFinal'][0]['LocationAttributeData'], count=count)
    result = {}
    for name in ('tech', 'eco'):
        rows = scoped(btr.joined_rows(context.output, name), payload, 'WHCode',
                      attributes=context.output['BTRFinal'][0], preserve_join_multiplicity=True)
        rows = [row for row in rows for _ in range(predicate(row))]
        if count:
            result['TechCount' if name == 'tech' else 'EcoCount'] = str(len(rows))
        elif str(payload.get('name', 'both')).lower() in (name, 'both'):
            result[name] = btr.project_rows(context.output, name, rows[(page - 1) * size:page * size], columns, size,
                                            join_multiplicity=predicate.join_multiplicity)
        else:
            result[name] = []
    if not count:
        result['labels'] = [{c: r[c] for c in columns} for r in context.output['BTRFinal'][0]['BufferTrendDates']]
    return envelope(data=result)


@endpoint('POST')
def history_graph(request, payload):
    sku, location = payload.get('SKUCode'), payload.get('WHCode')
    if not isinstance(sku, str) or not isinstance(location, str):
        raise ValueError('SKUCode_and_WHCode_required')
    if not payload.get('product_permissions') or not payload.get('location_permissions'):
        return envelope(data=[])
    context = publication()
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
    context = publication()
    if not _no_active_filters(payload): raise PublicationUnavailable('buffer_graph_filters_not_yet_connected')
    state=context.output['BTRFinal'][0]; products,locations=scope(payload,attributes=state)
    days=int(payload.get('Days',payload.get('days',90)))
    return envelope(data=history_native.buffer_graph(state,str(payload.get('bufferTrendType','tech')).lower(),days,
        products=products,locations=locations),message='')


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
    context = publication()
    state = context.output['BTRFinal'][0]
    if kind == 'chronic-grid':
        rows = insights.chronic_grid(state, context.output['ClosingState'][0]['consumer_context']['NMSAllItems'])
        rows = _filter_rows(scoped(rows, payload, 'WHCode', attributes=state,
                                  preserve_join_multiplicity=True), payload)
        return envelope(data=chronic_grid_payload(rows))
    if kind in ('availability-trend', 'availability-ageing'):
        horizon = int(payload.get('horizon', payload.get('horison', 90 if kind == 'availability-trend' else 30)))
        if not 1 <= horizon <= 90:
            raise ValueError('horizon must be between 1 and 90 days')
        cutoff = (context.business_date - timedelta(days=horizon)).isoformat()
        rows = [r for r in insights.availability_rows(state) if r['ReportDate'] > cutoff]
        rows = _filter_rows(scoped(rows, payload, 'WHCode', attributes=state,
                                  preserve_join_multiplicity=True), payload)
        values = (insights.availability_trend(rows) if kind == 'availability-trend' else
                  insights.availability_ageing(rows, state['BTRSnapshotForUI'], int(payload.get('ageing',1))))
    else:
        # Insight tables are producer-owned daily outputs. Later Apply/Sleep
        # changes the DBM action overlay, not these already-produced tables.
        rows = insights.joined_rows(state, context.output['DBMFinal'][0], kind)
        rows = _filter_rows(scoped(rows, payload, 'WHCode', attributes=state,
                                  preserve_join_multiplicity=True), payload)
        values = insights.project(rows, kind)
    return envelope(data=scalar_json_rows(values))
