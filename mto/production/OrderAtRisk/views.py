
from mto_app.models import ( OrderData)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import (ExcelExportData, api_response, CustomPagination,  filter_order_data_by_params,GetUserDetails,DataPermissionFilterForOrderData)
from mto_app.utils import   eReportName


logger = logging.getLogger(__name__)

class OrdersAtRiskView(APIView):
    pagination_class = CustomPagination
    @swagger_auto_schema(
        operation_description='Get Orders at Risk data',
        manual_parameters=[
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
        return self.getOrderForRisk(request)
    
    def put(self,request):
        return self.getOrderForRisk(request,method = 'PUT')

    def getOrderForRisk(self,request,method = "GET"):
        try:
            filter_data = request.data
            default_no_of_reasons_to_display = 10
            export = request.GET.get('export')
            graphflag =request.GET.get('graphflag')
            graph_data_param = bool(int(graphflag)) if graphflag is not None else False
            report_name = request.GET.get('report_name')
            export_param = bool(int(export)) if export is not None else False
            headers =  filter_data.get('headers',{}) if filter_data else None

            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')
            
            # Fetch impacted orders (orders with red and black color)
            order_details = OrderData.objects.filter(color__in = ['Red','Black']).exclude(major_reason_id__isnull=True, minor_reason_id__isnull=True).values(
                'color', 'bpp', 'plant__plant_name', 'dept__dept_name', 'order_id', 'vf_order_type', 'line_id', 'item_id', 'item__item_description', 'total_qty',
                'major_reason__major_reason_desc', 'minor_reason__minor_reason_desc', 'customer__cust_code', 'customer__cust_name','dept__dept_id','order_value','ccr__ccr_id'
            ).order_by('-bpp')

            order_details = DataPermissionFilterForOrderData(order_details,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            order_details = filter_order_data_by_params(order_details,filter_data)
            logger.info('Filtered order details fetched successfully')

            logger.info('Order details fetched successfully')
            reasons = {}
            orders_at_risk = []

            for order in order_details:
                order_key = (order['major_reason__major_reason_desc'], order['minor_reason__minor_reason_desc'])
                if order_key not in reasons:
                    reason = order['major_reason__major_reason_desc'] + " | " + order['minor_reason__minor_reason_desc']
                    reasons[order_key] = {
                        'r': reason,
                        'ro': 0,
                        'bo': 0,
                    }
                if (graph_data_param):    
                    reasons[order_key]['ro'] += 1 if order['color'].lower() == 'red' else 0
                    reasons[order_key]['bo'] +=1 if order['color'].lower() == 'black' else 0
                    logger.info('Reasosns based on plant, department and major reason fetched successfully')

                orders_at_risk.append({
                    'bpp': order['bpp'],
                    'plnt': order['plant__plant_name'],
                    'oid': order['order_id'],
                    'otyp': order['vf_order_type'],
                    'li_id': order['line_id'],
                    'itmc': order['item_id'],
                    'itmd': order['item__item_description'],
                    'oqty': order['total_qty'],
                    'mjr_r': order['major_reason__major_reason_desc'],
                    'min_r': order['minor_reason__minor_reason_desc'],
                    'cc': order['customer__cust_code'],
                    'cn': order['customer__cust_name'],
                    'cl' : order['color']
                })
                logger.info('Order at risk fetched successfully')

            if(graph_data_param):
                reasons_list = list(reasons.values())
                sorted_reasons_list = sorted(reasons_list, key=lambda x : x['ro'] + x['bo'], reverse=True)
                top_ten_reasons = []

                if len(sorted_reasons_list) <= default_no_of_reasons_to_display:
                    top_ten_reasons = sorted_reasons_list
                else :
                    top_ten_reasons = sorted_reasons_list[:default_no_of_reasons_to_display]

                logger.info('Top 10 reasons fetched successfully')
            if export_param:
                return ExcelExportData(orders_at_risk, report_name , eReportName.OrdersAtRisk.value, headers)
        

            # return paginated_orders
            if(graph_data_param):
                response_data = top_ten_reasons
                return api_response(data=response_data, msg='Data fetched successfully', status_code=status.HTTP_200_OK);

            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(orders_at_risk, request)
            return paginator.get_paginated_response(paginated_response_data, msg="Orders at risk fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f'An Exception has occurred in the order at risk of {str(e)}')
            return api_response(msg=f'An Exception has occurred in the order at risk because of {str(e)}',status_code=status.HTTP_400_BAD_REQUEST)
