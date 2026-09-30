from mto_app.models import (ClosedOrders)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import (ExcelExportData, api_response, CustomPagination,  filter_order_data_by_params ,
getOTIFStatusValue,GetUserDetails,DataPermissionFilterForOrderData, get_last_successful_run_date)
from django.db.models import  F, ExpressionWrapper, DurationField
from datetime import date,timedelta
from mto_app.common.commonfunctions import calculate_quartiles_and_whiskers

from dateutil.relativedelta import relativedelta

from mto_app.utils import  OTIFTags, eReportName, HorizonEnum


logger = logging.getLogger(__name__)

class LeadTimeForOrdersView(APIView):
    pagination_class = CustomPagination

    @swagger_auto_schema(
        operation_description='Lead time for orders data',
        manual_parameters=[
            openapi.Parameter('graphflag', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Graph flag'),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def process_month_data(self, start_date, end_date, closed_orders):
        closed_orders_data = closed_orders.filter(closure_date__range=[start_date, end_date])
        data_for_quartile_division = [data['lead_time'].days for data in closed_orders_data]
        if data_for_quartile_division:
            return calculate_quartiles_and_whiskers(data_for_quartile_division)
        return None

    def process_weekly_data(self, start_date, end_date, closed_orders, graph_data, month_name):
        weekly_data = self.process_month_data(start_date, end_date, closed_orders)
        if weekly_data:
            week_key = f"{month_name} - Week {((start_date.day - 1) // 7) + 1}"
            graph_data[week_key] = {
                'q1': weekly_data[0],
                'q2': weekly_data[1],
                'q3': weekly_data[2],
                'lw': weekly_data[3],
                'uw': weekly_data[4],
            }
        else:
            week_key = f"{month_name} - Week {((start_date.day - 1) // 7) + 1}"
            graph_data[week_key] = {
                'q1': 0.0,
                'q2': 0.0,
                'q3': 0.0,
                'lw': 0,
                'uw': 0,
            }

        # Check if the third week is past
        third_week_end = start_date + timedelta(days=21)
        if third_week_end < end_date:
            # Calculate the start date for the fourth week
            fourth_week_start = third_week_end + timedelta(days=1)
            fourth_week_end = fourth_week_start + timedelta(days=7)

            # Check if the fourth week end is past the end date
            if fourth_week_end > end_date:
                fourth_week_end = end_date

            # Process the data for the fourth week
            fourth_week_data = self.process_month_data(fourth_week_start, fourth_week_end, closed_orders)
            if fourth_week_data:
                week_key = f"{month_name} - Week {((fourth_week_start.day - 1) // 7) + 1}"
                graph_data[week_key] = {
                    'q1': fourth_week_data[0],
                    'q2': fourth_week_data[1],
                    'q3': fourth_week_data[2],
                    'lw': fourth_week_data[3],
                    'uw': fourth_week_data[4],
                }
    
    def get(self,request):
        return self.getleadtimeorderData(request)
    
    def put(self,request):
        return self.getleadtimeorderData(request,method = 'PUT')

    def getleadtimeorderData(self, request,method = 'GET'):
        try:
            headers = None
            if method == 'PUT':
                data = request.data
                headers = data.get('headers',{}) if data else None
            else:
                data = None 
            export = request.GET.get('export')
            export_param = bool(int(export)) if export else None
            report_name = request.GET.get('report_name')
            graphflag = request.GET.get('graphflag')
            graph_param = bool(int(graphflag)) if graphflag else False

            default_horizon = HorizonEnum.default_horizon.value
            today = get_last_successful_run_date()
            current_month_first_day = today.replace(day=1)
            three_months_ago_date = today - relativedelta(days=default_horizon)
            three_months_ago_first_date = three_months_ago_date.replace(day=1)
            filter_data = request.data
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')

            closed_orders = ClosedOrders.objects.filter(
                actual_released_date__isnull=False,
                closure_date__range=[three_months_ago_date, today]
            ).values(
                'bpp', 'order_type__desc', 'plant', 'plant__plant_name', 'line_id', 'item__item_code','ccr__ccr_id',
                'total_qty', 'due_date', 'customer__cust_name', 'customer__cust_code', 'order_id','vf_order_type','item__item_description',
                'order_key', 'color', 'closure_date', 'actual_released_date', 'order_attributes','dept__dept_id','order_value',
                'line_order_attributes', 'item_attributes', 'customer_attributes','pending_qty','expected_due_date', 'computed_line_attributes'
            ).annotate(lead_time=ExpressionWrapper(F('closure_date') - F('actual_released_date'), output_field=DurationField()))
            logger.info('Fetch the closed order data')
            
            closed_orders = DataPermissionFilterForOrderData(closed_orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the closed order data based on the permissions of the user')
            
            #Applying filter on the closed order data
            closed_orders = filter_order_data_by_params(closed_orders,filter_data)

            data_for_grid = []
            for order in closed_orders:
                tags = 0
                pending_qty = order['pending_qty']
                on_time_failed = order['due_date'] < order['closure_date'] if order['closure_date'] is not None and order['due_date'] is not None else 0
                if on_time_failed is True and pending_qty >0:
                    tags = OTIFTags.OT_False_IF_False
                elif on_time_failed is False and pending_qty==0:
                    tags = OTIFTags.OT_True_IF_True
                elif on_time_failed is True and pending_qty==0:
                    tags = OTIFTags.OT_False_IF_True
                else:
                    tags = OTIFTags.OT_True_IF_False

                if export_param:
                        OTIF_tag_value = getOTIFStatusValue(tags)

                combined_data = {
                    'bpp': order['bpp'],
                    'ot': order['order_type__desc'],
                    'pc': order['plant'],
                    'pn': order['plant__plant_name'],
                    'lid': order['line_id'],
                    'ic': order['item__item_code'],
                    'id': order['item__item_description'],
                    'oq': order['total_qty'],
                    'dd': order['due_date'],
                    'cn': order['customer__cust_name'],
                    'cc': order['customer__cust_code'],
                    'oid': order['order_id'],
                    'ok': order['order_key'],
                    'cl': order['color'],
                    'cd': order['closure_date'],
                    'ar': order['actual_released_date'],
                    'crdd' : order['expected_due_date'],
                    'lt': order['lead_time'].days, 
                    'tg' : OTIF_tag_value if export_param else tags 
                }
                line_attr = order['line_order_attributes']
                if line_attr:
                    combined_data.update(line_attr)
                
                # Update combined_data with order_attributes
                order_attr = order['order_attributes']
                if order_attr:
                    combined_data.update(order_attr)
                
                comp_line_attr = order['computed_line_attributes']
                if comp_line_attr:
                    combined_data.update(comp_line_attr)

                # Update combined_data with item_attributes
                item_attr = order['item_attributes']
                if item_attr:
                    combined_data.update(item_attr)
                
                # Update combined_data with customer_attributes
                customer_attr = order['customer_attributes']
                if customer_attr:
                    combined_data.update(customer_attr)

                data_for_grid.append(combined_data)
            logger.info('Data for grid has been fetched')
            if export_param and (not graph_param):
                if report_name and headers:
                    return ExcelExportData(data_for_grid,report_name, eReportName.LeadTime.value, headers)
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)
            if (not graph_param) and (not export_param):
                paginator = CustomPagination()
                paginated_response_data = paginator.paginate_queryset(data_for_grid, request)
                logger.info("Returning the paginated response for lead time for orders")
                return paginator.get_paginated_response(paginated_response_data, msg="Lead time data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                graph_data = {}
                # Iterate through months covering the 90-day range
                current_month = three_months_ago_first_date
                while current_month < current_month_first_day:
                    month_start = max(current_month, three_months_ago_date)
                    next_month_start = current_month + relativedelta(months=1)
                    if next_month_start == today:
                        break
                    month_end = next_month_start - timedelta(days=1)

                    data = self.process_month_data(month_start, month_end, closed_orders)
                    if data:
                        graph_data[month_start.strftime("%b %Y")] = {
                            'q1': data[0],
                            'q2': data[1],
                            'q3': data[2],
                            'lw': data[3],
                            'uw': data[4],
                        }
                    else:
                        graph_data[month_start.strftime("%b %Y")] = {
                            'q1': 0.0,
                            'q2': 0.0,
                            'q3': 0.0,
                            'lw': 0,
                            'uw': 0,
                        }

                    current_month = next_month_start
                # Process last month's data by week
                for week_num in range(1, 6):
                    week_start = current_month + timedelta(days=(week_num - 1) * 7)
                    week_end = min(current_month + timedelta(days=week_num * 7 - 1), today)
                    if week_start > today:
                        break
                    self.process_weekly_data(week_start, week_end, closed_orders, graph_data, current_month.strftime('%b %Y'))
                logger.info('Process the data for the last 3 months if today is not the first day of the month')
                '''
                if today.day == 1:
                    three_months_ago = today - relativedelta(months=3)
                    three_months_ago = three_months_ago.replace(day=1)
                    two_months_ago = three_months_ago + relativedelta(months=1)
                    one_month_ago = today - relativedelta(months=1)
                    one_month_ago = one_month_ago.replace(day=1)
                    current_month_start = today.replace(day=1)

                    # Process data for three months ago
                    three_months_ago_last_day = two_months_ago - timedelta(days=1)
                    three_months_ago_data = self.process_month_data(three_months_ago, three_months_ago_last_day, closed_orders)
                    if (three_months_ago_data):
                        graph_data[three_months_ago.strftime("%b %Y")] = {
                            'q1': three_months_ago_data[0],
                            'q2': three_months_ago_data[1],
                            'q3': three_months_ago_data[2],
                            'lw': three_months_ago_data[3],
                            'uw': three_months_ago_data[4],
                        }

                    # Process data for two months ago
                    two_months_ago_last_day = one_month_ago - timedelta(days=1)
                    two_months_ago_data = self.process_month_data(two_months_ago, two_months_ago_last_day, closed_orders)
                    if (two_months_ago_data):
                        graph_data[two_months_ago.strftime("%b %Y")] = {
                            'q1': two_months_ago_data[0],
                            'q2': two_months_ago_data[1],
                            'q3': two_months_ago_data[2],
                            'lw': two_months_ago_data[3],
                            'uw': two_months_ago_data[4],
                        }

                    # Process last month's data by week
                    for week_num in range(1, 6):
                        week_start = one_month_ago + timedelta(days=(week_num - 1) * 7)
                        week_end = min(one_month_ago + timedelta(days=week_num * 7 - 1), current_month_start - timedelta(days=1))
                        if week_start > current_month_start - timedelta(days=1):
                            break
                        self.process_weekly_data(week_start, week_end, closed_orders, graph_data, one_month_ago.strftime('%b %Y'))

                    logger.info('Process the data for the last 3 months if today is the first day of the month')
                # Handle case when today is not the first day of the month
                else:
                    two_months_ago = today - relativedelta(months=2)
                    two_months_ago = two_months_ago.replace(day=1)
                    one_month_ago = two_months_ago + relativedelta(months=1)
                    one_month_ago = one_month_ago.replace(day=1)
                    current_month_start = today.replace(day=1)

                    # Process data for two months ago
                    two_months_ago_last_day = one_month_ago - timedelta(days=1)
                    two_months_ago_data = self.process_month_data(two_months_ago, two_months_ago_last_day, closed_orders)
                    if (two_months_ago_data):
                        graph_data[two_months_ago.strftime("%b %Y")] = {
                            'q1': two_months_ago_data[0],
                            'q2': two_months_ago_data[1],
                            'q3': two_months_ago_data[2],
                            'lw': two_months_ago_data[3],
                            'uw': two_months_ago_data[4],
                        }

                    # Process data for one month ago
                    one_month_ago_last_day = current_month_start - timedelta(days=1)
                    one_month_ago_data = self.process_month_data(one_month_ago, one_month_ago_last_day, closed_orders)
                    if (one_month_ago_data):
                        graph_data[one_month_ago.strftime("%b %Y")] = {
                            'q1': one_month_ago_data[0],
                            'q2': one_month_ago_data[1],
                            'q3': one_month_ago_data[2],
                            'lw': one_month_ago_data[3],
                            'uw': one_month_ago_data[4],
                        }

                    # Process current month's data by week
                    for week_num in range(1, 6):
                        week_start = current_month_start + timedelta(days=(week_num - 1) * 7)
                        week_end = min(current_month_start + timedelta(days=week_num * 7 - 1), today)
                        if week_start > today:
                            break
                        self.process_weekly_data(week_start, week_end, closed_orders, graph_data, current_month_start.strftime('%b %Y'))
                    logger.info('Process the data for the last 3 months if today is not the first day of the month')
                '''
                return api_response(data=graph_data, msg='Lead time data fetched successfully', status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An exception occurred while fetching the data for the lead time API due to {str(ex)}')
            return api_response(msg=f'An exception occurred while fetching the data for the lead time API due to {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)

