"""Existing HTTP contracts over one explicitly selected immutable BPR view."""
import json
from django.db import connection, transaction, DatabaseError
from django.http import JsonResponse, StreamingHttpResponse, FileResponse
from mta.presentation.context import PublicationUnavailable, scope


def bpr_rows(view, payload, *, paging=None, count=False, analytics=False, export=False):
    from mta.presentation import bpr_prepared as reader
    from mta.presentation.bpr_filters import BprPredicate
    if export and (count or analytics): raise ValueError('BPR_export_mode_conflict')
    if not export and not count and not analytics and (not isinstance(paging, tuple) or len(paging) != 2
            or any(type(value) is not int or value < 1 for value in paging)):
        raise ValueError('positive_BPR_pagination_required')
    attributes = view.planning.attributes()
    BprPredicate(payload, attributes['LocationAttributeData'], export=export)
    ancillary = {'InTransitData': view.bpr.transit.rows('InTransitData')}
    query, params = reader._build(view.run, payload, attributes, ancillary, paging,
        count=count, analytics=analytics, export=export, live_remarks=True, daily_transit=True, read_binding=view.bpr)
    if query is None:
        if analytics: return [{prefix + color: 0 for prefix in ('OnHand', 'Pipeline')
            for color in ('Black', 'Red', 'Yellow', 'Green', 'White', 'Blue', 'Grey')}]
        return 0 if count else []
    def records():
        with transaction.atomic(), connection.cursor() as control:
            control.execute("SELECT current_setting('jit')"); previous = control.fetchone()[0]
            control.execute('SET LOCAL jit=off')
            with connection.chunked_cursor() as cursor:
                cursor.execute(query, params)
                fields = [item[0] for item in cursor.description]
                while batch := cursor.fetchmany(500):
                    yield from (dict(zip(fields, row)) for row in batch)
            control.execute("SELECT set_config('jit',%s,true)", [previous])
    if count:
        with connection.cursor() as cursor:
            cursor.execute(query, params); return cursor.fetchone()[0]
    rows = records()
    if not analytics: rows = reader._with_transit(rows, ancillary)
    return reader._primed_export(rows) if export else list(rows)


def _download(view, request, payload, report_name):
    from mta.presentation.views import identity
    from mta.presentation.pick_downloads import REPORTS, FORMED_REPORTS
    from mta.presentation.permissions import _sql_equal
    from mta.runtime.scoped_pick_files import open_file
    if report_name == 'InputData':
        if identity(request).get('entitlements') != ['mta-input-archive']:
            return JsonResponse({'error': 'mta_input_archive_forbidden'}, status=403)
        from mta.presentation import scoped_artifacts
        values = scoped_artifacts.configured()
        if values is None:
            raise PublicationUnavailable('phase_input_archive_not_prepared')
        try:
            stream = scoped_artifacts.open_archive(view, *values)
        except (OSError, ValueError) as error:
            raise PublicationUnavailable('phase_input_archive_unavailable') from error
        return FileResponse(stream, as_attachment=True, filename='InputData.zip', content_type='application/zip')
    if identity(request).get('entitlements') != ['mta-report-urls']:
        return JsonResponse({'error': 'mta_report_download_forbidden'}, status=403)
    if report_name == 'BOR_OrderAllocation':
        from mta.presentation import scoped_batch_downloads
        from mta.presentation.scoped_bor import require_binding
        bound = require_binding(view.run, view)
        rows, _ = bound._image(('consumers', 'production_reports', 'BORWithOrderAllocation'),
            'production/BORWithOrderAllocation', ('SKUCode', 'WhCode', 'SupplierCode'))
        products, locations = scope(payload, attributes=view.planning.attributes())
        if (not all(any(_sql_equal(row['SKUCode'], code) for code in products) for row in rows)
                or not all(any(_sql_equal(row[field], code) for code in locations)
                    for row in rows for field in ('WhCode', 'SupplierCode'))):
            return JsonResponse({'error': 'selected_run_bor_file_scope_denied'}, status=403)
        stream = scoped_batch_downloads.open_file(view, 'download/BOR_OrderAllocation.csv')
        return FileResponse(stream, as_attachment=True, filename='BOR_OrderAllocation.csv', content_type='text/csv')
    if report_name not in REPORTS: raise PublicationUnavailable('phase_download_not_prepared:' + report_name)
    name = 'LogisticPickList' if report_name in FORMED_REPORTS else 'PickListDataForTruckFormation'
    rows = view.bpr.sources.rows('closing/complete/' + name)
    products, locations = scope(payload, attributes=view.planning.attributes())
    if (not all(any(_sql_equal(row.get('SKUCode'), code) for code in products) for row in rows)
            or not all(any(_sql_equal(row.get(field), code) for code in locations)
                for row in rows for field in ('WHCode', 'ParentWHCode', 'LogisticLocation'))):
        return JsonResponse({'error': 'selected_run_pick_scope_denied'}, status=403)
    stream = open_file(view.bpr.sources.acceptance_id, REPORTS[report_name], expected_digest=view.bpr.sources.acceptance_digest)
    return FileResponse(stream, as_attachment=True, filename=REPORTS[report_name], content_type='text/csv')


