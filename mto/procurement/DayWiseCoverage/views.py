from datetime import  timedelta, datetime
from rest_framework.views import APIView
from rest_framework import status
from mto_app.models import (
DaywiseCoverageHistory, DaywiseCoverageRMDetails,  BatchwiseComponentAllocation ,  ItemMaster ,OrderData , EcoStock)
from mto_app.common.commonfunctions import (api_response , fetch_leaf_nodes, 
get_daywise_coverage_history_orders_details,ExcelExportData , GetUserDetails, DataPermissionFilterForOrderData ,
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
from django.db.models import Sum,CharField, Value, DecimalField, F, DateField, IntegerField
from mto_app.utils import eReportName

from django.db.models import CharField


logger = logging.getLogger(__name__)

class GetDayWiseCoverageView(APIView):
    @swagger_auto_schema(
        operation_description="Retrieve Day wise coverage data",
        manual_parameters=[
            openapi.Parameter('FromDate', openapi.IN_QUERY, description="from which date data need to be collected", type=openapi.TYPE_STRING,required=True),
            openapi.Parameter('ToDate', openapi.IN_QUERY, description="to which date data need to be collected, this will be the last date of current month", type=openapi.TYPE_STRING,required=True),
            openapi.Parameter('planned_release_date', openapi.IN_QUERY, description="get orders of this planned release date", type=openapi.TYPE_STRING),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            400: "Bad Request: Error retrieving data"
        }
    )

    def get(self,request):
        return self.getDayWiseCoverageData(request)
    
    def put(self,request):
        return self.getDayWiseCoverageData(request,method = 'PUT')
 
    def getDayWiseCoverageData(self, request, method = 'GET', format=None):
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
            data_for_permission = request.data
            response_data = []
            planned_release_date = None
            from_date = None
            to_date = None
            if request.GET.get('planned_release_date'):
                planned_release_date = datetime.strptime(request.GET.get('planned_release_date'), "%Y-%m-%d").date()
 
            if request.GET.get('FromDate') and request.GET.get('ToDate'):
                from_date = datetime.strptime(request.GET.get('FromDate'), "%Y-%m-%d").date()
                to_date = datetime.strptime(request.GET.get('ToDate'), "%Y-%m-%d").date()
 
            filter_for_daywise_coverage = []
            filter_for_order_data = []
 
            if from_date and to_date:
                todays_date = datetime.now().date()
                next_day = todays_date + timedelta(days=1)
                next_day = next_day.strftime("%Y-%m-%d")
 
                if from_date < todays_date and to_date < todays_date: # past past
                    filter_for_daywise_coverage = [from_date,to_date]
                    filter_for_order_data = None
                elif from_date == todays_date and to_date > todays_date: # present future
                    filter_for_daywise_coverage = [from_date,todays_date]
                    filter_for_order_data = [next_day, to_date]
                elif from_date < todays_date and to_date == todays_date: # past-present
                    filter_for_daywise_coverage = [from_date, to_date]
                    filter_for_order_data = None
                elif from_date > todays_date and to_date > todays_date: # future-future
                    filter_for_daywise_coverage = None
                    filter_for_order_data = [from_date, to_date]
                elif from_date < todays_date and to_date > todays_date: # past-future
                    filter_for_daywise_coverage = [from_date,todays_date]
                    filter_for_order_data = [next_day, to_date]
            all_orders = {}
            order_data_orders = None
            daywise_coverage_orders = None
            daywise_coverage_orders_with_details = None
            if filter_for_daywise_coverage:
                daywise_coverage_orders = DaywiseCoverageHistory.objects.filter(planned_release_date__range=filter_for_daywise_coverage).values('order_id',
                    'line_id', 'planned_release_date', 'order_entry_date', 'customer__cust_name','customer__cust_code', 'item', 'item__item_description').annotate(total_qty=Value(50.00, output_field=DecimalField(0.00)),
                    due_date=Value(None, output_field=DateField()), color=Value(None, output_field=CharField()), kit_status = F('kit_status'), plant=Value(None, output_field=IntegerField()))
                if daywise_coverage_orders:
                    # get order related latest details from orderdata  or closedorders
                    daywise_coverage_orders_with_details = get_daywise_coverage_history_orders_details(daywise_coverage_orders)
                    logger.info("Fetched latest order details successfully")
            if filter_for_order_data:
                product_permissions,location_permissions,is_admin = GetUserDetails(data_for_permission)
                logger.info('Permission data is fetched from the payload')

                order_data_orders = OrderData.objects.filter(planned_release_date__range=filter_for_order_data).values('order_id',
                    'line_id', 'planned_release_date', 'order_entry_date', 'customer__cust_name','customer__cust_code', 'item', 'item__item_description', 'total_qty', 'due_date', 'color').annotate(kit_status=Value(None, output_field=CharField())
                    , plant = F('plant__plant_id'))
                order_data_orders = DataPermissionFilterForOrderData(order_data_orders,product_permissions,location_permissions,is_admin)
                logger.info('Filtered the order data based on the permissions of the user')
                
            if order_data_orders and daywise_coverage_orders_with_details:
                all_orders = daywise_coverage_orders_with_details.union(order_data_orders)
            elif order_data_orders and not daywise_coverage_orders_with_details:
                all_orders = order_data_orders
            else:
                all_orders = daywise_coverage_orders_with_details
 
            order_ids = []
            line_ids = []
            plant_ids = []
            leaf_nodes_of_orders = []
            if all_orders:
                order_ids = [order['order_id'] for order in all_orders]
                line_ids = [order['line_id'] for order in all_orders]
                plant_ids = [order['plant'] for order in all_orders]
                leaf_nodes_of_orders = fetch_leaf_nodes()
 
                # Fetch data from EcoStock
                eco_stock_data = EcoStock.objects.filter(
                    item_code__in=leaf_nodes_of_orders,
                    plant_code__in=plant_ids,
                    type__in=['StockInHand', 'StockInQC', 'StockInTransit']
                ).values('item_code').annotate(total_qty=Sum('quantity'))
                logger.info("Fetched EcoStock data successfully")
 
                eco_stock_of_items = {es['item_code']: es['total_qty'] for es in eco_stock_data}
           
            daywise_coverage_rm_orders = {}
            if filter_for_daywise_coverage:
                daywise_coverage_rm_orders = DaywiseCoverageRMDetails.objects.filter(order_id__in = order_ids, line_id__in = line_ids).values('order_id',
             'line_id', 'item_code', 'item_code__item_description', 'rm_req_qty', 'rm_available_qty', 'rm_allocated')
            logger.info("from day wise coverage rm data fetched successfully")
           
            rm_orders = {}
            if filter_for_order_data:
                rm_orders = BatchwiseComponentAllocation.objects.filter(order_id__in = order_ids, line_item__in = line_ids, item_code__in = leaf_nodes_of_orders).values('order_id',
             'line_item', 'item_code', 'order_qty', 'order_remaining', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit')
            logger.info("from order data rm data fetched successfully")
 
            # Organize BatchwiseComponentAllocation data by order_id and line_item
            if rm_orders:
                item_codes = [rm['item_code'] for rm in rm_orders]
                itemcode_and_desc = ItemMaster.objects.filter(item_code__in = item_codes).values('item_code', 'item_description')
                logger.info("item description for item codes merged successfully")
 
            rm_details = {}
            if rm_orders:
                # fetch item description for item codes
                itemcodes_with_desc = {}
                for itemcode in itemcode_and_desc:
                    ikey = itemcode['item_code']
                    if ikey not in itemcodes_with_desc:
                        itemcodes_with_desc[ikey] = ''
                    itemcodes_with_desc[ikey] = itemcode['item_description']
 
                for rm_order in rm_orders:
                    okey = (rm_order['order_id'],rm_order['line_item'])
                    available_rm = 0
                    if okey not in rm_details:
                        rm_details[okey] = []
                    available_rm = eco_stock_of_items.get(rm_order['item_code'])
                    rm_details[okey].append({
                        "mrq": rm_order['order_qty'],
                        "rmc": rm_order['item_code'],
                        "rmd": itemcodes_with_desc.get(rm_order['item_code']),
                        "rmq": rm_order['order_qty'],
                        "rmav": available_rm,
                        "rmal": rm_order['stock_on_hand'] + rm_order['stock_in_qc'] + rm_order['stock_in_transit'],
                        "or": rm_order['order_remaining']
                        })
 
            # Organize DaywiseCoverageRMDetails data by order_id and line_id
            daywise_coverage_rm_details = {}
            if daywise_coverage_rm_orders:
                for rm_order in daywise_coverage_rm_orders:
                    okey = (rm_order['order_id'],rm_order['line_id'])
                    if okey not in daywise_coverage_rm_details:
                        daywise_coverage_rm_details[okey] = []
                    daywise_coverage_rm_details[okey].append({
                        "mrq": rm_order['rm_req_qty'],
                        "rmc": rm_order['item_code'],
                        "rmd": rm_order['item_code__item_description'],
                        "rmq": rm_order['rm_req_qty'],
                        "rmav": rm_order['rm_available_qty'] if rm_order['rm_available_qty'] else 0,
                        "rmal": rm_order['rm_allocated']
                        })
 
            # Combine rm details at one place
            all_rms = {}
            if rm_details or daywise_coverage_rm_details:
                all_rms = {**rm_details, **daywise_coverage_rm_details}
            logger.info("rm data of day wise coverage and order data merged successfully")
 
            # calculate kit status for orders
            rundatewise_orders = {}  # need global access of this variable
            if all_orders:
                for order in all_orders:
                    order_id = order["order_id"]
                    line_id = order["line_id"]
                    rm = rm_details.get((order_id, line_id), [])
 
                    # Calculate cumulative order quantities and remaining quantities
                    cum_ord_qty = sum(child['rmq'] for child in rm)
                    cum_rem_qty = sum(child['or'] for child in rm)
 
                    # Determine the value for "kit"
                    if cum_ord_qty == cum_rem_qty:
                        order_kit_status = "NK"
                    elif cum_rem_qty == 0:
                        order_kit_status = "FK"
                    else:
                        order_kit_status = "PK"
 
                    childrens = rm
                    if order_kit_status == "PK":
                        if childrens:
                            for data in childrens:
                                if data.get('or') == 0 and data.get('mrq')!=0:
                                    order_kit_status = "NK"
                    order['kit_status'] = order_kit_status if order['kit_status'] is None else order['kit_status']
                logger.info('Kit status calculate for orders successfully')
               
                # calculate run date wise orders
                for order in all_orders:
                    order_planned_release_date = order['planned_release_date'].strftime('%Y-%m-%d')
                    if order_planned_release_date not in rundatewise_orders:
                        rundatewise_orders[order_planned_release_date] = []
                    rundatewise_orders[order_planned_release_date].append({
                        'oid': order['order_id'],
                        'lid': order['line_id'],
                        'ks': order['kit_status']
                    })
            logger.info("run date wise orders kit status fetched successfully")  
 
            if rundatewise_orders:
                for date, orders in rundatewise_orders.items():
                    count_fk = 0
                    count_pk = 0
                    count_nk = 0
                    oc = 0
                    if orders:
                        oc = len(orders)
                    for order in orders:
                        ks = order.get('ks', '')
                        if ks == 'FK':
                            count_fk += 1
                        elif ks == 'PK':
                            count_pk += 1
                        elif ks == 'NK':
                            count_nk += 1
                    rundatewise_orders[date]= {
                        'oc':oc,
                        'fk':count_fk,
                        'nk':count_nk,
                        'pk':count_pk
                    }
            logger.info('rundate wise orders fetched successfully')
 
            # remove 'or' from all_rm  (after calculation of kit status)
            for key, list_of_dicts in all_rms.items():
                for dict_item in list_of_dicts:
                    dict_item.pop('or', None)
 
            # Calculate grid orders data
            grid_orders = {}
            if planned_release_date:
                if all_orders:
                    for order in all_orders:
                        grid_order_planned_release_date = order['planned_release_date'].strftime('%Y-%m-%d')
                        if grid_order_planned_release_date not in grid_orders:
                            grid_orders[grid_order_planned_release_date] = []
                        order_id = order["order_id"]
                        line_id = order["line_id"]
                        grid_orders[grid_order_planned_release_date].append({
                            'clr': order['color'],
                            'on': order['order_id'],
                            'ord': order['order_entry_date'],
                            'odd': order['due_date'],
                            'cn': order['customer__cust_name'],
                            'cc': order['customer__cust_code'],
                            'ic': order['item'],
                            'id': order['item__item_description'],
                            'oq': order['total_qty'],
                            's': order['kit_status'],
                            'children': all_rms.get((order_id,line_id), [])
                        })
            logger.info('grid orders fetched successfully')
            sorting_sequence = {"NK": 0, "PK": 1, "FK": 2}
            sorted_response_data = ''
            if export_param and grid_orders:
                if report_name and headers:
                    return ExcelExportData(grid_orders.get(planned_release_date.strftime('%Y-%m-%d')), report_name, eReportName.dayWiseCoverage.value, headers)
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

            if not grid_orders:
                response_data = rundatewise_orders
                return api_response(data = response_data, msg="Data fetched Successfully for the day wise coverage",status_code=status.HTTP_200_OK)
            else:
                response_data = grid_orders.get(planned_release_date.strftime('%Y-%m-%d'))
                if response_data:
                    sorted_response_data = sorted(response_data, key=lambda x: sorting_sequence[x['s']])
                logger.info("Returning the grid records as response")
                return api_response(data = sorted_response_data, msg="Data fetched Successfully for the day wise coverage",status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)

