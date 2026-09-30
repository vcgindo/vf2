import calendar
import decimal
from rest_framework.views import APIView
from rest_framework import status
from mto_app.common.commonfunctions import CustomPagination, ExcelExportData, api_response, filter_closed_orders_data_by_params, get_weeks_in_month_till_date, get_OTIF_status_of_order,  getOTIFStatusValue , GetUserDetails, DataPermissionFilterForOrderData, get_last_successful_run_date
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import F
from mto_app.models import DBRSettings, ClosedOrders, ProjectionOrder, ProjectionOrderDetails, RunDateTime
import logging
from datetime import datetime, timedelta
from mto_app.utils import OTIFTags, DBR_Settings,  eReportName, HorizonEnum
from dateutil.relativedelta import relativedelta

# Create your views here.


logger = logging.getLogger(__name__)

class GetOTIFAnalysisView(APIView):
    @swagger_auto_schema(
        operation_description='Get OTIF (on time in full) screen data for orders',
        manual_parameters=[
            openapi.Parameter('graphflag',openapi.IN_QUERY,description='Flag for fetching graph data',type=openapi.TYPE_INTEGER),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        return self.getOTIFAnalysisData(request)
    
    def put(self,request):
        return self.getOTIFAnalysisData(request,method = 'PUT')

    def getOTIFAnalysisData(self, request, method = 'GET'):
        try:
            if method == 'PUT':
                filter_data = request.data
            else:
                filter_data = None
            data_permission_data = request.data
            graphflag = request.GET.get('graphflag')
            graph_data_param = bool(int(graphflag)) if graphflag is not None else False
            export = request.GET.get('export')
            report_name = request.GET.get('report_name')
            export_param = bool(int(export)) if export is not None else False
            headers =  filter_data.get('headers',{}) if filter_data else None
            default_horizon = HorizonEnum.default_horizon.value

            # Get the current date
            todays_date = get_last_successful_run_date()

            # Get the first day of the current month
            # first_day_of_current_month = todays_date.replace(day=1)
            orders = None
            order_ids = None
            from_date = ''
            to_date = ''
            # calculate from which month to which month data need to be collected
            # if first_day_of_current_month == todays_date:
            #     from_month = todays_date - relativedelta(months=3)
            #     from_date = from_month.replace(day=1)
            #     to_date = todays_date + relativedelta(months=-1, day=31)
            # elif todays_date > first_day_of_current_month:
            #     from_month = todays_date - relativedelta(months=2)
            #     from_date = from_month.replace(day=1)
            #     to_date = todays_date
            from_date = todays_date - relativedelta(days=default_horizon)    # 90 days before the today's date.
            if todays_date.day == 1:                            # If today's date is 1st day of month don't include it.
                to_date = todays_date - relativedelta(days=1)
            else:
                to_date = todays_date
            product_permissions,location_permissions,is_admin = GetUserDetails(data_permission_data)
            logger.info('Permission data is fetched from the payload')

            orders = ClosedOrders.objects.filter(closure_date__range=[from_date, to_date], due_date__isnull=False,  total_qty__gt=0).values('bpp', 'ccr', 'dept').annotate(plnt = F('plant__plant_name'),
                oid = F('order_id'), ot = F('vf_order_type'), lid = F('line_id'), ic = F('item__item_code'), id = F('item__item_description'), 
                oqty = F('total_qty'), dd = F('due_date'), cc = F('customer__cust_code'), cn = F('customer__cust_name'), 
                rdt = F('actual_released_date'), mjr_r = F('major_reason__major_reason_desc'), min_r = F('minor_reason__minor_reason_desc'),
                pqty = F('pending_qty'), order_entry_dt = F('order_entry_date'), cdt = F('closure_date'), oattr = F('order_attributes'), ov = F('order_value'), ott = F('ot_tag'), ift = F('if_tag'), cl = F('color'), oa = F('order_attributes'), cla = F('computed_line_attributes'), loa = F('line_order_attributes'))
            logger.info('orders data fetched successfully')

            orders = DataPermissionFilterForOrderData(orders, product_permissions, location_permissions, is_admin,True)
            logger.info('Filtered the closed order data based on the permissions of the user')

            if filter_data:
                orders = filter_closed_orders_data_by_params(orders,filter_data)
            
            order_ids = [order['oid'] for order in orders]
            line_item_ids = [order['lid'] for order in orders]

            # Step 1 and 2: Fetch projection order IDs associated with the given order ID and line ID directly
            projection_order_plant_codes = ProjectionOrderDetails.objects.filter(
                order_id__in=order_ids,
                line_item__in=line_item_ids
            ).values_list(
                'order_plant_code', flat=True
            )

            # Directly fetch the order_ids from ProjectionOrder using distinct order_plant_codes in a single query
            projection_order_ids = ProjectionOrder.objects.filter(
                order_plant_code__in=projection_order_plant_codes
            ).values_list('order_id', flat=True).distinct()

            # to get customer requested due date
            projection_orders = ProjectionOrder.objects.filter(order_id__in = projection_order_ids).values('order_id', 'customer_expected_date')
            logger.info('projection orders data fetched successfully')

            flags = [DBR_Settings.delivery_tolerance, DBR_Settings.mfg_tolerance, DBR_Settings.unit_of_measurement]
            dbr_settings = DBRSettings.objects.filter(flag__in = flags).values('flag', 'value')

            delivery_tolerance = 0
            mfg_tolerance = 0
            unit_of_measurement = ''

            for dbr_setting in dbr_settings:
                if dbr_setting['flag'] == DBR_Settings.delivery_tolerance:
                    delivery_tolerance = int(dbr_setting['value'])
                elif dbr_setting['flag'] == DBR_Settings.mfg_tolerance:
                    mfg_tolerance = int(dbr_setting['value'])
                elif dbr_setting['flag'] == DBR_Settings.unit_of_measurement:
                    unit_of_measurement = str(dbr_setting['value'])


            grid_orders = {}
            crdd = 0
            extend_of_delay = 0
            extend_of_delay_in_days = 0
            tag = 0
            if orders:
                for order in orders:
                    okey = (order['oid'],order['lid'])
                    if okey not in grid_orders:
                        grid_orders[okey] = []

                    # claculate extend of shortage value for orders
                    extend_of_shortage = ((order['pqty']/order['oqty']) * 100)

                    # fetch customer requested due date for orders
                    if projection_orders:
                        for p_order in projection_orders:
                            if order['oid'] == p_order['order_id']:
                                crdd = p_order['customer_expected_date']

                    # calculate extend of delay in days for orders
                    extend_of_delay = order['cdt'] - order['dd']
                    extend_of_delay_in_days = extend_of_delay.days

                    tag = get_OTIF_status_of_order(order['ott'], order['ift'])
                    
                    if tag == OTIFTags.OTIFNone:
                        continue

                    if export_param:
                        OTIF_tag_value = getOTIFStatusValue(tag)

                    grid_orders[okey].append({
                        'tag': OTIF_tag_value if export_param else tag,
                        'bpp': order['bpp'],
                        'plnt': order['plnt'],
                        'oid': order['oid'],
                        'ot': order['ot'],
                        'lid': order['lid'],
                        'ic': order['ic'],
                        'id': order['id'],
                        'oqty': order['oqty'],
                        'dd': order['dd'],
                        'cdt': order['cdt'],
                        'ed': extend_of_delay_in_days,
                        'es': extend_of_shortage,
                        'pqty': order['pqty'],
                        'cc': order['cc'],
                        'cn': order['cn'],
                        'crdd': crdd,
                        'rd': order['rdt'],
                        'mjr': order['mjr_r'],
                        'mnr': order['min_r'],
                        'cl' : order['cl']
                        })
                    
                    if order['loa']:
                        grid_orders[okey][0].update({**order['loa']})
                    
                    
                    if order['cla']:
                        grid_orders[okey][0].update(**order['cla'])

                    if order['oattr']:
                        grid_orders[okey][0].update({
                            **order['oattr']
                        })

            logger.info('extend of shortage value for orders fetched successfully')
            logger.info('extend of delay in days for orders fetched successfully')
            logger.info('grid orders fetched successfully')

            otif_list_data = []
            ot_n_if_list_data = []
            # Generate all days between start_date and end_date
            all_days = [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]
            # Filter for first days of each month
            first_day_of_all_month = [day for day in all_days if day.day == 1 or day == from_date] # this is list of months, for which otif is calculated
            del first_day_of_all_month[-1]
            

            if graph_data_param and grid_orders:
                for first_date_of_month in first_day_of_all_month:
                    last_date_of_month = datetime(first_date_of_month.year, first_date_of_month.month, calendar.monthrange(first_date_of_month.year, first_date_of_month.month)[1])
                    
                    # OTIF value calculation
                    otif_sum = 0
                    otif_total_orders_in_month = 0
                    otif = 0

                    # OTIF plus value calculation
                    otif_plus_sum = 0
                    otif_plus_total_orders_in_month = 0
                    otif_plus = 0

                    # OT_N_IF value calculation (ot and if calculation)
                    ot_sum = 0
                    if_sum = 0
                    on_time = 0
                    in_full = 0

                    for key,orders in grid_orders.items():
                        for order in orders:
                            # calculate otif value for order between given months
                            if first_date_of_month.strftime('%Y-%m-%d') <= order['cdt'].strftime('%Y-%m-%d') <= last_date_of_month.strftime('%Y-%m-%d'):
                                pending_qty_as_per_mfg_tolerance = decimal.Decimal((mfg_tolerance/100)) * order['oqty']
                                otif_total_orders_in_month = otif_total_orders_in_month + 1
                                if order['ed'] <= 0 and order['pqty'] <= pending_qty_as_per_mfg_tolerance:
                                    otif_sum = otif_sum + 1
                                if order['ed'] <= 0:
                                    ot_sum = ot_sum + 1
                                if order['pqty'] <= pending_qty_as_per_mfg_tolerance:
                                    if_sum = if_sum + 1

                            # calculate otif plus value for order between given months with configurable value
                            if first_date_of_month.strftime('%Y-%m-%d') <= order['cdt'].strftime('%Y-%m-%d') <= last_date_of_month.strftime('%Y-%m-%d'):
                                pending_qty_as_per_mfg_tolerance = decimal.Decimal((mfg_tolerance/100)) * order['oqty']
                                otif_plus_total_orders_in_month = otif_plus_total_orders_in_month + 1
                                if (order['ed'] <= 0 or (order['ed'] > 0 and order['ed'] <= delivery_tolerance)) and order['pqty'] <= pending_qty_as_per_mfg_tolerance:
                                    otif_plus_sum = otif_plus_sum + 1

                        # calculation for otif
                        if otif_sum and otif_total_orders_in_month:
                            otif = (otif_sum/otif_total_orders_in_month) * 100
                            otif = round(otif, 2)

                        # calculation for ot
                        if ot_sum and otif_total_orders_in_month:
                            on_time = (ot_sum/otif_total_orders_in_month) * 100
                            on_time = round(on_time, 2)

                        # calculation for if
                        if if_sum and otif_total_orders_in_month:
                            in_full = (if_sum/otif_total_orders_in_month) * 100
                            in_full = round(in_full, 2)
                        
                        # calculation for otif plus
                        if otif_plus_sum and otif_plus_total_orders_in_month:
                            otif_plus = (otif_plus_sum/otif_plus_total_orders_in_month) * 100
                            otif_plus = round(otif_plus, 2)

                        formatted_month = f"{first_date_of_month:%B %Y}" # format => July 2024
                        month = formatted_month

                        otif_data = {
                            'otif_plus': otif_plus,
                            'otif': otif,
                            'm': month
                        }

                        ot_n_if_data = {
                            'ot': on_time,
                            'if': in_full,
                            'm': month
                        }

                    otif_list_data.append(otif_data)
                    ot_n_if_list_data.append(ot_n_if_data)
                logger.info('OTIF value calculated for given orders successfully')

                # distribute month in a week
                weeks_of_current_month = get_weeks_in_month_till_date(to_date)

                week_number = 0
                for i, week in enumerate(weeks_of_current_month):
                    week_number = week_number + 1
                    weeks_first_date, weeks_last_date = week

                    # OTIF value calculation
                    otif_sum = 0
                    otif_total_orders_in_month = 0
                    otif = 0

                    # OTIF plus value calculation
                    otif_plus_sum = 0
                    otif_plus_total_orders_in_month = 0
                    otif_plus = 0

                    # OT_N_IF value calculation (ot and if calculation)
                    ot_sum = 0
                    if_sum = 0
                    on_time = 0
                    in_full = 0

                    for key,orders in grid_orders.items():
                        for order in orders:
                            # calculate otif value for order between given weeks
                            if weeks_first_date.strftime('%Y-%m-%d') <= order['cdt'].strftime('%Y-%m-%d') <= weeks_last_date.strftime('%Y-%m-%d'):
                                pending_qty_as_per_mfg_tolerance = decimal.Decimal((mfg_tolerance/100)) * order['oqty']
                                otif_total_orders_in_month = otif_total_orders_in_month + 1
                                if order['ed'] <= 0 and order['pqty'] <= pending_qty_as_per_mfg_tolerance:
                                    otif_sum = otif_sum + 1
                                if order['ed'] <= 0:
                                    ot_sum = ot_sum + 1
                                if order['pqty'] <= pending_qty_as_per_mfg_tolerance:
                                    if_sum = if_sum + 1

                            # calculate otif plus value for order between given weeks with configurable value
                            if weeks_first_date.strftime('%Y-%m-%d') <= order['cdt'].strftime('%Y-%m-%d') <= weeks_last_date.strftime('%Y-%m-%d'):
                                pending_qty_as_per_mfg_tolerance = decimal.Decimal((mfg_tolerance/100)) * order['oqty']
                                otif_plus_total_orders_in_month = otif_plus_total_orders_in_month + 1
                                if (order['ed'] <= 0 or (order['ed'] > 0 and order['ed'] <= delivery_tolerance)) and order['pqty'] <= pending_qty_as_per_mfg_tolerance:
                                    otif_plus_sum = otif_plus_sum + 1

                        # calculation for otif
                        if otif_sum and otif_total_orders_in_month:
                            otif = (otif_sum/otif_total_orders_in_month) * 100
                            otif = round(otif, 2)

                        # calculation for ot
                        if ot_sum and otif_total_orders_in_month:
                            on_time = (ot_sum/otif_total_orders_in_month) * 100
                            on_time = round(on_time, 2)

                        # calculation for if
                        if if_sum and otif_total_orders_in_month:
                            in_full = (if_sum/otif_total_orders_in_month) * 100
                            in_full = round(in_full,2)

                        # calculation for otif plus
                        if otif_plus_sum and otif_plus_total_orders_in_month:
                            otif_plus = (otif_plus_sum/otif_plus_total_orders_in_month) * 100
                            otif_plus = round(otif_plus,2)

                        formatted_month = f"{weeks_first_date:%B %Y}"      # format => July 2024
                        formatted_month_week_value = formatted_month + ' - ' + 'wk ' + str(week_number)   # format => July 2024 - wk 1
                        month = formatted_month_week_value
                        
                        otif_data = {
                            'otif_plus': otif_plus,
                            'otif': otif,
                            'm': month
                        }

                        ot_n_if_data = {
                            'ot': on_time,
                            'if': in_full,
                            'm': month
                        }

                    otif_list_data.append(otif_data)
                    ot_n_if_list_data.append(ot_n_if_data)
                logger.info('OTIF plus value calculated for given orders successfully')
            
                # create otif graph data
                otif_graph = {
                    'start': from_date,
                    'end': to_date,
                    'data': otif_list_data
                }

                # create otif graph data
                ot_n_if_graph = {
                    'start': from_date,
                    'end': to_date,
                    'data': ot_n_if_list_data
                }

                graph = {
                    'otif': otif_graph,
                    'ot_n_if': ot_n_if_graph,
                    'uom': unit_of_measurement
                }
                # calculate graph data and send
                return api_response(data=graph, msg="Graph data fetched successfully", status_code=status.HTTP_200_OK)


            grid_orders_list = []
            for key, values in grid_orders.items():
                for value in values:
                    grid_orders_list.append(value)
            
            if export_param and (not graph_data_param):
                return ExcelExportData(grid_orders_list, report_name , eReportName.OTIFAnalysis.value, headers)
            logger.info('OTIF graph and grid data created successfully')

            # create paginated grid data
            paginator = CustomPagination()
            paginated_grid_response_data = paginator.paginate_queryset(grid_orders_list, request)
            logger.info("Returning the paginated response")
            return paginator.get_paginated_response(paginated_grid_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured in the get OTIF analysis view due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in the get OTIF analysis view due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)

