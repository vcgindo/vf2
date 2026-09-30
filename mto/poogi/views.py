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
from .models import *
import logging
from datetime import date, datetime, timedelta
from django.db.models import IntegerField, Case, When
from django.db import transaction
from mto_app.utils import OTIFTags, DBR_Settings, Report_Configurations, eReportName
from dateutil.relativedelta import relativedelta

# Create your views here.


logger = logging.getLogger(__name__)




class GetBMReportRemarksView(APIView):
    @swagger_auto_schema(
        operation_description='Get the remarks for the order',
        manual_parameters=[
            openapi.Parameter('ok', openapi.IN_QUERY,type=openapi.TYPE_STRING,description='get remarks for particular orders',required=True),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        try:
            order_key = request.GET.get('ok')
            if not order_key:
                return api_response('Order key parameter is required',status_code=status.HTTP_400_BAD_REQUEST)
            order_remarks_data = BMReportRemarks.objects.filter(order = order_key).values('dept','remark','added_on','added_by').order_by('-added_on')
            logger.info('Fetched the remarks for the order')

            if not order_remarks_data:
                return api_response('No remarks are present for the order',status_code=status.HTTP_200_OK)
            else:
                return api_response(data = order_remarks_data,msg='Remarks have been fetched sucessfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.error(f'An Eception has ocurred in the Get BM report remarks due to {str(ex)}')
            return api_response(msg=f'An Eception has ocurred in the Get BM report remarks due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)