def dispatch(function, request, payload, arguments):
    from mta.presentation import views, scoped_selection
    if function.__module__ == 'mta.presentation.mdm_views':
        # The existing MDM wrapper admits and locks the same certified source.
        # Keep family configuration, reads and task contracts in that owner.
        return function(request, payload, **arguments)
    # Configuration, hierarchy catalogue and layouts keep their established
    # authority. Business readers below must never re-enter a Full-run path.
    if function.__name__ == 'report_paths':
        from mta.presentation import scoped_batch_downloads
        values = json.loads((views.CONFIG / 'mta_report_paths.json').read_text())
        if scoped_batch_downloads.configured() is not None:
            scoped_batch_downloads.selected(scoped_selection.selected())
            values['BOR_OrderAllocation'] = dict(path='', downloadName='BOR_OrderAllocation.csv',
                reportName='Buyer Order Allocation Report', fileType='text/csv')
        return views.envelope(data=values)
    if function.__name__ in ('all_permissions', 'environment', 'user_layout'):
        return function(request, payload, **arguments)
    if function.__name__ == 'ui_config':
        if request.GET.get('reportName') in ('BOR_OA', 'BuyerOrderReport'):
            return _bor_config(scoped_selection.selected(), request.GET['reportName'])
        if request.GET.get('reportName') in ('InTransitWhereAbouts', 'OpenExpeditingRequests'):
            from mta.presentation.scoped_logistics import require_binding
            view = scoped_selection.selected()
            require_binding(view.run, view)
        return function(request, payload, **arguments)
    if function.__name__ == 'bpr_remark':
        from mta.presentation import scoped_remark_writer
        try:
            return views.envelope(data=scoped_remark_writer.append(payload, views.identity(request)))
        except scoped_remark_writer.RemarkDenied as error:
            return JsonResponse({'error': str(error)}, status=403)
        except PublicationUnavailable:
            raise
        except (ValueError, KeyError, TypeError, DatabaseError):
            return views.envelope(status=500)
    if function.__name__ == 'dbm_action':
        from mta.presentation import actions, scoped_action_writer
        try:
            _, response = scoped_action_writer.submit(payload, views.identity(request)['id'], arguments['operation'])
            return views.envelope(**response)
        except actions.ActionDenied as error:
            return JsonResponse({'error': str(error)}, status=403)
    view = scoped_selection.selected()
    if function.__module__ == 'mta.presentation.logistics_views' and function.__name__ == 'read':
        from mta.presentation import logistics_read as reader
        operation = arguments['operation']
        try:
            if operation == 'count':
                return views.envelope(record_count=str(reader.transit_grid(view.run, payload,
                    count=True, read_binding=view)))
            function = dict(grid=reader.transit_grid, contacts=reader.contacts,
                transit_history=reader.transit_history, requests=reader.open_requests,
                expedite_history=reader.expedite_history)[operation]
            return views.envelope(data=function(view.run, payload, read_binding=view))
        except reader.TargetDenied as error:
            return JsonResponse({'error': str(error)}, status=403)
        except DatabaseError:
            return views.envelope(status=500)
    name = function.__name__; count = arguments.get('count', False)
    if name == 'bor_ui_config':
        return _bor_config(view, 'BuyerOrderReport')
    if name in ('bor_data', 'boroa_data', 'bor_analytics'):
        from mta.presentation.bor_sql import read_bor
        from mta.presentation.boroa_sql import read_boroa
        from mta.presentation.bor_configuration import configuration, wire_rows
        try:
            if name == 'boroa_data':
                rows = read_boroa(payload, count=count, read_binding=view)
                return views.envelope(data=[{'count': rows}]) if count else views.envelope(data=rows if rows else '')
            rows = read_bor(payload, count=count, analytics=name == 'bor_analytics', read_binding=view)
            if count: return views.envelope(record_count=str(rows))
            return views.envelope(data=rows if name == 'bor_analytics' else wire_rows(rows, configuration()))
        except PublicationUnavailable:
            raise
        except (ValueError, KeyError, TypeError, DatabaseError):
            return views.envelope(status=500)
    if name == 'descriptions':
        from mta.presentation.scoped_history import descriptions
        return views.envelope(data=descriptions(view, payload, arguments['kind']))
    if name == 'history_graph':
        from mta.presentation.scoped_history import daily
        return views.envelope(data=daily(view, payload))
    if name == 'btr_data':
        from mta.presentation.scoped_btr import bind
        from mta.presentation.btr_sql import read_btr
        from mta.presentation.btr_display import display_horizon, prepare_display
        paging = views._pagination(payload)
        if paging is None: raise ValueError('invalid_pagination')
        horizon = None if count else display_horizon(payload)
        data = read_btr(view.run, payload, paging=paging, count=count, read_binding=bind(view))
        if horizon is not None and data.get('displayPrepared') is not True:
            data = prepare_display(data, horizon)
        return views.envelope(data=data)
    if name == 'buffer_trends':
        from mta.presentation.scoped_btr import bind
        from mta.presentation.buffer_trends_sql import read_graph
        return views.envelope(data=read_graph(view.run, payload, read_binding=bind(view)), message='')
    if name == 'bpr_remark_history':
        from mta.presentation.scoped_remark_writer import history
        return views.envelope(data=history(view, payload))
    if name == 'last_run_date':
        value = view.run.business_date
        return views.envelope(data=[dict(formatted=value.strftime('%d %b %Y'), rawDate=value.isoformat())])
    if name == 'location_types':
        rows = view.bpr.sources.rows('closing/importer/LocationAttributeData')
        values = list(dict.fromkeys(row['LocationType'] for row in rows if row['LocationType'] is not None))
        return views.envelope(data=json.dumps([dict(lt=v) for v in values], separators=(',', ':'), ensure_ascii=False))
    if name == 'dbm_data':
        from mta.presentation.scoped_dbm import bind
        paging = views._pagination(payload)
        if paging is None: raise ValueError('invalid_pagination')
        context = getattr(view,'dbm_context',None) or bind(view.bpr.sources.acceptance_id,
            expected_digest=view.bpr.sources.acceptance_digest,
            action_revision=view.bpr.sources.action_revision)
        rows = views.dbm_filtered(context, payload)
        if count: return views.envelope(record_count=str(len(rows)))
        page, size = paging
        return views.envelope(data=views.scalar_json_rows([
            {k: v for k, v in row.items() if v is not None}
            for row in rows[(page - 1) * size:page * size]]))
    if name == 'planning_overview':
        from mta.presentation.scoped_overview import read
        values, business_date = read(view, payload)
        return JsonResponse(dict(recordCount=None, data=values, status=200, msg='', errorCount=None,
            error=None, conflictErrorCount=None, conflictError=None, businessDate=business_date))
    if name in ('planning_grid', 'planning_custom', 'planning_graph'):
        return _planning(view, name, payload, count=count)
    if name == 'rrr_data':
        from mta.presentation.scoped_rrr import read
        paging = views._pagination(payload)
        if paging is None: raise ValueError('invalid_pagination')
        rows = read(view.run, payload, paging=paging, count=count, read_binding=view.pick)
        return views.envelope(record_count=str(rows)) if count else views.envelope(data=[views.selected_rrr_response(row) for row in rows])
    if name == 'rrr_colour_data':
        from mta.presentation.daily_rrr_read import read
        try:
            rows = read(view.run, payload, count=count, read_binding=view)
            return views.envelope(data=[{'count': rows}]) if count else views.envelope(data=rows if rows else '')
        except PublicationUnavailable:
            raise
        except (ValueError, KeyError, TypeError, DatabaseError):
            return views.envelope(status=500)
    if name in ('bpr_data', 'bpr_analytics'):
        from mta.presentation.bpr_response import response_row
        analytics = name == 'bpr_analytics'
        if analytics and payload.get('name') != 'BPR': raise PublicationUnavailable('selected_analytics_report_not_connected')
        p = payload.get('paginationParameter') or {}
        paging = (p.get('pageNumber'), p.get('recordsPerPage'))
        rows = bpr_rows(view, payload, paging=paging, count=count, analytics=analytics)
        if count: return views.envelope(record_count=str(rows))
        return views.envelope(data=rows if analytics else [response_row(row, daily_transit=True) for row in rows])
    if name == 'download_report': return _download(view, request, payload, arguments['report_name'])
    if name == 'export_data':
        from mta.presentation.rrr_export import FIELDS, selected_headers, csv_chunks
        report = payload.get('reportName')
        if report in ('BOR', 'BOROA'):
            return _bor_export(view, request, payload, report)
        if report == 'RRROA':
            from mta.presentation.daily_rrr_read import read, projection
            from mta.presentation.legacy_ui import RRR_OA_UI_CONFIG
            try:
                rows = read(view.run, payload, export=True, read_binding=view)
            except PublicationUnavailable:
                raise
            except (ValueError, KeyError, TypeError, DatabaseError):
                return views.envelope(status=500)
            state = views.ui_state.get_layout(views.identity(request)['id'], 'RRRColorBandWise')
            headers = selected_headers(state, ['RN', *[n for n, _ in projection()]], configuration=RRR_OA_UI_CONFIG)
            response = StreamingHttpResponse(csv_chunks(rows, headers), content_type='text/csv')
            response['Content-Disposition'] = 'attachment'
            return response
        if report not in ('BPR', 'RRR', 'BTR'): raise PublicationUnavailable('phase_export_not_prepared')
        state = views.ui_state.get_layout(views.identity(request)['id'], report)
        if report == 'BPR':
            from mta.presentation.bpr_export import selected_headers as headers, transport_chunks
            rows = bpr_rows(view, payload, export=True)
            class Chunks:
                def __iter__(self): yield from transport_chunks(rows, headers(state))
                def close(self): rows.close()
            chunks = Chunks()
        elif report == 'BTR':
            from mta.presentation.scoped_btr import bind
            from mta.presentation.btr_sql import read_btr
            from mta.presentation.btr_export import selected_headers as headers
            rows, dates = read_btr(view.run, payload, paging=None, export=True, read_binding=bind(view))
            layout = 'BTRon-hand' if payload.get('name') == 'tech' else 'BTRpipeline'
            state = views.ui_state.get_layout(views.identity(request)['id'], layout)
            chunks = csv_chunks(rows, headers(state, dates))
        else:
            from mta.presentation.scoped_rrr import read
            rows = read(view.run, payload, paging=None, read_binding=view.pick)
            chunks = csv_chunks(rows, selected_headers(state, FIELDS))
        response = StreamingHttpResponse(chunks, content_type='text/csv')
        response['Content-Disposition'] = 'attachment'
        return response
    # Current writers require their own atomic action/remark + reference commit;
    # denying here prevents a successful write leaving the selected view stale.
    raise PublicationUnavailable('phase_endpoint_not_prepared:' + name)


