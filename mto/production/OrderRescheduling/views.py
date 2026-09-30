from mto_app.models import ( FOL_Data,  OrderData, OrderBufferMapping ,DDQChangesLog,  LineCCRDetails,
DailyWorkingCalendar,DBRSettings,OverallBMReport)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import (ExcelExportData, api_response, CustomPagination, filter_order_data_by_params)
from django.db.models import Max
from datetime import datetime , date , timedelta
from django.db import transaction
from mto_app.utils import  eReportName
from ..Common.views import CreateOverallBMReportView , UpdateOrderWIPDataView , UpdateFOLandSTPL , CalculateAndUpdateBufferPenetration 
import pandas as pd

logger = logging.getLogger(__name__)

class UpdateOrderDueDateView(APIView):
    @swagger_auto_schema(
        operation_description="Order Rescheduling - Overwrite Due Date or Unschedule Orders",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                    'isUnSch': openapi.Schema(type=openapi.TYPE_INTEGER, description='Operation Type - whether Unschedule or not'),
                    'ordData':  openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'ok': openapi.Schema(type=openapi.TYPE_STRING, description='Order Key'),
                                'dd': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE, description='Due Date'),
                                'r': openapi.Schema(type=openapi.TYPE_STRING, description='Reason')
                            },
                            required=['ok', 'r']
                        )
                    )
                },
                required=['unm', 'isUnSch', 'ordData']
            )
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def put(self, request):
        try:
            logger.info("Order Rescheduling Processing started")

            for data in request.data.get('data'):
                user_name = data.get('unm')
                isUnScheduled = data.get('isUnSch')
                orders_to_be_rescheduled = data.get('ordData', [])
            logger.info('Read parameters for API')

            if not isinstance(orders_to_be_rescheduled, list):
                return api_response({"error": "Expected a list of JSON objects"}, status=status.HTTP_400_BAD_REQUEST)
            
            order_key_list = [order['ok'] for order in orders_to_be_rescheduled]

            order_data_instances = OrderData.objects.filter(order_key__in=order_key_list)
            logger.info('Order key list formed and fetched corresponding orderData instances')

            # Fetch buffer details for orders
            order_buffer_data_instances = OrderBufferMapping.objects.filter(order__in = order_key_list)
            logger.info('Fetched buffer details for orders')

            #get AutoRelease falg value to set IsRMReleased value
            auto_release = DBRSettings.objects.filter(flag = 'AutoRelease').values('value')
            logger.info('AutoRelease flag value fetched')
            orders_to_update = []
            orders_log_instances = []
            order_buffer_date_to_update = []
            failed_orders = {}
            if isUnScheduled: #Unschedule Orders
                logger.info('Unscheduling Orders started')               

                # collect order data for updating buffer dates                
                for order in order_buffer_data_instances:
                    order.buffer_date = None
                    order_buffer_date_to_update.append(order)
                logger.info('collected order buffer date data to be updated')
 
                #create orderKey and reason dict
                order_reason_dict = {order['ok']:order['r'] for order in orders_to_be_rescheduled}
                logger.info('Order key and reason dictionary created')               

                #loop thorugh order_data_instances
                for order in order_data_instances:
                    #get DDQ change log data first as later due date is assigned to none and change log requires org DD
                    key = order.order_key
                    order_log_instance = DDQChangesLog(order=order,org_due_date=order.due_date,is_unscheduled=True,is_due_date_changed=False,user_name=user_name, updated_on = datetime.now(),reason = order_reason_dict.get(key))
                    orders_log_instances.append(order_log_instance)
 
                    # re-initialize orderdata fields
                    order.due_date = None
                    order.actual_released_date = None
                    order.planned_release_date = None
                    order.color = None
                    order.bpp = None
                    order.pre_order_buffer_size = None
                    order.post_order_buffer_size = None
                    order.is_rm_released = False
                    order.is_line_finished =  False
                    order.computed_dd = None
                    order.scheduled_on = None
                    order.major_reason = None
                    order.minor_reason = None
                    order.order_stage =  None
                    order.delay_days = None


                    orders_to_update.append(order)
                logger.info('collected order data to be updated')


                fields_to_update = {
                                        'due_date',
                                        'planned_release_date',
                                        'actual_released_date',
                                        'color',
                                        'bpp',
                                        'pre_order_buffer_size',
                                        'post_order_buffer_size',
                                        'is_rm_released',
                                        'is_line_finished',
                                        'computed_dd',
                                        'scheduled_on',
                                        'major_reason',
                                        'minor_reason',
                                        'order_stage',
                                        'delay_days'
                                    }
                logger.info('created list of fields to be updated in orderData table')
 
                with transaction.atomic():
                    OrderData.objects.bulk_update(orders_to_update, fields_to_update)
                    OrderBufferMapping.objects.bulk_update(order_buffer_date_to_update,['buffer_date'])
                    OverallBMReport.objects.filter(order_key__in=order_key_list).delete()
                    DDQChangesLog.objects.bulk_create(orders_log_instances)

                    update_order_wip_data_view = UpdateOrderWIPDataView()
                    update_order_wip_data_request_data = {'order_keys': order_key_list}
                    update_order_wip_data_request = request._request  
                    update_order_wip_data_request.POST = update_order_wip_data_request.POST.copy()
                    update_order_wip_data_request.POST.update(update_order_wip_data_request_data)
                    update_order_wip_data_request.GET = update_order_wip_data_request.GET.copy()
                    update_order_wip_data_request.GET['unscheduled'] = 1
                    update_order_wip_data_response = update_order_wip_data_view.put(request=update_order_wip_data_request)
                    if update_order_wip_data_response.status_code != status.HTTP_200_OK:
                        raise Exception("Order WIP Data updation failed")
                    
                    fol_api_view = UpdateFOLandSTPL()
                    fol_request = request
                    fol_request.data['order_keys'] = order_key_list
                    fol_response = fol_api_view.put(request=fol_request)
                    if fol_response.status_code != status.HTTP_200_OK:
                        raise Exception("FOl update data failed")
                    
                    logger.info('Unschedule data updated in Order Data table and log data inserted')
 
            else: #Overwrite DD
                logger.info('Overwrite order Due Date started')
                order_requestData_dict = {order['ok']:{ 'dd':order['dd'], 'r':order['r']} for order in orders_to_be_rescheduled} 
                logger.info('order_requestData_dict formed')
                for order in order_data_instances:
                    key = order.order_key
                    requestData =  order_requestData_dict.get(key)
                    #get DDQ chnage log data first as later due date is assigned to new dd and change log requires org DD
                    order_log_instance = DDQChangesLog(order=order,org_due_date=order.due_date,is_unscheduled=False,is_due_date_changed=True,user_name=user_name, updated_on = datetime.now(), reason = requestData['r'])
                    orders_log_instances.append(order_log_instance)
                    logger.info('DDQ log change data collected')

                    ccr_id_list = LineCCRDetails.objects.filter(order = order.order_key).values('ccr_id')
                    logger.info('Fetched CCR ids for order from LineCCR Details table')
                    order_ccr_fol_data = FOL_Data.objects.filter(ccr_id__in = ccr_id_list).values('ccr_id','fol_in_days')
                    logger.info('Fetched Fetched FOL Data for CCRs of order')
                    max_fol_in_days = order_ccr_fol_data.aggregate(Max('fol_in_days'))['fol_in_days__max']
                    logger.info('Max FOL calculated')
                    ccr_with_max_fol = order_ccr_fol_data.filter(fol_in_days=max_fol_in_days).first()
                    logger.info('Get CCR with max FOL')
                    #get DD index considering daily working calendar of Max FOL CCR
                    daily_working_calendar = DailyWorkingCalendar.objects.filter(ccr_id = ccr_with_max_fol['ccr_id'], working_date__lte = requestData['dd']).values('working_date'
                                            ,'ccr_id','lno')
                    logger.info('fetched daily working calendar for Max-FOL CCR for working dates less than or equal to requsted DD')
                    # if DD index not avilable get Index of earlier working date
                    daily_working_calender_instance = daily_working_calendar.filter(working_date = requestData['dd']).first()
                    if daily_working_calender_instance is None:
                        failed_orders[order.order_id] = f"Requested Due Date {requestData['dd']} is holiday for CCR {ccr_with_max_fol['ccr_id']}"
                        continue

                    dd_index = daily_working_calender_instance.get('lno',None) 
                    order_buffer_data = order_buffer_data_instances.filter(order = order.order_key).prefetch_related('buffer').prefetch_related('buffer__buffer_type').values('order_id'
                    ,'buffer_id','buffer__buffer_size','buffer__buffer_type__buffer_type')
                    logger.info('Get Oder buffer data from OrderBufferMapping into order_buffer_data')
                    prod_buff_size = 0
                    proc_buff_size = 0
                    for order_buffer in order_buffer_data:
                        typeName = order_buffer['buffer__buffer_type__buffer_type'].lower()
                        if 'prod' in typeName:
                            prod_buff_size = order_buffer['buffer__buffer_size']
                            prod_buff_date_data = daily_working_calendar.filter(lno = (dd_index - prod_buff_size +1)).first()
                            order_buff_map_instance = order_buffer_data_instances.filter(order = order.order_key, buffer_id = order_buffer['buffer_id']).first()
                            logger.info('Get OrderBufferMapping instance for ',prod_buff_date_data)
                            order_buff_map_instance.buffer_date = prod_buff_date_data.get('working_date',None)
                            order_buffer_date_to_update.append(order_buff_map_instance)
                        elif 'proc' in typeName:
                            proc_buff_size = order_buffer['buffer__buffer_size']
                            if prod_buff_size == 0:
                                prod_buff_data = order_buffer_data.filter(order_id = order.order_key, buffer__buffer_type__buffer_type__icontains = 'prod').first()
                                prod_buff_size = prod_buff_data.get('buffer__buffer_size',0)
                            proc_buff_date_data = daily_working_calendar.filter(lno = (dd_index - (proc_buff_size + prod_buff_size) + 1)).first()
                            order_buff_map_instance = order_buffer_data_instances.filter(order = order.order_key, buffer_id = order_buffer['buffer_id']).first()
                            logger.info('Get OrderBufferMapping instance for ',proc_buff_date_data)
                            order_buff_map_instance.buffer_date = proc_buff_date_data.get('working_date',None)
                            order_buffer_date_to_update.append(order_buff_map_instance)
                    logger.info('Collected Order buffer data to be upadted')

                    #re-assign feilds in Order Data and push order to array
                    order.planned_release_date = prod_buff_date_data.get('working_date',None)
                    order.pre_order_buffer_size = 0
                    order.post_order_buffer_size = 0
                    order.delay_days = 0
                    order.due_date = requestData['dd']
                    order.is_line_finished = False
                    order.delay_days = 0
                    if auto_release and prod_buff_date_data['working_date']==date.today():
                        order.is_rm_released = True
                        order.actual_released_date = prod_buff_date_data['working_date']
                    
                    orders_to_update.append(order)

                fields_to_update_order_data = {
                                        'due_date',
                                        'planned_release_date',
                                        'actual_released_date',
                                        'pre_order_buffer_size',
                                        'post_order_buffer_size',
                                        'delay_days',
                                        'is_rm_released',                                        
                                        'is_line_finished',
                                        'delay_days'
                                    }

                with transaction.atomic():
                    OrderData.objects.bulk_update(orders_to_update, fields_to_update_order_data)
                    OrderBufferMapping.objects.bulk_update(order_buffer_date_to_update,['buffer_date'])
                    DDQChangesLog.objects.bulk_create(orders_log_instances)

                    bpp_request_data = {'orderData': order_key_list}
                    bpp_view = CalculateAndUpdateBufferPenetration()
                    bpp_request = request._request  # Get the original Django request object
                    bpp_request.POST = bpp_request.POST.copy()  # Make the POST data mutable
                    bpp_request.POST.update(bpp_request_data)  # Update the POST data with the new data
                    bpp_response = bpp_view.put(request=bpp_request)
                    if bpp_response.status_code != status.HTTP_200_OK:
                        raise Exception("Buffer penetration Calculation failed")

                    OverallBMReport.objects.filter(order_key__in=order_key_list).delete()
                    bm_report_request_data = {'ok': order_key_list}
                    bm_report_view = CreateOverallBMReportView()
                    bm_report_request = request._request  # Get the original Django request object
                    bm_report_request.POST = bm_report_request.POST.copy()  # Make the POST data mutable
                    bm_report_request.POST.update(bm_report_request_data)  # Update the POST data with the new data
                    bm_response = bm_report_view.post(request=bm_report_request)
                    if bm_response.status_code != status.HTTP_200_OK:
                        raise Exception("Create Overall BM Report Failed")
                    
                    fol_api_view = UpdateFOLandSTPL()
                    fol_request = request
                    fol_request.data['order_keys'] = order_key_list
                    fol_response = fol_api_view.put(request=fol_request)
                    if fol_response.status_code != status.HTTP_200_OK:
                        raise Exception("FOl update data failed")

            logger.info('Order Rescheduling data updated successfully')
            return api_response(data = {"failed_orders" : failed_orders},msg='Order Rescheduling data updated successfully', status_code=status.HTTP_200_OK)

        except Exception as ex:
            transaction.rollback()
            logger.error(f"Exception occurred in Updating Order Due Dates: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class GetOrderReschedulingDataView(APIView):
    pagination_class = CustomPagination

    @swagger_auto_schema(
        operation_description="Get data for Order Rescheduling screen",
        manual_parameters=[
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self,request):
        return self.getOrderReschedulingData(request)
    
    def put(self,request):
        return self.getOrderReschedulingData(request,method = 'PUT')

    def getOrderReschedulingData(self, request, method = 'GET'):
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

            filter_data = request.data

            # Fetch all schedules orders
            scheduledOrders = OrderData.objects.filter(due_date__isnull = False , is_rm_released = False).values(
                'order_id', 'line_id', 'order_key', 'item__attributes', 'item__item_code',
                'item__item_description', 'item__item_type__item_type','item__item_type__item_type_id', 'total_qty',
                'pending_qty', 'pending_ccr_qty', 'plant__plant_id', 'plant__plant_name',
                'dept__dept_id', 'dept__dept_name', 'customer__cust_code',
                'customer__attribute', 'customer__cust_name', 'market_based_order_type',
                'route__route_code', 'route__route_id', 'route__route_name', 'expected_due_date',
                'order_value', 'ccr__ccr_id', 'ccr__ccr_code', 'ccr__ccr_name', 'ccr__capacity_per_day',
                'computed_dd','order_attributes','line_order_attributes','vf_order_type','due_date').order_by('order_key')
            logger.info('All scheduled orders fetched')

            scheduledOrders = filter_order_data_by_params(scheduledOrders, filter_data)
            #prepare order key list
            order_key_list = [order['order_key'] for order in scheduledOrders]
            # Fetch buffer details for scheduled orders
            order_buffer_data = OrderBufferMapping.objects.filter(order__in = order_key_list).prefetch_related('buffer').prefetch_related('buffer__buffer_type').values('order_id','buffer__buffer_size','buffer__buffer_type__buffer_type')
            logger.info('Fetched buffer details for scheduled orders')
            #create orderid bufferData map
            order_id_buffer_map = {}
            if order_buffer_data is not None: #in reality orders cannot be scheduled without Prod buff assigned. this is handled just to void error in api
                for data in order_buffer_data:
                    if data['order_id'] not in order_id_buffer_map:
                        order_id_buffer_map[data['order_id']] = {}
                    typeName = data['buffer__buffer_type__buffer_type'].lower()
                    if 'prod' in typeName:
                        order_id_buffer_map[data['order_id']]['PdSz'] = data['buffer__buffer_size']
                    elif 'proc' in typeName:
                        order_id_buffer_map[data['order_id']]['PcSz'] = data['buffer__buffer_size']
                logger.info('Order id and buffer mapping created')

            #prepare response data
            response_data=[]
            for order in scheduledOrders:
                combined_data = {
                    'oid': order['order_id'],
                    'lid': order['line_id'],
                    'dd' : order['due_date'],
                    'rnm': order['route__route_name'],
                    'odk': order['order_key']
                }

                if order_id_buffer_map and order:
                    buffer_map_value = order_id_buffer_map.get(order['order_key']) 
                    if buffer_map_value is not None:
                        combined_data.update(buffer_map_value)

                response_data.append(combined_data)

            if export_param:
                if report_name and headers:
                    return ExcelExportData(response_data,report_name, eReportName.OrderRescheduling.value, headers)
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(response_data, request)

            logger.info("Returning the paginated response for Get Order Rescheduling view")
            return paginator.get_paginated_response(paginated_response_data, msg="Order Rescheduling data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in Get Order Rescheduling Data Response : {str(ex)}")
            return api_response(error=f"Object does not exist GetOrderReschedulingDataView : {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)


class GetHolidaysForMaxFolCCROfOrder(APIView):
    @swagger_auto_schema(
        operation_description="Get holidays for Max FOL CCR of an order",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'ok': openapi.Schema(type=openapi.TYPE_STRING, description='Order Key')
            },
            required=['ok']
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def post(self , request):
        try:
            order_key = request.data.get('ok')
            line_ccr_details = LineCCRDetails.objects.filter(order = order_key).values_list('ccr_id')
            logger.info('Fetched CCR ids for order from LineCCR Details table')
            if not line_ccr_details:
                return api_response(error=f"No CCR details found for order {order_key}", status_code=status.HTTP_404_NOT_FOUND)
            order_ccr_fol_data = FOL_Data.objects.filter(ccr_id__in = line_ccr_details).values('ccr_id','fol_in_days')
            logger.info('Fetched FOL Data for CCRs of order')
            max_fol_in_days = order_ccr_fol_data.aggregate(Max('fol_in_days'))['fol_in_days__max']
            logger.info('Max FOL calculated')
            ccr_with_max_fol = order_ccr_fol_data.filter(fol_in_days=max_fol_in_days).first()
            logger.info('Get CCR with max FOL')
            if not ccr_with_max_fol:
                return api_response(error=f"No FOL data found for CCRs of order {order_key}", status_code=status.HTTP_404_NOT_FOUND)
            daily_working_calendar = DailyWorkingCalendar.objects.filter(ccr_id = ccr_with_max_fol['ccr_id'] , working_date__gte = date.today()).values('working_date'
                                        ,'ccr_id','lno')
            from_date = date.today()
            to_date = from_date + timedelta(days=365)
            date_range = pd.date_range(start=from_date, end=to_date, freq="D")
            date_df = pd.DataFrame({'date': date_range})
            working_calendar_df = pd.DataFrame(list(daily_working_calendar))
            working_calendar_df['working_date'] = pd.to_datetime(working_calendar_df['working_date'])
            date_df['date'] = pd.to_datetime(date_df['date'])
            merged_df = pd.merge(date_df, working_calendar_df, left_on='date', right_on='working_date', how='left', indicator=True)
            holidays_df = merged_df[merged_df['_merge'] == 'left_only']
            holidays_list = holidays_df['date'].dt.date.tolist()
            logger.info('Holidays for Max FOL CCR calculated')
            return api_response(data = {'holidays': holidays_list}, msg='Holidays for Max FOL CCR fetched successfully', status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.error(f"Exception occurred in Get Holidays For Max Fol CCR Of Order : {str(ex)}")
            return api_response(error=f"Object does not exist GetHolidaysForMaxFolCCROfOrder : {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)