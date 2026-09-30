

import math
from mto_app.models import ( BatchwiseProductionComponentAllocation, CCRMaster,FOL_Data,  OrderData, OrderBufferMapping ,
BatchwiseComponentAllocation,ComputedOrderAttributes,RouteMaster, LineCCRDetails,CCRGroupMaster,RouteDetails,ItemMaster,
DailyWorkingCalendar,ItemDeptMapping,Order_WIPDetails,DBRSettings,DeptMaster,BMReportRemarks,OverallBMReport,CustomerMaster,ComputedLineAttributes,
 OrderwiseFolGap)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import ( api_response)
from django.db.models import  F, Sum,Value, DecimalField
from datetime import date,datetime
from django.db import transaction
from collections import defaultdict
from django.db.models.functions import Coalesce
from decimal import Decimal
import pandas as pd
#Create your views here.

logger = logging.getLogger(__name__)

class CreateOverallBMReportView(APIView):
    @swagger_auto_schema(
        operation_description='Add newly scheduled orders to Over all BM Report',
        request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'ok' : openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_STRING
                        ),
                        description='order keys'
                    )
                }
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def post(self,request):
        try:
            if(request.POST):
                order_keys = request.POST.get('ok')
            else:
                order_keys = request.data.get('ok')

            order_data = OrderData.objects.filter(order_key__in = order_keys)
            order_ids = [data.order_id for data in order_data]
            customer_instance_map = {data.cust_code : data for data in CustomerMaster.objects.all()}
            order_computed_attributes = {data.order_id : data for data in ComputedOrderAttributes.objects.filter(order_id__in = order_ids)}
            line_computed_attributes = {(data.order_id,data.line_id) : data for data in ComputedLineAttributes.objects.filter(order_id__in = order_ids)}
            order_instances = {order.order_key : order for order in order_data}
            bm_reports_to_be_created = []
            for order in order_keys:
                order_data = order_instances.get(order,{})
                if order_data:
                    order_computed_attr = order_computed_attributes.get(order_data.order_id,{})
                    line_computed_attr = line_computed_attributes.get((order_data.order_id,order_data.line_id),{})
                    if order_data.is_rm_released == True and order_data.actual_released_date <= date.today():
                        bm_reports_to_be_created.append(
                            OverallBMReport(
                                order_key = order_data,
                                order_id = order_data.order_id,
                                line_id = order_data.line_id,
                                color = order_data.color,
                                bpp  = order_data.bpp,
                                release_date = order_data.planned_release_date,
                                due_date = order_data.due_date,
                                plant_id = order_data.plant.plant_id,
                                dept_id = order_data.dept.dept_id if order_data.dept else None,
                                dept_code = order_data.dept.dept_code if order_data.dept else None,
                                pending_qty = order_data.pending_qty,
                                pending_ccr_qty = order_data.pending_ccr_qty,
                                allocated_qty = order_data.allocated_fg,
                                major_r_id = order_data.major_reason,
                                minor_r_id = order_data.minor_reason,
                                major_r_desc = order_data.major_reason.major_reason_desc if order_data.major_reason else None,
                                minor_r_desc = order_data.minor_reason.minor_reason_desc if order_data.minor_reason else None,
                                route_name = order_data.route.route_name,
                                ccr_name = order_data.ccr.ccr_name if order_data.ccr else None,
                                item_code = order_data.item.item_code if order_data.item else None,
                                item_desc = order_data.item.item_description if order_data.item else None,
                                item_group = order_data.item.item_type.item_type if order_data.item else None,
                                order_type = order_data.vf_order_type,
                                can_finish_from_ui = order_data.can_finish_from_ui,
                                is_finished = order_data.is_line_finished,
                                delay_days = order_data.delay_days,
                                plant_name = order_data.plant.plant_name if order_data.plant else None,
                                expected_due_date  = order_data.expected_due_date,
                                cust_code = customer_instance_map.get(order_data.customer,None),
                                cust_name = order_data.customer.cust_name if order_data.customer else None,
                                actual_released_date = order_data.actual_released_date,
                                order_entry_date = order_data.order_entry_date,
                                order_value = order_data.order_value,
                                dept_ageing = 0,
                                trailing_dept = None,
                                elapsed_days = 0,
                                need_confirmation = False,
                                order_attributes = order_data.order_attributes if order_data.order_attributes else None,
                                line_order_attributes = order_data.line_order_attributes if order_data.line_order_attributes else None,
                                item_attributes = order_data.item.attributes if order_data.item.attributes else None,
                                customer_attributes = order_data.customer.attribute if order_data.customer else None,
                                oc01 = getattr(order_computed_attr, 'c01', None),
                                oc02 = getattr(order_computed_attr, 'c02', None),
                                oc03 = getattr(order_computed_attr, 'c03', None),
                                oc04 = getattr(order_computed_attr, 'c04', None),
                                oc05 = getattr(order_computed_attr, 'c05', None),
                                oc06 = getattr(order_computed_attr, 'c06', None),
                                oc07 = getattr(order_computed_attr, 'c07', None),
                                oc08 = getattr(order_computed_attr, 'c08', None),
                                oc09 = getattr(order_computed_attr, 'c09', None),
                                oc10 = getattr(order_computed_attr, 'c10', None),
                                oc11 = getattr(order_computed_attr, 'c11', None),
                                oc12 = getattr(order_computed_attr, 'c12', None),
                                oc13 = getattr(order_computed_attr, 'c13', None),
                                oc14 = getattr(order_computed_attr, 'c14', None),
                                oc15 = getattr(order_computed_attr, 'c15', None),
                                oc16 = getattr(order_computed_attr, 'c16', None),
                                oc17 = getattr(order_computed_attr, 'c17', None),
                                oc18 = getattr(order_computed_attr, 'c18', None),
                                oc19 = getattr(order_computed_attr, 'c19', None),
                                oc20 = getattr(order_computed_attr, 'c20', None),
                                lc01 = getattr(line_computed_attr, 'c01', None),
                                lc02 = getattr(line_computed_attr, 'c02', None),
                                lc03 = getattr(line_computed_attr, 'c03', None),
                                lc04 = getattr(line_computed_attr, 'c04', None),
                                lc05 = getattr(line_computed_attr, 'c05', None),
                                lc06 = getattr(line_computed_attr, 'c06', None),
                                lc07 = getattr(line_computed_attr, 'c07', None),
                                lc08 = getattr(line_computed_attr, 'c08', None),
                                lc09 = getattr(line_computed_attr, 'c09', None),
                                lc10 = getattr(line_computed_attr, 'c10', None),
                                lc11 = getattr(line_computed_attr, 'c11', None),
                                lc12 = getattr(line_computed_attr, 'c12', None),
                                lc13 = getattr(line_computed_attr, 'c13', None),
                                lc14 = getattr(line_computed_attr, 'c14', None),
                                lc15 = getattr(line_computed_attr, 'c15', None),
                                lc16 = getattr(line_computed_attr, 'c16', None),
                                lc17 = getattr(line_computed_attr, 'c17', None),
                                lc18 = getattr(line_computed_attr, 'c18', None),
                                lc19 = getattr(line_computed_attr, 'c19', None),
                                lc20 = getattr(line_computed_attr, 'c20', None)

                            )
                        )
            with transaction.atomic():
                if bm_reports_to_be_created:
                    OverallBMReport.objects.bulk_create(bm_reports_to_be_created)
            return api_response(msg='BM report has been saved successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            return api_response(f'An Exception has occured in saving the bm report due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)

