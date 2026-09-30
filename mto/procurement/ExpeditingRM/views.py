from collections import defaultdict
from datetime import date, timedelta
from rest_framework.views import APIView
from rest_framework import status
from mto_app.models import (BatchwiseComponentAllocation ,  ReportConfiguration , ItemMaster ,OrderData,ItemSupplierMapping)
from mto_app.common.commonfunctions import (api_response , fetch_leaf_nodes,filter_order_data_by_params , GetUserDetails, DataPermissionFilterForOrderData, get_last_successful_run_date)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

logger = logging.getLogger(__name__)

class ExpiditingRMAndSupplierView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'rm_horizon',
                openapi.IN_QUERY,
                description="Pass the horizon for collecting orders",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'supplier_horizon',
                openapi.IN_QUERY,
                description="pass the horizon for collecting suuplier data",
                type=openapi.TYPE_STRING,  # Change type as necessary
             ),
             
        ],
    
        responses= { 200 : 'Success' , 400 : 'Not Found'}
    )   
    def get(self,request):
        return self.getexpiditingrmsupplierdata(request)
    
    def put(self,request):
        return self.getexpiditingrmsupplierdata(request,method = 'PUT')

    def getexpiditingrmsupplierdata(self,request,method='GET'):    
        try:
            rm_horizon = 14
            sup_horizon = 14
            rmCount = 10
            maxAllowedHorizon = 90
            rm_flag = False
            supp_flag = False
            filter_data = request.data
            if request.GET.get('rm_horizon') is not None:
                rm_horizon = request.GET.get('rm_horizon')
                rm_flag = True
            if request.GET.get('supplier_horizon') is not None:
                sup_horizon = request.GET.get('supplier_horizon')
                supp_flag = True
            if int(rm_horizon)>maxAllowedHorizon or int(sup_horizon)>maxAllowedHorizon:
                    return api_response(msg="Data beyond 90 days cannot be shown",status_code=status.HTTP_400_BAD_REQUEST)

            run_date = get_last_successful_run_date()
            horizon_date = run_date + timedelta(days=int(rm_horizon if rm_flag else sup_horizon))
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)   
            logger.info('Permission data is fetched from the payload')

            orders = OrderData.objects.filter(planned_release_date__lte = horizon_date,planned_release_date__gte = run_date,is_rm_released = False).values('order_id','item','line_id','ccr__ccr_id',
            'customer__cust_code','customer__cust_name','plant__plant_name','item__item_description',
            'dept__dept_id','order_value','vf_order_type','item__item_code') 
            logger.info('Order data is fetched from the order data model')
            
            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            #Applying filter for orders
            orders = filter_order_data_by_params(orders,filter_data)

            order_item_codes = [order['item'] for order in orders]
            order_ids = [order['order_id'] for order in orders]
            component_item_codes = fetch_leaf_nodes()
            batchwise_component = BatchwiseComponentAllocation.objects.filter(order_id__in = order_ids,item_code__in = component_item_codes).values(
                'order_id','line_item','item_code','order_remaining')  
            logger.info('Batchwise component data is fetched based on the leaf nodes and order count in ExpiditingRmSupplierView')

            item_codes_for_desc = [batch['item_code'] for batch in batchwise_component]
            item_desc = ItemMaster.objects.filter(item_code__in = item_codes_for_desc).values('item_code','item_description')
            logger.info('Fetched the Item description form itemmaster')

            supplier_name = ItemSupplierMapping.objects.filter(item__in = item_codes_for_desc).prefetch_related('supplier').values('item','supplier__supplier_name')
            logger.info('Supplier data is fetched from the item supplier mapping')

            supplier_map = {supplier['item']: supplier['supplier__supplier_name'] for supplier in supplier_name}
            item_desc_map = {item['item_code'] : item['item_description'] for item in item_desc}
            rm_count_dict = defaultdict(int)
            unique_entries = set()

            for component in batchwise_component:
                entry = (component['order_id'], component['line_item'], component['item_code'])
                if entry not in unique_entries and component['order_remaining']>0:
                    unique_entries.add(entry)
                    rm_count_dict[component['item_code']] += 1
            sorted_item_code_dict = dict(sorted(rm_count_dict.items(), key=lambda item: item[1], reverse=True)) 
            report_config = ReportConfiguration.objects.get(report_name='ExpiditingRmView')
            logger.info('Custom data for the ExpiditingRmView is fetched in the ExpiditingRmSupplierView')

            if report_config.start:
                rmCount = int(report_config.start)
            if rmCount > len(sorted_item_code_dict):
                rmCount = len(sorted_item_code_dict)
            rm_order_count_dict = dict(list(sorted_item_code_dict.items())[:rmCount])
            response_data = {}
            response_data['rm'] = []
            response_data['supplier'] = {}
            supplier_data = {}
            for rm,value in rm_order_count_dict.items():
                rmdesc = item_desc_map.get(rm)
                data_rm = {
                    'rn' : rm,
                    'rc' : value,
                    'rd' : rmdesc
                }
                supplier = supplier_map.get(rm, None)
                if supplier is not None:
                    if supplier not in supplier_data:
                        supplier_data[supplier] = []
                    supplier_data[supplier].append({
                        rm: value
                    })
                suppliers = {}
                for supplier, items in supplier_data.items():
                    suppliers[supplier] = {list(item.keys())[0]: list(item.values())[0] for item in items}
                response_data.get('rm').append(data_rm)
                response_data['supplier'] = suppliers
            if not rm_flag and supp_flag:
                response_data.pop('rm',None)
            elif not supp_flag and rm_flag:
                response_data.pop('supplier',None)
            return api_response(data = response_data,msg="Data fetched Successfully for the ExpiditingRmSupplierView",status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred in ExpiditingRmSupplierView: {str(e)}")
            return api_response(error=f"Failed due to the exception in ExpiditingRmSupplierView {str(e)}",status_code=status.HTTP_400_BAD_REQUEST)
