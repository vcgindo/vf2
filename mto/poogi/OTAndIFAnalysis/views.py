import calendar
from rest_framework.views import APIView
from rest_framework import status
from mto_app.common.commonfunctions import (CustomPagination, ExcelExportData, api_response, filter_closed_orders_data_by_params, get_weeks_in_month_till_date, get_OTIF_status_of_order,
getOTIFStatusValue , GetUserDetails, DataPermissionFilterForOrderData, get_range_index, get_last_successful_run_date)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import F
from mto_app.models import ClosedOrders, ProjectionOrder, ReportConfiguration,  ProjectionOrderDetails, DBRSettings
import logging
from datetime import  datetime, timedelta
from mto_app.utils import  Report_Configurations, eReportName, DBR_Settings
from dateutil.relativedelta import relativedelta
import decimal
from mto_app.utils import  HorizonEnum

# Create your views here.


logger = logging.getLogger(__name__)

class OldGetOTandIFAnalysisView(APIView):
    @swagger_auto_schema(
        operation_description='Get OTandIF (on time and in full) screen data for orders',
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
        return self.getOTandIFAnalysisData(request)
    
    def put(self,request):
        return self.getOTandIFAnalysisData(request,method = 'PUT')

    def getOTandIFAnalysisData(self, request, method = 'GET'):
        try:
            if method == 'PUT':
                filter_data = request.data
            else:
                filter_data = None
            graphflag = request.GET.get('graphflag')
            graph_data_param = bool(int(graphflag)) if graphflag is not None else False
            export = request.GET.get('export')
            report_name = request.GET.get('report_name')
            export_param = bool(int(export)) if export is not None else False
            headers =  filter_data.get('headers',{}) if filter_data else None
            data_permission_data = request.data
            default_horizon = HorizonEnum.default_horizon.value
            
            # Get the current date
            todays_date = get_last_successful_run_date()

            # Get the first day of the current month
            first_day_of_current_month = todays_date.replace(day=1)

            from_date = ''
            to_date = ''
            '''
            # calculate from which month to which month data need to be collected
            if first_day_of_current_month == todays_date:
                from_month = todays_date - relativedelta(months=3)
                from_date = from_month.replace(day=1)
                to_date = todays_date + relativedelta(months=-1, day=31)
            elif todays_date > first_day_of_current_month:
                from_month = todays_date - relativedelta(months=2)
                from_date = from_month.replace(day=1)
                to_date = todays_date
            '''
            from_date = todays_date - relativedelta(days=default_horizon)    # 90 days before the today's date.
            if todays_date.day == 1:                            # If today's date is 1st day of month don't include it.
                to_date = todays_date - relativedelta(days=1)
            else:
                to_date = todays_date
            product_permissions,location_permissions,is_admin = GetUserDetails(data_permission_data)
            logger.info('Permission data is fetched from the payload')
                
            orders = ClosedOrders.objects.filter(closure_date__range=[from_date, to_date],  total_qty__gt=0).values('bpp').annotate(plnt = F('plant__plant_name'),
                oid = F('order_id'), ot = F('vf_order_type'), lid = F('line_id'), ic = F('item__item_code'), id = F('item__item_description'), 
                oqty = F('total_qty'), dd = F('due_date'), cc = F('customer__cust_code'), cn = F('customer__cust_name'), 
                rdt = F('actual_released_date'), mjr_r = F('major_reason__major_reason_desc'), min_r = F('minor_reason__minor_reason_desc'),
                pqty = F('pending_qty'), order_entry_dt = F('order_entry_date'), cdt = F('closure_date'), oattr = F('order_attributes'))
            logger.info('orders data fetched successfully')

            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin,True)
            logger.info('Filtered the closed order data based on the permissions of the user')

            if filter_data:
                orders = filter_closed_orders_data_by_params(orders,filter_data)

            order_ids = [order['oid'] for order in orders]

            # to get customer requested due date
            projection_orders = ProjectionOrder.objects.filter(order_id__in = order_ids).values('order_id', 'customer_expected_date')
            logger.info('projection orders data fetched successfully')

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

                    tag = get_OTIF_status_of_order(order['pqty'], order['cdt'], order['dd'])

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
                        'mnr': order['min_r']
                        })
                    if order['oattr']:
                        grid_orders[okey][0].update({
                            **order['oattr']
                        })

            logger.info('extend of shortage value for orders fetched successfully')
            logger.info('extend of delay in days for orders fetched successfully')
            logger.info('grid orders fetched successfully')

            ot_list_data = []
            if_list_data = []

            report_names = [Report_Configurations.OT_failed_difference_range, Report_Configurations.IF_failed_difference_range_in_percent]
            report_config_values = ReportConfiguration.objects.filter(report_name__in = report_names).values('report_name', 'json_value')
            OT_failed_difference_range = {}
            IF_failed_difference_range_in_percent = {}

            for report_config_value in report_config_values:
                if report_config_value['report_name'] == Report_Configurations.OT_failed_difference_range:
                    # Value is in numbers of attributes : "low", "high"
                    OT_failed_difference_range = report_config_value['json_value']
                elif report_config_value['report_name'] == Report_Configurations.IF_failed_difference_range_in_percent:
                    # Value is in percentage of attributes : "low", "high"
                    IF_failed_difference_range_in_percent = report_config_value['json_value']
                
            # Generate all days between start_date and end_date
            all_days = [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]
            # Filter for first days of each month
            first_day_of_all_month = [day for day in all_days if day.day == 1 or day == from_date] # this is list of months, for which otif is calculated
            del first_day_of_all_month[-1]

            if graph_data_param:
                #calculate ot failed graph data
                for first_date_of_month in first_day_of_all_month:
                    last_date_of_month = datetime(first_date_of_month.year, first_date_of_month.month, calendar.monthrange(first_date_of_month.year, first_date_of_month.month)[1])

                    # OT in OTandIF Calculation
                    range1_ot_failed_order_count = 0
                    range2_ot_failed_order_count = 0
                    range3_ot_failed_order_count = 0
                    range4_ot_failed_order_count = 0

                    # OT in OTandIF Calculation
                    range1_1_2 = 0
                    range2_3_7 = 0
                    range3_8_15 = 0
                    range4_16_30 = 0

                    # IF in OTandIF Calculation
                    range1_if_failed_order_count = 0
                    range2_if_failed_order_count = 0
                    range3_if_failed_order_count = 0
                    range4_if_failed_order_count = 0
                    range5_if_failed_order_count = 0

                    # IF in OTandIF Calculation
                    range1_0_2 = 0
                    range2_20_40 = 0
                    range3_40_60 = 0
                    range4_60_80 = 0
                    range5_80_100 = 0

                    for key,orders in grid_orders.items():
                        for order in orders:
                            # calculate ot value for order between given months
                            if first_date_of_month.strftime('%Y-%m-%d') <= order['cdt'].strftime('%Y-%m-%d') <= last_date_of_month.strftime('%Y-%m-%d'):
                                order_on_time_failed_difference = order['cdt'] - order['dd']
                                ot_order_diff_in_days = order_on_time_failed_difference.days

                                if ot_order_diff_in_days > 0:
                                    for key, range_value in OT_failed_difference_range.items():
                                        start_of_range = range_value['low']
                                        end_of_range = range_value['high']
                                        if start_of_range <= ot_order_diff_in_days <= end_of_range:
                                            range1_ot_failed_order_count = range1_ot_failed_order_count + 1
                                        elif start_of_range <= ot_order_diff_in_days <= end_of_range:
                                            range2_ot_failed_order_count = range2_ot_failed_order_count + 1
                                        elif start_of_range <= ot_order_diff_in_days <= end_of_range:
                                            range3_ot_failed_order_count = range3_ot_failed_order_count + 1
                                        elif start_of_range <= ot_order_diff_in_days <= end_of_range:
                                            range4_ot_failed_order_count = range4_ot_failed_order_count + 1

                                if order['pqty'] > 0:
                                    order_in_full_failed_difference_in_percent = (order['pqty'] / order['oqty']) * 100
                                    for key, range_value in IF_failed_difference_range_in_percent.items():
                                        start_of_range = range_value['low']
                                        end_of_range = range_value['high']
                                        if start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range1_if_failed_order_count = range1_if_failed_order_count + 1
                                        elif start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range2_if_failed_order_count = range2_if_failed_order_count + 1
                                        elif start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range3_if_failed_order_count = range3_if_failed_order_count + 1
                                        elif start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range4_if_failed_order_count = range4_if_failed_order_count + 1
                                        elif start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range5_if_failed_order_count = range5_if_failed_order_count + 1

                        # Calculation for OT Failed for multiple ranges

                        # calculation for ot range1
                        range1_1_2 = range1_ot_failed_order_count if range1_ot_failed_order_count else 0
                        
                        # calculation for ot range2
                        range2_3_7 = range2_ot_failed_order_count if range2_ot_failed_order_count else 0

                        # calculation for ot range3
                        range3_8_15 = range3_ot_failed_order_count if range3_ot_failed_order_count else 0

                        # calculation for ot range4
                        range4_16_30 = range4_ot_failed_order_count if range4_ot_failed_order_count else 0

                        # Calculation for IF Failed for multiple ranges

                        # calculation for if range1
                        range1_0_2 = range1_if_failed_order_count if range1_if_failed_order_count else 0
                        
                        # calculation for if range2
                        range2_20_40 = range2_if_failed_order_count if range2_if_failed_order_count else 0

                        # calculation for if range3
                        range3_40_60 = range3_if_failed_order_count if range3_if_failed_order_count else 0

                        # calculation for if range4
                        range4_60_80 = range4_if_failed_order_count if range4_if_failed_order_count else 0

                        # calculation for if range5
                        range5_80_100 = range5_if_failed_order_count if range5_if_failed_order_count else 0

                        formatted_month = f"{first_date_of_month:%B %Y}" # format => July 2024
                        month = formatted_month

                        ot_failed_data = {
                            "1_2_d": range1_1_2,
                            "3_7_d": range2_3_7,
                            "8_15_d": range3_8_15,
                            "16_30_d": range4_16_30,
                            'm': month
                        }

                        if_failed_data = {
                            "0_2_p": range1_0_2,
                            "20_40_p": range2_20_40,
                            "40_60_p": range3_40_60,
                            "60_80_p": range4_60_80,
                            "80_100_p": range5_80_100,
                            'm': month
                        }

                    ot_list_data.append(ot_failed_data)
                    if_list_data.append(if_failed_data)
                logger.info('OT failed and IF failed value calculated for given orders successfully')

                # distribute month in a week
                weeks_of_current_month = get_weeks_in_month_till_date(to_date)

                week_number = 0
                for i, week in enumerate(weeks_of_current_month):
                    week_number = week_number + 1
                    weeks_first_date, weeks_last_date = week

                    # OT in OTandIF Calculation
                    range1_ot_failed_order_count = 0
                    range2_ot_failed_order_count = 0
                    range3_ot_failed_order_count = 0
                    range4_ot_failed_order_count = 0

                    # OT in OTandIF Calculation
                    range1_1_2 = 0
                    range2_3_7 = 0
                    range3_8_15 = 0
                    range4_16_30 = 0

                    # IF in OTandIF Calculation
                    range1_if_failed_order_count = 0
                    range2_if_failed_order_count = 0
                    range3_if_failed_order_count = 0
                    range4_if_failed_order_count = 0
                    range5_if_failed_order_count = 0

                    # IF in OTandIF Calculation
                    range1_0_2 = 0
                    range2_20_40 = 0
                    range3_40_60 = 0
                    range4_60_80 = 0
                    range5_80_100 = 0

                    for key,orders in grid_orders.items():
                        for order in orders:
                            # calculate ot failed value for order between given weeks
                            if weeks_first_date.strftime('%Y-%m-%d') <= order['cdt'].strftime('%Y-%m-%d') <= weeks_last_date.strftime('%Y-%m-%d'):
                                order_on_time_difference = order['cdt'] - order['dd']
                                ot_order_diff_in_days = order_on_time_difference.days

                                if ot_order_diff_in_days > 0:
                                    for key, range_value in OT_failed_difference_range.items():
                                        start_of_range = range_value['low']
                                        end_of_range = range_value['high']
                                        if start_of_range <= ot_order_diff_in_days <= end_of_range:
                                            range1_ot_failed_order_count = range1_ot_failed_order_count + 1
                                        elif start_of_range <= ot_order_diff_in_days <= end_of_range:
                                            range2_ot_failed_order_count = range2_ot_failed_order_count + 1
                                        elif start_of_range <= ot_order_diff_in_days <= end_of_range:
                                            range3_ot_failed_order_count = range3_ot_failed_order_count + 1
                                        elif start_of_range <= ot_order_diff_in_days <= end_of_range:
                                            range4_ot_failed_order_count = range4_ot_failed_order_count + 1

                                if order['pqty'] > 0:
                                    order_in_full_failed_difference_in_percent = (order['pqty'] / order['oqty']) * 100
                                    for key, range_value in IF_failed_difference_range_in_percent.items():
                                        start_of_range = range_value['low']
                                        end_of_range = range_value['high']
                                        if start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range1_if_failed_order_count = range1_if_failed_order_count + 1
                                        elif start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range2_if_failed_order_count = range2_if_failed_order_count + 1
                                        elif start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range3_if_failed_order_count = range3_if_failed_order_count + 1
                                        elif start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range4_if_failed_order_count = range4_if_failed_order_count + 1
                                        elif start_of_range <= order_in_full_failed_difference_in_percent <= end_of_range:
                                            range5_if_failed_order_count = range5_if_failed_order_count + 1

                        # Calculation for OT Failed for multiple ranges

                        # calculation for ot range1
                        range1_1_2 = range1_ot_failed_order_count if range1_ot_failed_order_count else 0
                        
                        # calculation for ot range2
                        range2_3_7 = range2_ot_failed_order_count if range2_ot_failed_order_count else 0

                        # calculation for ot range3
                        range3_8_15 = range3_ot_failed_order_count if range3_ot_failed_order_count else 0

                        # calculation for ot range4
                        range4_16_30 = range4_ot_failed_order_count if range4_ot_failed_order_count else 0

                        # Calculation for IF Failed for multiple ranges

                        # calculation for if range1
                        range1_0_2 = range1_if_failed_order_count if range1_if_failed_order_count else 0
                        
                        # calculation for if range2
                        range2_20_40 = range2_if_failed_order_count if range2_if_failed_order_count else 0

                        # calculation for if range3
                        range3_40_60 = range3_if_failed_order_count if range3_if_failed_order_count else 0

                        # calculation for if range4
                        range4_60_80 = range4_if_failed_order_count if range4_if_failed_order_count else 0

                        # calculation for if range5
                        range5_80_100 = range5_if_failed_order_count if range5_if_failed_order_count else 0

                        formatted_month = f"{weeks_first_date:%B %Y}"      # format => July 2024
                        formatted_month_week = formatted_month + ' - ' + 'wk ' + str(week_number)   # format => July 2024 - wk 1
                        month = formatted_month_week
                        
                        ot_failed_data = {
                            "1_2_d": range1_1_2,
                            "3_7_d": range2_3_7,
                            "8_15_d": range3_8_15,
                            "16_30_d": range4_16_30,
                            'm': month
                        }

                        if_failed_data = {
                            "0_2_p": range1_0_2,
                            "20_40_p": range2_20_40,
                            "40_60_p": range3_40_60,
                            "60_80_p": range4_60_80,
                            "80_100_p": range5_80_100,
                            'm': month
                        }

                    ot_list_data.append(ot_failed_data)
                    if_list_data.append(if_failed_data)
                logger.info('OTIF plus value calculated for given orders successfully')
            
                # create ot failed graph data
                ot_failed_graph = {
                    'start': from_date,
                    'end': to_date,
                    'data': ot_list_data
                }

                # create if failed graph data
                if_failed_graph = {
                    'start': from_date,
                    'end': to_date,
                    'data': if_list_data
                }

                # create graph data
                graph = {
                    'ot': ot_failed_graph,
                    'if': if_failed_graph
                }
                # create graph data and send
                return api_response(data=graph, msg="Graph data fetched successfully", status_code=status.HTTP_200_OK)

            # create grid data
            grid_orders_list = []
            for key, values in grid_orders.items():
                for value in values:
                    grid_orders_list.append(value)
            
            if export_param and (not graph_data_param):
                return ExcelExportData(grid_orders_list, report_name ,eReportName.OTIFAnalysis.value, headers)
            logger.info('OTandIF graph and grid data created successfully')

            # create paginated grid data
            paginator = CustomPagination()
            paginated_grid_response_data = paginator.paginate_queryset(grid_orders_list, request)
            logger.info("Returning the paginated response")
            return paginator.get_paginated_response(paginated_grid_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured in the get OTIF analysis view due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in the get OTIF analysis view due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)    

