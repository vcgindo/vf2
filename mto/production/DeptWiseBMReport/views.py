from mto_app.models import ( CloseTypeMaster, OrderData,BatchwiseComponentAllocation,ItemDeptMapping,Order_WIPDetails,DBRSettings,DeptMaster,BMReportRemarks,OverallBMReport,
OrderBatchDetails,BMReportAnalytics,PlantMaster )
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import ( api_response, CustomPagination, 
filter_overall_bm_report_data_by_params,DataPermissionFilter,GetUserDetails, get_order_information , get_pagewise_data,CustomExcelExport)
from django.db.models import  Sum,OuterRef, Subquery, Value, CharField, Exists
from datetime import date,datetime
from django.db import transaction
from mto_app.common.commonfunctions import  MTOPagination
from collections import defaultdict
from mto_app.utils import DBR_Settings, eReportName, eChildName, DefaultPageConfig
from django.db.models.functions import Coalesce
import pandas as pd
from ..Common.views import  BomLevelExplosionForExcelExportView

logger = logging.getLogger(__name__)

class DeptWiseBMReportView(APIView):
    pagination_class = CustomPagination
    @swagger_auto_schema(
        operation_description='Get department-wise BM report data',
        manual_parameters=[
            openapi.Parameter('avawip', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Order with full WIP', required=True),
            openapi.Parameter('analytics', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Parameters for analytics'),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data found"),
            400: openapi.Response(description="Bad request"),
        }
    )
    def get(self,request):
        return self.getDeptWiseBMreport(request)
    
    def put(self,request):
        return self.getDeptWiseBMreport(request,method = 'PUT')

    def getAnalyticsData(self, request):
        try:
            custom_color_order = ["BLACK", "RED", "YELLOW", "GREEN", "BLUE", "WHITE"]
            analytics_data = BMReportAnalytics.objects.values()
            analytic_data_map = defaultdict(lambda: defaultdict(lambda: {'tc': 0, 'yc': 0}))
            for data in analytics_data:
                type = data['type']
                color = data['color'].upper()                
                analytic_data_map[type][color]['tc'] += data.get('today_count', 0) if data.get('today_count', 0) else 0
                analytic_data_map[type][color]['yc'] += data.get('yesterday_count', 0) if data.get('yesterday_count', 0) else 0
                analytic_data_map[type]['total']['tc'] += data.get('today_count', 0) if data.get('today_count', 0) else 0
                analytic_data_map[type]['total']['yc'] += data.get('yesterday_count', 0) if data.get('yesterday_count', 0) else 0

            for type, color_data in analytic_data_map.items():
                total_tc = color_data['total']['tc']
                total_yc = color_data['total']['yc']
                color_data.pop('total')
                
                for color in color_data:
                    color_data[color]['tcp'] = round((color_data[color]['tc'] / total_tc) * 100, 2) if total_tc != 0 else 0
                    color_data[color]['ycp'] = round((color_data[color]['yc'] / total_yc) * 100, 2) if total_yc != 0 else 0
                
                sorted_colors = dict(
                    sorted(
                        color_data.items(),
                        key=lambda item: custom_color_order.index(item[0]) if item[0] in custom_color_order else float('inf')
                    )
                )
                analytic_data_map[type] = sorted_colors

            return api_response(data=analytic_data_map, msg='Data has been fetched successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            return api_response(msg=f'An Exception has occurred due to {str(e)}', status_code=status.HTTP_400_BAD_REQUEST)


    def getDeptWiseBMreport(self, request,method = 'GET'):
        try:
            headers = None
            if method == 'PUT':
                data = request.data
                headers = data.get('headers',{}) if data else None
            else:
                data = None 
            export = request.GET.get('export')
            export_param = bool(int(export)) if export else None
            
            isBomExplosion_param = request.GET.get('isBomExplosion')
            isBomExplosion = bool(int(isBomExplosion_param)) if isBomExplosion_param else False

            report_name = request.GET.get('report_name')

            all_data = request.GET.get('alldata')
            all_data_param = bool(int(all_data)) if all_data is not None else False
            wip_available = request.GET.get('avawip')
            analytics = request.GET.get('analytics')
            analytics_param = bool(int(analytics)) if analytics is not None else False
            wip_available_param = bool(int(wip_available)) if wip_available else None
            


            if analytics_param:
                return self.getAnalyticsData(request)
            
            page_number = int(request.GET.get('page', DefaultPageConfig.default_page_number.value))
            page_size = int(request.GET.get('page_size', DefaultPageConfig.default_page_size.value))

            if method == 'PUT':
                filter_data = request.data
            else:
                filter_data = None
            data_for_permission = request.data
            product_permissions,location_permissions,is_admin = GetUserDetails(data_for_permission)
            logger.info('Permission data is fetched from the payload')
            # Query the required fields from OrderData
            wip_sum_subquery = None
            if all_data_param:
                wip_sum_subquery = Order_WIPDetails.objects.filter(
                    order=OuterRef('order_key')
                ).values('order').annotate(
                    total_wip=Sum('wip_on_hand')
                ).filter(
                    total_wip__gt=0
                ).values('order')  
            else:
                wip_sum_subquery = Order_WIPDetails.objects.none()

            order_data = OverallBMReport.objects.all().annotate(in_batchwise_allocation=Exists(
                        BatchwiseComponentAllocation.objects.filter(
                            order_id=OuterRef('order_id'),
                            line_item=OuterRef('line_id')
                        )
                    ),has_wip = Exists(wip_sum_subquery)).values(
                        'order_id','line_id','order_key',  'item_code', 'plant_id',  
                        'dept_id',  'due_date','release_date',  'actual_released_date',
                        'order_entry_date','buffer_days',  'bpp', 'color',
                        'delay_days','need_confirmation',  'major_r_desc',  'minor_r_desc', 
                        'pending_qty','allocated_qty', 'route_name',  'ccr_name',  'expected_due_date',  
                        'cust_name','order_value','order_attributes',
                        'line_order_attributes','order_type', 'dept_code',  'plant_name',  
                        'route_name'  ,'item_desc','cust_code','major_r_id','minor_r_id','dept_ageing','close_type__close_type', 
                        'pending_ccr_qty', 'computed_line_attributes', 'item_attributes' ,'in_batchwise_allocation'
            ).order_by( '-bpp','-in_batchwise_allocation', 'order_id').distinct()
            

            order_data = DataPermissionFilter(order_data,product_permissions,location_permissions,is_admin)  
            logger.info('Filtered the order data based on the permissions of the user')

            if filter_data:
                order_data = filter_overall_bm_report_data_by_params(order_data,filter_data)
            
            
            if wip_available_param:
                order_data = order_data.filter(has_wip=True)
                logger.info('Filtered the order data to include only those with WIP')
            
            if not export_param:
                record_count , nop = get_order_information(order_data, page_number, page_size)
                order_data = get_pagewise_data(order_data, page_number, page_size) 
            
            logger.info('Filtered the order data to include only those with WIP')
            
            order_attr_map = {
                data['order_key']: {
                    **(data.get('order_attributes') or {}),
                    **(data.get('line_order_attributes') or {}),
                    **(data.get('item_attributes') or {}),
                    **(data.get('computed_line_attributes') or {})
                }
                for data in order_data if data.get('order_key')
            }

            if not order_data:
                return api_response(msg="There is no order  available",status_code=status.HTTP_200_OK)
            logger.info('Filtered the order data based on the filter parameters')

            order_data_df = pd.DataFrame(list(order_data))
            if order_data_df.empty:
                return api_response(msg="There is no order  available",status_code=status.HTTP_200_OK)
            
            dept_ids = order_data_df['dept_id'].unique().tolist()
            plant_ids = order_data_df['plant_id'].unique().tolist()
            order_keys = order_data_df['order_key'].unique().tolist()
            orders_plant_details = pd.DataFrame(list(PlantMaster.objects.filter(plant_id__in=plant_ids).values('plant_id', 'plant_name','plant_code')),columns = [
                'plant_id', 'plant_name', 'plant_code'
            ])
            order_data_df = order_data_df.merge(orders_plant_details, left_on='plant_id', right_on='plant_id', how='left',suffixes=('', '_plant_details'))
            order_batch_details_map = OrderBatchDetails.objects.filter(order_key__in=order_keys).values('order_key')
            order_batch_details_df = pd.DataFrame(list(order_batch_details_map) , columns=['order_key'])
            logger.info('Fetched order data')
            
            order_wip_details = Order_WIPDetails.objects.filter(order__in=order_keys).values('wip_on_hand','mfg_balance','elapsed_days','order','dept')
            logger.info('Fetched order WIP data')

            orders_with_wip = []
            order_elapsed_days_map = {}
            
            wip_data_df = pd.DataFrame(list(order_wip_details), columns = ['wip_on_hand', 'mfg_balance', 'elapsed_days', 'order', 'dept'])
            wip_data_df.rename(columns={
                'wip_on_hand': 'woh',
                'mfg_balance': 'mfg',
                'elapsed_days': 'ed'
            }, inplace=True)
            if not wip_data_df.empty:
                wip_data_df = wip_data_df.groupby('order').agg({
                    'woh': 'sum',
                    'mfg': 'sum',
                    'ed': 'sum'
                }).reset_index()

                logger.info('Fetched order WIP cumulative data')


                orders_with_wip = wip_data_df[wip_data_df['woh'] > 0]['order'].unique().tolist()
                logger.info('Order that needed to be considered are calculated')
            
            order_elapsed_days = order_wip_details.values('order', 'dept', 'elapsed_days')
            order_elapsed_days_map = {(data['order'], data['dept']): data['elapsed_days'] for data in order_elapsed_days}
            logger.info('Fetched order and department-wise elapsed days')            
            logger.info('Filtered those orders whose WIP was available')

            #collect order remarks data
            today_remark_subquery = BMReportRemarks.objects.filter(
                order=OuterRef('order'),
                added_on=date.today()
            ).order_by('-added_on').values('remark')[:1]

            latest_remark_subquery = BMReportRemarks.objects.filter(
                order=OuterRef('order'),
                added_on__lte=datetime.now()
            ).order_by('-added_on').values('remark')[:1]

            # Annotate the queryset to get today's remark and the max date remark
            remarks = BMReportRemarks.objects.filter(order__in=order_keys).values('order' ).annotate(
                today_remark=Coalesce(Subquery(today_remark_subquery, remark=CharField()), Value('')),
                latest_remark=Coalesce(Subquery(latest_remark_subquery, output_field=CharField()), Value(''))
            ).distinct()
            logger.info('Fetched today''s remark and latest remark for each order on BM report')

            remark_data_df = pd.DataFrame(list(remarks), columns=['order', 'today_remark', 'latest_remark'])
            # if not remark_data_df.empty:
            order_data_df = order_data_df.merge(remark_data_df, left_on='order_key', right_on='order', how='left')
            order_data_df.rename(columns={'today_remark': 'r', 'latest_remark': 'lr'}, inplace=True)
            
            logger.info('Merged order data with remarks data')
            
            # if not order_batch_details_df.empty:
            order_data_df = order_data_df.merge(order_batch_details_df, left_on='order_key', right_on='order_key', how='left' , suffixes=('', '_batch_details'))
            if 'order_key_batch_details' not in order_data_df.columns:
                order_data_df['order_key_batch_details'] = None
            order_data_df['ha'] = order_data_df[order_data_df['order_key_batch_details'].notnull()]['order_key_batch_details'].apply(lambda x: True if x else False)

            # if not wip_data_df.empty:
            order_data_df = order_data_df.merge(wip_data_df, left_on='order_key', right_on='order', how='left')
            logger.info('Merged order data with batch details data')
            
            column_map = {
                'bpp': 'bpp',
                'order_type': 'ot',
                'color': 'cl',
                'ccr_name': 'ccr',
                'order_id': 'oid',
                'line_id': 'lid',
                'dept_id': 'did',
                'order_key': 'ok',
                'item_code': 'ic',
                'item_desc': 'id',
                'allocated_qty': 'aq',
                'pending_qty': 'pq',
                'major_r_desc': 'maj',
                'minor_r_desc': 'min',
                'plant_name': 'pn',
                'cust_name': 'cn',
                'cust_code': 'cc',
                'due_date': 'dd',
                'expected_due_date': 'crdd',
                'release_date': 'rd',
                'actual_released_date': 'ard',
                'route_name': 'rot',
                'elapsed_days': 'ed',
                'dept_ageing': 'da',
                'r': 'r',
                'lr': 'lr',
                'close_type__close_type': 'ct',
                'pending_ccr_qty': 'pcq',
                'oq' : 'oq',
                'rm' : 'rm',
                'ha' : 'ha',
                'woh': 'woh',
                'mfg': 'mfg',
                'plant_code': 'plc'
            }
            # order_data_df.fillna(None , inplace = True)
            order_data_df['oq'] = order_data_df[['allocated_qty', 'pending_qty']].sum(axis=1)
            order_data_df['rm'] =  [[] for _ in range(len(order_data_df))]
            order_data_df = order_data_df.rename(columns=column_map)
            order_data_df = order_data_df[column_map.values()]
            order_data_df = order_data_df.astype(object).where(pd.notna(order_data_df), None)
            data_for_grid = order_data_df.to_dict(orient='records')

            for data in data_for_grid:
                data.update(order_attr_map.get(data['ok'], {}))
                elapsed_days = order_elapsed_days_map.get((data['ok'], data['did']), None)
                data['ed'] = elapsed_days            
            if export_param and not all_data_param:
                if report_name and headers:
                    order_ids = []
                    line_ids = []
                    if isBomExplosion:
                        for item in data_for_grid:
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
                            for item in data_for_grid:
                                rm_key = (item.get('oid'),item.get('lid'))
                                item['bomexplosion'] = bom_explosion_data.get(rm_key,[])

                    return CustomExcelExport(
                    data_for_grid,
                    report_name,
                    headers,
                    isGrouped=True,
                    isChildren=isBomExplosion,
                    child_element=eChildName.bomexplosion.value,
                    name_of_report_parent=eReportName.DeptWiseReport.value,
                    name_of_report_child=eReportName.bom_explosion.value
                )
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)
            
            if all_data_param and export_param:
                return api_response(data = {'result' : data_for_grid} , msg='Dept Wise data for excel export fetched successfully',status_code=status.HTTP_200_OK)
            elif all_data_param:
                return api_response(data = {'nop' : nop , 'count' : record_count , 'result' : data_for_grid},msg='Data for overall BM report fetched',status_code=status.HTTP_200_OK)
            paginator = MTOPagination()
            paginated_response_data = paginator.create_paginated_response(request , data_for_grid , nop= nop, count=record_count)
            logger.info("Dept-wise BM report data has been fetched successfully")
            return api_response(data = paginated_response_data, msg="Dept Wise data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An exception occurred while fetching details for dept-wise BM report due to {str(ex)}')
            return api_response(msg=f'An exception occurred while fetching details for dept-wise BM report due to {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)


    # def getDeptWiseBMreport_old(self, request,method = 'GET'):
    #     try:
    #         headers = None
    #         if method == 'PUT':
    #             data = request.data
    #             headers = data.get('headers',{}) if data else None
    #         else:
    #             data = None 
    #         export = request.GET.get('export')
    #         export_param = bool(int(export)) if export else None
    #         report_name = request.GET.get('report_name')

    #         all_data = request.GET.get('alldata')
    #         all_data_param = bool(int(all_data)) if all_data is not None else None
    #         wip_available = request.GET.get('avawip')
    #         analytics = request.GET.get('analytics')
    #         analytics_param = bool(int(analytics)) if analytics is not None else False
    #         wip_available_param = bool(int(wip_available)) if wip_available else None
            


    #         if analytics_param:
    #             return self.getAnalyticsData(request)
            
    #         page_number = int(request.GET.get('page'))
    #         page_size = int(request.GET.get('page_size'))

    #         if method == 'PUT':
    #             filter_data = request.data
    #         else:
    #             filter_data = None
    #         data_for_permission = request.data
    #         product_permissions,location_permissions,is_admin = GetUserDetails(data_for_permission)
    #         logger.info('Permission data is fetched from the payload')
    #         # Query the required fields from OrderData
    #         wip_exists = None
    #         if all_data_param:
    #             wip_exists = Order_WIPDetails.objects.filter(order__in = OuterRef('order_key'))
    #         else:
    #             wip_exists = Order_WIPDetails.objects.none()

    #         order_data = OverallBMReport.objects.all().annotate(in_batchwise_allocation=Exists(
    #                     BatchwiseComponentAllocation.objects.filter(
    #                         order_id=OuterRef('order_id'),
    #                         line_item=OuterRef('line_id')
    #                     )
    #                 ),has_wip = Exists(wip_exists)).values(
    #                     'order_id','line_id','order_key',  'item_code', 'plant_id',  
    #                     'dept_id',  'due_date','release_date',  'actual_released_date',
    #                     'order_entry_date','buffer_days',  'bpp', 'color',
    #                     'delay_days','need_confirmation',  'major_r_desc',  'minor_r_desc', 
    #                     'pending_qty','allocated_qty', 'route_name',  'ccr_name',  'expected_due_date',  
    #                     'cust_name','order_value','order_attributes',
    #                     'line_order_attributes','order_type', 'dept_code',  'plant_name',  
    #                     'route_name'  ,'item_desc','cust_code','major_r_id','minor_r_id','dept_ageing','close_type__close_type', 
    #                     'pending_ccr_qty', 'computed_line_attributes', 'item_attributes' ,'in_batchwise_allocation'
    #         ).order_by( '-bpp','-in_batchwise_allocation', 'order_id').distinct()
            

    #         order_data = DataPermissionFilter(order_data,product_permissions,location_permissions,is_admin)  
    #         logger.info('Filtered the order data based on the permissions of the user')

    #         if filter_data:
    #             order_data = filter_overall_bm_report_data_by_params(order_data,filter_data)
            
    #         record_count , nop = getOrderInformation(order_data, page_number, page_size)

    #         order_data = getPageWiseData(order_data, page_number, page_size) 
    #         logger.info('Filtered the order data to include only those with WIP')
            
    #         if wip_available_param:
    #             order_data = order_data.filter(has_wip=True)
    #             logger.info('Filtered the order data to include only those with WIP')
            
    #         order_attr_map = {
    #             data['order_key']: {
    #                 **(data.get('order_attributes') or {}),
    #                 **(data.get('line_order_attributes') or {}),
    #                 **(data.get('item_attributes') or {}),
    #                 **(data.get('computed_line_attributes') or {})
    #             }
    #             for data in order_data if data.get('order_key')
    #         }

    #         if not order_data:
    #             return api_response(msg="There is no order  available",status_code=status.HTTP_200_OK)
    #         logger.info('Filtered the order data based on the filter parameters')

    #         order_data_df = pd.DataFrame(list(order_data))
    #         if order_data_df.empty:
    #             return api_response(msg="There is no order  available",status_code=status.HTTP_200_OK)
            
    #         dept_ids = order_data_df['dept_id'].unique().tolist()
    #         plant_ids = order_data_df['plant_id'].unique().tolist()
    #         order_keys = order_data_df['order_key'].unique().tolist()
    #         order_batch_details_map = OrderBatchDetails.objects.filter(order_key__in=order_keys).values('order_key')
    #         order_batch_details_df = pd.DataFrame(list(order_batch_details_map) , columns=['order_key'])
    #         logger.info('Fetched order data')
            
    #         order_wip_details = Order_WIPDetails.objects.filter(order__in=order_keys).values('wip_on_hand','mfg_balance','elapsed_days','order','dept')
    #         logger.info('Fetched order WIP data')

    #         orders_with_wip = []
    #         order_elapsed_days_map = {}
            
    #         wip_data_df = pd.DataFrame(list(order_wip_details), columns = ['wip_on_hand', 'mfg_balance', 'elapsed_days', 'order', 'dept'])
    #         wip_data_df.rename(columns={
    #             'wip_on_hand': 'woh',
    #             'mfg_balance': 'mfg',
    #             'elapsed_days': 'ed'
    #         }, inplace=True)
    #         if not wip_data_df.empty:
    #             wip_data_df = wip_data_df.groupby('order').agg({
    #                 'woh': 'sum',
    #                 'mfg': 'sum',
    #                 'ed': 'sum'
    #             }).reset_index()

    #             logger.info('Fetched order WIP cumulative data')


    #             orders_with_wip = wip_data_df[wip_data_df['woh'] > 0]['order'].unique().tolist()
    #             logger.info('Order that needed to be considered are calculated')
            
    #         order_elapsed_days = order_wip_details.values('order', 'dept', 'elapsed_days')
    #         order_elapsed_days_map = {(data['order'], data['dept']): data['elapsed_days'] for data in order_elapsed_days}
    #         logger.info('Fetched order and department-wise elapsed days')            
    #         # if wip_available_param:
               
    #             # for data in order_wip_details:
    #             #     if data['order'] not in wip_data:
    #             #         wip_data[data['order']] = {
    #             #             'woh': 0,
    #             #             'mfg': 0,
    #             #             'ed': 0
    #             #         }
    #             #     wip_data[data['order']]['woh'] += data['wip_on_hand'] if data['wip_on_hand'] else 0
    #             #     wip_data[data['order']]['mfg'] += data['mfg_balance'] if data['mfg_balance'] else 0
    #             #     wip_data[data['order']]['ed'] += data['elapsed_days'] if data['elapsed_days'] else 0
    #             # logger.info('Fetched order WIP cumulative data')

    #             # for order_key,values in wip_data.items():
    #             #     if values.get('woh') > 0:
    #             #         orders_with_wip.append(order_key)
    #             # logger.info('Order that needed to be considered are calculated')

    #         # if wip_available_param:
    #         #     filter_condition = {'order_key__in': orders_with_wip}
    #         # else:
    #         #     filter_condition = {}
            
    #         # item_desc_map = {data['item_code'] : data['item_description'] for data in ItemMaster.objects.values('item_code','item_description')}
            
    #         # order_data = order_data.filter(**filter_condition)
    #         logger.info('Filtered those orders whose WIP was available')

    #         #collect order remarks data
    #         order_remarks_map = {}
    #         today_remark_subquery = BMReportRemarks.objects.filter(
    #             order=OuterRef('order'),
    #             added_on=date.today()
    #         ).order_by('-added_on').values('remark')[:1]

    #         latest_remark_subquery = BMReportRemarks.objects.filter(
    #             order=OuterRef('order'),
    #             added_on__lte=datetime.now()
    #         ).order_by('-added_on').values('remark')[:1]

    #         # Annotate the queryset to get today's remark and the max date remark
    #         remarks = BMReportRemarks.objects.filter(order__in=order_keys).values('order' ).annotate(
    #             today_remark=Coalesce(Subquery(today_remark_subquery, remark=CharField()), Value('')),
    #             latest_remark=Coalesce(Subquery(latest_remark_subquery, output_field=CharField()), Value(''))
    #         ).distinct()
    #         logger.info('Fetched today''s remark and latest remark for each order on BM report')

    #         # remark_data = list(remarks)
    #         # for data in remark_data:
    #         #     if data['order'] not in order_remarks_map:
    #         #         order_remarks_map[data['order']] = {
    #         #             'r':  data['today_remark'],
    #         #             'lr': data['latest_remark']
    #         #         }
    #         # logger.info('created order wise remarks dictionary')

    #         remark_data_df = pd.DataFrame(list(remarks), columns=['order', 'today_remark', 'latest_remark'])
    #         # if not remark_data_df.empty:
    #         order_data_df = order_data_df.merge(remark_data_df, left_on='order_key', right_on='order', how='left')
    #         order_data_df.rename(columns={'today_remark': 'r', 'latest_remark': 'lr'}, inplace=True)
            
    #         logger.info('Merged order data with remarks data')
            
    #         # if not order_batch_details_df.empty:
    #         order_data_df = order_data_df.merge(order_batch_details_df, left_on='order_key', right_on='order_key', how='left' , suffixes=('', '_batch_details'))
    #         if 'order_key_batch_details' not in order_data_df.columns:
    #             order_data_df['order_key_batch_details'] = None
    #         order_data_df['ha'] = order_data_df[order_data_df['order_key_batch_details'].notnull()]['order_key_batch_details'].apply(lambda x: True if x else False)

    #         # if not wip_data_df.empty:
    #         order_data_df = order_data_df.merge(wip_data_df, left_on='order_key', right_on='order', how='left')
    #         logger.info('Merged order data with batch details data')
            
    #         column_map = {
    #             'bpp': 'bpp',
    #             'order_type': 'ot',
    #             'color': 'cl',
    #             'ccr_name': 'ccr',
    #             'order_id': 'oid',
    #             'line_id': 'lid',
    #             'dept_id': 'did',
    #             'order_key': 'ok',
    #             'item_code': 'ic',
    #             'item_desc': 'id',
    #             'allocated_qty': 'aq',
    #             'pending_qty': 'pq',
    #             'major_r_desc': 'maj',
    #             'minor_r_desc': 'min',
    #             'plant_name': 'pn',
    #             'cust_name': 'cn',
    #             'cust_code': 'cc',
    #             'due_date': 'dd',
    #             'expected_due_date': 'crdd',
    #             'release_date': 'rd',
    #             'route_name': 'rot',
    #             'elapsed_days': 'ed',
    #             'dept_ageing': 'da',
    #             'r': 'r',
    #             'lr': 'lr',
    #             'close_type__close_type': 'ct',
    #             'pending_ccr_qty': 'pcq',
    #             'oq' : 'oq',
    #             'rm' : 'rm',
    #             'ha' : 'ha',
    #             'woh': 'woh',
    #             'mfg': 'mfg'
    #         }
    #         # order_data_df.fillna(None , inplace = True)
    #         order_data_df['oq'] = order_data_df[['allocated_qty', 'pending_qty']].sum(axis=1)
    #         order_data_df['rm'] =  [[] for _ in range(len(order_data_df))]
    #         order_data_df = order_data_df.rename(columns=column_map)
    #         order_data_df = order_data_df[column_map.values()]
    #         order_data_df = order_data_df.astype(object).where(pd.notna(order_data_df), None)
    #         data_for_grid = order_data_df.to_dict(orient='records')

    #         for data in data_for_grid:
    #             data.update(order_attr_map.get(data['ok'], {}))
    #             elapsed_days = order_elapsed_days_map.get((data['ok'], data['did']), None)
    #             data['ed'] = elapsed_days


    #         # data_for_grid = []
    #         # for order in order_data:
    #         #     wip = wip_data.get(order['order_key'], {})
    #         #     elapsed_days = order_elapsed_days_map.get((order['order_key'], order['dept_id']), None)
    #         #     order_remarks = order_remarks_map.get(order['order_key'],{})
    #         #     order_batch_details = order_batch_details_map.get(order['order_key'],{})
    #         #     high_ageing_dept_flag = False
    #         #     if order_batch_details:
    #         #         high_ageing_dept_flag = True
    #         #     order_qty = 0
    #         #     if order.get('allocated_qty') and order.get('pending_qty'):
    #         #         order_qty = (order.get('allocated_qty',0) + order.get('pending_qty',0))  
    #         #     elif order.get('allocated_qty'):
    #         #         order_qty = order.get('allocated_qty')
    #         #     else:
    #         #         order_qty= order.get('pending_qty')
    #         #     combined_data = {
    #         #         'bpp': order['bpp'],
    #         #         'ot': order['order_type'],
    #         #         'cl' : order['color'],
    #         #         'ccr' : order['ccr_name'],
    #         #         'oid': order['order_id'],
    #         #         'lid': order['line_id'],
    #         #         'did' : order['dept_id'],
    #         #         'ok': order['order_key'],
    #         #         'ic': order['item_code'],
    #         #         'id': order['item_desc'],
    #         #         'oq': order_qty,
    #         #         'maj' : order['major_r_desc'],
    #         #         'min' : order['minor_r_desc'],
    #         #         'woh': wip.get('woh', 0),
    #         #         'mfg': wip.get('mfg', 0),
    #         #         'td': dept_names_map.get(order['dept_id'],None) if order['dept_id'] else None,
    #         #         'pn': order['plant_name'] if order['plant_name'] else None,
    #         #         'cn': order['cust_name'] if order['cust_name'] else None,
    #         #         'pn': order['plant_name'] if order['plant_name'] else None,
    #         #         'cc': order['cust_code'] if order['cust_code'] else None,
    #         #         'dd': order['due_date'],
    #         #         'crdd': order['expected_due_date'],
    #         #         'rd': order['release_date'],
    #         #         'rot': order['route_name'] if order['route_name'] else None,
    #         #         'ed': wip.get('ed',0),
    #         #         'ha' : high_ageing_dept_flag,
    #         #         'da': order['dept_ageing'],
    #         #         'r' : order_remarks.get('r',None),
    #         #         'lr' : order_remarks.get('lr',None),
    #         #         'ct' : order['close_type__close_type'],
    #         #         'pcq' : order['pending_ccr_qty'],
    #         #         'plc' : plant_names_map.get(order['plant_id'],None) if order['plant_id'] else None,
    #         #         'rm': []
    #         #     }
    #         #     line_attribute = order['line_order_attributes']
    #         #     if line_attribute:
    #         #         combined_data.update(line_attribute)
    #         #     order_attribute = order['order_attributes']
    #         #     if order_attribute:
    #         #         combined_data.update(order_attribute)
    #         #     computed_attribute = order['computed_line_attributes']
    #         #     if computed_attribute:
    #         #         combined_data.update(computed_attribute)
    #         #     item_attributes = order['item_attributes']
    #         #     if item_attributes:
    #         #         combined_data.update(item_attributes)
    #         #     data_for_grid.append(combined_data)
    #         # if filter_data is not None :
    #         #     data_for_grid = filter_attribute_data_by_params(data_for_grid, filter_data)
            
            
    #         if export_param and not all_data_param:
    #             if report_name and headers:
    #                 return ExcelExportData(data_for_grid,report_name,headers)
    #             else:
    #                 return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)
    #         if all_data_param:
    #             return api_response(data = {'nop' : nop , 'count' : record_count , 'result' : data_for_grid},msg='Data for overall BM report fetched',status_code=status.HTTP_200_OK)
    #         paginator = MTOPagination()
    #         paginated_response_data = paginator.create_paginated_response(request , data_for_grid , nop= nop, count=record_count)
    #         logger.info("Dept-wise BM report data has been fetched successfully")
    #         return api_response(data = paginated_response_data, msg="Dept Wise data fetched successfully", status_code=status.HTTP_200_OK)
    #     except Exception as ex:
    #         logger.info(f'An exception occurred while fetching details for dept-wise BM report due to {str(ex)}')
    #         return api_response(msg=f'An exception occurred while fetching details for dept-wise BM report due to {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)


class DepartmentWiseWIPForOrdersView(APIView):
    @swagger_auto_schema(
        operation_description='Get WIP data for specific orders dept wise',
        manual_parameters=[
            openapi.Parameter(
                'ok', 
                openapi.IN_QUERY, 
                type=openapi.TYPE_ARRAY, 
                items=openapi.Items(type=openapi.TYPE_STRING),
                description='Array of order keys'
            )
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            400: openapi.Response(description="Bad request"),
        }
    )
    def get(self, request):
        return self.getdeptwisewipdata(request)

    def post(self, request):
        return self.getdeptwisewipdata(request, method='PUT')

    def getdeptwisewipdata(self,request,method='GET'):
        try:
            if method == 'GET':
                order_keys = request.GET.getlist('ok')
            elif request.POST:
                order_keys = request.POST.get('ok')
            else:
                order_keys = request.data
                
            if not order_keys:
                return api_response('There order keys cannot be null',status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            order_data = OverallBMReport.objects.filter(order_key__in = order_keys).values('order_key','allocated_qty','line_id')
            logger.info('Fetched order data')

            order_qty_map = {data['order_key'] : data for data in order_data}
            order_wip = Order_WIPDetails.objects.filter(order__in = order_keys).values('dept','item_code','order','wip_on_hand','mfg_balance','entered_on','exited_on','dept__dept_name')
            logger.info('Fetched order wip data')

            logger.info('Fetched dept to next dept mapping data')

            dept_wise_wip = {}
            for data in order_wip:
                order_dt = order_qty_map.get(data['order'],{})
                if data['order'] not in dept_wise_wip:
                    dept_wise_wip[data['order']] = {}
                if 'total_qty' not in dept_wise_wip[data['order']]:
                    dept_wise_wip[data['order']]['tq'] = order_dt.get('allocated_qty',0)
                    dept_wise_wip[data['order']]['li'] = order_dt.get('line_id',None)
                if data['dept__dept_name'] not in dept_wise_wip[data['order']]:
                    dept_wise_wip[data['order']][data['dept__dept_name']] = {
                        'woh' : 0,
                        'mfg' : 0,
                        'int' : 0,
                        'out' : 0
                    }
                dept_wise_wip[data['order']][data['dept__dept_name']]['int'] = data['entered_on']
                dept_wise_wip[data['order']][data['dept__dept_name']]['out'] = data['exited_on']
                dept_wise_wip[data['order']][data['dept__dept_name']]['woh'] += data['wip_on_hand']
                dept_wise_wip[data['order']][data['dept__dept_name']]['mfg'] += data['mfg_balance']

            logger.info('Assigned the out date to the parent dept of order')

            return api_response(data=dept_wise_wip,msg='dept wise wip has been fetched',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occured in getting dept wise wip due to {str(ex)}')
            return api_response(msg=f'An Exception has occured in getting dept wise wip due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)


class DeptHighAgeingView(APIView):
    @swagger_auto_schema(
        operation_description='Get department-wise BM report data',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'order_keys': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description='Array of order keys'
                ),
            },
            
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data found"),
            400: openapi.Response(description="Bad request"),
        }
    )
    def put(self,request):
        try:
            order_keys_data = request.data
            today = date.today()
            data_for_dept_ageing = OrderBatchDetails.objects.filter(order_key__in = order_keys_data).values('order_key','item_code','batch_no','date_of_posting')
            logger.info("High ageing details for the order has been fetched")

            order_keys = [data['order_key'] for data in data_for_dept_ageing]
            order_info_map = {data['order_key'] : data for data in OrderData.objects.filter(order_key__in = order_keys).values('order_id','order_key','item','plant__plant_name','total_qty','line_id')}
            logger.info("order details for the order has been fetched")

            item_codes = [data['item_code'] for data in data_for_dept_ageing]
            item_dept_details = ItemDeptMapping.objects.filter(item_code__in = item_codes).values('item_code','current_dept_id')
            logger.info("Item code wise dept for the order has been fetched")

            dept_ids = [data['current_dept_id'] for data in item_dept_details]
            dept_names = {data['dept_id'] : data['dept_name'] for data in DeptMaster.objects.filter(dept_id__in = dept_ids).values('dept_id','dept_name')}
            logger.info("dept name for the dept id has been fetched")

            item_dept_mapping = {data['item_code'] : data['current_dept_id'] for data in item_dept_details}
            data = []
            for details in data_for_dept_ageing:
                order_key = details['order_key']
                order_info = order_info_map.get(order_key,None)
                line_item = None
                if order_info:
                    line_item = order_info.get('line_id')
                dept = item_dept_mapping.get(details['item_code'],None)
                if details['item_code'] is not None and dept:
                    combined_data = {
                        'oid' : order_info.get('order_id'),
                        'lid' : line_item,
                        'ok' : order_info.get('order_key'),
                        'dept' : dept_names.get(dept,dept),
                        'age' : (today - details['date_of_posting']).days if details['date_of_posting'] else 0,
                        'bn' : details['batch_no']
                    }
                    data.append(combined_data)

            logger.info("High ageing details for the order has been fetched")
            return api_response(data = data,msg='High ageing data has beem fetched successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.info(f'An Exception has occurred in high ageing data api due to {str(ex)}')
            return api_response(msg=f'An Exception has occurred in high ageing data API due to {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)

class UpdateBMReportOrdersView(APIView):

    def get_orders_to_update(self, orders, is_finished, close_type):
        orders_to_update = []
        for order in orders:
            order.is_finished = is_finished
            order.close_type = close_type
            orders_to_update.append(order)
        return orders_to_update

    @swagger_auto_schema(
        operation_description='mark bm report orders closed',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'close_type': openapi.Schema(type=openapi.TYPE_STRING, description="string value (short close or complete close) remove close type parameter during the undo operation"),
                'order_keys': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_STRING
                    )
                )
            }
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def put(self,request):
        try:
            input_params = request.data
            close_type_param = input_params.get('close_type')
            order_keys = input_params.get('order_keys')
            if not order_keys:
                return api_response(msg='order keys are required to update bm report', status_code=status.HTTP_400_BAD_REQUEST)
            is_closed_orders_from_ui = DBRSettings.objects.filter(flag = DBR_Settings.close_orders_from_ui).values_list('value', flat=True).first()
            logger.info("close orders from ui value has been fetched")
            if is_closed_orders_from_ui:
                close_type = None
                overall_bm_report_orders = OverallBMReport.objects.filter(order_key__in = order_keys).all()
                if close_type_param:
                    close_type = CloseTypeMaster.objects.get(close_type_code = close_type_param)
                    orders_to_update = self.get_orders_to_update(overall_bm_report_orders, True, close_type)
                else:
                    orders_to_update = self.get_orders_to_update(overall_bm_report_orders, False, close_type)

                fields_to_update = {
                    'is_finished',
                    'close_type_id'
                }
                with transaction.atomic():
                    OverallBMReport.objects.bulk_update(orders_to_update, fields_to_update)
                    logger.info("orders details updated successfully")
                    return api_response(msg='orders from ui closed successfully',status_code=status.HTTP_200_OK)
            else:
                return api_response(msg='Close orders from UI is not enabled',status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as ex:
            logger.info(f'An Exception has occurred in close bm report order due to {str(ex)}')
            return api_response(msg=f'An Exception has occurred in close bm report order API due to {str(ex)}', status_code=status.HTTP_400_BAD_REQUEST)
