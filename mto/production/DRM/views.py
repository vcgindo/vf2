from mto_app.models import ( 
ExcludedOrders, FOL_Data,  OrderData,RouteDetails,ItemDeptMapping,MasterItemProductionBatchsize,Order_WIPDetails,
LineCCRDetails)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import (ExcelExportData, api_response, CustomPagination,  filter_order_data_by_params
,GetUserDetails,DataPermissionFilterForOrderData , getOTIFStatusValue,DataPermissionFilter,GetUserDetails,DataPermissionFilterForOrderData , 
get_order_information , get_pagewise_data,CustomExcelExport,get_ccr_fol_gap,get_ccr_fol_gap_mapping )
from datetime import date
from django.db import transaction
from mto_app.utils import   eReportName
import pandas as pd
from ..Common.views import  UpdateFOLandSTPL 
from collections import defaultdict
from decimal import Decimal
logger = logging.getLogger(__name__)

class DynamicReleaseView(APIView):
    pagination_class = CustomPagination
    @swagger_auto_schema(
        operation_description='Get orders whose RM is not released and due date is present',
        manual_parameters=[
            openapi.Parameter('graph',openapi.IN_QUERY,type=openapi.TYPE_STRING,description='graph flag'),
            openapi.Parameter('ao',openapi.IN_QUERY,type=openapi.TYPE_INTEGER,description='parameter for all orders'),
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
        return self.getdynamicrelease(request)
    
    def put(self,request):
        return self.getdynamicrelease(request,method = 'PUT')

    # def getWipDataForOrders(self,order_data, wip_order_keys , batchwise_production_allocation , route_details):
    #     try:
    #         order_data = order_data.filter(order_key__in = wip_order_keys)
    #         batchwise_production_allocation = batchwise_production_allocation.filter(order__in = wip_order_keys)
    #         production_order_keys = [data['order'] for data in batchwise_production_allocation]
    #         item_code_for_dept_mapping = set()
    #         allocated_rm = {}
    #         for data in batchwise_production_allocation:
    #             allocation_key = data['order']
    #             if allocation_key not in allocated_rm:
    #                 allocated_rm[allocation_key] = {}
    #             if data['item_code'] not in allocated_rm[allocation_key] and data['wip_on_hand']>0:
    #                 item_code_for_dept_mapping.add(data['item_code'])
    #                 allocated_rm[allocation_key][data['item_code']] = data['wip_on_hand'] 
            

    #         item_dept_mapping_data = ItemDeptMapping.objects.filter(item_code__in = item_code_for_dept_mapping).values('item_code','current_dept_id')
    #         items_with_dept = {data['item_code'] : data['current_dept_id'] for data in item_dept_mapping_data}
    #         logger.info('Fetched the dept for items of orders components')

    #         dept_in_item_dept_mapping = [data['current_dept_id'] for data in item_dept_mapping_data]
    #         ccr_information = CCRMaster.objects.filter(dept__in = dept_in_item_dept_mapping).values('dept','ccr_id','ccr_code')

    #         ccrs_in_dept = {}
    #         for ccr in ccr_information:
    #             if ccr['dept'] not in ccrs_in_dept:
    #                 ccrs_in_dept[ccr['dept']] = []
    #             ccrs_in_dept[ccr['dept']].append(ccr['ccr_code'])
    #         logger.info('Fetched the route details')

    #         filtered_order_data = order_data.filter(order_key__in = production_order_keys)
    #         wips_for_orders = {}
    #         for data in filtered_order_data:
    #             order_key = data['order_key']
    #             route = data['route']
    #             route_qs = route_details.filter(route = route)
    #             ccrs_for_this_orders = [data['ccr__ccr_code'] for data in route_qs] if route_qs else []
    #             rm_key = data['order_key']
    #             order_level_explosion_data = allocated_rm.get(rm_key,{})
    #             if order_level_explosion_data:
    #                 if order_key not in wips_for_orders:
    #                     wips_for_orders[order_key] = {}
    #                 for key,value in order_level_explosion_data.items():
    #                     dept_for_ccr = items_with_dept.get(key,None)
    #                     ccr_for_dept = ccrs_in_dept.get(dept_for_ccr,[]) if dept_for_ccr is not None else []
    #                     for ccr in ccr_for_dept:
    #                         if ccr in ccrs_for_this_orders:
    #                             wips_for_orders[order_key][ccr] = value
    #         logger.info('Fetched the wip data for orders')
    #         return api_response(data = wips_for_orders,msg='WIP data for orders',status_code=status.HTTP_200_OK)
    #     except Exception as e:
    #         logger.error(f'An Exception has occurred in the getWipDataForOrders of {str(e)}')
    #         return api_response(msg=f'An Exception has occurred in the getWipDataForOrders because of {str(e)}',status_code=status.HTTP_400_BAD_REQUEST)

    def getWipDataForOrders(self, wip_order_keys):
        try:
            # Let the DB group and sum
            line_ccr_details = (
                LineCCRDetails.objects
                .filter(order_id__in=wip_order_keys)
                .values('order', 'ccr__ccr_code', 'order_load')
            )
 
            # Convert queryset to a simple dict
            ccr_order_load = defaultdict(dict)
            for data in line_ccr_details:
                wip_key = data['order']
                ccr_code = data['ccr__ccr_code']
                order_load = data['order_load'] or 0
                ccr_order_load[wip_key][ccr_code] = order_load
 
            logger.info('Fetched the wip data for orders')
            return api_response(data = ccr_order_load, msg='WIP data for orders', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'An Exception has occurred in the getWipDataForOrders of {str(e)}')
            return api_response(msg=f'An Exception has occurred in the getWipDataForOrders because of {str(e)}',status_code=status.HTTP_400_BAD_REQUEST)

    def getdynamicrelease(self,request,method = 'GET'):
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
            payload_data = request.data
            wip_for_orders = payload_data.get('wip',None) if data else None

            all_orders = request.GET.get('ao')
            is_graph_required = request.GET.get('graph')
            filter_data = request.data
            graph_data_param = bool(int(is_graph_required)) if is_graph_required is not None else False
            all_order_param = bool(int(all_orders)) if all_orders is not None else False
            if not all_order_param:
                excluded_order = ExcludedOrders.objects.values('order_id','line_item')
                excluded_oid = [data['order_id'] for data in excluded_order]
                excluded_lid = [data['line_item'] for data in excluded_order]
                filter_condition = {'order_id__in':excluded_oid,'line_id__in' : excluded_lid}
            else:
                filter_condition = {}

            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')

            order_data = OrderData.objects.filter(is_rm_released = False,due_date__isnull = False,vf_order_type = 'MTO').exclude(**filter_condition).values('order_id','line_id','order_key','item__item_code','item__item_type','dept__dept_name',
                        'due_date','planned_release_date','actual_released_date',
                        'order_entry_date','bpp','color','dept__dept_id',
                        'major_reason__major_reason_desc','order_value'
                        ,'minor_reason__minor_reason_desc','total_qty','pending_qty','pending_ccr_qty','allocated_fg','route','route__route_name','ccr','ccr__ccr_code','customer__cust_name',
                        'customer__cust_code','expected_due_date','computed_dd','order_stage','item__item_description',
                        'delay_days','pre_order_buffer_size','post_order_buffer_size','market_based_order_type','plant__plant_name',
                        'order_attributes','line_order_attributes','computed_line_attributes' , 'item__item_type__item_type_id','plant__plant_id'
                        ).order_by('-bpp','order_id')
            logger.info('Fetched the MTO Order data')
            
            order_data = DataPermissionFilterForOrderData(order_data,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            if not order_data:
                return api_response(msg="There is no order available for release",status_code=status.HTTP_200_OK)

            # Applying the filter if the filter data body is present
            order_data = filter_order_data_by_params(order_data,filter_data)
            if not order_data:
                return api_response(data = {}, msg="No Data found", status_code=status.HTTP_200_OK)

            route_code = [order['route'] for order in order_data]
            
            route_details = RouteDetails.objects.filter(route__in = route_code).values('route','ccr','ccr__ccr_code','ccr__ccr_name','ccr__cumulative_wip_limit')
            fol_data = FOL_Data.objects.filter(ccr__in = [data['ccr'] for data in route_details]).values('ccr','ccr__ccr_code','ccr__ccr_name','fol_end_date','stpl_in_days')
            if graph_data_param:
                fol_df   = pd.DataFrame(list(fol_data))
                route_df = pd.DataFrame(route_details)
                merged = fol_df.merge(route_df,how='left',on='ccr',suffixes=('', '_route'))
                merged['stpl_in_days'] = merged['stpl_in_days'].fillna(0)
                clean = (merged.drop_duplicates(subset='ccr__ccr_code', keep='first').set_index('ccr__ccr_code').rename(columns={'ccr__ccr_code_route': 'ccr_code','ccr__cumulative_wip_limit': 'limit',
                    'ccr__ccr_name_route': 'ccr_name','stpl_in_days': 'wip'})[['ccr_code', 'limit', 'ccr_name', 'wip']])
                ccr_release_capacity = clean.to_dict(orient='index')    
 
                # Add fol_gap per CCR
                ccr_fol_gap_mapping = get_ccr_fol_gap_mapping()
                for ccr_code, row in ccr_release_capacity.items():
                    # match CCR by code → need CCR ID mapping
                    ccr_id = route_df.loc[route_df['ccr__ccr_code'] == ccr_code, 'ccr'].values
                    row['fol_gap'] = ccr_fol_gap_mapping.get(ccr_id[0], Decimal('0.00')) if len(ccr_id) > 0 else Decimal('0.00')
                
                return api_response(data=ccr_release_capacity, msg='Data for graph', status_code=status.HTTP_200_OK)
            
            batch_size_for_item_code = MasterItemProductionBatchsize.objects.filter(item_code__in = [data['item__item_code'] for data in order_data]).values('item_code','batch_size')
            item_codes_with_batchsize = {data['item_code']: data['batch_size'] for data in batch_size_for_item_code}
            order_keys = [data['order_key'] for data in order_data]

            batchwise_production_allocation = Order_WIPDetails.objects.filter(order__in = order_keys).values('order','item_code','dept','wip_on_hand')
            if wip_for_orders is not None:
                # return  self.getWipDataForOrders(order_data,wip_for_orders,batchwise_production_allocation = batchwise_production_allocation,route_details = route_details)
                return  self.getWipDataForOrders(wip_for_orders)
            logger.info('Fetched the BOM level wise order details')
            production_order_keys = [data['order'] for data in batchwise_production_allocation]
            
            

            logger.info('Fetched the WIP data for orders')

            logger.info('Fetched the FOl data')
            logger.info('CCR limit and wip released calculated')
            result = []
            filtered_order_data = order_data.filter(order_key__in = production_order_keys)
            for order in filtered_order_data:
                combined_data = {
                        'oid': order['order_id'],
                        'ok': order['order_key'],
                        'lid': order['line_id'],
                        'bs' : item_codes_with_batchsize.get(order['item__item_code'],None),
                        'itemt': order['item__item_code'],
                        'mbot': order['market_based_order_type'],
                        'cedd': order['expected_due_date'],
                        'cdd': order['computed_dd'],
                        'pdd' : order['planned_release_date'],
                        'in': order['item__item_code'],
                        'oq': order['total_qty'],
                        'pqty' : order['pending_qty'],
                        'pcqty' : order['pending_ccr_qty'],
                        'dn': order['dept__dept_name'],
                        'pn': order['plant__plant_name'],
                        'cn': order['customer__cust_name'],
                        'rid': order['route'],
                        'rn': order['route__route_name'],
                        'dd' : order['due_date'],
                        'afg' : order['allocated_fg'],
                        'os' : order['order_stage'],
                        'dlds' : order['delay_days'],
                        'prbs' : order['pre_order_buffer_size'],
                        'pobs' : order['post_order_buffer_size'],
                        'ccr' : order['ccr__ccr_code'],
                        'cp' : order['color'],
                        'mjd' : order['major_reason__major_reason_desc'],
                        'mid' : order['minor_reason__minor_reason_desc'],
                        'bpp' : order['bpp'],
                        'itid' : order['item__item_type__item_type_id'],
                        'plid' : order['plant__plant_id'],
                        'ide' : order['item__item_description']
                }
                line_attributes = order['line_order_attributes']
                if line_attributes:
                    combined_data.update(line_attributes)
                order_attributes = order['order_attributes']
                if order_attributes:
                    combined_data.update(order_attributes)
                computed_attributes = order['computed_line_attributes']
                if computed_attributes:
                    combined_data.update(computed_attributes)
                result.append(combined_data)

            logger.info('Dynamic release required data has been generated')
            
            if export_param and not graph_data_param:
                if report_name and headers:
                    return ExcelExportData(result,report_name, eReportName.DynamicReleaseManagement.value, headers)
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

            if not graph_data_param and not export_param:
                paginator = CustomPagination()
                paginated_response_data = paginator.paginate_queryset(result, request)
                return paginator.get_paginated_response(paginated_response_data, msg="fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(data=ccr_release_capacity,msg='Data for graph',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured in the dynamic release api due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in the dynamic release api due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)

class UpdateDynamicReleaseOrderView(APIView):
    @swagger_auto_schema(
        operation_description='update the order data for the dynamic release of orders',
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                'ok',
                type=openapi.TYPE_STRING,
                description='order keys',
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
            order_keys = request.data.get('data')
            if not order_keys:
                return api_response(msg='There must be atleast one order to be updated',status_code=status.HTTP_400_BAD_REQUEST)
            today = date.today()
            order_data = OrderData.objects.filter(order_key__in = order_keys,vf_order_type = 'MTO')
            logger.info('Data fetched that need to be updated')
            
            order_data_to_be_updated = []
            for data in order_data:
                data.is_rm_released =True
                data.actual_released_date = today
                order_data_to_be_updated.append(data)
            
            fields_to_be_updated = {
                'is_rm_released',
                'actual_released_date'
            }
            with transaction.atomic():
                if order_data_to_be_updated:
                    OrderData.objects.bulk_update(order_data_to_be_updated,fields_to_be_updated)
                    
                # bm_report_view = CreateOverallBMReportView()
                # bm_report_request = request
                # bm_report_request.data['ok'] = order_keys
                # bm_report_response = bm_report_view.post(request=bm_report_request)
                # if bm_report_response.status_code != status.HTTP_200_OK:
                #     raise Exception("BM report Data saving failed") 

                fol_api_view = UpdateFOLandSTPL()
                fol_request = request
                fol_request.data['order_keys'] = order_keys
                fol_response = fol_api_view.put(request=fol_request)
                if fol_response.status_code != status.HTTP_200_OK:
                    raise Exception("FOl update data failed")
            
            return api_response(msg='The orders has been released',status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.info(f'An Exception has occured during the updation of the order data in dynamic release due to {str(ex)}')
            return api_response(msg=f'An Exception has occured during the updation of the order data in dynamic release due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)




class CalculateFOLBasedDueDateView(APIView):

    # Define the schema for a single CCR detail
    ccr_detail_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'ccrid': openapi.Schema(type=openapi.TYPE_INTEGER, example=38),
            'ccrgrp': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
            'pcQty': openapi.Schema(type=openapi.TYPE_INTEGER, example=0),
            'pos':   openapi.Schema(type=openapi.TYPE_STRING,  example="1"),
            'ol':    openapi.Schema(type=openapi.TYPE_INTEGER, example=0),
        },
        required=['ccrid', 'ccrgrp', 'pcQty', 'pos', 'ol']
    )

    # Define the schema for a single order entry
    order_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'route':      openapi.Schema(type=openapi.TYPE_STRING,
                                        example="Rapid - (01)/Carousell - (01)"),
            'ok':         openapi.Schema(type=openapi.TYPE_STRING,
                                        example="P000946_P000946"),
            'ccrdetails': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=ccr_detail_schema
            ),
        },
        required=['route', 'ok', 'ccrdetails']
    )

    # Define the top‐level schema for routeData
    route_data_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'routeData': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'orders': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=order_schema
                    )
                },
                required=['orders']
            )
        },
        required=['routeData']
    )
    
    @swagger_auto_schema(
        operation_description="FOL based due date calculation based on new route assignment",
        request_body=route_data_schema,
    )
    
    def post(self, request):
        try:
            route_orders = request.data.get('routeData')
            order_details = route_orders['orders']

            # This code will be used in phase-2

            '''
            new_route_ccr_ids = [item['ccrid'] for item in order_details[0]['ccrdetails']]
            ccr_details = {item['ccrid']: {'ccrgrp': item['ccrgrp'], 'pos': item['pos'], 'pcqty': item['pcQty'], 'ol': item['ol']} for item in order_details[0]['ccrdetails']}
           
            # assumption : order_key is unique
            order_data = OrderData.objects.select_related('item__item_type').get(order_key = order_details[0]['ok'])

            ccr_errors, valid_ccrs, ccr_details = validate_ccr_mappings(new_route_ccr_ids, order_data.item.item_type.item_type_id, ccr_details)

            # pending_ccr_qty_errors, pending_ccr_qty_details = get_pending_ccr_qty(order_data.order_key, new_route_ccr_ids)
            fol_data_errors, fol_data = get_fol_data_by_ccrids(new_route_ccr_ids)
            error_list = ccr_processing_errors(ccr_errors, fol_data_errors)
            if error_list:
                return api_response(msg=f'An Exception has occurred while processing ccr details', error = error_list,  status_code=status.HTTP_400_BAD_REQUEST)
            order_ccr_data = {}
            for ccrid in new_route_ccr_ids:
                order_ccr_data[ccrid] = {
                    'ccr' : ccrid,
                    'ccrn' : ccr_details[ccrid]['ccrn'],
                    'ccrgrp' : ccr_details[ccrid]['ccrgrp'],
                    'ol' : math.ceil(ccr_details[ccrid]['tt'] * ccr_details[ccrid]['pcqty']),
                    'pos' : ccr_details[ccrid]['pos'],
                    'pcqty' : ccr_details[ccrid]['pcqty'],
                    'folSpan' : (math.ceil((fol_data[ccrid]['fol_in_days'] * ccr_details[ccrid]['working_hrs_per_day'] * 60) + fol_data[ccrid]['occupied_qty_in_mins'])) / (ccr_details[ccrid]['working_hrs_per_day'] * 60)
                }
            max_fol_span_obj = max(order_ccr_data.values(), key=lambda x: x['folSpan'])
            working_calendar_error, latest_working_day_lno = get_latest_working_day_lno(max_fol_span_obj['ccr'], order_data.plant.plant_id)
            if working_calendar_error:
                return api_response(msg=f'An Exception has occurred while processing working calendar details', error = error_list,  status_code=status.HTTP_400_BAD_REQUEST)
            
            buffer_data_errors, order_buffer_data = get_order_buffer_data(order_data.order_key)
            if buffer_data_errors:
                return api_response(msg=f'An Exception has occurred while processing order buffer details', error = error_list,  status_code=status.HTTP_400_BAD_REQUEST)

            #  Math.ceil(latestWorkingDayLno + maxFolSpan.folSpan + (residualBuffer * prodBufferSize)) - 1
            fol_due_date_index = math.ceil(latest_working_day_lno + max_fol_span_obj['folSpan'] + (ccr_details[max_fol_span_obj['ccr']]['res_buff'] * order_buffer_data['prod'])) - 1

            fol_due_date_lno = DailyWorkingCalendar.objects.filter(
                lno=fol_due_date_index,
                ccr__ccr_id=max_fol_span_obj['ccr'],
                plant__plant_id=order_data.plant.plant_id
            ).first()
            fol_due_date = fol_due_date_lno.working_date
            customer_expected_date = ProjectionOrder.objects.filter(order_id=order_data.order_id).values_list('customer_expected_date', flat=True).first()
            fol_data_to_be_created = get_fol_data(order_data, ccr_details, order_buffer_data, valid_ccrs)
            
            expected_columns = [
                'fol_end_date',
                'fol_in_days',
                'stpl_in_days',
                'ccr_id',
                'occupied_qty_in_units',
                'occupied_qty_in_mins'
            ]
            
            fol_df = pd.DataFrame([{
                'fol_end_date': fol.fol_end_date,
                'fol_in_days': fol.fol_in_days,
                'stpl_in_days': fol.stpl_in_days,
                'ccr_id': fol.ccr.ccr_id,
                'occupied_qty_in_units': fol.occupied_qty_in_units,
                'occupied_qty_in_mins': fol.occupied_qty_in_mins
            } for fol in fol_data_to_be_created], columns=expected_columns)

            # route_details = RouteDetails.objects.filter(route__route_id__in = order_details[0]['rid']).values('route__route_id','ccr','ccr__ccr_code','ccr__ccr_name','ccr__cumulative_wip_limit')
            # fol_data = FOL_Data.objects.filter(ccr__in = [data['ccr'] for data in route_details]).values('ccr','ccr__ccr_code','ccr__ccr_name','fol_end_date','stpl_in_days')

            # Convert queryset of ccr_details to DataFrame
            ccr_data_for_route = CCRMaster.objects.filter(ccr_id__in = new_route_ccr_ids).values('ccr_id', 'ccr_code','ccr_name','cumulative_wip_limit')
            route_df = pd.DataFrame(list(ccr_data_for_route))

            # Merge FOL data with CCR details using CCR ID as key
            merged = fol_df.merge(route_df, how='left', on='ccr_id', suffixes=('', '_route'))

            # Replace missing WIP values with 0
            merged['stpl_in_days'] = merged['stpl_in_days'].fillna(0)

            # Define expected columns for final DataFrame
            expected_graph_data_columns = ['ccr_code', 'limit', 'ccr_n', 'wip']

            # Clean and reshape data for graph consumption
            if not merged.empty and 'ccr_code' in merged.columns:
                clean_graph_data = (
                    merged.drop_duplicates(subset='ccr_code', keep='first')
                    .set_index('ccr_code')
                    .rename(columns={
                        'cumulative_wip_limit': 'limit',
                        'ccr_name': 'ccr_n',
                        'stpl_in_days': 'wip'
                    })[expected_graph_data_columns]
                )
            else:
                # Create empty DataFrame with expected columns
                clean_graph_data = pd.DataFrame(columns=expected_graph_data_columns).set_index('ccr_code')

            ccr_release_capacity = clean_graph_data.to_dict(orient='index')

            # response['due_date'] = {
            #     'foldd' : fol_due_date,
            #     'crdd' : customer_expected_date
            # }
            # response['graph_data'] = ccr_release_capacity
            '''

            ccr_fol_gap, ccr_order_load = get_ccr_fol_gap(order_details[0]['rid'], order_details[0]['ccrdetails'], order_details[0]['ok'])
            response = {}
            response['ccr_fol_gap'] = ccr_fol_gap
            response['ccr_order_load'] = ccr_order_load
            return api_response(msg='Fol gap calculated based on new route successfully', data=response, status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Exception has occurred due to {str(e)}')
            return api_response({'msg': f'Exception has occurred in the Fol gap calculation view, due to {str(e)}'}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)