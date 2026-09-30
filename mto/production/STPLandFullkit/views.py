from mto_app.models import ( BatchwiseProductionComponentAllocation, BatchwiseProductionOrderAllocation, CCRUtilizationHistory,  FOL_Data, CCRItemTypeMapping,
 OrderData,BatchwiseComponentAllocation)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import (ExcelExportData, api_response, CustomPagination, filter_order_data_by_params,GetUserDetails,DataPermissionFilterForOrderData)
from django.db.models import F,OuterRef,  Exists

from mto_app.utils import  eReportName


logger = logging.getLogger(__name__)

class STPLandFullkitInDaysView(APIView):
    pagination_class = CustomPagination
    @swagger_auto_schema(
        operation_description='Get order balance screen data for orders',
        manual_parameters=[
            openapi.Parameter('graphflag',openapi.IN_QUERY,description='Flag for fetching graph data',type=openapi.TYPE_INTEGER),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        return self.getSTPLandFullkitData(request)

    def put(self, request):
        return self.getSTPLandFullkitData(request,method = 'PUT')

    def getSTPLandFullkitData(self,request,method = 'GET'):
        try:
            graphflag =request.GET.get('graphflag')
            graph_data_param = bool(int(graphflag)) if graphflag is not None else False
            result = ''
            filter_data = request.data
            export = request.GET.get('export')
            report_name = request.GET.get('report_name')
            export_param = bool(int(export)) if export is not None else False
            headers =  filter_data.get('headers',{})
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')

            # Fetch order (fg) data
            orders = OrderData.objects.filter(is_rm_released = True).values('order_id', 'vf_order_type', 'line_id', 'item_id', 'item__item_description', 
                'total_qty', 'pending_qty', 'is_rm_released', 'plant__plant_name', 'dept__dept_name','item__item_code','dept__dept_id','customer__cust_code','customer__cust_name',
                'ccr__ccr_group__ccr_group_name', 'ccr__ccr_name', 'ccr__ccr_id', 'ccr__working_hours_per_day','vf_order_type', 'order_value'
            ).annotate(
                    in_batchwise_allocation=Exists(
                        BatchwiseComponentAllocation.objects.filter(
                            order_id=OuterRef('order_id'),
                            line_item=OuterRef('line_id')
                        )
                    )
                ).order_by('-in_batchwise_allocation', 'order_id').distinct()
            logger.info("Order data fetched successfully")
            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            orders = filter_order_data_by_params(orders,filter_data)

            # Fetch FOL data for all CCRs (collecting additional attributes for fullkit list)
            ccr_ids = [order['ccr__ccr_id'] for order in orders]
            ccr_fol_data = FOL_Data.objects.filter(ccr_id__in=ccr_ids).prefetch_related('ccr').values('ccr__ccr_id', 'ccr__ccr_name',
                 'ccr__cumulative_wip_limit', 'stpl_in_days', 'fol_in_days')
            logger.info("stpl with limits fetched successfully")  

            stpl = []
            for fol_data in ccr_fol_data:
                stpl.append({
                    'ccr_n': fol_data['ccr__ccr_name'],
                    'limit': fol_data['ccr__cumulative_wip_limit'],
                    'r_wip': fol_data['stpl_in_days']
                })
            logger.info("stpl with limits structured in list successfully")

            # Fetch batchwise component data for level 0
            order_ids = [order['order_id'] for order in orders]
            fg_data = BatchwiseProductionOrderAllocation.objects.filter(order_id__in = order_ids).values(
                'order_id','line_item','item_code').annotate(available_fg=F('stock_on_hand') + F('stock_in_qc') + F('stock_in_transit'))
            logger.info("batchwise component fetched successfully")
            fg_details = {(data['order_id'],data['line_item'],data['item_code']) : data for data in fg_data}

            # Fetch batchwise component data for level1 to level n
            rm_data = BatchwiseProductionComponentAllocation.objects.filter(order_id__in = order_ids).values(
                'order_id','line_item','item_code', 'order_remaining', 'bom_level').annotate(available_rm=F('stock_on_hand') + F('stock_in_qc') + F('stock_in_transit'), 
                required_rm = F('order_qty'), wip = F('stock_in_qc') + F('stock_in_transit'))
            logger.info("batchwise component fetched successfully")

            grid_orders = {}
            for order in orders:
                okey = (order['order_id'], order['line_id'], order['item_id'])
                if okey not in grid_orders:
                    grid_orders[okey] = []
                grid_orders[okey].append({
                    'oid': order['order_id'],
                    'lid': order['line_id'],
                    'ic': order['item_id'],
                    'req': order['total_qty'],
                    'plnt': order['plant__plant_name'],
                    'cg': order['ccr__ccr_group__ccr_group_name'],
                    'dept': order['dept__dept_name'],
                    'ccr': order['ccr__ccr_name'],
                    'stk': '',
                    'rwip': 0,
                    'gap': '',
                    'un_fk': 0,
                    'is_rm': order['is_rm_released'],
                    'whrs': order['ccr__working_hours_per_day'],
                    'pqty': order['pending_qty'],
                    'rm_dtls':[]
                })
            logger.info("grid orders fetched and formed successfully")

            wip_dtls = CCRUtilizationHistory.objects.filter(ccr__in = ccr_ids).values('ccr__ccr_name', 'wip_released_days')

            for key, order_values in grid_orders.items():
                for wip in wip_dtls:
                    if order_values[0]['ccr'] == wip['ccr__ccr_name']:
                        order_values[0]['rwip'] = wip['wip_released_days']
            logger.info("wip details fetched successfully")

            rm_dtls = {}
            # collecting rm which belongs to specific order
            for rm in rm_data:
                okey = (rm['order_id'],rm['line_item'])
                if okey not in rm_dtls:
                    rm_dtls[okey] = []
                rm_dtls[okey].append({
                        'rc': rm['item_code'],
                        'req': rm['required_rm'], 
                        'stk': rm['available_rm'], 
                        'wip': rm['wip'],
                        'gap': rm['required_rm'] - rm['available_rm'],
                        'lvl': rm['bom_level'],
                        'or': rm['order_remaining']
                })
            logger.info("rm details fetched successfully")

            for okey in grid_orders:
                if okey in fg_details:
                    grid_orders[okey][0]['stk'] = fg_details[okey]['available_fg']
                    grid_orders[okey][0]['gap'] = grid_orders[okey][0]['req'] - fg_details[okey]['available_fg']
                okey_for_rm = okey[:-1]
                if okey_for_rm in rm_dtls :
                    grid_orders[okey][0]['rm_dtls'].append(rm_dtls[okey_for_rm])

            tt_details_of_ccr = CCRItemTypeMapping.objects.filter(ccr__in = ccr_ids).values('ccr', 'ccr__ccr_name', 'item_type', 'touch_time_in_mins')

            orderwise_fullkit_in_days = {}
            for key, order_values in grid_orders.items():
                for ccr in tt_details_of_ccr:
                    if order_values[0]['ccr'] == ccr['ccr__ccr_name']:
                        ord_rem_sum = sum(item['or'] for sublist in grid_orders[key][0]['rm_dtls'] for item in sublist if item.get('or'))
                        fullkit_in_days = 0
                        if ord_rem_sum == 0 and grid_orders[key][0]['is_rm']:
                            if order_values[0]['whrs'] != 0 and order_values[0]['whrs']:
                                ccr_capacity = (ccr['touch_time_in_mins'] * 60) / order_values[0]['whrs'] if ccr['touch_time_in_mins'] and order_values[0]['whrs'] else 0
                                if ccr_capacity and ccr_capacity > 0:
                                    fullkit_in_days = order_values[0]['pqty']/ccr_capacity
                            if ccr['ccr__ccr_name'] not in orderwise_fullkit_in_days:
                                orderwise_fullkit_in_days[ccr['ccr__ccr_name']] = []
                                orderwise_fullkit_in_days[ccr['ccr__ccr_name']].append({
                                    'ccr_n': ccr['ccr__ccr_name'],
                                    'days': round(fullkit_in_days,2) if fullkit_in_days else 0
                                })
                        elif ord_rem_sum == 0 and not grid_orders[key][0]['is_rm']:
                            if order_values[0]['whrs'] != 0 and order_values[0]['whrs']:
                                ccr_capacity = (ccr['touch_time_in_mins'] * 60) / order_values[0]['whrs'] if ccr['touch_time_in_mins'] and order_values[0]['whrs'] else 0
                                if ccr_capacity and ccr_capacity > 0:
                                    fullkit_in_days = order_values[0]['pqty']/ccr_capacity
                                    fullkit_in_days = round(fullkit_in_days, 2) if fullkit_in_days else 0
                            grid_orders[key][0]['un_fk'] = fullkit_in_days
            logger.info("graph data fetched successfully")

            for key,value in grid_orders.items():
                if value[0]['whrs']:
                    del value[0]['whrs']
                if value[0]['pqty']:
                    del value[0]['pqty']
                if value[0]['is_rm']:
                    del value[0]['is_rm']
                if value[0]['rm_dtls']:
                    del value[0]['rm_dtls']

            orderwise_fullkit_in_days_list = []
            for key, values in orderwise_fullkit_in_days.items():
                for value in values:
                    orderwise_fullkit_in_days_list.append(value)
            sorted_orderwise_fullkit_in_days_list = sorted(orderwise_fullkit_in_days_list, key=lambda x: x['days'])

            if graph_data_param:
                result = {
                    'stpl': stpl,
                    'fk':sorted_orderwise_fullkit_in_days_list
                }
                return api_response(data = result,msg='Data fetched successfully',status_code=status.HTTP_200_OK)

            grid_orders_list = []
            for key, values in grid_orders.items():
                for value in values:
                    grid_orders_list.append(value)
            if export_param  and (not graph_data_param):
                return ExcelExportData(grid_orders_list, report_name , eReportName.STPLAndFullKits.value, headers)
            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(grid_orders_list, request)

            logger.info("Returning the paginated response")
            return paginator.get_paginated_response(paginated_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.info(f'An Exception has occurred in the stpl and fullkit in days of {str(e)}')