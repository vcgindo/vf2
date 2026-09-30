from mto_app.models import (ClosedOrders,Closed_Order_WIPDetails)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import (ExcelExportData, api_response, CustomPagination, filter_order_data_by_params,filer_order_wip_by_params,GetUserDetails,DataPermissionFilterForOrderData, getOTIFStatusValue, get_last_successful_run_date)
from datetime import date,timedelta
from mto_app.common.commonfunctions import calculate_quartiles_and_whiskers 
from dateutil.relativedelta import relativedelta
import numpy as np
from mto_app.utils import HorizonEnum, OTIFTags,  eReportName
logger = logging.getLogger(__name__)

class GetElapsedTimeDataView(APIView):
    pagination_class = CustomPagination
    @swagger_auto_schema(
        operation_description='get elapsed time for dept order wise data view',
        manual_parameters=[
            openapi.Parameter('graphflag',openapi.IN_QUERY,type=openapi.TYPE_INTEGER,description='graph flag'),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
          responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }   
    )
    def get(self,request):
        return self.getelapsedtimeData(request)
    
    def put(self,request):
        return self.getelapsedtimeData(request,method = 'PUT')

    def getelapsedtimeData(self,request,method='GET'):
        try:
            graphflag = request.GET.get('graphflag')
            graph_params = bool(int(graphflag)) if graphflag else False

            horizon_date = 7  #configurable quantity
            percentage_of_buffer = 0.15
            run_date = get_last_successful_run_date()
            new_horizon_date = run_date - timedelta(days=horizon_date)  #first day in past, except current week

            filter_data = request.data
            export = request.GET.get('export')
            report_name = request.GET.get('report_name')
            export_params = bool(int(export)) if export else False
            headers = None 
            if filter_data:
                headers = filter_data.get('headers') if 'headers' in filter_data else None
            
            order_wip_details = Closed_Order_WIPDetails.objects.values(
                'order_key','wip_on_hand','elapsed_days','entered_on','exited_on','dept','mfg_balance','item_code','dept__dept_name','dept__dept_id'
            )

            #applying thr
            order_wip_details = filer_order_wip_by_params(order_wip_details,filter_data)

            order_wip_details_of_past_week = order_wip_details.filter(exited_on__range = [new_horizon_date,run_date])
            order_id_set = set(data['order_key'] for data in order_wip_details_of_past_week)
            elapsed_days_details_for_dept = order_wip_details.filter(order_key__in = order_id_set)
            logger.info('Fetched the data for last 7 days for grid')
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Fetched the user details for the permissions')

            order_data = ClosedOrders.objects.filter(order_key__in = order_id_set).values('bpp','order_type__desc','plant','plant__plant_name',
            'line_id','item__item_code','total_qty','due_date','item__item_description','vf_order_type',
            'customer__cust_name','customer__cust_code','ccr__ccr_id','dept__dept_id','order_value',
            'order_id','order_key','color','closure_date','pending_qty')
            order_data = DataPermissionFilterForOrderData(order_data,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            #Applying filters to the closed orders
            order_data = filter_order_data_by_params(order_data,filter_data)

            logger.info('Fetched the order data for that specific order of last 7 days')

            order_plant_map = {data['order_key'] : data['plant__plant_name'] for data in order_data}
            logger.info('Order plant mapping for plant dept mapping of order wip details')

            order_dept_elapsed_time = {}
            for data in elapsed_days_details_for_dept:
                order_key = data['order_key']
                if order_key not in order_dept_elapsed_time:
                    order_dept_elapsed_time[order_key] = {}
                if data['dept__dept_name'] not in order_dept_elapsed_time[order_key]:
                    if data['entered_on'] is not None:
                        order_dept_elapsed_time[order_key][data['dept__dept_name']] = (data['exited_on'] - data['entered_on']).days if data['exited_on'] is not None else (date.today() - data['entered_on']).days
            
            lead_time = {}
            for order,value in order_dept_elapsed_time.items():
                if order not in lead_time:
                    lead_time[order] = 0
                for dept,days in value.items():
                    lead_time[order]+=days

            data_for_grid = []
            filtered_order_data = order_data.filter(order_key__in = [data['order_key'] for data in elapsed_days_details_for_dept])
            for order in filtered_order_data:
                order_key = order['order_key']
                lead_time_in_days = lead_time.get(order_key,0)
                dept_details = order_dept_elapsed_time.get(order_key,{})
                tags = 0
                pending_qty = order['pending_qty'] if order['pending_qty'] is not None else 0
                on_time_failed = order['due_date'] < order['closure_date'] if order['closure_date'] is not None and order['due_date'] is not None else 0
                if on_time_failed is True and pending_qty >0:
                    tags = OTIFTags.OT_False_IF_False
                elif on_time_failed is False and pending_qty==0:
                    tags = OTIFTags.OT_True_IF_True
                elif on_time_failed is True and pending_qty==0:
                    tags = OTIFTags.OT_False_IF_True
                else:
                    tags = OTIFTags.OT_True_IF_False
                if export_params:
                    OTIF_tag_value = getOTIFStatusValue(tags)

                combined_data = {
                    'oid' : order['order_id'],
                    'lid' : order['line_id'],
                    'cn' : order['customer__cust_name'],
                    'cc' : order['customer__cust_code'],
                    'pl' : order['plant'],
                    'pn' : order['plant__plant_name'],
                    'bpp' : order['bpp'],
                    'cl' : order['color'],
                    'ok' : order['order_key'],
                    'ot' : order['order_type__desc'],
                    'ic' : order['item__item_code'],
                    'oqty' : order['total_qty'],
                    'dd' : order['due_date'],
                    'ddtl' : dept_details,
                    'lt' : lead_time_in_days,
                    'tg' : OTIF_tag_value if export_params else tags 
                }
                data_for_grid.append(combined_data)
            logger.info('Data for grid has been generated')
            
            if export_params:
                return ExcelExportData(data_for_grid, report_name, eReportName.ElapseTime.value, headers)
            if graph_params:
                dept_set = set()
                data_for_box_plot = {}
                for data in elapsed_days_details_for_dept:
                    order_key = data['order_key']
                    dept_set.add(data['dept'])
                    order_plant = order_plant_map.get(order_key,None)
                    if order_plant is not None and data['exited_on'] is not None:
                        dept_plant_key = (order_plant,data['dept__dept_name'])
                        if dept_plant_key not in data_for_box_plot:
                            data_for_box_plot[dept_plant_key] = []
                        if data['entered_on'] is not None:
                            data_for_box_plot[dept_plant_key].append(
                                (data['exited_on'] - data['entered_on']).days
                            )
                logger.info('Data for quartile division is generated')

                quartile_division_based_on_plant_dept = {}
                for key,value in data_for_box_plot.items():
                    if str(key) not in quartile_division_based_on_plant_dept:
                        quartile_division_based_on_plant_dept[str(key)] = {}
                    quartiles_values = calculate_quartiles_and_whiskers(value)
                    if None not in quartiles_values:
                        quartile_division_based_on_plant_dept[str(key)] = {
                            'q1' : quartiles_values[0],
                            'q2' : quartiles_values[1],
                            'q3' : quartiles_values[2],
                            'lw' : quartiles_values[3],
                            'uw' : quartiles_values[4],
                            'cl' : 'Grey'
                        }
                logger.info('Quartile division for current week generated successfully')

                data_for_four_weeks_from_last_week = {}
                last_week_last_day = run_date - timedelta(days=7)
                day_in_last_month =  last_week_last_day - relativedelta(months=1)
                elapsed_days_data_for_dept_for_last_four_weeks = order_wip_details.filter(exited_on__range = [day_in_last_month,last_week_last_day],dept__in = dept_set).values(
                    'order_key','wip_on_hand','elapsed_days','entered_on','exited_on','dept','mfg_balance','item_code','dept__dept_name'
                )
                logger.info('Fetched the previous 1 month data for analysis')

                order_keys_for_history_data = [data['order_key'] for data in elapsed_days_data_for_dept_for_last_four_weeks]

                order_data_for_previous_month = ClosedOrders.objects.filter(order_key__in = order_keys_for_history_data).values('bpp','order_type__desc','plant','plant__plant_name',
                'line_id','item__item_code','total_qty','due_date','item__item_description','vf_order_type',
                'customer__cust_name','customer__cust_code','ccr__ccr_id','dept__dept_id','order_value',
                'order_id','order_key','color','closure_date','pending_qty')
                logger.info('Fetched the previous 1 month order data for analysis')
                order_data_for_previous_month = DataPermissionFilterForOrderData(order_data_for_previous_month,product_permissions,location_permissions,is_admin)
                logger.info('Filtered the closed order data based on the permissions of the user')
                order_data_for_previous_month = filter_order_data_by_params(order_data_for_previous_month,filter_data)

                order_plant_map_for_history_data = {data['order_key'] : data['plant__plant_name'] for data in order_data_for_previous_month}
                for data in elapsed_days_data_for_dept_for_last_four_weeks:
                    order_key = data['order_key']
                    order_plant = order_plant_map_for_history_data.get(order_key,None)
                    if order_plant is not None and data['exited_on'] is not None:
                        dept_plant_key = (order_plant,data['dept__dept_name'])
                        if dept_plant_key not in data_for_four_weeks_from_last_week:
                            data_for_four_weeks_from_last_week[dept_plant_key] = []
                        if data['entered_on'] is not None:
                            data_for_four_weeks_from_last_week[dept_plant_key].append(
                                (data['exited_on'] - data['entered_on']).days
                            )

                quartile_division_data_for_dept_history = {}
                for key,value in data_for_four_weeks_from_last_week.items():
                    if str(key) not in quartile_division_data_for_dept_history:
                        quartile_division_data_for_dept_history[str(key)] = {}
                    quartiles_values = calculate_quartiles_and_whiskers(value)
                    if None not in quartiles_values:
                        quartile_division_data_for_dept_history[str(key)] = {
                                'q1' : quartiles_values[0],
                                'q2' : quartiles_values[1],
                                'q3' : quartiles_values[2],
                                'lw' : quartiles_values[3],
                                'uw' : quartiles_values[4],
                            }

                for dept_plant,quartiles in quartile_division_based_on_plant_dept.items():
                    if dept_plant in quartile_division_data_for_dept_history:
                        q2_history = quartile_division_data_for_dept_history.get(dept_plant,0).get('q2',0)
                        q2_for_current_week = quartiles.get('q2',None)
                        if q2_for_current_week > (q2_history + percentage_of_buffer*q2_history):
                            quartiles['cl'] = 'Red'
                        
                return api_response(data = quartile_division_based_on_plant_dept,msg='graph data fetched successfully',status_code=status.HTTP_200_OK)
            
            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(data_for_grid, request)

            logger.info("Returning the paginated response for elapsed time dept wise for orders")
            return paginator.get_paginated_response(paginated_response_data, msg="Elapsed Time data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured in the elapsed time data view due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in the elapsed time data view due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)


class ElapsedTimeForPlantAndDeptView(APIView):
    @swagger_auto_schema(
        operation_description='get elapsed time data for dept and plant',
        manual_parameters=[
            openapi.Parameter('dept', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='dept'),
            openapi.Parameter('plant', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='plant')
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        } 
    )
    
    def process_month_data(self, start_date, end_date, order_wip_details, order_plant_map):
        wip_details = order_wip_details.filter(exited_on__range=[start_date, end_date])
        data_for_quartile_division = [
            (data['exited_on'] - data['entered_on']).days
            for data in wip_details
            if order_plant_map.get(data['order_key']) is not None and data['exited_on'] is not None
        ]
        
        if data_for_quartile_division:
            return calculate_quartiles_and_whiskers(data_for_quartile_division)
        return None
    
    def get_order_wip_details(self, dept, plant, start_date, end_date):
        order_wip_details = Closed_Order_WIPDetails.objects.filter(
            dept=dept, exited_on__range=[start_date, end_date]
        ).values('order_key', 'wip_on_hand', 'elapsed_days', 'entered_on', 'exited_on', 'mfg_balance', 'dept', 'item_code')
        logger.info('Fetched the data for the range from order wip details')
        
        order_key_list = [data['order_key'] for data in order_wip_details]
        order_plant_details = ClosedOrders.objects.filter(order_key__in=order_key_list, plant=plant).values('order_key', 'plant')
        logger.info('Fetched the data for order plant and dept mapping')
        
        order_plant_map = {data['order_key']: data['plant'] for data in order_plant_details}
        return order_wip_details, order_plant_map
    
    def process_quartile_data(self, order_wip_details, order_plant_map, start_date, end_date, label):
        data = self.process_month_data(start_date, end_date, order_wip_details, order_plant_map)
        if  data:
            return {
                label: {
                    'q1': data[0],
                    'q2': data[1],
                    'q3': data[2],
                    'lw': data[3],
                    'uw': data[4],
                }
            }
        else:
            return {
                label: {
                    'q1': 0.0,    
                    'q2': 0.0,
                    'q3': 0.0,
                    'lw': 0,
                    'uw': 0,
                }
            }

    def get(self, request):
        try:
            dept = request.GET.get('dept')
            plant = request.GET.get('plant')
            if dept is None or plant is None:
                return api_response(msg='dept or plant cannot be null', status_code=status.HTTP_400_BAD_REQUEST)
            
            default_horizon = HorizonEnum.default_horizon.value
            run_date = get_last_successful_run_date()
            graph_data = {}
            current_month_first_day = run_date.replace(day=1)
            three_months_ago_date = run_date - timedelta(days=default_horizon)

            # Determine the first month that starts within this 90-day window
            three_months_ago_first_date = three_months_ago_date.replace(day=1)

            order_wip_details, order_plant_map = self.get_order_wip_details(dept, plant, three_months_ago_date, run_date)
            
            # Iterate through months covering the 90-day range
            current_month = three_months_ago_first_date
            while current_month < current_month_first_day:
                month_start = max(current_month, three_months_ago_date)
                next_month_start = current_month + relativedelta(months=1)
                if next_month_start == run_date:
                    break
                month_end = next_month_start - timedelta(days=1)
                graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, month_start, month_end, month_start.strftime("%b %Y")))
                current_month = next_month_start
            # Process last month's data by week
            for week_num in range(1, 6):
                week_start = current_month + timedelta(days=(week_num - 1) * 7)
                week_end = min(current_month + timedelta(days=week_num * 7 - 1), run_date)
                if week_start > run_date:
                    break
                week_key = f"{current_month.strftime('%b %Y')} - Week {week_num}"
                graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, week_start, week_end, week_key))
            logger.info('Process the data for the last 3 months if today is not the first day of the month')
            '''
            if todays_date.day == 1:
                three_months_ago = todays_date - relativedelta(months=3)
                three_months_ago = three_months_ago.replace(day=1)
                two_months_ago = three_months_ago + relativedelta(months=1)
                two_months_ago = two_months_ago.replace(day=1)
                one_month_ago = todays_date - relativedelta(months=1)
                one_month_ago = one_month_ago.replace(day=1)
                current_month_start = todays_date.replace(day=1)
            else:
                two_months_ago = todays_date - relativedelta(months=2)
                two_months_ago = two_months_ago.replace(day=1)
                one_month_ago = two_months_ago + relativedelta(months=1)
                one_month_ago = one_month_ago.replace(day=1)
                current_month_start = todays_date.replace(day=1)
            
            order_wip_details, order_plant_map = self.get_order_wip_details(dept, plant, two_months_ago, todays_date)
            
            if todays_date.day == 1:
                # Process 3 months ago
                three_months_ago_last_day = two_months_ago - timedelta(days=1)
                graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, three_months_ago, three_months_ago_last_day, three_months_ago.strftime("%b %Y")))

                # Process 2 months ago
                two_months_ago_last_day = one_month_ago - timedelta(days=1)
                graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, two_months_ago, two_months_ago_last_day, two_months_ago.strftime("%b %Y")))

                # Process last month's data by week
                for week_num in range(1, 6):
                    week_start = one_month_ago + timedelta(days=(week_num - 1) * 7)
                    week_end = min(one_month_ago + timedelta(days=week_num * 7 - 1), current_month_start - timedelta(days=1))
                    if week_start > current_month_start - timedelta(days=1):
                        break
                    week_key = f"{one_month_ago.strftime('%b %Y')} - Week {week_num}"
                    graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, week_start, week_end, week_key))

                # Process the fourth week
                fourth_week_start = current_month_start + timedelta(days=7)
                fourth_week_end = min(fourth_week_start + timedelta(days=7), todays_date)
                fourth_week_key = f"{current_month_start.strftime('%b %Y')} - Week 4"
                graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, fourth_week_start, fourth_week_end, fourth_week_key))
            else:
                # Process 2 months ago
                two_months_ago_last_day = one_month_ago - timedelta(days=1)
                graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, two_months_ago, two_months_ago_last_day, two_months_ago.strftime("%b %Y")))

                # Process last month
                one_month_ago_last_day = current_month_start - timedelta(days=1)
                graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, one_month_ago, one_month_ago_last_day, one_month_ago.strftime("%b %Y")))

                # Process current month's data by week
                for week_num in range(1, 6):
                    week_start = current_month_start + timedelta(days=(week_num - 1) * 7)
                    week_end = min(current_month_start + timedelta(days=week_num * 7 - 1), todays_date)
                    if week_start > todays_date:
                        break
                    week_key = f"{current_month_start.strftime('%b %Y')} - Week {week_num}"
                    graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, week_start, week_end, week_key))

                # Process the fourth week
                fourth_week_start = current_month_start + timedelta(days=7*4)
                fourth_week_end = min(fourth_week_start + timedelta(days=7), todays_date)
                fourth_week_key = f"{current_month_start.strftime('%b %Y')} - Week 4"
                graph_data.update(self.process_quartile_data(order_wip_details, order_plant_map, fourth_week_start, fourth_week_end, fourth_week_key))
            '''
            return api_response(data=graph_data, msg='Elapsed time data for graph fetched successfully', status_code=status.HTTP_200_OK)
        
        except Exception as ex:
            logger.info(f'An Exception has occurred in fetching the elapsed days data for {dept} and {plant} due to {str(ex)}')
            return api_response(msg=f'An Exception has occurred in fetching the elapsed days data for {dept} and {plant} due to {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)