class GetOTandIFAnalysisView(APIView):
    @swagger_auto_schema(
        operation_description='Get OTandIF (on time and in full) screen data for orders',
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
        return self.getOTandIFAnalysisData(request)
    
    def put(self,request):
        return self.getOTandIFAnalysisData(request,method = 'PUT')

    def getOTandIFAnalysisData(self, request, method = 'GET'):
        try:
            if method == 'PUT':
                filter_data = request.data
            else:
                filter_data = None
            graphflag = request.GET.get('graphflag')
            graph_data_param = bool(int(graphflag)) if graphflag is not None else False
            export = request.GET.get('export')
            report_name = request.GET.get('report_name')
            export_param = bool(int(export)) if export is not None else False
            headers =  filter_data.get('headers',{}) if filter_data else None
            data_permission_data = request.data
            default_horizon = HorizonEnum.default_horizon.value

            # Get the current date
            todays_date = get_last_successful_run_date()

            # Get the first day of the current month
            # first_day_of_current_month = todays_date.replace(day=1)

            from_date = ''
            to_date = ''
            '''
            # calculate from which month to which month data need to be collected
            if first_day_of_current_month == todays_date:
                from_month = todays_date - relativedelta(months=3)
                from_date = from_month.replace(day=1)
                to_date = todays_date + relativedelta(months=-1, day=31)
            elif todays_date > first_day_of_current_month:
                from_month = todays_date - relativedelta(months=2)
                from_date = from_month.replace(day=1)
                to_date = todays_date
            '''
            from_date = todays_date - relativedelta(days=default_horizon)    # 90 days before the today's date.
            if todays_date.day == 1:                            # If today's date is 1st day of month don't include it.
                to_date = todays_date - relativedelta(days=1)
            else:
                to_date = todays_date
            product_permissions,location_permissions,is_admin = GetUserDetails(data_permission_data)
            logger.info('Permission data is fetched from the payload')

            orders = ClosedOrders.objects.filter(closure_date__range=[from_date, to_date], due_date__isnull=False,  total_qty__gt=0).values('bpp').annotate(plnt = F('plant__plant_name'),
                oid = F('order_id'), ot = F('vf_order_type'), lid = F('line_id'), ic = F('item__item_code'), id = F('item__item_description'), 
                oqty = F('total_qty'), dd = F('due_date'), cc = F('customer__cust_code'), cn = F('customer__cust_name'), 
                rdt = F('actual_released_date'), mjr_r = F('major_reason__major_reason_desc'), min_r = F('minor_reason__minor_reason_desc'),
                pqty = F('pending_qty'), order_entry_dt = F('order_entry_date'), cdt = F('closure_date'), oattr = F('order_attributes'), ott = F('ot_tag'), ift = F('if_tag'), cl = F('color'), oa = F('order_attributes'), cla = F('computed_line_attributes'), loa = F('line_order_attributes'))
            logger.info('Closed orders data fetched successfully')

            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin,True)
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

            flags = [DBR_Settings.delivery_tolerance, DBR_Settings.mfg_tolerance]
            dbr_settings = DBRSettings.objects.filter(flag__in = flags).values('flag', 'value')

            delivery_tolerance = 0
            mfg_tolerance = 0

            for dbr_setting in dbr_settings:
                if dbr_setting['flag'] == DBR_Settings.delivery_tolerance:
                    delivery_tolerance = int(dbr_setting['value'])
                elif dbr_setting['flag'] == DBR_Settings.mfg_tolerance:
                    mfg_tolerance = int(dbr_setting['value'])

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
                    
                    if tag == 0:
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
                    
                    if order['cla']:
                        grid_orders[okey][0].update({
                            **order['cla']
                        })
                    if order['loa']:
                        grid_orders[okey][0].update({
                            **order['loa']
                        })
                    if order['oattr']:
                        grid_orders[okey][0].update({
                            **order['oattr']
                        })

            logger.info('extend of shortage value for orders fetched successfully')
            logger.info('extend of delay in days for orders fetched successfully')
            logger.info('grid orders fetched successfully')

            ot_list_data = []
            if_list_data = []

            report_names = [Report_Configurations.OT_failed_difference_range, Report_Configurations.IF_failed_difference_range_in_percent]
            report_config_values = ReportConfiguration.objects.filter(report_name__in = report_names).values('report_name', 'json_value')
            OT_failed_difference_range = {}
            IF_failed_difference_range_in_percent = {}

            for report_config_value in report_config_values:
                if report_config_value['report_name'] == Report_Configurations.OT_failed_difference_range:
                    # Value is in numbers of attributes : "low", "high"
                    OT_failed_difference_range = report_config_value['json_value']
                elif report_config_value['report_name'] == Report_Configurations.IF_failed_difference_range_in_percent:
                    # Value is in percentage of attributes : "low", "high"
                    IF_failed_difference_range_in_percent = report_config_value['json_value']
                
            # Generate all days between start_date and end_date
            all_days = [from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)]
            # Filter for first days of each month
            first_day_of_all_month = [day for day in all_days if day.day == 1 or day == from_date] # this is list of months, for which otif is calculated
            del first_day_of_all_month[-1]

            if graph_data_param:
                ot_list_data = []
                if_list_data = []

                range_to_display_key_ot = {
                    'range1': '1_2_d',
                    'range2': '3_7_d',
                    'range3': '8_15_d',
                    'range4': '16_30_d'
                }
                range_to_display_key_if = {
                    'range1': '0_2_p',
                    'range2': '20_40_p',
                    'range3': '40_60_p',
                    'range4': '60_80_p',
                    'range5': '80_100_p'
                }

                # Monthly OTIF Failed Graph
                for first_date_of_month in first_day_of_all_month:
                    last_date_of_month = datetime(first_date_of_month.year, first_date_of_month.month, calendar.monthrange(first_date_of_month.year, first_date_of_month.month)[1])

                    ot_failed_counts = {k: 0 for k in OT_failed_difference_range}
                    if_failed_counts = {k: 0 for k in IF_failed_difference_range_in_percent}

                    for _, orders in grid_orders.items():
                        for order in orders:
                            if first_date_of_month.strftime('%Y-%m-%d') <= order['cdt'].strftime('%Y-%m-%d') <= last_date_of_month.strftime('%Y-%m-%d'):
                                ot_days_diff = (order['cdt'] - (order['dd']+ timedelta(days=delivery_tolerance))).days
                                
                                if ot_days_diff > 0:
                                    key = get_range_index(ot_days_diff, OT_failed_difference_range)
                                    if key:
                                        ot_failed_counts[key] += 1
                                pending_qty_as_per_mfg_tolerance = decimal.Decimal((mfg_tolerance/100)) * order['oqty']
                                if order['pqty'] > pending_qty_as_per_mfg_tolerance:
                                    order_qty_as_per_mfg_tolerance = order['oqty']-pending_qty_as_per_mfg_tolerance
                                    if_percent_diff = (order['pqty'] / order_qty_as_per_mfg_tolerance) * 100
                                    key = get_range_index(if_percent_diff, IF_failed_difference_range_in_percent)
                                    if key:
                                        if_failed_counts[key] += 1

                    month = f"{first_date_of_month:%B %Y}"

                    ot_entry = {value: ot_failed_counts.get(key, 0) for key, value in range_to_display_key_ot.items()}
                    ot_entry["m"] = month
                    ot_list_data.append(ot_entry)

                    if_entry = {value: if_failed_counts.get(key, 0) for key, value in range_to_display_key_if.items()}
                    if_entry["m"] = month
                    if_list_data.append(if_entry)

                logger.info('OT and IF failed data (monthly) calculated successfully')

                # Weekly OTIF Failed Graph
                weeks_of_current_month = get_weeks_in_month_till_date(to_date)

                for week_number, (week_start, week_end) in enumerate(weeks_of_current_month, start=1):
                    ot_failed_counts = {k: 0 for k in OT_failed_difference_range}
                    if_failed_counts = {k: 0 for k in IF_failed_difference_range_in_percent}

                    for _, orders in grid_orders.items():
                        for order in orders:
                            if week_start.strftime('%Y-%m-%d') <= order['cdt'].strftime('%Y-%m-%d') <= week_end.strftime('%Y-%m-%d'):
                                ot_days_diff = (order['cdt'] - (order['dd']+timedelta(days=delivery_tolerance))).days
                                if ot_days_diff > 0:
                                    key = get_range_index(ot_days_diff, OT_failed_difference_range)
                                    if key:
                                        ot_failed_counts[key] += 1

                                pending_qty_as_per_mfg_tolerance = decimal.Decimal((mfg_tolerance/100)) * order['oqty']
                                if order['pqty'] > pending_qty_as_per_mfg_tolerance:
                                    order_qty_as_per_mfg_tolerance = order['oqty']-pending_qty_as_per_mfg_tolerance
                                    if_percent_diff = (order['pqty']/ order_qty_as_per_mfg_tolerance) * 100
                                    key = get_range_index(if_percent_diff, IF_failed_difference_range_in_percent)
                                    if key:
                                        if_failed_counts[key] += 1

                    formatted_week = f"{week_start:%B %Y} - wk {week_number}"

                    ot_entry = {value: ot_failed_counts.get(key, 0) for key, value in range_to_display_key_ot.items()}
                    ot_entry["m"] = formatted_week
                    ot_list_data.append(ot_entry)

                    if_entry = {value: if_failed_counts.get(key, 0) for key, value in range_to_display_key_if.items()}
                    if_entry["m"] = formatted_week
                    if_list_data.append(if_entry)

                logger.info('OT and IF failed data (weekly) calculated successfully')

                graph = {
                    'ot': {
                        'start': from_date,
                        'end': to_date,
                        'data': ot_list_data
                    },
                    'if': {
                        'start': from_date,
                        'end': to_date,
                        'data': if_list_data
                    }
                }

                return api_response(data=graph, msg="Graph data fetched successfully", status_code=status.HTTP_200_OK)

            # If only grid export is requested
            grid_orders_list = [value for orders in grid_orders.values() for value in orders]

            if export_param and not graph_data_param:
                return ExcelExportData(grid_orders_list, report_name, eReportName.OTIFAnalysis.value, headers)

            # Paginate and return grid data
            paginator = CustomPagination()
            paginated_grid_response_data = paginator.paginate_queryset(grid_orders_list, request)
            logger.info("Returning the paginated response")
            return paginator.get_paginated_response(paginated_grid_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.info(f'An Exception has occured in the get OTIF analysis view due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in the get OTIF analysis view due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)    

