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

class TrendOfFailureReasonsView(APIView):
    @swagger_auto_schema(
        operation_description='Get trend of failure reasons',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request): 
        return self.trendOfFailureReasons(request) 

    def put(self,request): 
        return self.trendOfFailureReasons(request,method = 'PUT') 

    def get_impacted_OTIF_orders_with_reasons(self, first_day, last_day, orders):
        reasons = {}
        for order in orders:
            if first_day <= order['cdt'] <= last_day:
                reason_key = (order['mjr'], order['mnr'])
                reason = order['mjr'] + " - " + order['mnr']
                cdate = datetime.strptime(order['cdt'].strftime('%Y-%m-%d'), '%Y-%m-%d').strftime('%b %Y')
                if reason_key not in reasons:
                    reasons[reason_key] = {
                        'oc' : 0,
                        'mr' : {}
                    }
                if reason_key in reasons:
                    reasons[reason_key]['oc']+=1
                    if cdate not in reasons[reason_key]['mr']:
                        reasons[reason_key]['mr'][cdate] = {}
                    if (reason,order['clr']) not in reasons[reason_key]['mr'][cdate]:
                        reasons[reason_key]['mr'][cdate][(reason,order['clr'])] = {
                            'oc' : 0
                        }
                    reasons[reason_key]['mr'][cdate][(reason,order['clr'])] = {
                        'r': reason,
                        'cdt': cdate,
                        'oc': reasons[reason_key]['mr'][cdate][(reason,order['clr'])].get('oc',0) + 1,
                        'clr': order['clr']
                    }
        return reasons

    def get_monthwise_reasons(self, reasons):
        monthwise_reasons = {}
        for reason_key, reason_value in reasons.items():
            for cdt_key, cdt_value in reason_value['mr'].items():
                monthwise_reason_list = list(cdt_value.values())
                monthwise_reasons[cdt_key] = monthwise_reason_list
        return monthwise_reasons

    def trendOfFailureReasons(self,request,method = 'GET'): 
        try:
            if method == 'PUT':
                filter_data = request.data
            else:
                filter_data = None
            
            data_permission_data = request.data
            todays_date = get_last_successful_run_date()
            
            first_day_of_current_month = todays_date.replace(day=1)
            first_day_of_initial_past_month = first_day_of_current_month - relativedelta(months=4)
            
            last_day_of_past_month = first_day_of_current_month - relativedelta(days=1)
            product_permissions,location_permissions,is_admin = GetUserDetails(data_permission_data)
            logger.info('Data permissions fetched successfully')

            orders = ClosedOrders.objects.filter(closure_date__range = [first_day_of_initial_past_month, todays_date]).exclude(major_reason_id__isnull=True, minor_reason_id__isnull=True).values('bpp', 'ccr', 'dept').annotate(plnt = F('plant__plant_name'),oid = F('order_id'), 
                lid = F('line_id'), pqty = F('pending_qty'), cdt = F('closure_date'), clr = F('color'), 
                id = F('item__item_description'), cc = F('customer__cust_code'), cn = F('customer__cust_name'), 
                mjr = F('major_reason__major_reason_desc'), mnr = F('minor_reason__minor_reason_desc'), 
                dd = F('due_date'), ov = F('order_value'), ot = F('order_type__desc'), ic = F('item__item_code'), ott = F('ot_tag'), ift = F('if_tag'))
            logger.info('orders data fetched successfully')
            orders = DataPermissionFilterForOrderData(orders, product_permissions,location_permissions,is_admin,True)
            logger.info('Filtered the closed order data based on the permissions of the user')
            
            if filter_data:
                orders = filter_closed_orders_data_by_params(orders, filter_data)

            flags = [DBR_Settings.unresolved_reason_threshold, DBR_Settings.emergent_reason_threshold]
            dbr_settings = DBRSettings.objects.filter(flag__in = flags).values('flag', 'value')

            unresolved_reason_threshold = 0
            emergent_reason_threshold = 0

            for dbr_setting in dbr_settings:
                if dbr_setting['flag'] == DBR_Settings.unresolved_reason_threshold:
                    unresolved_reason_threshold = int(dbr_setting['value'])
                elif dbr_setting['flag'] == DBR_Settings.emergent_reason_threshold:
                    emergent_reason_threshold = int(dbr_setting['value'])

            grid_orders = []
            tag = 0
            top_ten_unresolved_reasons = {}
            if orders:
                for order in orders:
                    tag = get_OTIF_status_of_order(order['ott'], order['ift'])
                    if tag == OTIFTags.OT_False_IF_False:
                        grid_orders.append({
                            'tag': tag,
                            'oid': order['oid'],
                            'lid': order['lid'],
                            'mjr': order['mjr'],
                            'mnr': order['mnr'],
                            'cdt': order['cdt'],
                            'clr': order['clr']
                            })
            logger.info('grid orders fetched successfully')
            
            past_four_month_OTIF_reasons = self.get_impacted_OTIF_orders_with_reasons(first_day_of_initial_past_month, last_day_of_past_month, grid_orders)
            logger.info('past four months OTIF orders fetched successfully')
            orders_with_unresolved_reasons = dict(sorted(past_four_month_OTIF_reasons.items(), key=lambda item: item[1]['oc'], reverse=True))
            if len(orders_with_unresolved_reasons) <= unresolved_reason_threshold:
                top_ten_unresolved_reasons = orders_with_unresolved_reasons
            else :
                top_ten_unresolved_reasons = dict(list(orders_with_unresolved_reasons.items())[:unresolved_reason_threshold])
            logger.info('top ten unresolved reasons fetched successfully')
            
            current_month_OTIF_reasons = self.get_impacted_OTIF_orders_with_reasons(first_day_of_current_month, todays_date, grid_orders)
            logger.info('current month OTIF reasons fetched successfully')

            emergent_reason_threshold_value = (emergent_reason_threshold/100)
            number_of_days_in_past_four_months = (last_day_of_past_month - first_day_of_initial_past_month).days + 1
            no_days_in_current_month = (todays_date - first_day_of_current_month).days + 1
            past_month_oc = 0
            current_month_oc = 0
            # if current_month_reasons and past_four_month_reasons:
            for key in past_four_month_OTIF_reasons:
                past_month_oc = past_four_month_OTIF_reasons[key]['oc']
                if key in current_month_OTIF_reasons:
                    current_month_oc = current_month_OTIF_reasons[key]['oc']
                # Calculate 15% increase of 'oc' value in past_four_month_reasons
                average_oc_of_past_four_months = past_month_oc / (number_of_days_in_past_four_months if number_of_days_in_past_four_months else 1)
                average_oc_of_current_month = current_month_oc / (no_days_in_current_month if no_days_in_current_month else 1)
                expected_increased_oc =average_oc_of_past_four_months + (average_oc_of_past_four_months * emergent_reason_threshold_value)
                # Check if the increased 'oc' value matches the 'oc' value in current_month_reasons
                if key in current_month_OTIF_reasons:
                    if round(expected_increased_oc,2) < round(average_oc_of_current_month,2):
                        # Insert new key 'e' with value 'true' in both dictionaries
                        past_four_month_OTIF_reasons[key]['e'] = True
                        current_month_OTIF_reasons[key]['e'] = True
                    elif round(expected_increased_oc,2) > round(average_oc_of_current_month,2):
                        # Insert new key 'dt' with value 'true' in both dictionaries
                        past_four_month_OTIF_reasons[key]['dt'] = True
                        if current_month_OTIF_reasons:
                            current_month_OTIF_reasons[key]['dt'] = True
                    if key in top_ten_unresolved_reasons:
                        # Insert new key 'ur' with value 'true' in both dictionaries
                        past_four_month_OTIF_reasons[key]['ur'] = True
                        if key in current_month_OTIF_reasons:
                            current_month_OTIF_reasons[key]['ur'] = True
            logger.info('emergent unresolved, downtrend reasons marked successfully')
            
            emergent_and_unresolved_issues = {key: value for key, value in past_four_month_OTIF_reasons.items() if value.get('e') and value.get('ur')}
            downward_trend = {key: value for key, value in past_four_month_OTIF_reasons.items() if value.get('dt')}

            if emergent_and_unresolved_issues:
                for key in emergent_and_unresolved_issues:
                    if 'e' in emergent_and_unresolved_issues[key]:
                        del emergent_and_unresolved_issues[key]['e']
                    if 'ur' in emergent_and_unresolved_issues[key]:
                        del emergent_and_unresolved_issues[key]['ur']

            if downward_trend:
                for key in downward_trend:
                    if 'dt' in downward_trend[key]:
                        del downward_trend[key]['dt']

            emergent_and_unresolved_reasons = self.get_monthwise_reasons(emergent_and_unresolved_issues)
            down_trend_reasons = self.get_monthwise_reasons(downward_trend)
            logger.info('monthwise reasons arranged successfully')
            response_data = {
                'eu': emergent_and_unresolved_reasons,
                'dt': down_trend_reasons
            }

            return api_response(data=response_data,msg="Trend of failure reasons data has been fetched successfully",status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An exception has ouccured in get Trend of failure reasons api due to {str(ex)}')
            return api_response(msg=f'An exception has ouccured in Trend of failure reasons api due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)