def _bor_config(view, name):
    from mta.presentation import views, scoped_bor, bor_configuration, boroa_configuration
    bound = scoped_bor.require_binding(view.run, view)
    if name == 'BOR_OA':
        return views.envelope(data=boroa_configuration.ui_columns(bound.configuration()))
    return views.envelope(data=bor_configuration.ui_columns(bor_configuration.configuration()))


def _bor_export(view, request, payload, report):
    from mta.presentation import views, bor_sql, boroa_sql, scoped_bor, bor_configuration
    from mta.presentation.rrr_export import selected_headers, csv_chunks
    try:
        if report == 'BOROA':
            rows = boroa_sql.read_boroa(payload, export=True, read_binding=view)
            config = scoped_bor.require_binding(view.run, view).configuration()
            fields = ['RN', *[name for name, _ in boroa_sql.projection()]]
            layout = 'BORColorBandwise'
        else:
            rows = bor_sql.read_bor(payload, export=True, read_binding=view)
            config = bor_configuration.configuration()
            fields = [name for name, _ in bor_sql.projection()]
            layout = 'BOR'
    except PublicationUnavailable:
        raise
    except (ValueError, KeyError, TypeError, DatabaseError):
        return views.envelope(status=500)
    state = views.ui_state.get_layout(views.identity(request)['id'], layout)
    headers = selected_headers(state, fields, configuration=config['columns'])
    response = StreamingHttpResponse(csv_chunks(rows, headers), content_type='text/csv')
    response['Content-Disposition'] = 'attachment'
    return response


