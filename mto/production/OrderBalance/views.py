
from mto_app.models import ( OrderData, Order_WIPDetails)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import (ExcelExportData, api_response, CustomPagination, filter_order_data_by_params,GetUserDetails,DataPermissionFilterForOrderData)
from django.db.models import Count
from mto_app.utils import  eReportName

logger = logging.getLogger(__name__)

class GetOrderBalanceView(APIView):
    pagination_class = CustomPagination
    @swagger_auto_schema(
        operation_description='Get order balance screen data for orders',
        manual_parameters=[
            openapi.Parameter('graphflag',openapi.IN_QUERY,description='Flag for fetching graph data',type=openapi.TYPE_INTEGER),
            openapi.Parameter('ordertype',openapi.IN_QUERY,description='dropdown selection for fetching order of that type',type=openapi.TYPE_STRING),
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
        return self.getOrderBalanceData(request)
    
    def put(self,request):
        return self.getOrderBalanceData(request,method = 'PUT')
    

    def getOrderBalanceData(self, request,method = 'GET'):
        try:
            graphflag =request.GET.get('graphflag')
            ordertype = request.GET.get('ordertype')
            graph_data_param = bool(int(graphflag)) if graphflag is not None else False
            order_type_param = ordertype
            filter_data = request.data
            export = request.GET.get('export')
            report_name = request.GET.get('report_name')
            export_param = bool(int(export)) if export is not None else False
            headers =  filter_data.get('headers',{})
            response_data = []
            # bpp is null is for temporary
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')

            orders = OrderData.objects.filter(is_line_finished = False, is_rm_released = True, trailing_dept__isnull=False).values('color',
            'bpp', 'plant__plant_name', 'order_id', 'order_type__desc', 'line_id', 'item_id', 'item__item_description', 'total_qty','dept__dept_id',
            'customer__cust_code', 'customer__cust_name', 'ccr__ccr_id', 'ccr__ccr_name', 'order_key','order_value','item__item_code',
            'trailing_dept__dept_name', 'trailing_dept__dept_id', 'order_type__order_type').order_by('-bpp')
            logger.info("Orders fetched successfully")
            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            orders = filter_order_data_by_params(orders,filter_data)

            order_keys = []
            order_keys = [order['order_key'] for order in orders]
            tdept_ids = [order['trailing_dept__dept_id'] for order in orders]

            wip_orders = Order_WIPDetails.objects.filter(order__in = order_keys).values(
                'order_id', 'mfg_balance', 'dispatch_balance', 'dept')
            logger.info("Order details fetched successfully")

            
            tdept_ord_cnt = {}
            balance_orders = []

            dispatch_qty = 0
            pending_qty = 0

            for order in orders:
                current_wip_orders = wip_orders.filter(order = order)
                for wip_order in current_wip_orders:
                        if wip_order['mfg_balance']:
                            pending_qty += wip_order['mfg_balance']
                        if wip_order['dispatch_balance']:
                            dispatch_qty += wip_order['dispatch_balance']
                balance_orders.append({
                    'bpp': order['bpp'],
                    'plnt': order['plant__plant_name'],
                    'oid': order['order_id'],
                    'otyp': order['order_type__desc'],
                    'li_id': order['line_id'],
                    'itmc': order['item_id'],
                    'itmd': order['item__item_description'],
                    'oqty': order['total_qty'],
                    'tdept': order['trailing_dept__dept_name'],
                    'bal_mfg': pending_qty,
                    'bal_dis': dispatch_qty,
                    'cc': order['customer__cust_code'],
                    'cn': order['customer__cust_name'],
                    'clr': order['color'],
                    'tdept_id': order['trailing_dept__dept_id']
                })

            balance_to_mfg = {}
            balance_to_disp = {}

            if graph_data_param:
                trailing_dept_details  = orders.values('color','trailing_dept__dept_name').annotate(color_count = Count('color')).order_by('trailing_dept__dept_name','color')
                for dept in trailing_dept_details:
                    if dept['trailing_dept__dept_name'] not in tdept_ord_cnt:
                        tdept_ord_cnt[dept['trailing_dept__dept_name']] = {}
                    if dept['color'] not in tdept_ord_cnt[dept['trailing_dept__dept_name']]:
                        tdept_ord_cnt[dept['trailing_dept__dept_name']][dept['color']] = 0 
                    tdept_ord_cnt[dept['trailing_dept__dept_name']][dept['color']] = dept['color_count']
                logger.info("Trailing department wise orders fetched successfully")

                if order_type_param and graph_data_param:
                    orders_of_ordertype = orders.filter(order_type__order_type = order_type_param)

                    if orders_of_ordertype:
                        bal_to_dispatch = 0
                        bal_to_mfg = 0
                        for order in orders_of_ordertype:
                            for wip_order in wip_orders:
                                color = None
                                wip_dept = None
                                if order['order_key'] == wip_order['order_id'] and order['trailing_dept__dept_id'] == wip_order['dept']:
                                    color = order['color']
                                    bal_to_mfg += wip_order['mfg_balance'] if wip_order['mfg_balance'] else 0
                                    bal_to_dispatch += wip_order['dispatch_balance'] if wip_order['dispatch_balance'] else 0
                                    wip_dept = order['trailing_dept__dept_name']

                                if wip_dept and color:
                                    if wip_dept not in balance_to_mfg:
                                        balance_to_mfg[wip_dept] = {}

                                    if wip_dept not in balance_to_disp:
                                        balance_to_disp[wip_dept] = {}

                                    if color not in balance_to_mfg[wip_dept]:
                                        balance_to_mfg[wip_dept][color] = 0 

                                    if color not in balance_to_disp[wip_dept]:
                                        balance_to_disp[wip_dept][color] = 0 

                                    balance_to_mfg[wip_dept][color] = bal_to_mfg
                                    balance_to_disp[wip_dept][color] = bal_to_dispatch
                    logger.info("Trailing department wise balance to manufacture and balance to disptach is calculated successfully for orders of specific order type")
                response_data.append({
                    'tdept_ord_cnt' : tdept_ord_cnt,
                    'mfg': balance_to_mfg,
                    'disp': balance_to_disp
                })
                return api_response(data = response_data,msg='Line CCR Details has been fetched successfully',status_code=status.HTTP_200_OK)
            if export_param :
                return ExcelExportData(balance_orders, report_name , eReportName.OrderBalance.value, headers)

            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(balance_orders, request)

            logger.info("Returning the paginated response")
            return paginator.get_paginated_response(paginated_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)

