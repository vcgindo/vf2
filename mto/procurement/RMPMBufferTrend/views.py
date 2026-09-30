from datetime import date, timedelta
from rest_framework.views import APIView
from rest_framework import status
from mto_app.models import ( OrderHistory )
from mto_app.common.commonfunctions import (api_response , filter_order_history_data_by_params, get_last_successful_run_date)
import logging
from django.db.models import Count
from mto_app.utils import  HorizonEnum


logger = logging.getLogger(__name__)

class GetRMPMBufferTrendMTOMTAView(APIView):
    def get(self,request):
        return self.get_rm_pm_buffer_trend(request)
    
    def put(self,request):
        return self.get_rm_pm_buffer_trend(request,method = 'PUT')

    def get_rm_pm_buffer_trend(self,request , method = 'GET'):
        default_horizon = HorizonEnum.default_horizon.value
        try:
            filter_data = request.data
            run_date = get_last_successful_run_date()
            horizon_start_date = run_date - timedelta(days=default_horizon)
            run_dates = OrderHistory.objects.filter(run_date__gte = horizon_start_date).values()
            logger.info("Order History fetched forprevious 90 days in GetRmPmBufferTrendMTOView")
            if filter_data:
                run_dates = filter_order_history_data_by_params(run_dates,filter_data)
                logger.info("Filtered the order history based on the filter data provided in GetRmPmBufferTrendMTOView")
                
            grouped_data = {}
            run_dates = run_dates.values('run_date','color','vf_order_type').annotate(color_count = Count('id')).order_by('run_date')
            #color mapping for storing the color initiales in the response data
            color_mapping = {'Black' : 'B','Blue': 'Bl','White':'W','Yellow':'Y','Red' : 'R','Green':'G'}
            for entry in run_dates:
                run_date = entry['run_date']
                #conversion of date into standard format
                run_date_str = run_date.isoformat()
                color = entry['color']
                color  = color.capitalize()
                color = color_mapping.get(color)
                if entry['vf_order_type'] not in grouped_data:
                    grouped_data[entry['vf_order_type']] = {}
                if run_date_str not in grouped_data[entry['vf_order_type']]:
                    grouped_data[entry['vf_order_type']][run_date_str] = {}
                count = entry['color_count']
                grouped_data[entry['vf_order_type']][run_date_str][color] = count
            return api_response(data = grouped_data,msg='Data fetched successfully for GetRmPmBufferTrendMTOView',status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred in GetRmPmBufferTrendMTOView: {str(e)}")
            return api_response(error=f"Failed due to the exception {str(e)}",status_code=status.HTTP_400_BAD_REQUEST)
