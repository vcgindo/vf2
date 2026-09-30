from mto_app.models import ( OrderHistory,PlantMaster )
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import ( api_response, color_mapping, get_last_successful_run_date)
from django.db.models import Count
from datetime import date,timedelta

logger = logging.getLogger(__name__)

class BMTrendDataView(APIView):
    @swagger_auto_schema(
        operation_description="Fetch color trend data for the past 90 days with an optional plant filter",
        manual_parameters=[
            openapi.Parameter(
                'plantId', openapi.IN_QUERY,description="Filter results by plant ID", type=openapi.TYPE_INTEGER, required=False
            )
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        default_horizon = 90
        try:
            plant_id_param = request.GET.get('plantId')
            if plant_id_param is not None:
                filter_condition = {'plant': plant_id_param}
            else:
                filter_condition = {}

            run_date = get_last_successful_run_date()
            ninety_days_back_date = run_date - timedelta(days = default_horizon)
            distinct_orders = OrderHistory.objects.filter(**filter_condition, run_date__gte = ninety_days_back_date).values('order_id','line_id','color','run_date','plant','plant__plant_name').distinct().order_by('run_date')
            logger.info('Distinct orders have been fetched for previous 90 days from orderhistory')
            #fetch all plant data from PlantMaster
            plant_master_data = PlantMaster.objects.values('plant_id','plant_name')
            logger.info('Plant master data fetched')
            orders = distinct_orders.values('run_date','color').annotate(color_count = Count('color')).order_by('run_date','color')
            logger.info('Color count for a specific run date')
            result = {}
            color_map = color_mapping()
            for order in orders:
                run_date = order['run_date']
                run_date = run_date.isoformat()
                color = order['color']
                color = color.capitalize()
                color_initials = color_map.get(color)
                colorcount = order['color_count']
                if run_date not in result:
                    result[run_date] = {}
                result[run_date][color_initials] = colorcount

            result["plants"] = {plant["plant_id"]: plant["plant_name"] for plant in plant_master_data}
           
            return api_response(data = result,msg='Data fetched successfully',status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f'An Exception has occurred in the BM Trend Data because of {str(e)}')
            return api_response(msg=f'An Exception has occurred in the BM Trend Data because of {str(e)}',status_code=status.HTTP_400_BAD_REQUEST)

