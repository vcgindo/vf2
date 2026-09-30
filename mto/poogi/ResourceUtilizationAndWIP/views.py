import calendar
from collections import defaultdict
import decimal
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from mto_app.common.commonfunctions import CustomPagination, ExcelExportData, api_response, filter_closed_orders_data_by_params, get_weeks_in_month_till_date, get_OTIF_status_of_order, get_past_month_date,filter_order_data_by_params, getOTIFStatusValue , GetUserDetails, DataPermissionFilterForOrderData, get_range_index
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

class GetResourceUtilizationAndWIPProfileView(APIView):
    @swagger_auto_schema(
        operation_description="Get Utilization and WIP Data",
        manual_parameters=[
            openapi.Parameter('plantid', openapi.IN_QUERY, description="Plant ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('deptid', openapi.IN_QUERY, description="Department ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('ccrid', openapi.IN_QUERY, description="CCR ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('hs', openapi.IN_QUERY, description="Horizon Start date", type=openapi.TYPE_STRING),
            openapi.Parameter('he', openapi.IN_QUERY, description="Horizon End date", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            400: "Bad Request: Error retrieving data"
        }
    )
    def get(self, request, format=None):
        try:
            plantid = request.GET.get('plantid')
            deptid = request.GET.get('deptid')
            ccrid = request.GET.get('ccrid')
            hs = request.GET.get('hs')
            he = request.GET.get('he')

            start_date = datetime.strptime(hs, "%Y-%m-%d").date()
            end_date = datetime.strptime(he, "%Y-%m-%d").date()

             # Initialize filter dictionary
            filter_kwargs = {
                'entry_on__range': [start_date, end_date],
                'ccr_id__is_valid': True
            }

            if plantid:
                filter_kwargs['ccr_id__plant'] = plantid
            if deptid:
                filter_kwargs['ccr_id__dept'] = deptid

            ccr_utilization_history = CCRUtilizationHistory.objects.filter(**filter_kwargs).values('ccr_id', 'entry_on', 'produced','capacity', 'ccr_id__ccr_name','wip_released_days','ccr_id__cumulative_wip_limit','cumulative_wip_limit')
            logger.info('Fetched records from CCR Utilization History table based on filters')

            # Calculate Utilization value
            ccrwise_percent_utilization = defaultdict(list)
            for record in ccr_utilization_history:
                produced = record['produced']
                capacity = record['capacity']
                percent_utilization = round((produced / capacity) * 100, 2) if capacity else 0
                record['percent_utilization'] = percent_utilization
                ccrwise_percent_utilization[record['ccr_id__ccr_name']].append(percent_utilization)

            # Calculate average percent_utilization for each ccr_id
            result = []
            for ccr_name, percent_list in ccrwise_percent_utilization.items():
                avg_wip_released = sum(percent_list) / len(percent_list) if percent_list else 0
                result.append({
                    'ccr': ccr_name,
                    'aup': round(avg_wip_released, 2)
                })
            logger.info('Fetched Utilization values')

            # Calculate WIP Limit
            ccrwise_wip_data = defaultdict(list)
            ccrwise_wip_limits = {}
            for record in ccr_utilization_history:
                ccr_wip_limit = record['ccr_id__cumulative_wip_limit']
                wip_released_days = record['wip_released_days']
                record['wip_released_days'] = wip_released_days
                ccrwise_wip_data[record['ccr_id__ccr_name']].append(wip_released_days)
                ccrwise_wip_limits[record['ccr_id__ccr_name']] = ccr_wip_limit

            wip_result = {
                'ulimit': [],
                'olimit': []
            }

            threshold_value = float(DBRSettings.objects.get(flag="WIPThresholdLimit").value)

            for ccr_name, wip_released_days_list in ccrwise_wip_data.items():
                avg_wip_released = sum(wip_released_days_list) / len(wip_released_days_list) if wip_released_days_list else 0
                ccr_wip_limit = ccrwise_wip_limits[ccr_name]
                threshold_limit = ccr_wip_limit * (1 + threshold_value / 100)
                
                if threshold_limit > avg_wip_released:
                    wip_result['ulimit'].append({
                        'ccr': ccr_name,
                        'awip': round(avg_wip_released, 2),
                        'lm': round(ccr_wip_limit, 2),
                        'us': round((avg_wip_released / ccr_wip_limit) * 100, 2) if ccr_wip_limit != 0 else 0
                    })
                else:
                    wip_result['olimit'].append({
                        'ccr': ccr_name,
                        'awip': round(avg_wip_released, 2),
                        'lm': round(ccr_wip_limit, 2),
                        'us': round((avg_wip_released / ccr_wip_limit) * 100, 2) if ccr_wip_limit != 0 else 0
                    })
            logger.info('Fetched WIP Limit values')

            # Analytics part
            analytics = {}
            ccr = {}

            max_awip_days = ''
            if wip_result['olimit']:
                max_awip_days = max(wip_result['olimit'], key=lambda x: x['us'])
            elif wip_result['ulimit']:
                max_awip_days = max(wip_result['ulimit'], key=lambda x: x['us'])

            if max_awip_days:
                ccr_name = max_awip_days['ccr']

            # Filter ccr_utilization_history for the specific ccr_name
            if ccrid: 
                filtered_data = [record for record in ccr_utilization_history if str(record['ccr_id']) == str(ccrid)]
            else:
                filtered_data = [record for record in ccr_utilization_history if record['ccr_id__ccr_name'] == ccr_name]

            if filtered_data:
                ccr["ccr_id"] = filtered_data[0]['ccr_id']
                ccr["ccr_name"] = filtered_data[0]['ccr_id__ccr_name']

            # Populate the analytics dictionary
            for record in filtered_data:
                date = record['entry_on'].strftime('%Y-%m-%d')  # Ensure date is formatted as string
                percent_utilization = record['percent_utilization']
                history_wip_limit = record['cumulative_wip_limit']
                wip_released_days = record['wip_released_days']
                
                threshold_limit = history_wip_limit * (1 + threshold_value / 100)
                wc_status = 'ol' if wip_released_days > threshold_limit else 'ul'

                analytics[date] = {
                    'up': percent_utilization,
                    'wc': wc_status
                }

            logger.info('Fetched Analytics data')

            response_data = {
                'utilization': result,
                'wiplimit': wip_result,
                'analytics': analytics,
                'ccr': ccr
            }

            return api_response(data = response_data, msg='Data fetched successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)