def _planning(view, name, payload, *, count=False):
    from mta.presentation import views
    from mta.presentation.excess_read import pagination
    category = str(payload.get('category', '')).casefold()
    if (category in ('git', 'expedite') and (name != 'planning_graph' or category == 'git')
            and payload.get('category') != category):
        raise PublicationUnavailable('selected_planning_branch_not_yet_connected')
    if category == 'expedite':
        if name == 'planning_grid':
            from mta.presentation import expedite_read, planning_expedite_sql
            if count: return views.envelope(data=planning_expedite_sql.counts(view.run, payload, read_binding=view.expedite))
            kind = payload.get('type')
            if kind not in ('parent', 'child'): raise ValueError('Unsupported Expedite direction')
            reader = expedite_read.parent_grid if kind == 'parent' else expedite_read.child_grid
            return views.envelope(data=reader(payload, read_binding=view.expedite))
        if name == 'planning_custom':
            from mta.presentation.expedite_read import custom_grid
            return views.envelope(data=custom_grid(payload, read_binding=view.expedite))
        from mta.presentation.planning_expedite_chart_sql import queries
        kind = str(payload.get('type', '')).casefold()
        if not views._no_active_filters(payload): raise PublicationUnavailable('selected_planning_filters_not_yet_connected')
        return views.envelope(data=views.expedite_chart_response(queries(view.run, payload, kind,
            read_binding=view.expedite), kind, receiving_own_label=True), message='')
    if category == 'git':
        if name == 'planning_grid':
            from mta.presentation.planning_git_sql import grid
            return views.envelope(data=grid(view.run, payload, count=count, read_binding=view.git))
        products, locations = scope(payload, attributes=view.git.attributes())
        if name == 'planning_custom':
            from mta.presentation.daily_git_custom import custom
            return views.envelope(data=custom(view.run, products, locations, pagination(payload), read_binding=view.bpr))
        if str(payload.get('type', '')).casefold() != 'child':
            raise PublicationUnavailable('selected_git_parent_graph_not_implemented_by_legacy')
        from mta.presentation.daily_git_read import graph
        return views.envelope(data=graph(view.run, products, locations, read_binding=view.bpr), message='')
    if category not in ('excessinventory', 'orderfulfillment'):
        raise PublicationUnavailable('selected_planning_branch_not_yet_connected')
    if name == 'planning_custom' and payload.get('category') not in ('excessInventory', 'orderFulfillment'):
        raise PublicationUnavailable('selected_planning_custom_branch_not_yet_connected')
    family = 'excess' if category == 'excessinventory' else 'fulfillment'
    if name == 'planning_grid':
        from mta.presentation.planning_grid_sql import read_grid
        rows = read_grid(view.run, payload, family=family, paging=pagination(payload), count=count, read_binding=view.planning)
        if count: return views.envelope(data=rows)
        return views.envelope(data=dict(data=rows, uiConfig=views.excess_grid_config() if family == 'excess' else views.fulfillment_grid_config()))
    if name == 'planning_custom':
        from mta.presentation.planning_custom_sql import custom_grid
        return views.envelope(data=custom_grid(view.run, payload, pagination(payload), family=family, read_binding=view.planning))
    from mta.presentation.planning_chart_sql import graph
    return views.envelope(data=graph(view.run, payload, family, read_binding=view.planning), message='')
