import calendar
from collections import defaultdict
import decimal
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from mto_app.common.commonfunctions import CustomPagination, ExcelExportData, api_response, filter_closed_orders_data_by_params, get_weeks_in_month_till_date, get_OTIF_status_of_order, get_past_month_date,filter_order_data_by_params, getOTIFStatusValue , GetUserDetails, DataPermissionFilterForOrderData, get_range_index, get_last_successful_run_date
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Count, F, Subquery
from mto_app.models import BMReportRemarks, CCRUtilizationHistory, DBRSettings, OrderData,POOGIMajorReason,POOGIMinorReason,ClosedOrders, ProjectionOrder, ReportConfiguration, FailureReasonsTrend, ProjectionOrderDetails
import logging
from datetime import date, datetime, timedelta
from django.db.models import IntegerField, Case, When
from django.db import transaction
from mto_app.utils import OTIFTags, DBR_Settings, Report_Configurations, eReportName
from dateutil.relativedelta import relativedelta

# Create your views here.


logger = logging.getLogger(__name__)
class TopFailureReasonsView(APIView):
    
    @swagger_auto_schema(
        operation_description='Get top failure reasons for orders',
        manual_parameters=[
            openapi.Parameter('graphflag',openapi.IN_QUERY,description='Flag for fetching graph data',type=openapi.TYPE_INTEGER)
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request): 
        return self.topFailureReasons(request) 

    def put(self,request): 
        return self.topFailureReasons(request,method = 'PUT') 
         
    def get_major_minor_reasons_for_given_month(self, first_day, last_day, grid_orders, total_records_to_display):
        reasons = {}
        for order in grid_orders:
            if last_day <= order['cdt'] <= first_day:
                if order['mjr'] and order['mnr']:
                    reasonkey = str(order['mjr'] + " | " + order['mnr'])
                    if reasonkey in reasons:
                        reasons[reasonkey] += 1
                    else:
                        reasons[reasonkey] = 1
        
        if len(reasons) <= total_records_to_display:
            top_ten_reasons = reasons
        else :
            top_ten_reasons = dict(list(reasons.items())[:total_records_to_display])
        logger.info('major and minor reasosns based on OT and IF fetched successfully')
        return top_ten_reasons

    def topFailureReasons(self,request,method = 'GET'): 
        try:
            if method == 'PUT':
                filter_data = request.data
            else:
                filter_data = None

            graphflag = request.GET.get('graphflag')
            graph_data_param = bool(int(graphflag)) if graphflag is not None else False
            todays_date = get_last_successful_run_date()
            data_permission_data = request.data
            total_records_to_display = int(DBRSettings.objects.get(flag="TopFailureReasons").value)
            product_permissions,location_permissions,is_admin = GetUserDetails(data_permission_data)
            logger.info('Permission data is fetched from the payload')

            orders = ClosedOrders.objects.exclude(major_reason_id__isnull=True, minor_reason_id__isnull=True).values('bpp', 'ccr', 'dept').annotate(plnt = F('plant__plant_name'),oid = F('order_id'), 
                ot = F('order_type__desc'), lid = F('line_id'), ic = F('item__item_code'), id = F('item__item_description'), 
                oqty = F('total_qty'), dd = F('due_date'), cc = F('customer__cust_code'), cn = F('customer__cust_name'), 
                rdt = F('actual_released_date'), mjr_r = F('major_reason__major_reason_desc'), 
                min_r = F('minor_reason__minor_reason_desc'), pqty = F('pending_qty'), cdt = F('closure_date'), ov = F('order_value'), ott = F('ot_tag'), ift = F('if_tag'), oa = F('order_attributes'), cla = F('computed_line_attributes'), loa = F('line_order_attributes'))
            logger.info('orders data fetched successfully')
            orders = DataPermissionFilterForOrderData(orders, product_permissions, location_permissions, is_admin,True)
            logger.info('Filtered the closed order data based on the permissions of the user')

            if filter_data:
                orders = filter_closed_orders_data_by_params(orders, filter_data)
            
            grid_orders = []
            tag = 0
            if orders:
                for order in orders:
                    tag = get_OTIF_status_of_order(order['ott'], order['ift'])
                    if tag == OTIFTags.OT_False_IF_False:
                        grid_orders.append({
                            'tag': tag,
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
                            'pqty': order['pqty'],
                            'cc': order['cc'],
                            'cn': order['cn'],
                            'mjr': order['mjr_r'],
                            'mnr': order['min_r']
                            })
                        if order['oa']:
                            grid_orders[0].update(**order['oa'])
                        if order['cla']:
                            grid_orders[0].update(**order['cla'])
                        if order['loa']:
                            grid_orders[0].update(**order['loa'])
            logger.info('grid orders fetched successfully')

            if graph_data_param:
                # for first past month
                last_range_day_of_first_month = get_past_month_date(todays_date)
                reasons_for_first_past_month = self.get_major_minor_reasons_for_given_month(todays_date, last_range_day_of_first_month, grid_orders, total_records_to_display)

                # for second past month
                last_range_day_of_second_month = get_past_month_date(last_range_day_of_first_month)
                first_range_day_of_first_month = last_range_day_of_first_month + timedelta(days=1)
                reasons_for_second_past_month = self.get_major_minor_reasons_for_given_month(first_range_day_of_first_month, last_range_day_of_second_month, grid_orders, total_records_to_display)
                
                OTIF_reasons = {
                    'm1': reasons_for_first_past_month,
                    'm2': reasons_for_second_past_month
                }
                logger.info('Top 10 reasons fetched successfully')
                return api_response(data = OTIF_reasons,msg='Data fetched successfully',status_code=status.HTTP_200_OK)

            paginator = CustomPagination()
            paginated_grid_response_data = paginator.paginate_queryset(grid_orders, request)
            logger.info("Returning the paginated response")
            return paginator.get_paginated_response(paginated_grid_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f'An Exception has occurred in the top failure reasons of {str(e)}')
            return api_response(msg=f'An Exception has occurred in the top failure reasons because of {str(e)}',status_code=status.HTTP_400_BAD_REQUEST)