class CalculateAndUpdateBufferPenetration(APIView):
    @swagger_auto_schema(
        operation_description='Assign the bpp for the orders',
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_STRING
            )
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def put(self,request):
        try:
            # proc rope date is not calculated in this api
            if(request.POST):
                orders_for_bpp = request.POST.get('orderData')
            else:
                orders_for_bpp = request.data.get('orderData')

            today = date.today()
            least_allowed_pen = -99999999
            threshold_black = 100
            threshold_red = 67
            threshold_yellow = 34
            threshold_green = 0
            # CCR working date data
            ccr_wise_working_dates = DailyWorkingCalendar.objects.filter(working_date__gte=today).values('lno','ccr','plant','working_date').order_by('working_date')
            logger.info('Fetched daily working data for the CCR')
        
            # Calculating next working day for each CCR
            working_date_map = {}
            for data in ccr_wise_working_dates:
                    working_key = (data['ccr'],data['plant'])
                    working_date = data['working_date']
                    if working_key not in working_date_map or working_date < working_date_map[working_key]['wd']:
                        working_date_map[working_key] = {
                            'lno' : data['lno'],
                            'wd' : working_date
                    }
            logger.info('Next working date for each ccr and plant has been fetched')

            if orders_for_bpp:
                filter_condition = {'order_key__in' : orders_for_bpp}
            else:
                filter_condition = {}
            #Fetching all the order data
            scheduled_Orders = OrderData.objects.filter(due_date__isnull = False,**filter_condition)
            logger.info('All the order data for both MTA and MTO has been fetched')
            # Fetching the MTO data from all order data
            order_data = scheduled_Orders.filter(vf_order_type = 'MTO').values('order_id','order_key','delay_days','line_id','is_rm_released','item','ccr','plant','vf_order_type','post_order_buffer_size',
            'pre_order_buffer_size','color','bpp','due_date')
            logger.info('Fetched the MTO order data only whose rm is released')
            order_keys =  [order['order_key'] for order in order_data]
            # order_ccr_plant_map = {(data['ccr'],data['plant']) : data for data in order_data}

            # Fetching order buffer data for MTO orders
            order_buffer_data = OrderBufferMapping.objects.filter(order__in = order_keys).values('order','buffer__buffer_type__buffer_type','buffer__buffer_size','buffer_date','buffer__is_blue')
            logger.info('Fetched the order buffer mapping data')

            order_buffer_map = {}
            for data in order_buffer_data:
                order_key  = data['order']
                if order_key not in order_buffer_map:
                    order_buffer_map[order_key] = {}
                if data['buffer__buffer_type__buffer_type'].lower() == 'prod':
                    order_buffer_map[order_key] = {
                        'bsize' : data['buffer__buffer_size'],
                        'bdate' : data['buffer_date'],
                        'isBlue' : data['buffer__is_blue']
                    }
            
            # mto orders that need to be updated
            mto_order_data_to_be_updated = []
            # Assigning the bpp for MTO orders
            for data in order_data:
                ccr = data['ccr']
                plant = data['plant']
                buffer_info = order_buffer_map.get(data['order_key'],{})
                isBlue = buffer_info.get('isBlue')
                if isBlue == 0:
                    buff_size = buffer_info.get('bsize',0)
                    post_order_buffer_size = data['post_order_buffer_size'] if data['post_order_buffer_size'] else 0
                    due_date = data['due_date']
                    next_working_data = working_date_map.get((ccr,plant),{})
                    ccr_working_date_qs = ccr_wise_working_dates.filter(working_date = due_date,ccr = ccr,plant = plant).values('working_date','lno')
                    lno = ccr_working_date_qs[0]['lno'] if ccr_working_date_qs else 0
                    data['bpp'] = math.ceil((100.0 * ((buff_size +post_order_buffer_size) - (lno - next_working_data.get('lno',0)) - 1)) / (buff_size + post_order_buffer_size))
                    bpp = data['bpp']
                    pre_order_buffer_size = data['pre_order_buffer_size'] if  data['pre_order_buffer_size'] else 0
                    if bpp < threshold_green and pre_order_buffer_size > 0 and date.today() <= buffer_info.get('bdate',0):
                        data['color'] = 'Blue'
                    elif bpp < threshold_green:
                        data['color'] = 'White'
                    elif bpp  >= threshold_green and bpp < threshold_yellow:
                        data['color'] = 'Green'
                    elif bpp>=threshold_yellow and bpp<threshold_red:
                        data['color'] = 'Yellow'
                    elif bpp>=threshold_red and bpp<threshold_black:
                        data['color'] = 'Red'
                    elif bpp>=threshold_black:
                        data['color'] = 'Black'
                        data['delay_days'] = (next_working_data.get('lno',0) - lno)
                else:
                    data['color'] = 'Blue'
                mto_order_data_to_be_updated.append(data)   
            logger.info('BPP and color has been assigned to the orders')

            with transaction.atomic():
                try:
                    for mto_order in mto_order_data_to_be_updated:
                        order_id = mto_order.pop('order_id', None)
                        line_id = mto_order.pop('line_id', None)
                        OrderData.objects.filter(order_id=order_id, line_id = line_id).update(**mto_order)
                    logger.info('Data successfully updated')
                except Exception as e:
                    logger.error('Error while updating the data', exc_info=True)
                    return api_response( msg=str(e),status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return api_response(msg='Data fetched successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured in the buffer penetration assignment due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in the buffer penetration assignment due to {str(ex)}',status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateFOLandSTPL(APIView):
    @swagger_auto_schema(
        operation_description='update the STPL and FOL',
        request_body=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'ok' : openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_STRING
                        ),
                        description='order keys'
                    )
                }
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
       
    )
    def put(self,request):
        try:
            '''
            # FOL data
            fol_data_instance = FOL_Data.objects.all()
            logger.info('Fetched FOL Data')
           
            #get ccr ids from FOL Data
            ccr_ids = [data.ccr for data in fol_data_instance]
            logger.info('collected ccr ids from FOL data')
 
            #Get today's date
            todays_date = date.today()
            logger.info('todays date from date.today()')
            # Daily working calender data
            working_details = DailyWorkingCalendar.objects.filter(ccr__in = ccr_ids,working_date__gte=todays_date).values('lno','ccr','plant','working_date').order_by('working_date')
            logger.info('Fetched daily working data for the CCRs')
 
            #create ccrId - WorkingDate map
            ccr_next_working_date_map = {}
            for data in working_details:
                    working_key = data['ccr']
                    working_date = data['working_date']
                    if working_key not in ccr_next_working_date_map or working_date < ccr_next_working_date_map[working_key]['wd']:
                        ccr_next_working_date_map[working_key] = {
                            'lno' : data['lno'],
                            'wd' : working_date
                        }
            # CCR master data
            ccr_details = CCRMaster.objects.annotate(capacity =F('working_hours_per_day')*60).values('ccr_id','plant','capacity','fol_horizon')
            logger.info('Fetched ccr master data and capacity based on working hours per day of each CCR')

            #create dict of ccrId - CCr_details
            ccr_details_mapping = {data['ccr_id'] : data for data in ccr_details}
            ccr_fol_data = {}
            for data in ccr_details:
                ccr_key = data['ccr_id']
                next_wd_lno = ccr_next_working_date_map.get(ccr_key,{})
                if ccr_key not in ccr_fol_data:
                    horizon_date_qs = working_details.filter(lno = (data['fol_horizon']  + next_wd_lno.get('lno',0))).values('working_date')
                    horizon_date = horizon_date_qs[0]['working_date'] if horizon_date_qs else next_wd_lno.get('wd',date.today())
                    ccr_fol_data[ccr_key] = {
                        'fhd' : horizon_date ,
                        'wd' : next_wd_lno.get('wd',None),
                        'cdI' : next_wd_lno.get('lno') if next_wd_lno.get('lno') else 0,
                        'mtofol' : 0,
                        'mtostpl' : 0,
                        'mtafol': 0 ,
                        'mtastpl' : 0
                    }
            # Order data both MTO and MTA orders is fetched here
            scheduled_Orders = OrderData.objects.filter(is_line_finished = False).values('order_key','bpp','order_id','line_id','plant','ccr','due_date','is_rm_released','vf_order_type','actual_released_date')
            logger.info('Fetched order data for both MTO and MTA orders')
 
            # Line CCR details for all orders
            line_ccr_details = LineCCRDetails.objects.filter(ccr__isnull = False).values('order','ccr','pending_ccr_qty','order_load')
            logger.info('Fetched the Line ccr details for the orders')

            # MTO order for FOL and STPL
            mto_scheduled_order_data = scheduled_Orders.filter(vf_order_type = 'MTO', due_date__isnull = False)
            logger.info('Filtered MTO order data from Scheduled orders')
            mto_scheduled_order_keys = [data['order_key'] for data in mto_scheduled_order_data]           
            # line ccr details for mto order
            mto_scheduled_orders_line_ccr_details = line_ccr_details.filter(order__in = mto_scheduled_order_keys)
            # order buffer for mto orders
            order_buffer_mapping = OrderBufferMapping.objects.filter(order__in = mto_scheduled_order_keys).values('order','buffer__buffer_type__buffer_type','buffer_date')
            logger.info('Fetched the order buffer data for production buffer date')
 
            #create map for order-ProdBuffDate
            order_buffer_date_map = {}
            for data in order_buffer_mapping:
                order = data['order']
                buffer_type = data['buffer__buffer_type__buffer_type'].lower()
                if 'prod' in buffer_type:
                    if order not in order_buffer_date_map:
                        order_buffer_date_map[order] = data['buffer_date']
           
            # max fol horizon for mto orders - get orderwise max FOL horizon date
            # from multiple ccrs in route get max FOL horizon date by comparing FOlHOrizon date of each ccr in route
            orderwise_mfhd = defaultdict(lambda: {'mfhd': None, 'pbd': None})
            for data in mto_scheduled_orders_line_ccr_details:
                order = data['order']
                ccr = data['ccr']
                fol_data = ccr_fol_data.get(ccr, {})
                prod_buffer_date = order_buffer_date_map.get(order, 0)
                if orderwise_mfhd[order]['pbd'] is None and prod_buffer_date :
                    orderwise_mfhd[order]['pbd'] = prod_buffer_date
                mfhd = orderwise_mfhd[order]['mfhd'] if orderwise_mfhd[order]['mfhd'] else None
                fhd = fol_data.get('fhd', None)
                if mfhd and fhd:
                    max_fol_horizon_date = max(mfhd, fhd)
                elif fhd and not mfhd:
                    max_fol_horizon_date = fhd
                else:
                    max_fol_horizon_date = mfhd
                
                orderwise_mfhd[order]['mfhd'] = max_fol_horizon_date

            # MTO orders to be considered for FOL - orders whose release date is within Fol Horizon are to be considered for FOL calculations
            mto_orders_to_be_considered_for_FOL = []
            for key,value in orderwise_mfhd.items():
                if value['mfhd'] and value['pbd']:
                    if value['mfhd'] >= value['pbd']:
                        mto_orders_to_be_considered_for_FOL.append(key)
            # line ccr for filtered MTO FOL orders
            filtered_line_ccr_data = mto_scheduled_orders_line_ccr_details.filter(order__in = mto_orders_to_be_considered_for_FOL)
            ccr_order_loads = filtered_line_ccr_data.values('ccr').annotate(total_order_load=Coalesce(Sum('order_load'),Value(0), output_field=DecimalField())).order_by('ccr')
            # FOL data for MTO
            mto_fol_in_days = {}
            for data in ccr_order_loads:
                if data['ccr'] not in mto_fol_in_days:
                    ccr_detail = ccr_details_mapping.get(data['ccr'],{})
                    capacity = ccr_detail.get('capacity',0)
                    mto_fol_in_days[data['ccr']] = (data['total_order_load'] / capacity) if capacity>0 else data['total_order_load']
                    # else data['total_order_load'] is not done in script but here its done to handle error on UI
            # orders for MTO STPL
            mto_order_for_stpl = mto_scheduled_order_data.filter(is_rm_released = True, actual_released_date__lte = todays_date)
            mto_stpl_order_keys = [data['order_key'] for data in mto_order_for_stpl]
            stpl_mto_orders_to_be_considered = []
            
            for keys in mto_stpl_order_keys:
                stpl_mto_orders_to_be_considered.append(keys)
            # line ccr details for MTO STPL
            mto_stpl_filter_line_ccr_data = mto_scheduled_orders_line_ccr_details.filter(order__in = stpl_mto_orders_to_be_considered)
            mto_stpl_ccr_order_loads = mto_stpl_filter_line_ccr_data.values('ccr').annotate(total_order_load=Coalesce(Sum('order_load'),Value(0), output_field=DecimalField())).order_by('ccr')
            mto_stpl_in_days = {}
            for data in mto_stpl_ccr_order_loads:
                if data['ccr'] not in mto_stpl_in_days:
                    ccr_detail = ccr_details_mapping.get(data['ccr'],{})
                    capacity = ccr_detail.get('capacity',0)
                    mto_stpl_in_days[data['ccr']] = (data['total_order_load'] / capacity) if capacity>0 else data['total_order_load']
                    # else data['total_order_load'] is not done in script but here its done to handle error on UI
            #start calculating FOL and STPL for MTA orders
            is_mta_capacity_reserved = DBRSettings.objects.get(flag = 'IsMTACapacityReserved').value
            logger.info('Fetched DBR setting value for flag IsMTACapacityReserved')
            mta_fol_in_days = {}
            mta_stpl_in_days = {}
            # do calculation only if MTA capacity is not
            if int(is_mta_capacity_reserved) == 0 or is_mta_capacity_reserved == 'False':
                #MTA orders FOL and STPL
                mta_order_data = scheduled_Orders.filter(vf_order_type = 'MTA')
                logger.info('Filtered MTA order data from scheduled_Orders')
                
                #get MTA order keys
                mta_order_keys = [data['order_key'] for data in mta_order_data]
 
                # MTA orders line ccr details
                mta_line_ccr_details = line_ccr_details.filter(order__in = mta_order_keys)
                logger.info('Filtered line ccr details for the MTA orders')
 
                # line ccr for filtered MTA FOL orders
                #mta_filter_line_ccr_data = mta_line_ccr_details.filter(order__in = mta_order_keys)
                mta_ccr_order_loads = mta_line_ccr_details.values('ccr').annotate(total_order_load=Sum('order_load')).order_by('ccr')     
                 
                # FOL data for MTA Orders          
                for data in mta_ccr_order_loads:
                    if data['ccr'] not in mta_fol_in_days and data['ccr'] is not None:
                        ccr_detail = ccr_details_mapping.get(data['ccr'],{})
                        capacity = ccr_detail.get('capacity',0)
                        if data['total_order_load'] is None:
                            data['total_order_load']= 0
                        mta_fol_in_days[data['ccr']] = (data['total_order_load'] / capacity) if capacity>0 else data['total_order_load']               
 
                #MTA order for STPL
                mta_order_for_stpl = mta_order_data.filter(bpp__gt = 0)
                order_key_for_mta_stpl = [data['order_key'] for data in mta_order_for_stpl]
                mta_stpl_filtered_line_ccr_data = mta_line_ccr_details.filter(order__in = order_key_for_mta_stpl)
                mta_stpl_ccr_order_load = mta_stpl_filtered_line_ccr_data.values('ccr').annotate(total_order_load=Sum('order_load')).order_by('ccr')
               
                for data in mta_stpl_ccr_order_load:
                    if data['ccr'] not in mta_stpl_in_days:
                        ccr_detail = ccr_details_mapping.get(data['ccr'],{})
                        capacity = ccr_detail.get('capacity',0)
                        if data['total_order_load'] is None:
                            data['total_order_load']= 0
                        mta_stpl_in_days[data['ccr']] = (data['total_order_load'] / capacity) if capacity>0 else data['total_order_load']
           
            # ccrs whose data needed to be updated in the fol data
            ccrs_of_line_ccr_details = [data['ccr'] for data in line_ccr_details]
            fol_data_to_be_created = []
            fol_data_to_be_updated = []
 
            # Getting CCR instances
            ccr_instances = CCRMaster.objects.all()
            logger.info('Fetched the ccr instances from CCR Master')
            ccr_instance_mapping = {data.ccr_id : data for data in ccr_instances}
            # getting fol data instances
            fol_data_instance_mapping = {data.ccr.ccr_id : data for data in fol_data_instance}
            unique_ccrs_in_line_ccr_details = set(ccrs_of_line_ccr_details)
            for ccr in unique_ccrs_in_line_ccr_details:
                mto_fol = mto_fol_in_days.get(ccr,0)
                mta_fol = mta_fol_in_days.get(ccr,0)
                mto_stpl = mto_stpl_in_days.get(ccr,0)
                mta_stpl = mta_stpl_in_days.get(ccr,0)
                fol_in_days = round((mto_fol + mta_fol) if mto_fol and mta_fol else (mto_fol if  mto_fol else mta_fol),2)
                fol_in_days_for_fol_end_date = round(fol_in_days,0)
                stpl_in_days = (mto_stpl + mta_stpl) if mto_stpl and mta_stpl else (mto_stpl if  mto_stpl else mta_stpl)
                todays_lno = ccr_next_working_date_map.get(ccr,None)
                todays_lno_date = 0
                if todays_lno:
                    todays_lno_date = todays_lno.get('lno',0)
                fol_end_date_qs = working_details.filter(lno =  todays_lno_date + fol_in_days_for_fol_end_date).values('working_date')
                fol_end_date =  fol_end_date_qs[0]['working_date'] if fol_end_date_qs else None
                if fol_end_date is not None:
                    if ccr in fol_data_instance_mapping:
                        fol_instance = fol_data_instance_mapping.get(ccr)
                        fol_instance.fol_in_days = fol_in_days
                        fol_instance.fol_end_date = fol_end_date
                        fol_instance.stpl_in_days = stpl_in_days
                        fol_data_to_be_updated.append(fol_instance)
                    else:
                        fol_data_to_be_created.append(
                            FOL_Data(
                            fol_end_date = fol_end_date,
                            fol_in_days = fol_in_days,
                            stpl_in_days = stpl_in_days,
                            ccr = ccr_instance_mapping.get(ccr),
                            occupied_qty_in_units = 0,
                            occupied_qty_in_mins = 0,
                        ))
            '''

            # Fetch CCRs involved in this update
            order_keys = request.data.get('order_keys')
            old_ccr_ids = request.data.get('old_ccrs')      # old CCRs affected due to route change
            
            # Fetch NEW CCRs assigned to the given order_keys
            new_ccrs = set(LineCCRDetails.objects.filter(order__in=order_keys, ccr__isnull=False).values_list('ccr',flat=True).distinct())
            logger.info('Fetched the Line ccr details for the orders')

            # final CCR set = new_ccrs XOR old_ccrs (for route change cases)
            ccr_ids = new_ccrs if new_ccrs else set()
            ccr_ids = ccr_ids ^ old_ccr_ids if old_ccr_ids else ccr_ids 
            logger.info('collected ccr ids from FOL data')

            # Line CCR details for these ccrs
            line_ccr_details = pd.DataFrame(list(LineCCRDetails.objects.filter(ccr__in=ccr_ids).values('order','order_load','ccr')))
            line_ccr_details['order_load'] = line_ccr_details['order_load'].fillna(0)
            if line_ccr_details.empty:
                raise Exception(f"No Line CCR details found for the given ccr's: {ccr_ids}")

            # existing FOL data for these CCRs
            fol_data_instance = FOL_Data.objects.filter(ccr__in=ccr_ids)
            logger.info('Fetched FOL Data')
            
            # Get today's date
            todays_date = date.today()
            logger.info('todays date from date.today()')

            # Working Calendar for these CCRs
            working_details = pd.DataFrame(list(
                DailyWorkingCalendar.objects.filter(
                    ccr__in=ccr_ids,
                    working_date__gte=todays_date
                ).values('ccr', 'lno', 'plant', 'working_date')
            ))

            # Ensure date column is datetime
            working_details['working_date'] = pd.to_datetime(working_details['working_date'])

            # For each CCR, find its earliest next working date (first date >= today)
            ccr_next_working_date_map = working_details.sort_values('working_date').groupby('ccr', as_index=False).first()

            # Load CCR Master & Compute Capacity
            ccr_master_data = CCRMaster.objects.filter(ccr_id__in=ccr_ids).annotate(
                    capacity=F('working_hours_per_day') * 60
                )
            ccr_details = pd.DataFrame(list(ccr_master_data.values('ccr_id', 'plant', 'capacity', 'fol_horizon','ccr_name')))
            if (ccr_details['capacity']<=0).any():
                raise Exception(f"Capacity missing for some CCRs: {ccr_details.query('capacity<=0')['ccr_name'].tolist()}")
            
            if (ccr_details['fol_horizon']<0).any():
                raise Exception(f"FOL Horizon missing for some CCRs: {ccr_details.query('fol_horizon<0')['ccr_name'].tolist()}")
            
            # Merge CCR Master + Next Working Date
            ccr_next_wd = ccr_details.merge(
                ccr_next_working_date_map, how='left',
                left_on=['ccr_id','plant'], right_on=['ccr','plant']
            ).rename(columns={'working_date':'next_wk_dt', 'lno':'next_wk_lno'}).drop(columns=['ccr'])
            
             # If any CCR has no next working date entry → error
            if ccr_next_wd['next_wk_dt'].isna().any():   
                raise Exception(f"Next working date missing for some CCRs: {ccr_next_wd.query('next_wk_dt.isna()')['ccr_name'].tolist()}")

            # Compute Horizon LNO (lno = next working lno + horizon)
            ccr_next_wd['horizon_lno'] = ccr_next_wd['fol_horizon'] + ccr_next_wd['next_wk_lno']

            # Fetch horizon date from working calendar
            ccr_next_wd = ccr_next_wd.merge(
                working_details[['ccr','lno', 'working_date']] ,
                how='left',
                left_on=['ccr_id','horizon_lno'],
                right_on=['ccr','lno']
            ).rename(columns={'working_date': 'horizon_date'}).drop(columns=['ccr','lno'])
            
            # If any CCR has no horizon date entry → error
            if ccr_next_wd['horizon_date'].isna().any():   
                raise Exception(f"Next working date missing for some CCRs: {ccr_next_wd.query('horizon_date.isna()')['ccr_name'].tolist()}")

            # CCR FOL Data Table
            ccr_fol_data = pd.DataFrame({
                'ccr': ccr_next_wd['ccr_id'],
                'fhd': ccr_next_wd['horizon_date'],     # Fol Horizon Date
                'wd': ccr_next_wd['next_wk_dt'],      # Next Working Date
                'cdI': ccr_next_wd['next_wk_lno'],    # Current Day Index
                'mtofol': 0,
                'mtostpl': 0,
                'mtafol': 0,
                'mtastpl': 0
            })

            # Fetch Orders belonging to these CCRs
            scheduled_orders = pd.DataFrame(list(
                OrderData.objects.filter(order_key__in = line_ccr_details['order'], is_line_finished=False).values(
                    'order_key', 'bpp', 'order_id', 'line_id', 'plant',
                    'ccr', 'due_date', 'is_rm_released', 'vf_order_type',
                    'actual_released_date'
                )
            ))
            logger.info("Fetched order data for both MTO and MTA orders")

            # MTO order for FOL and STPL
            mto_scheduled_order_data = scheduled_orders[
                (scheduled_orders['vf_order_type'] == 'MTO') &
                (scheduled_orders['due_date'].notna())
            ]
            logger.info("Filtered MTO order data from Scheduled orders")

            # line ccr details for mto order
            mto_scheduled_orders_line_ccr_details = mto_scheduled_order_data.merge(
                line_ccr_details,
                how='inner',
                left_on='order_key',
                right_on='order',
            ).drop(columns=['ccr_x', 'order']).rename(columns={'ccr_y':'ccr'})

            # order buffer for mto orders
            order_buffer_date_map = pd.DataFrame(list(
                OrderBufferMapping.objects.filter(
                    order__in=mto_scheduled_orders_line_ccr_details['order_key'], buffer__buffer_type__buffer_type__icontains='prod'
                ).distinct('order').values('order', 'buffer_date')
            ))
            logger.info('Fetched the order buffer data for production buffer date')

            # Add FOL Horizon Date (FHD)
            mto_ccr_fhd = mto_scheduled_orders_line_ccr_details.merge(
                ccr_fol_data[['ccr', 'fhd']], 
                how='left', 
                left_on='ccr', 
                right_on='ccr'
            )

            # Add Production Buffer Date (PBD)
            mto_ccr_fhd_pbd = mto_ccr_fhd.merge(
                order_buffer_date_map,
                how='left',
                left_on='order_key',
                right_on='order'
            ).rename(columns={'buffer_date': 'pbd'}).drop(columns=['order_key'])

            # compute max FHD & single PBD
            orderwise_mfhd = (
                mto_ccr_fhd_pbd
                .groupby('order', as_index=False)
                .agg({'fhd': 'max', 'pbd': 'first'})
                .rename(columns={'fhd': 'mfhd'})
            )

            # Filter orders for FOL computation (mfhd >= pbd)            
            orderwise_mfhd= orderwise_mfhd[
                (orderwise_mfhd['mfhd'].notna()) &
                (orderwise_mfhd['pbd'].notna()) &
                (orderwise_mfhd['mfhd'] >= orderwise_mfhd['pbd'])
            ]

            mto_orders_to_be_considered_for_FOL = orderwise_mfhd['order'].tolist()

            # line ccr for filtered MTO FOL orders
            filtered_line_ccr_data = mto_scheduled_orders_line_ccr_details.query('order_key in @mto_orders_to_be_considered_for_FOL')
            filtered_line_ccr_data['order_load'] = filtered_line_ccr_data['order_load'].fillna(0)
            ccr_order_loads = filtered_line_ccr_data[['ccr','order_load']].groupby('ccr',as_index=False).agg({'order_load':'sum'}).rename(columns={'order_load':'total_order_load'})
 
            # FOL data for MTO
            mto_fol_in_days = ccr_order_loads.merge(
                ccr_details[['ccr_id','capacity']],
                how='left',
                left_on='ccr',
                right_on='ccr_id'
            ).drop(columns=['ccr_id'])
            
            mto_fol_in_days['mto_fol_in_days'] = pd.to_numeric(mto_fol_in_days['total_order_load'])/ pd.to_numeric(mto_fol_in_days['capacity'])

            # orders for MTO STPL
            mto_order_for_stpl = mto_scheduled_order_data.query(f'is_rm_released == True and actual_released_date.notna() and actual_released_date <= @todays_date')
            stpl_mto_orders_to_be_considered = mto_order_for_stpl['order_key'].tolist()
            
            # line ccr details for MTO STPL
            mto_stpl_filtered_line_ccr_data = mto_scheduled_orders_line_ccr_details.query('order_key in @stpl_mto_orders_to_be_considered')
            mto_stpl_filtered_line_ccr_data['order_load'] = mto_stpl_filtered_line_ccr_data['order_load'].fillna(0)
            mto_stpl_ccr_order_loads = mto_stpl_filtered_line_ccr_data[['ccr','order_load']].groupby('ccr',as_index=False).agg({'order_load':'sum'}).rename(columns={'order_load':'total_order_load'})

            # STPL data for MTO
            mto_stpl_in_days = mto_stpl_ccr_order_loads.merge(
                ccr_details[['ccr_id','capacity']],
                how='left',
                left_on='ccr',
                right_on='ccr_id'
            ).drop(columns=['ccr_id'])
            
            mto_stpl_in_days['mto_stpl_in_days'] = pd.to_numeric(mto_stpl_in_days['total_order_load'])/ pd.to_numeric(mto_stpl_in_days['capacity'])
            
            # Compute MTA FOL & STPL (only if capacity is not reserved)
            is_mta_capacity_reserved = DBRSettings.objects.get(flag = 'IsMTACapacityReserved').value
            logger.info('Fetched DBR setting value for flag IsMTACapacityReserved')
            
            if int(is_mta_capacity_reserved) == 0 or is_mta_capacity_reserved == 'False':
                
                # MTA orders FOL and STPL
                mta_order_data = scheduled_orders[(scheduled_orders['vf_order_type'] == 'MTA')]
                logger.info('Filtered MTA order data from scheduled_Orders')
                
                if not mta_order_data.empty:
                    
                    # MTA orders line ccr details
                    mta_line_ccr_details = mta_order_data.merge(
                        line_ccr_details,
                        how='inner',
                        left_on='order_key',
                        right_on='order',
                    ).drop(columns=['ccr_x', 'order']).rename(columns={'ccr_y':'ccr'})

                    mta_line_ccr_details['order_load'] = mta_line_ccr_details['order_load'].fillna(0)
                    mta_ccr_order_loads = mta_line_ccr_details[['ccr','order_load']].groupby('ccr',as_index=False).agg({'order_load':'sum'}).rename(columns={'order_load':'total_order_load'})

                    # FOL data for MTA
                    mta_fol_in_days = mta_ccr_order_loads.merge(
                        ccr_details[['ccr_id','capacity']],
                        how='left',
                        left_on='ccr',
                        right_on='ccr_id'
                    ).drop(columns=['ccr_id'])
                    
                    mta_fol_in_days['mta_fol_in_days'] = pd.to_numeric(mta_fol_in_days['total_order_load'])/ pd.to_numeric(mta_fol_in_days['capacity'])

                    # orders for MTA STPL
                    mta_order_for_stpl = mta_order_data.query("bpp > 0")
                    order_key_for_mta_stpl = mta_order_for_stpl['order_key'].tolist()

                    mta_stpl_filtered_line_ccr_data = mta_line_ccr_details.query('order_key in @order_key_for_mta_stpl')
                    mta_stpl_filtered_line_ccr_data['order_load'] = mta_stpl_filtered_line_ccr_data['order_load'].fillna(0)
                    mta_stpl_ccr_order_loads = mta_stpl_filtered_line_ccr_data[['ccr','order_load']].groupby('ccr',as_index=False).agg({'order_load':'sum'}).rename(columns={'order_load':'total_order_load'})

                    # STPL data for MTA
                    mta_stpl_in_days = mta_stpl_ccr_order_loads.merge(
                        ccr_details[['ccr_id','capacity']],
                        how='left',
                        left_on='ccr',
                        right_on='ccr_id'
                    ).drop(columns=['ccr_id'])
                    
                    mta_stpl_in_days['mta_stpl_in_days'] = pd.to_numeric(mta_stpl_in_days['total_order_load'])/ pd.to_numeric(mta_stpl_in_days['capacity'])
                else:
                    # No MTA orders -> empty dataframes
                    mta_fol_in_days = pd.DataFrame({'ccr':[], 'mta_fol_in_days':[]})
                    mta_stpl_in_days = pd.DataFrame({'ccr':[], 'mta_stpl_in_days':[]})
            else:
                # MTA capacity reserved -> empty dataframes
                mta_fol_in_days = pd.DataFrame({'ccr':[], 'mta_fol_in_days':[]})
                mta_stpl_in_days = pd.DataFrame({'ccr':[], 'mta_stpl_in_days':[]})
            
            # unique ccrs from line ccr details
            unique_ccrs_in_line_ccr_details = pd.DataFrame({'ccr' : list(set(line_ccr_details['ccr']))})

            fol_data_instance_mapping = (
                unique_ccrs_in_line_ccr_details
                .merge(mto_fol_in_days[['ccr', 'mto_fol_in_days']], on='ccr', how='left')
                .merge(mta_fol_in_days[['ccr', 'mta_fol_in_days']], on='ccr', how='left')
                .merge(mto_stpl_in_days[['ccr', 'mto_stpl_in_days']], on='ccr', how='left')
                .merge(mta_stpl_in_days[['ccr', 'mta_stpl_in_days']], on='ccr', how='left')
                .merge(ccr_fol_data[['ccr','cdI','wd']], on='ccr', how='left')  # next working date info
            )
            fol_data_instance_mapping = fol_data_instance_mapping.fillna(0)

            # Compute total fol_in_days
            fol_data_instance_mapping['fol_in_days'] = (
                fol_data_instance_mapping[['mto_fol_in_days', 'mta_fol_in_days']]
                .sum(axis=1, skipna=True)
                .round(2)
            )
            fol_data_instance_mapping['fol_in_days_for_fol_end_date'] = fol_data_instance_mapping['fol_in_days'].round()

            # Compute total stpl_in_days
            fol_data_instance_mapping['stpl_in_days'] = (
                fol_data_instance_mapping[['mto_stpl_in_days', 'mta_stpl_in_days']]
                .sum(axis=1, skipna=True)
                .round(2)
            )

            # Compute LNO for fol_end_date
            fol_data_instance_mapping['fol_end_date_lno'] = fol_data_instance_mapping['cdI'] + fol_data_instance_mapping['fol_in_days_for_fol_end_date']
            fol_data_instance_mapping = fol_data_instance_mapping.merge(
                working_details[['ccr','lno', 'working_date']], 
                how='left', 
                left_on=['ccr', 'fol_end_date_lno'], 
                right_on=['ccr', 'lno']
            ).rename(columns={'working_date':'fol_end_date'}).drop(columns=['lno'])

            # fol_data_instance_mapping = fol_data_instance_mapping[fol_data_instance_mapping['fol_end_date'].notna()]
            if fol_data_instance_mapping['fol_end_date'].isna().any():
                raise Exception(f"FOL End Date could not be computed for some CCRs: {fol_data_instance_mapping.query('fol_end_date.isna()')['ccr'].tolist()}")
            
            # Separate data to be created vs updated
            fol_existing_ccrs = fol_data_instance.values_list('ccr__ccr_id', flat=True)
            fol_data_condition = fol_data_instance_mapping['ccr'].isin(fol_existing_ccrs)
            fol_data_to_be_updated_df = fol_data_instance_mapping[fol_data_condition]
            fol_data_to_be_created_df = fol_data_instance_mapping.loc[~fol_data_condition]

            # Create model instance maps
            fol_model_instance = {
                data.ccr.ccr_id: data 
                    for data in fol_data_instance
            }
            ccr_model_instance = {
                data.ccr_id: data 
                for data in ccr_master_data
            }

            # Prepare update instances
            fol_data_to_be_updated = []
            for index, row in fol_data_to_be_updated_df.iterrows():
                instance = fol_model_instance.get(row['ccr'])
                instance.fol_in_days = row['fol_in_days']
                instance.stpl_in_days = row['stpl_in_days']
                instance.fol_end_date = row['fol_end_date']
                fol_data_to_be_updated.append(instance)

            # Prepare create instances
            fol_data_to_be_created = [
                FOL_Data(
                    ccr = ccr_model_instance.get(row['ccr']),
                    fol_in_days = row['fol_in_days'],
                    stpl_in_days = row['stpl_in_days'],
                    fol_end_date = row['fol_end_date'],
                    occupied_qty_in_units = 0,
                    occupied_qty_in_mins = 0,
                )
                for _, row in fol_data_to_be_created_df.iterrows()
            ]

            fol_data_fields = {
                'fol_end_date',
                'fol_in_days',
                'stpl_in_days',
            }
            with transaction.atomic():
                if fol_data_to_be_updated:
                    FOL_Data.objects.bulk_update(fol_data_to_be_updated,fol_data_fields)
                if fol_data_to_be_created:
                    FOL_Data.objects.bulk_create(fol_data_to_be_created)
               
            return api_response(msg="FOL and STPL calculated and data has been saved Successfully",status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'Some exception has been occured in the update fol and stpl view due to {str(ex)}')
            return api_response(msg=f'Some exception has been occured in the update fol and stpl view  due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)

class UpdateOrderWIPDataView(APIView):
    @swagger_auto_schema(
        operation_description='Update order WIP data',
        manual_parameters=[
            openapi.Parameter(
                "unscheduled",
                openapi.IN_QUERY,
                description="Set to true to include unscheduled orders",
                type=openapi.TYPE_INTEGER,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Array of order keys to update"
            ),
            description="Array of order keys to update",      
        )
    )
    def put(self, request):
        try:
            if(request.POST):
                order_keys = request.POST.get('order_keys')
            else:
                order_keys = request.data.get('order_keys')
            Bom_active_flag = "BOMActive"
            unscheduled = request.GET.get('unscheduled')
            unscheduled_param = bool(int(unscheduled)) if unscheduled else False
            if not order_keys:
                return api_response(msg='Order keys are required', status_code=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                Order_WIPDetails.objects.filter(order__in=order_keys).delete()
                if unscheduled_param:
                    return api_response(msg="Order WIP details have been deleted for the unscheduled order", status_code=status.HTTP_200_OK)
                else:
                    bom_active = DBRSettings.objects.get(flag = Bom_active_flag).value
                    order_data_instances = OrderData.objects.filter(order_key__in=order_keys)
                    order_data_instance_map = {order.order_key : order for order in order_data_instances}
                    ccr_data_instances = CCRMaster.objects.all()
                    ccr_instance_map = {ccr_instance.ccr_id : ccr_instance for ccr_instance in ccr_data_instances}
                    route_ids = [order.route for order in order_data_instances]
                    route_details_instances = RouteDetails.objects.filter(route_id__in=route_ids)
                    batchwise_component_allocation = BatchwiseComponentAllocation.objects.filter(order_id__in = [order.order_id for order in order_data_instances] , line_item__in = [order.line_id for order in order_data_instances])
                    item_dept_mapping = ItemDeptMapping.objects.all()
                    item_dept_mapping_map = {item_dept.current_dept_id : item_dept for item_dept in item_dept_mapping}
                    order_wip_data_to_be_created = [ ]
                    for order_key in order_keys:
                        order_instance = order_data_instance_map.get(order_key)
                        if not order_instance:
                            return api_response(msg=f'Order is not found with order key {str(order_key)}',status_code=status.HTTP_400_BAD_REQUEST)
                        actual_release_date = order_instance.actual_released_date
                        route_detail_instance_with_ccrs = route_details_instances.filter(route = order_instance.route)
                        if int(bom_active) == 1 or bom_active == 'True':
                            batchwise_component_allocation_of_order = batchwise_component_allocation.filter(order_id = order_instance.order_id, line_item = order_instance.line_id)
                            for route_detail_ccr in route_detail_instance_with_ccrs:
                                ccr = route_detail_ccr.ccr.ccr_id
                                ccr_instance = ccr_instance_map.get(ccr)
                                if not ccr_instance:
                                    continue
                                ccr_dept = ccr_instance.dept
                                item_code = item_dept_mapping_map.get(ccr_dept.dept_id).item_code
                                if not item_code:
                                    continue
                                batchwise_component_to_be_considered = batchwise_component_allocation_of_order.filter(parent_code = item_code)
                                total_values = batchwise_component_to_be_considered.aggregate(
                                    total_stock_in_qc=Sum('stock_in_qc'),
                                    total_stock_in_transit=Sum('stock_in_transit'),
                                    total_order_remaining=Sum('order_remaining'),
                                )
                                total_stock_in_qc = total_values['total_stock_in_qc'] or 0
                                total_stock_in_transit = total_values['total_stock_in_transit'] or 0
                                total_order_remaining = total_values['total_order_remaining'] or 0
                                order_wip_data_to_be_created.append(
                                    Order_WIPDetails(
                                        order = order_instance,
                                        item_code  = item_code,
                                        wip_on_hand = total_stock_in_qc+total_stock_in_transit,
                                        dept = ccr_dept,
                                        mfg_balance = total_order_remaining,
                                        dispatch_balance = order_instance.total_qty,
                                        elapsed_days = 0,
                                        exited_on = None,
                                        entered_on = date.today() if order_instance.is_rm_released and actual_release_date == date.today() else None
                                    )       
                                )
                        else:
                            item_code  =  order_instance.item.item_code
                            for route_detail_ccr in route_detail_instance_with_ccrs:
                                ccr = route_detail_ccr.ccr.ccr_id
                                ccr_instance = ccr_instance_map.get(ccr)
                                if not ccr_instance:
                                    continue
                                ccr_dept = ccr_instance.dept
                                order_wip_data_to_be_created.append(
                                    Order_WIPDetails(
                                        order = order_instance,
                                        item_code  = item_code,
                                        wip_on_hand = 0,
                                        dept = ccr_dept,
                                        mfg_balance = order_instance.pending_ccr_qty,
                                        dispatch_balance = order_instance.total_qty,
                                        elapsed_days = 0,
                                        exited_on = None,
                                        entered_on = date.today() if order_instance.is_rm_released and actual_release_date == date.today() else None
                                    )       
                                )
                    if order_wip_data_to_be_created:
                        Order_WIPDetails.objects.bulk_create(order_wip_data_to_be_created)
                        return api_response(msg="Order WIP details have been updated successfully", status_code=status.HTTP_200_OK)
                    else:
                        return api_response(msg="No order WIP details to update", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f'An Exception has occurred in update order wip data due to {str(e)}')
            return api_response(msg=f'An Exception has occurred in update order wip data API due to {str(e)}', status_code=status.HTTP_400_BAD_REQUEST)

class AssignRouteView(APIView):
    @swagger_auto_schema(
        operation_description="route assignment",
        manual_parameters=[
            openapi.Parameter('update_order_wip', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='parameter to check that the request is from DDQ or from Full kit and dynamic Release'),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'routeData': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'orders': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'route': openapi.Schema(type=openapi.TYPE_STRING, description='Route value'),
                                    'ok' : openapi.Schema(type=openapi.TYPE_STRING,description='order id'),
                                    'ccrdetails': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'ccrid': openapi.Schema(type=openapi.TYPE_INTEGER, description='ccr id'),
                                                'ccrgrp' : openapi.Schema(type=openapi.TYPE_INTEGER,description='ccr group'),
                                                'pcQty' : openapi.Schema(type=openapi.TYPE_INTEGER,description='pending ccr quanitiy'),
                                                'pos' : openapi.Schema(type=openapi.TYPE_STRING,description='position of ccr'),
                                                'ol': openapi.Schema(type=openapi.TYPE_STRING, description='Order load'),
                                            },
                                        ),
                                        description='List of order details'
                                    ),
                                },
                            ),
                        ),
                    },
                    required=['orders']
                ),
            },
            required=['routeData']
        )
    )
    def put(self, request):
        try:
            route_orders = request.data.get('routeData')
            order_data = route_orders['orders']
            order_keys = [order['ok'] for order in order_data]
            ccr_id_set = set()
            ccrgrp_set = set()
            Update_Order_Wip = request.GET.get('update_order_wip')
            Update_Order_Wip_params = bool(int(Update_Order_Wip)) if Update_Order_Wip else False 
            for data in order_data:
                ccr_data = data['ccrdetails']
                for details in ccr_data:
                    if details['ccrid'] not in ccr_id_set:
                        ccr_id_set.add(details['ccrid'])
                    if details['ccrgrp'] not in ccrgrp_set:
                        ccrgrp_set.add(details['ccrgrp'])

            ccr_ids = list(ccr_id_set)
            ccr_grps = list(ccrgrp_set)

            if not order_keys:
                return api_response({'msg': 'There should be at least one order to assign the route'}, status_code=status.HTTP_400_BAD_REQUEST)

            # Fetch OrderData instances using order_keys
            order_instances = OrderData.objects.filter(order_key__in=order_keys)
            logger.info('Fetched the order data instances')
            order_instance_dict = {order.order_key: order for order in order_instances}

            ccr_instances = {ccr.ccr_id: ccr for ccr in CCRMaster.objects.filter(ccr_id__in=ccr_ids)}
            logger.info('Fetched the ccr instances')
            
            ccr_group_instances = CCRGroupMaster.objects.filter(ccr_group_id__in = ccr_grps)
            ccr_group_instance_dict = {data.ccr_group_id : data for data in ccr_group_instances}
            logger.info('Fetched the ccr group instances')
            
            with transaction.atomic():
                orders_to_be_updated = []
                new_route_details = []
                new_ccr_details_records = []
                old_ccrs_set = set()
                for order in order_data:
                    route_name = order['route']
                    route_master_instance, route_master_created = RouteMaster.objects.get_or_create(
                        route_name=route_name,
                        defaults={'route_code': f'r_{RouteMaster.objects.count() + 1}'}
                    )
                    logger.info('Route data fetched if it exists otherwise created a new route in Route Master')

                    order_instance = order_instance_dict.get(order['ok'],{})
                    if order_instance:
                        order_instance.route = route_master_instance
                    orders_to_be_updated.append(order_instance)
                    
                    if route_master_created:
                        for data in order['ccrdetails']:
                            ccr_group = data['ccrgrp']
                            group_instance = ccr_group_instance_dict.get(ccr_group)
                            new_route_details.append(
                                RouteDetails(
                                    route = route_master_instance,
                                    ccr = ccr_instances.get(data['ccrid'],None),
                                    ccr_grp = group_instance,
                                    position = data['pos']
                                )
                            )
                    # Storing old ccrs to update FOL/STPL of the removed ccrs
                    old_ccrs = LineCCRDetails.objects.filter(order=order_instance)  
                    old_ccrs_set.update(old_ccrs.values_list('ccr__ccr_id', flat=True))
                    old_ccrs.delete()
                    order_ccr_detail = order['ccrdetails']
                    for ccr in order_ccr_detail:
                        new_ccr_details_records.append(
                                LineCCRDetails(
                                    order = order_instance,
                                    route = route_master_instance,
                                    ccr = ccr_instances.get(ccr['ccrid']),
                                    pending_ccr_qty = ccr['pcQty'],
                                    order_load = ccr['ol']
                                )
                        )
                
                if orders_to_be_updated:
                    OrderData.objects.bulk_update(orders_to_be_updated, ['route'])
                
                if new_route_details:
                    RouteDetails.objects.bulk_create(new_route_details)

                if new_ccr_details_records:
                    LineCCRDetails.objects.bulk_create(new_ccr_details_records)
                
                if Update_Order_Wip_params:
                    update_order_wip_data_view = UpdateOrderWIPDataView()
                    update_order_wip_data_request = request
                    update_order_wip_data_request.data['order_keys'] = order_keys
                    update_order_wip_data_response = update_order_wip_data_view.put(request=update_order_wip_data_request)
                    if update_order_wip_data_response.status_code != status.HTTP_200_OK:
                        raise Exception("Order WIP Data updation failed") 

                    fol_api_view = UpdateFOLandSTPL()
                    fol_request = request
                    fol_request.data['old_ccrs'] = old_ccrs_set   
                    fol_response = fol_api_view.put(request=fol_request)
                    if fol_response.status_code != status.HTTP_200_OK:
                        raise Exception("FOl update data failed")

                    # save_fol_data_view = SaveFolGapAndUpdateFolDataView()
                    # save_fol_data_request = request
                    # save_fol_data_response = save_fol_data_view.put(request=save_fol_data_request)
                    # if save_fol_data_response.status_code != status.HTTP_200_OK:
                    #     raise Exception("FOL data updation failed") 

            return api_response(msg='The Route has been assigned to the orders', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Exception has occurred due to {str(e)}')
            return api_response({'msg': f'Exception has occurred in the assign route view due to {str(e)}'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SaveFolGapAndUpdateFolDataView(APIView):
    @swagger_auto_schema(
        operation_description="Save FOL gap and update FOL data for an order",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'routeData': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'orders': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'rid': openapi.Schema(type=openapi.TYPE_INTEGER, description="Route ID"),
                                    'route': openapi.Schema(type=openapi.TYPE_STRING, description="Route value"),
                                    'ok': openapi.Schema(type=openapi.TYPE_STRING, description="Order key"),
                                    'ccrdetails': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'ccrid': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR ID'),
                                                'ccrgrp': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR group'),
                                                'pcQty': openapi.Schema(type=openapi.TYPE_INTEGER, description='Pending CCR quantity'),
                                                'pos': openapi.Schema(type=openapi.TYPE_STRING, description='Position of CCR'),
                                                'ol': openapi.Schema(type=openapi.TYPE_NUMBER, description='Order load'),
                                            },
                                        ),
                                        description="List of CCR details"
                                    ),
                                    'ccr_fol_gap': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'ccrname': openapi.Schema(type=openapi.TYPE_STRING, description='CCR name'),
                                                'ccrid': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR ID'),
                                                'fol_gap': openapi.Schema(type=openapi.TYPE_NUMBER, description='FOL gap value'),
                                            },
                                        ),
                                        description="List of CCR fol gap data"
                                    ),
                                    'ccr_order_load': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'ccrname': openapi.Schema(type=openapi.TYPE_STRING, description='CCR name'),
                                                'ccrid': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR ID'),
                                                'order_load': openapi.Schema(type=openapi.TYPE_NUMBER, description='Order load value'),
                                            },
                                        ),
                                        description="List of CCR order load data"
                                    ),
                                },
                            ),
                        )
                    },
                    required=['orders']
                )
            },
            required=['routeData']
        ),
        responses={
            200: openapi.Response(description="FOL gap and FOL data updated successfully"),
            400: openapi.Response(description="Invalid input / Missing order details"),
            404: openapi.Response(description="Order not found"),
            500: openapi.Response(description="Server error while saving fol gap"),
        }
    )
    
    def put(self, request):
        try:
            route_orders = request.data.get('routeData')
            order_details = route_orders['orders']
            if not order_details:
                return api_response({'msg': "No order details provided"}, status_code=status.HTTP_400_BAD_REQUEST)

            order_key = order_details[0].get('ok')
            ccr_fol_gap = order_details[0].get('ccr_fol_gap',[])
            ccr_order_load= order_details[0].get('ccr_order_load',[])

            # Collect all CCR ids
            all_ccr_ids = {d.get("ccrid") for d in (ccr_fol_gap + ccr_order_load)}

            order_instance = OrderData.objects.filter(order_key=order_key).first()
            if not order_instance:
                return api_response({"msg": "Order not found"}, status_code=status.HTTP_404_NOT_FOUND)

            ccr_instances = CCRMaster.objects.in_bulk(all_ccr_ids, field_name="ccr_id")
            fol_data_dict = FOL_Data.objects.filter(ccr_id__in=all_ccr_ids).in_bulk(field_name="ccr_id")

            new_orderwise_folgap_records = []
            fol_data_to_be_updated = []

            for data in ccr_fol_gap:
                ccr_id = data.get("ccrid")
                gap = Decimal(str(data.get("fol_gap", "0")))

                OrderwiseFolGap.objects.filter(order_key=order_instance,ccr_id =ccr_id).delete()

                new_orderwise_folgap_records.append(
                    OrderwiseFolGap(
                        order_key=order_instance,
                        ccr=ccr_instances.get(ccr_id),
                        fol_gap=gap,
                    )
                )

                fol_instance = fol_data_dict.get(data['ccrid'])
                if fol_instance:
                    fol_instance.fol_in_days -= gap
                    fol_data_to_be_updated.append(fol_instance)
                   
            for data in ccr_order_load:
                ccr_id = data.get("ccrid")
                order_load = Decimal(str(data.get("order_load", "0")))

                fol_instance = fol_data_dict.get(data['ccrid'])
                if fol_instance:
                    fol_instance.fol_in_days += order_load
                    fol_data_to_be_updated.append(fol_instance)
            
            with transaction.atomic():
                if new_orderwise_folgap_records:
                    OrderwiseFolGap.objects.bulk_create(new_orderwise_folgap_records)
                if fol_data_to_be_updated:
                    FOL_Data.objects.bulk_update(fol_data_to_be_updated,['fol_in_days'])

            logger.info(f"Updated fol gap for order {order_key}")
            return api_response(msg='FOL gap and FOL data updated successfully', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f'Exception has occurred in SaveFolGapAndUpdateFolDataView due to {str(e)}')
            return api_response({'msg': f'Exception has occurred in saving fol gap due to {str(e)}'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BomLevelExplosionView(APIView):
    @swagger_auto_schema(
    operation_description='DDQ - Get level wise Data for production batchwise component allocation',
    manual_parameters=[
            openapi.Parameter('oid',openapi.IN_QUERY,type=openapi.TYPE_STRING,description='order id',required=True),
            openapi.Parameter('lid',openapi.IN_QUERY,type=openapi.TYPE_STRING,description='line id',required=True),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def add_child_to_parent(self, parent_list, parent_code, child_data):
        for item in parent_list:
            if item['rmc'] == parent_code:
                item['child'].append(child_data)
                return True
            if self.add_child_to_parent(item['child'], parent_code, child_data):
                return True
        return False

    def flatten_hierarchy(self, node, hierarchy, flattened_list):
        new_hierarchy = hierarchy + [node['rmc']]
        flattened_list.append({
            'path': new_hierarchy,
            
                'rmc': node['rmc'],
                'id': node['id'],
                
                'qty': node['qty'],
                'soh': node['soh'],
                'wip': node['wip'],
                'gap': node['gap'],
            
        })
        for child in node['child']:
            self.flatten_hierarchy(child, new_hierarchy, flattened_list)

    def get(self, request):
        try:
            order_id = request.GET.get('oid')
            line_id = request.GET.get('lid')
            if not order_id or not line_id:
                return api_response(msg='The order id and line id cannot be null')

            level_wise_component_allocation = BatchwiseProductionComponentAllocation.objects.filter(
                order_id=order_id, line_item=line_id).values(
                'srl_no', 'order_id', 'line_item', 'item_code', 'plant_code', 'parent_code', 'bom_level',
                'order_qty', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit', 'order_remaining',
                'identifier', 'simulated_qty', 'open_po', 'item_srl_no'
            ).order_by('bom_level')

            if not level_wise_component_allocation:
                return api_response(msg='The explosion data for this order is not available',status_code=status.HTTP_200_OK)

            item_descriptions = {order['item_code']: order['item_description'] for order in ItemMaster.objects.filter(
                item_code__in=[order['item_code'] for order in level_wise_component_allocation]).values()}

            rm_allocated = {}
            for order in level_wise_component_allocation:
                rm_key = (order['order_id'], order['line_item'])
                if rm_key not in rm_allocated:
                    rm_allocated[rm_key] = {}
                key = (order['order_id'], order['line_item'], order['item_code'])
                if key not in rm_allocated[rm_key] and order['bom_level'] == 1:
                    rm_allocated[rm_key][key] = {}
                if order['bom_level'] == 1:
                    rm_allocated[rm_key][key] = {
                        'rmc': order['item_code'],
                        'id': item_descriptions.get(order['item_code']),
                        'bl': order['bom_level'] - 1,
                        'qty': order['order_qty'],
                        'soh': order['stock_on_hand'],
                        'wip': order['stock_in_qc'] + order['stock_in_transit'],
                        'gap': order['order_qty'] - (order['stock_on_hand'] + order['stock_in_qc'] + order['stock_in_transit']),
                        'child': []
                    }
                else:
                    parent_found = False
                    # Check top level
                    for parent_item_key, parent_item_data in rm_allocated[rm_key].items():
                        if parent_item_key[2] == order['parent_code']:
                            if 'child' not in parent_item_data:
                                parent_item_data['child'] = []
                            parent_item_data['child'].append({
                                'rmc': order['item_code'],
                                'id': item_descriptions.get(order['item_code']),
                                'bl': order['bom_level'] - 1,
                                'qty': order['order_qty'],
                                'soh': order['stock_on_hand'],
                                'wip': order['stock_in_qc'] + order['stock_in_transit'],
                                'gap': order['order_qty'] - (order['stock_on_hand'] + order['stock_in_qc'] + order['stock_in_transit']),
                                'child': []
                            })
                            parent_found = True
                            break

                    # Handle nested children if parent not found at the top level
                    if not parent_found:
                        for parent_item_key, parent_item_data in rm_allocated[rm_key].items():
                            if self.add_child_to_parent(parent_item_data['child'], order['parent_code'], {
                                'rmc': order['item_code'],
                                'id': item_descriptions.get(order['item_code']),
                                'bl': order['bom_level'] - 1,
                                'qty': order['order_qty'],
                                'soh': order['stock_on_hand'],
                                'wip': order['stock_in_qc'] + order['stock_in_transit'],
                                'gap': order['order_qty'] - (order['stock_on_hand'] + order['stock_in_qc'] + order['stock_in_transit']),
                                'child': []
                            }):
                                parent_found = True
                                break

            # Flattening the hierarchy
            heriarchical_data = []
            rm_key = (order_id, line_id)
            rm_data = rm_allocated.get(rm_key)
            for key, value in rm_data.items():
                self.flatten_hierarchy(value, [], heriarchical_data)
            return api_response(data=heriarchical_data, msg='Data has been fetched successfully', status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f'There has been an exception in fetching the level wise data due to {str(ex)}')
            return api_response(msg=f'There has been an exception in fetching the level wise data due to {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)


class GetLineCCRDetailsView(APIView):
    @swagger_auto_schema(
        operation_description='Get the line ccr details for the orders',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def post(self,request):
        try:
            order_keys = request.data.get('data')
            if not order_keys:
                return api_response(msg='The array of order keys cannot be empty',status_code=status.HTTP_400_BAD_REQUEST)
            line_ccr_details = LineCCRDetails.objects.filter(order__in = order_keys).values('order','order_load','ccr','pending_ccr_qty','route')
            data = {}
            for order in line_ccr_details:
                if order['order'] not in data:
                    data[order['order']] = {}
                if order['ccr'] not in data[order['order']]:
                    data[order['order']][order['ccr']] = {
                        'load' : order['order_load'],
                        'pcqty' : order['pending_ccr_qty'],
                        'rid' : order['route']
                    }
            return api_response(data = data,msg='Line CCR Details has been fetched successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured in fetching the line ccr details due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in fetching the line ccr details due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)



class UpdateBMReportRemarksView(APIView):
    @swagger_auto_schema(
        operation_description='add the remark for data',
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'ok' : openapi.Schema(type=openapi.TYPE_STRING,description='order key'),
                    'dept' : openapi.Schema(type=openapi.TYPE_INTEGER,description='dept id'),
                    'rm' : openapi.Schema(type=openapi.TYPE_STRING,description='remark'),
                    'user' : openapi.Schema(type=openapi.TYPE_STRING,description='user who added remark')
                }
            )
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }    
    )
    def post(self,request):
        try:
            remarks = request.data.get('data')
            order_keys = [data['ok'] for data in remarks]
            dept_ids = [data['dept'] for data in remarks]
            orders = OrderData.objects.filter(order_key__in = order_keys)
            logger.info('Fetched the order data instances')

            depts = DeptMaster.objects.filter(dept_id__in = dept_ids)
            logger.info('Fetched the dept data instances')         

            depts_map = {dept.dept_id : dept for dept in depts}
            orders_map = {order.order_key : order for order in orders}

            remarks_to_be_created = []
            for remark in remarks:
                order_key = remark['ok']
                dept = remark['dept']
                remark_str = remark['rm']
                user = remark['user']
                
                remarks_to_be_created.append(
                        BMReportRemarks(
                            order = orders_map.get(order_key,{}),
                            dept = depts_map.get(dept,{}),
                            remark = remark_str,
                            added_on = datetime.now(),
                            added_by = user
                        )
                    )
            with transaction.atomic():
                if remarks_to_be_created:
                    BMReportRemarks.objects.bulk_create(remarks_to_be_created)
            return api_response(msg='The remarks for the orders has been saved successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured while saving remarks due to {str(ex)}')
            return api_response(msg=f'An Exception has occured while saving remarks due to {str(ex)} in update bm report remarks',status_code=status.HTTP_400_BAD_REQUEST)

class BomLevelExplosionForExcelExportView(APIView):
    @swagger_auto_schema(
    operation_description='DDQ - Get level wise Data for production batchwise component allocation for excel export',
    request_body = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["oid", "lid"],
        properties={
            "oid": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING),
                description="order id"
            ),
            "lid": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING),
                description="line id"
            ),
        },
    ))
    def add_child_to_parent(self, parent_list, parent_code, child_data):
        for item in parent_list:
            if item['rmc'] == parent_code:
                item['child'].append(child_data)
                return True
            if self.add_child_to_parent(item['child'], parent_code, child_data):
                return True
        return False

    def flatten_hierarchy(self, node, hierarchy, flattened_list):
        new_hierarchy = hierarchy + [node['rmc']]
        flattened_list.append({
            'path': new_hierarchy,
            
                'rmc': node['rmc'],
                'id': node['id'],
                
                'qty': node['qty'],
                'soh': node['soh'],
                'wip': node['wip'],
                'gap': node['gap'],
            
        })
        for child in node['child']:
            self.flatten_hierarchy(child, new_hierarchy, flattened_list)

    def post(self, request):
        try:
            order_ids = request.data.get('oids')
            line_ids = request.data.get('lids')
            if not order_ids or not line_ids:
                return api_response(msg='The order id and line id cannot be null')

            level_wise_component_allocation = BatchwiseProductionComponentAllocation.objects.filter(
                order_id__in=order_ids, line_item__in=line_ids).values(
                'srl_no', 'order_id', 'line_item', 'item_code', 'plant_code', 'parent_code', 'bom_level',
                'order_qty', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit', 'order_remaining',
                'identifier', 'simulated_qty', 'open_po', 'item_srl_no'
            )

            if not level_wise_component_allocation:
                return api_response(msg='The explosion data for this order is not available',status_code=status.HTTP_200_OK)

            item_descriptions = {order['item_code']: order['item_description'] for order in ItemMaster.objects.filter(
                item_code__in=[order['item_code'] for order in level_wise_component_allocation]).values()}

            rm_allocated = {}
            for order in level_wise_component_allocation:
                rm_key = (order['order_id'], order['line_item'])
                if rm_key not in rm_allocated:
                    rm_allocated[rm_key] = {}
                key = (order['order_id'], order['line_item'], order['item_code'])
                if key not in rm_allocated[rm_key] and order['bom_level'] == 1:
                    rm_allocated[rm_key][key] = {}
                if order['bom_level'] == 1:
                    rm_allocated[rm_key][key] = {
                        'rmc': order['item_code'],
                        'id': item_descriptions.get(order['item_code']),
                        'bl': order['bom_level'] - 1,
                        'qty': order['order_qty'],
                        'soh': order['stock_on_hand'],
                        'wip': order['stock_in_qc'] + order['stock_in_transit'],
                        'gap': order['order_qty'] - (order['stock_on_hand'] + order['stock_in_qc'] + order['stock_in_transit']),
                        'child': []
                    }
                else:
                    parent_found = False
                    # Check top level
                    for parent_item_key, parent_item_data in rm_allocated[rm_key].items():
                        if parent_item_key[2] == order['parent_code']:
                            if 'child' not in parent_item_data:
                                parent_item_data['child'] = []
                            parent_item_data['child'].append({
                                'rmc': order['item_code'],
                                'id': item_descriptions.get(order['item_code']),
                                'bl': order['bom_level'] - 1,
                                'qty': order['order_qty'],
                                'soh': order['stock_on_hand'],
                                'wip': order['stock_in_qc'] + order['stock_in_transit'],
                                'gap': order['order_qty'] - (order['stock_on_hand'] + order['stock_in_qc'] + order['stock_in_transit']),
                                'child': []
                            })
                            parent_found = True
                            break

                    # Handle nested children if parent not found at the top level
                    if not parent_found:
                        for parent_item_key, parent_item_data in rm_allocated[rm_key].items():
                            if self.add_child_to_parent(parent_item_data['child'], order['parent_code'], {
                                'rmc': order['item_code'],
                                'id': item_descriptions.get(order['item_code']),
                                'bl': order['bom_level'] - 1,
                                'qty': order['order_qty'],
                                'soh': order['stock_on_hand'],
                                'wip': order['stock_in_qc'] + order['stock_in_transit'],
                                'gap': order['order_qty'] - (order['stock_on_hand'] + order['stock_in_qc'] + order['stock_in_transit']),
                                'child': []
                            }):
                                parent_found = True
                                break

            heriarchical_data_for_all_orders = {}
            for rm_key, rm_data in rm_allocated.items():
                heriarchical_data = []
                for key, value in rm_data.items():
                    self.flatten_hierarchy(value, [], heriarchical_data)
                heriarchical_data_for_all_orders[rm_key] = heriarchical_data
            return api_response(data=heriarchical_data_for_all_orders, msg='Data has been fetched successfully', status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f'There has been an exception in fetching the level wise data due to {str(ex)}')
            return api_response(msg=f'There has been an exception in fetching the level wise data due to {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)
