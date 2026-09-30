

import math
from mto_app.models import (CCRMaster,  FOL_Data, CCRItemTypeMapping,  OrderData, OrderBufferMapping ,BatchwiseComponentAllocation,BufferMaster,RouteDetails,
DailyWorkingCalendar,DBRSettings, OrderItemDetails)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import ( api_response, CustomPagination,  filter_order_data_by_params,filter_buffer_data_by_params
,GetUserDetails,DataPermissionFilterForOrderData ,CustomExcelExport)
from django.db.models import Q,OuterRef,  Exists
from datetime import date,timedelta,datetime
from django.db import transaction
from mto_app.utils import   eReportName, eChildName
import pandas as pd 
from ..Common.views import UpdateFOLandSTPL , UpdateOrderWIPDataView , CreateOverallBMReportView ,CalculateAndUpdateBufferPenetration , BomLevelExplosionForExcelExportView , AssignRouteView
#Create your views here.

logger = logging.getLogger(__name__)

class GetOrdersForDDQView(APIView):
    pagination = CustomPagination
    @swagger_auto_schema(
        operation_description='DDQ - Get order data for scheduled and unscheduled orders',
        manual_parameters=[
            openapi.Parameter('unSch',openapi.IN_QUERY,type=openapi.TYPE_INTEGER,description='parameter for scheduled or unscheduled'),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
            openapi.Parameter('analytics', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='parameter for analytics'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        return self.getOrderForDDQ(request)
    
    def put(self,request):
        return self.getOrderForDDQ(request,method = 'PUT')

    def getAnalyticsData(self,request):
        try:
            MTO_Orders = 'MTO'
            prod = 'prod'
            proc = 'proc'
            order_data = OrderData.objects.filter(vf_order_type = MTO_Orders).values('order_key','due_date','route__route_id')
            logger.info("Order data has been fetched successfully")

            unscheduled_orders = order_data.filter(due_date__isnull = True)
            total_unassigned_routes = len(unscheduled_orders.filter(route__route_id__isnull = True))
            total_scheduled_orders = len(order_data) - len(unscheduled_orders)
            order_keys = [order['order_key'] for order in unscheduled_orders]
            order_buffer_data = OrderBufferMapping.objects.filter(order__in=order_keys).values(
            'order', 'buffer', 'buffer__buffer_size', 'buffer__buffer_type__buffer_type', 'buffer__buffer_code')
            logger.info("Order buffer data has been fetched successfully")
            
            total_assigned_prod_buffer = len(order_buffer_data.filter(buffer__buffer_type__buffer_type__icontains = prod).distinct())
            total_assigned_proc_buffer = len(order_buffer_data.filter(buffer__buffer_type__buffer_type__icontains = proc).distinct())
            total_unassigned_prod_buffer = len(unscheduled_orders) - total_assigned_prod_buffer
            total_unassigned_proc_buffer = len(unscheduled_orders) - total_assigned_proc_buffer
            total_unscheduled_orders = max(total_unassigned_prod_buffer , total_unassigned_routes , len(unscheduled_orders))

            total_orders = len(order_data)
            logger.info("Total order count has been calculated successfully")

            data = {
                'pcb' : total_unassigned_proc_buffer,
                'pdb' : total_unassigned_prod_buffer,
                'ccr' : total_unassigned_routes,
                'us' : total_unscheduled_orders,
                'sc' : total_scheduled_orders,
                'ttl' : total_orders
            }
            logger.info("Data for the analytics generated")

            return api_response(data = data , msg="Analytics data has been fetched successfully",status_code = status.HTTP_200_OK)
        except Exception as e:
            return api_response(msg=f"An exception has occurred while fetching analytics data due to {str(e)}",status_code = status.HTTP_400_BAD_REQUEST)


    def getOrderForDDQ(self, request,method = 'GET'):
        try:
            headers = None
            if method == 'PUT':
                data = request.data
                headers = data.get('headers',{}) if data else None
            else:
                data = None 

            analytics = request.GET.get('analytics')
            analytics_params = bool(int(analytics)) if analytics else False
            if analytics_params:
                return self.getAnalyticsData(request)
            export = request.GET.get('export')
            export_param = bool(int(export)) if export else None

            isBomExplosion_param = request.GET.get('isBomExplosion')
            isBomExplosion = bool(int(isBomExplosion_param)) if isBomExplosion_param else False

            report_name = request.GET.get('report_name')

            filter_applied = False
            filter_data = request.data
            isFetchOnlyUnScheduledOrders = request.GET.get('unSch')
            isFetchOnlyUnScheduledOrders = bool(int(isFetchOnlyUnScheduledOrders)) if isFetchOnlyUnScheduledOrders is not None else False
            if isFetchOnlyUnScheduledOrders:
                filter_condition = {'due_date__isnull': True}
            else:
                filter_condition = {}
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')

            orders_for_scheduling = OrderData.objects.filter(**filter_condition, vf_order_type = 'MTO').values(
                'order_id', 'line_id', 'order_key', 'item__attributes', 'item__item_code',
                'item__item_description', 'item__item_type__item_type','item__item_type__item_type_id', 'total_qty',
                'pending_qty', 'pending_ccr_qty', 'plant__plant_id', 'plant__plant_name',
                'dept__dept_id', 'dept__dept_name', 'customer__cust_code',
                'customer__attribute', 'customer__cust_name', 'market_based_order_type',
                'route__route_code', 'route__route_id', 'route__route_name', 'expected_due_date',
                'order_value', 'ccr__ccr_id', 'ccr__ccr_code', 'ccr__ccr_name', 'ccr__capacity_per_day',
                'computed_dd','order_attributes','line_order_attributes','vf_order_type','due_date'
            ).annotate(
                    in_batchwise_allocation=Exists(
                        BatchwiseComponentAllocation.objects.filter(
                            order_id=OuterRef('order_id'),
                            line_item=OuterRef('line_id')
                        )
                    )
                ).order_by('-in_batchwise_allocation', 'expected_due_date', 'order_id').distinct()
            logger.info('Fetched the orders for scheduling')
            
            orders_for_scheduling = DataPermissionFilterForOrderData(orders_for_scheduling,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            orders_for_scheduling = filter_order_data_by_params(orders_for_scheduling, filter_data)
            order_keys = [order['order_key'] for order in orders_for_scheduling]
            buffer_data = OrderBufferMapping.objects.filter(order__in=order_keys).values(
                'order', 'buffer', 'buffer__buffer_size', 'buffer__buffer_type__buffer_type', 'buffer__buffer_code')
            logger.info('Fetched buffer data for the orders')
            
            if filter_data:
                buffer_data ,buffer_data_applied= filter_buffer_data_by_params(buffer_data,filter_data)
                filter_applied = filter_applied or buffer_data_applied
            
            buffer_code_order_mapping = {(order['order'], (order['buffer__buffer_type__buffer_type']).lower()): order['buffer__buffer_code'] for order in buffer_data}
            
            order_buffer_map = {}
            order_buffer_size_map = {}
            for data in buffer_data:
                if data['order'] not in order_buffer_map:
                    order_buffer_map[data['order']] = {}
                buffer_type = data['buffer__buffer_type__buffer_type'].lower()
                order_buffer_map[data['order']][buffer_type] = data['buffer']
                if data['order'] not in order_buffer_size_map:
                    order_buffer_size_map[data['order']] = {}
                buffer_type = data['buffer__buffer_type__buffer_type'].lower()
                order_buffer_size_map[data['order']][buffer_type] = data['buffer__buffer_size']

            item_attribute_map = {}
            customer_attribute_map = {}
            for order in orders_for_scheduling:
                if order['item__item_code'] not in item_attribute_map:
                    item_attribute_map[order['item__item_code']] = order['item__attributes']
                if order['customer__cust_code'] not in customer_attribute_map:
                    item_attribute_map[order['customer__cust_code']] = order['customer__attribute']

            logger.info('Fetched the Item and Customer attributes for the order to be scheduled')
            
            if filter_applied:
                orders_for_scheduling = orders_for_scheduling.filter(order_key__in = [data['order_key'] for data in buffer_data])

            data = []
            for order in orders_for_scheduling:
                buffer_info = order_buffer_map.get(order['order_key'], {})
                buffer_prod_code = buffer_code_order_mapping.get((order['order_key'], 'prod'), None)
                buffer_proc_code = buffer_code_order_mapping.get((order['order_key'], 'proc'), None)
                buffer_size_info = order_buffer_size_map.get(order['order_key'], {})
                combined_data = {
                    'oid': order['order_id'],
                    'ok': order['order_key'],
                    'lid': order['line_id'],
                    'did' : order['dept__dept_id'],
                    'dd' : order['due_date'],
                    'ides' : order['item__item_description'],
                    'itemt': order['item__item_type__item_type'],
                    'itid' : order['item__item_type__item_type_id'],
                    'mbot': order['market_based_order_type'],
                    'cedd': order['expected_due_date'],
                    'cdd': order['computed_dd'],
                    'in': order['item__item_code'],
                    'oq': order['total_qty'],
                    'pqty' : order['pending_qty'],
                    'pcqty' : order['pending_ccr_qty'],
                    'dn': order['dept__dept_name'],
                    'pn': order['plant__plant_name'],
                    'cn': order['customer__cust_name'],
                    'prid': buffer_info.get('prod', None),
                    'pcid': buffer_info.get('proc', None),
                    'prSz': buffer_size_info.get('prod', None),
                    'pcSz': buffer_size_info.get('proc', None),
                    'prodc': buffer_prod_code,
                    'procc': buffer_proc_code,
                    'rid': order['route__route_id'],
                    'rn': order['route__route_name'],
                    'plid': order['plant__plant_id'],
                    'ot' : order['vf_order_type'],
                    'childs': []
                }
                line_attributes = order['line_order_attributes']
                if line_attributes:
                    combined_data.update(line_attributes)
                order_attributes = order['order_attributes']
                if order_attributes:
                    combined_data.update(order_attributes)
                data.append(combined_data)
            logger.info('Response data created')
            # if filter_data is not None :
            #     data = filter_attribute_data_by_params(data, filter_data)
            if export_param:
                order_ids = []
                line_ids = []
                if isBomExplosion:
                    for item in data:
                        order_id = item.get('oid')
                        line_id = item.get('lid')
                        order_ids.append(order_id)
                        line_ids.append(line_id)
                        # if not order_id or not line_id:
                    bom_explosion_view = BomLevelExplosionForExcelExportView()
                    bom_query_dict  = request
                    bom_query_dict.data['oids'] = order_ids
                    bom_query_dict.data['lids'] = line_ids
                    bom_reponse = bom_explosion_view.post(request=bom_query_dict)
                    if bom_reponse.status_code == status.HTTP_200_OK:
                        bom_explosion_data = bom_reponse.data.get('data',{})
                    else:
                        bom_explosion_data = {}
                    if bom_explosion_data :
                        for item in data:
                            rm_key = (item.get('oid'),item.get('lid'))
                            item['bomexplosion'] = bom_explosion_data.get(rm_key,[])
                return CustomExcelExport(
                    data,
                    report_name,
                    headers,
                    isGrouped=True,
                    isChildren=isBomExplosion,
                    child_element=eChildName.bomexplosion.value,
                    name_of_report_parent=eReportName.DDQ.value,
                    name_of_report_child=eReportName.bom_explosion.value
                )
            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(data, request)

            return paginator.get_paginated_response(paginated_response_data, msg="Order data for DDQ fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.error(f"Exception occurred while getting orders for scheduling: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)


class DDQBufferAndRouteAssignment(APIView):#DDQ buffer route CCR Load and Estimated DD updation in DB
    @swagger_auto_schema(
        operation_description='Assignment of buffer , route  and Estimated DD',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'bufferData' : openapi.Schema(
                    type=openapi.TYPE_OBJECT
                ),
                'routeData' : openapi.Schema(
                    type=openapi.TYPE_OBJECT
                )
            },
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def put(self,request):
        try:
            buffer_data = request.data.get('bufferData')
            route_data = request.data.get('routeData')
            if not buffer_data and not route_data:
                return api_response(msg='Both route and buffer data cannot be empty',status_code=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                assign_buffer_view = AssignBufferAndEstimatedDueDateView()
                buffer_request = request
                buffer_request.data['ordData'] = buffer_data['ordData']
                buffer_response = assign_buffer_view.put(request = buffer_request)
                if buffer_response.status_code != status.HTTP_200_OK:
                        raise Exception("Buffer assignment failed")

                assign_route_view = AssignRouteView()
                route_request = request
                route_request.data['routeData'] = route_data
                route_response = assign_route_view.put(request=route_request)
                if route_response.status_code != status.HTTP_200_OK:
                    raise Exception("Route assignment failed")


            return api_response(msg='Buffer and route assigned successfully', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Exception has occurred in the DDQBRCEAssignment due to {str(e)}')
            return api_response(msg=f'Exception has occurred in the DDQBRCEAssignment view due to {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssignBufferAndEstimatedDueDateView(APIView):
    @swagger_auto_schema(
    operation_description="DDQ - Assign buffer and Estimated Due Date to orders",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'ordData': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'ok': openapi.Schema(type=openapi.TYPE_STRING, description='Order Key'),
                        'prod_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='production buffer id'),
                        'proc_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='procurement buffer id'),
                        'ccr' : openapi.Schema(type=openapi.TYPE_INTEGER,description='max fol ccr'),
                        'estdd' : openapi.Schema(type=openapi.TYPE_STRING,description='estimated due date',format='date')
                    },
                    required=['ok']
                        )
                    )
                },
                required=['ordData']
            )
        )
    def put(self, request):
        try:
            order_data = request.data.get('ordData')
            if not order_data:
                return api_response(msg= 'The order data for buffer assignment must not be empty', status_code=status.HTTP_400_BAD_REQUEST)

            order_keys = [data['ok'] for data in order_data]
            ccrs = [data['ccr'] for data in order_data]
            orders = OrderData.objects.filter(order_key__in=order_keys)
            logger.info('orders from OrderData table fetched for buffer assignment')
            orders_dict = {order.order_key: order for order in orders}
            logger.info('order key and order data dictionary formed')

            ccr_instances = CCRMaster.objects.filter(ccr_id__in = ccrs)
            ccr_instance_map = {ccr.ccr_id : ccr for ccr in ccr_instances}
            buffer_order_mapping = OrderBufferMapping.objects.filter(order__in=orders).select_related('buffer')
            logger.info('Order buffer mapping data fetched')
            buffer_order_mapping_dict = {(mapping.order.order_key, mapping.buffer.buffer_type.buffer_type_id): mapping for mapping in buffer_order_mapping}

            buffer_ids = set()
            for data in order_data:
                if 'prod_id' in data:
                    buffer_ids.add(data['prod_id'])
                if 'proc_id' in data:
                    buffer_ids.add(data['proc_id'])


            buffer_buffer_type = BufferMaster.objects.filter(buffer_id__in=buffer_ids).select_related('buffer_type')
            logger.info('Fetched buffer type data from buffer master')
            buffers_dict = {buffer.buffer_id: buffer for buffer in buffer_buffer_type}

            order_buffer_mapping_to_update = []
            order_buffer_mapping_to_create = []
            order_data_to_be_updated =[]
            for data in order_data:
                order_key = data['ok']
                prod_id = data.get('prod_id')
                proc_id = data.get('proc_id')

                order = orders_dict.get(order_key)
                if not order:
                    logger.error(f'Order with key {order_key} does not exist.')
                    continue

                estimated_dd = data['estdd']
                ccr = data['ccr']
                if estimated_dd:
                    order_instance = orders_dict.get(order_key,{})
                    ccr_instance = ccr_instance_map.get(ccr,None) if ccr else None
                    if order_instance:
                        order_instance.computed_dd = estimated_dd
                        order_instance.ccr = ccr_instance
                        order_data_to_be_updated.append(order_instance)

                if prod_id:
                    buffer = buffers_dict.get(prod_id)
                    if buffer and  ('prod' in buffer.buffer_type.buffer_type.lower()):
                        mapping_key = (order_key, buffer.buffer_type.buffer_type_id)
                        if mapping_key in buffer_order_mapping_dict:
                            buffer_order_mapping_dict[mapping_key].buffer = buffer
                            order_buffer_mapping_to_update.append(buffer_order_mapping_dict[mapping_key])
                        else:
                            order_buffer_mapping_to_create.append(OrderBufferMapping(order=order, buffer=buffer))

                if proc_id:
                    buffer = buffers_dict.get(proc_id)
                    if buffer and ('proc' in buffer.buffer_type.buffer_type.lower()) :
                        mapping_key = (order_key, buffer.buffer_type.buffer_type_id)
                        if mapping_key in buffer_order_mapping_dict:
                            buffer_order_mapping_dict[mapping_key].buffer = buffer
                            order_buffer_mapping_to_update.append(buffer_order_mapping_dict[mapping_key])
                        else:
                            order_buffer_mapping_to_create.append(OrderBufferMapping(order=order, buffer=buffer))
                
            
            logger.info('Data arranged for updation and creation')
            with transaction.atomic():
                if order_buffer_mapping_to_update:
                    OrderBufferMapping.objects.bulk_update(order_buffer_mapping_to_update, ['buffer'])
                if order_buffer_mapping_to_create:
                    OrderBufferMapping.objects.bulk_create(order_buffer_mapping_to_create)
                if order_data_to_be_updated:
                    OrderData.objects.bulk_update(order_data_to_be_updated,["computed_dd","ccr"])

            return api_response(msg='Buffer for selected orders updated successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Exception has occurred due to {str(e)}')
            return api_response(msg=f'The exception has occurred in the assign buffer view due to {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssignDueDateView(APIView):
    # is in progress
    @swagger_auto_schema(
    operation_description='DDQ - Assign Due date to the orders',
        request_body = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'orderData': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'ok': openapi.Schema(type=openapi.TYPE_STRING, description='order key to update due date'),
                            'dd': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='due date to be assigned'),
                            'rd': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='release date for order'),
                            'pobsz': openapi.Schema(type=openapi.TYPE_INTEGER, description='post order buffer size for order')
                        },
                        required=['ok', 'dd', 'rd']
                    )
                )
            }
        )

    )

    def put(self,request):
        try:
            order_data = request.data.get('orderData')
            if not order_data:
                return api_response('The orders and due date cannot be empty',status_code=status.HTTP_400_BAD_REQUEST)

            order_keys = []

            for order in order_data:
                order_keys.append(order['ok'])
            
            order_instances = OrderData.objects.filter(order_key__in = order_keys)
            order_buffer_data_instances = OrderBufferMapping.objects.filter(order__in = order_keys)
            order_buffer_map_data = {}
            for data in order_buffer_data_instances:
                if data.order not in order_buffer_map_data:
                    order_buffer_map_data[data.order] = []
                order_buffer_map_data[data.order].append(data)
            logger.info('Orders has been fetched for which due date has to be assigned')
            # Todays date for updating the scheduled on column
            todays_date = date.today()

            order_info_dict = {order['ok'] : order for order in order_data}
            orders_to_be_updated = []
            
            auto_release = DBRSettings.objects.get(flag = 'AutoRelease')

            order_buffer_map_to_be_updated = []
            for order in order_instances:
                order_key = order.order_key
                order_info = order_info_dict.get(order_key)
                post_order_buffer_size = order_info['pobsz'] if order_info['pobsz'] else None
                due_date = datetime.strptime(order_info['dd'], '%Y-%m-%d').date()
                release_date = order_info['rd']
                order_buffer_data_list = order_buffer_map_data.get(order,None)
                if order_buffer_data_list:
                    for order_buffer_data in order_buffer_data_list:
                        if 'prod' in order_buffer_data.buffer.buffer_type.buffer_type.lower():
                            order_buffer_data.buffer_date = release_date
                            order_buffer_map_to_be_updated.append(order_buffer_data)
                        if 'proc' in order_buffer_data.buffer.buffer_type.buffer_type.lower():
                            proc_buff_size = order_buffer_data.buffer.buffer_size
                            prod_buffer_size = order_buffer_data_instances.filter(order = order_key,buffer__buffer_type__buffer_type__icontains = 'prod',buffer__buffer_size__isnull = False).values('buffer__buffer_size')[0]
                            if prod_buffer_size:
                                proc_rope_date = due_date - timedelta(days = prod_buffer_size.get('buffer__buffer_size',0) - proc_buff_size)
                                order_buffer_data.buffer_date = proc_rope_date
                                order_buffer_map_to_be_updated.append(order_buffer_data)
                
                order.planned_release_date = release_date
                order.post_order_buffer_size = post_order_buffer_size
                formatted_release_date = (datetime.strptime(release_date, '%Y-%m-%d').date())
                calculated_pre_order_buffer_size = (formatted_release_date - todays_date).days
                order.pre_order_buffer_size = max(calculated_pre_order_buffer_size, 0)
                order.due_date = due_date
                order.scheduled_on = todays_date
                
                # Changes requested by Soumya as it is observed in Mallcom Shoes , future actual release date was captured
                if (int(auto_release.value) == 1 or auto_release.value == 'True') and (formatted_release_date == todays_date):
                    order.actual_released_date = date.today() 
                    order.is_rm_released = True 
                else:
                    order.actual_released_date = None
                    order.is_rm_released = False

                orders_to_be_updated.append(order)

            #Fields to be updated
            data_to_be_updated = {
                'post_order_buffer_size',
                'scheduled_on',
                'due_date',
                'is_rm_released',
                'actual_released_date',
                'planned_release_date',
                'pre_order_buffer_size',
                
            }

            logger.info('Data processed for due date updation')
            with transaction.atomic():
                if orders_to_be_updated:
                    OrderData.objects.bulk_update(orders_to_be_updated,data_to_be_updated)
                if order_buffer_map_to_be_updated:
                    OrderBufferMapping.objects.bulk_update(order_buffer_map_to_be_updated,["buffer_date"])
            return api_response(msg=f'The due date has been updated successfully',status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f'An Exception has occurred in the assign due date view due to {str(e)}')
            return api_response(msg=f'An Exception has occurred in the assign due date view due to {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ccr for buffer penetration of order will be given by UI 

class ScheduleOrdersView(APIView):#DDQ assign due date , bpp and FOL and STPL
    @swagger_auto_schema(
        operation_description='Assignment of due date,bpp and fol and STPL',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'orders' : openapi.Schema(
                    type=openapi.TYPE_OBJECT
                ),                
            },
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def put(self,request):
        try:
            orders = request.data.get('orders')
            if not orders:
                return api_response(msg='The orders cannot be empty',status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            order_keys = []
            for data in orders:
                order_keys.append(data['ok'])
            with transaction.atomic():
                due_date_view = AssignDueDateView()
                due_date_request = request
                due_date_request.data['orderData'] = orders
                due_date_response = due_date_view.put(request = due_date_request)
                if due_date_response.status_code != status.HTTP_200_OK:
                        raise Exception("Due date assignment failed")

                bpp_view = CalculateAndUpdateBufferPenetration()
                bpp_request = request
                bpp_request.data['orderData'] = order_keys
                bpp_response = bpp_view.put(request=bpp_request)
                if bpp_response.status_code != status.HTTP_200_OK:
                    raise Exception("Buffer penetration Calculation failed")

                bm_report_view = CreateOverallBMReportView()
                bm_report_request = request
                bm_report_request.data['ok'] = order_keys
                bm_report_response = bm_report_view.post(request=bm_report_request)
                if bm_report_response.status_code != status.HTTP_200_OK:
                    raise Exception("BM report Data saving failed")                    
                
                fol_api_view = UpdateFOLandSTPL()
                fol_request = request
                fol_request.data['order_keys'] = order_keys
                fol_response = fol_api_view.put(request=fol_request)
                if fol_response.status_code != status.HTTP_200_OK:
                    raise Exception("FOl update data failed")

                update_order_wip_data_view = UpdateOrderWIPDataView()
                update_order_wip_data_request = request
                update_order_wip_data_request.data['order_keys'] = order_keys
                update_order_wip_data_response = update_order_wip_data_view.put(request=update_order_wip_data_request)
                if update_order_wip_data_response.status_code != status.HTTP_200_OK:
                    raise Exception("Order WIP Data updation failed")   

            return api_response(msg='Bpp,due date,BM report and fol and stpl assigned successfully', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Exception has occurred in scheduling orders due to{str(e)}')
            return api_response(msg=f'Exception has occurred in the scheduling orders view due to {str(e)}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)




