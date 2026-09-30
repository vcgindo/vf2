from collections import Counter, defaultdict
from datetime import date, timedelta, datetime
from functools import reduce
from operator import and_
import re
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status
from mto_app.common.commonfunctions import filter_attribute_data_by_params , CustomExcelExport
from mto_app.models import (AdditionalStock, AllocationSequence, BatchwiseProcurementComponentAllocation, BatchwiseProductionComponentAllocation, CCRMaster, 
DBRSettings, DaywiseCoverageHistory, DaywiseCoverageRMDetails, ExcludedOrders, FreeRMStock, MTAStockGITData, MTOLineItemData, MTOOrderData, 
MasterItemProductionBatchsize, ProjectionOrder, BOMHeader, BOMDetail, CalculateBOMRequirement, BatchwiseComponentAllocation , ProjectionOrderDetails, 
PendingOrder, BatchwiseOrderAllocation, EcoStock, ReportConfiguration , OrderHistory , ItemMaster ,OrderData,ItemSupplierMapping,ComputedOrderAttributes, 
SimulationConfiguration, SimulationHistory, KitAllocation , PlantMaster)
from mto_app.common.commonfunctions import (api_response , CustomPagination, fetch_leaf_nodes, sort_key,get_item_batchsize,filter_order_data_by_params, 
get_daywise_coverage_history_orders_details,ExcelExportData , sort_color_priority , GetUserDetails, DataPermissionFilterForOrderData ,
get_color_mapping, is_batchwise_allocation, get_kit_allocation_data, get_order_fullkit_value , filter_order_history_data_by_params ,
 get_order_information , get_pagewise_data , MTOPagination , from_queryset_to_polars_df, get_last_successful_run_date)
from ..serializers import BatchwiseComponentAllocationSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Prefetch,Subquery
import logging
from django.db.models import Sum, Q ,Count,CharField, Value, DecimalField, F, DateField, IntegerField, Case, When
from django.utils import timezone
from math import modf
from decimal import Decimal
from django.db import transaction
import pandas as pd
from mto_app.utils import DBR_Settings , HorizonEnum, eReportName, eChildName
import numpy as np
import itertools
from django.db.models.functions import Concat, Cast
from django.db.models import CharField
import polars as pl

logger = logging.getLogger(__name__)

class GetProdDataForRMPMCoverageView(APIView):
    pagination_class = CustomPagination

    def aggregateDataByWeek(self, week_data_dict, combined_data, week_number):
        if combined_data['soh'] == combined_data['rm_qty']:
            week_data_dict[week_number]['total_soh'] +=1 
        elif combined_data['sit']>0 and combined_data['po'] == 0 and combined_data['or'] == 0:
            week_data_dict[week_number]['total_sit'] +=1
        elif combined_data['po']>0 and combined_data['or'] == 0:
            week_data_dict[week_number]['total_po'] +=1 
        else:
            week_data_dict[week_number]['total_or'] +=1

    @swagger_auto_schema(
        operation_description='Get RMPM orderwise coverage',
        manual_parameters=[
            openapi.Parameter('graphflag',openapi.IN_QUERY,description='Flag for fetching graph data',type=openapi.TYPE_INTEGER),
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
        return self.getrmpmcoveragedata(request)
    
    def put(self,request):
        return self.getrmpmcoveragedata(request,method = 'PUT')
    
    def getrmpmcoveragedata(self, request,method = 'GET'):
        try:
            graphflag =request.GET.get('graphflag')
            graph_data_param = bool(int(graphflag)) if graphflag is not None else False
            filter_data = request.data
            export = request.GET.get('export')
            report_name = request.GET.get('report_name')
            export_param = bool(int(export)) if export is not None else False
            headers =  filter_data.get('headers',{}) if filter_data else None
            default_horizon = HorizonEnum.default_horizon.value

            run_date = get_last_successful_run_date()
            horizon_start_date = run_date + timedelta(days=default_horizon)
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')

            orders = OrderData.objects.filter(is_rm_released = False,planned_release_date__lte = horizon_start_date).values('order_id','color', 'due_date', 'bpp', 'customer__cust_code',
            'customer__cust_name','planned_release_date','plant','plant__plant_name','ccr__ccr_id','ccr__ccr_name','ccr__ccr_name','order_value','dept__dept_id','dept__dept_name',
            'ccr__ccr_group__ccr_group_id','ccr__ccr_group__ccr_group_name','ccr__ccr_group__ccr_group_code','item','item__item_code','item__item_description','line_id','total_qty').order_by('-bpp')
            logger.info('Orders fetched from the orderData')
            
            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            #Applying filters to the orderData
            orders = filter_order_data_by_params(orders,filter_data)

            order_ids = [order['order_id'] for order in orders]
            item_codes = [ord['item'] for ord in orders]


            item_batch_size_map = get_item_batchsize(item_codes)
            #fetching the leaf nodes using common fucntions
            component_item_codes = fetch_leaf_nodes()
            logger.info("Fetched projection orders")
            
            #Getting the RM quanitity from Batchwise Allocation
            batchwise_component_allocations = BatchwiseComponentAllocation.objects.filter(
                    order_id__in=order_ids,
                    line_item__in=[po['line_id'] for po in orders]
            ).values('order_id', 'line_item', 'item_code', 'order_qty','order_remaining','simulated_qty','stock_on_hand','stock_in_qc','stock_in_transit','parent_code','plant_code','open_po')
            batchwise_data_fk = {(fk['order_id'],fk['item_code']) : fk for fk in batchwise_component_allocations}

            
            bom_details = BOMDetail.objects.filter(component_item_code__in=item_codes).values(
                'component_item_code', 'bom_srl_no__parent_item_code', 'component_qty'
            )

            bom_details_dict = {}
            for data in bom_details:
                key = (data['component_item_code'],data['bom_srl_no__parent_item_code'])
                bom_details_dict[key] = data['component_qty']
            logger.info("Fetched BOMDetail data")

            # calculating the RMs for the each order and line item
            rm_allocation = {}
            allocated_dict = {}
            for items in batchwise_component_allocations:
                rm_keys = (items["order_id"],items["line_item"])
                if items["item_code"] in component_item_codes:
                    if rm_keys not in rm_allocation:
                        rm_allocation[rm_keys] = []
                        allocated_dict[rm_keys] = {
                        'total_qt': 0,
                        'total_soh': 0,
                        'total_sit': 0,
                        'total_or': 0,
                        'total_po': 0,
                    }
                    rm_allocation[rm_keys].append(
                            {
                                "rmc" : items['item_code'],
                                "oq" : items['order_qty'],
                                "soh" : items['stock_on_hand'],
                                "sit" : items['stock_in_qc'] + items['stock_in_transit'],
                                "po" : items['open_po'],
                                "or" : items['order_remaining'],
                                'rmto' : items['stock_in_qc'] + items['stock_in_transit'] + items['stock_on_hand'] 
                            }
                    )
                    allocated_dict[rm_keys]['total_qt'] += items['order_qty']
                    allocated_dict[rm_keys]['total_soh'] += items['stock_on_hand']
                    allocated_dict[rm_keys]['total_sit'] += items['stock_in_transit'] + items['stock_in_qc']
                    allocated_dict[rm_keys]['total_or'] += items['order_remaining']
                    allocated_dict[rm_keys]['total_po'] += items['open_po']
                    
            data = []
            for order in orders:
                order_id = order['order_id']
                rm_data_key = (order_id,order['line_id'])
                rm_data = rm_allocation.get(rm_data_key)
                if not rm_data:
                    continue
                combined_data = {
                    "oid" : order["order_id"],
                    "lid" : order['line_id'],
                    "ic" : order['item'],
                    "id" : order['item__item_description'],
                    "dd" : order["due_date"],
                    "rd" : order["planned_release_date"],
                    "oq" : order['total_qty'],
                    "bs" : 0,
                    "fk" : 0,
                    "cc" : order['customer__cust_code'],
                    "cn" : order['customer__cust_name'],
                    "bpp" : order["bpp"],
                    "clr" : order["color"],
                    "pid" : order['plant'],
                    "pnm" : order['plant__plant_name'],
                    "ccrid" :  order['ccr__ccr_id'],
                    "ccrname" : order['ccr__ccr_name'],
                    "ccrgrnm" : order['ccr__ccr_group__ccr_group_name'],
                    "ccrgrid":order['ccr__ccr_group__ccr_group_id'],
                    "soh" : 0,
                    "sit" : 0,
                    "po" : 0,
                    "or" : 0,
                    "rm_qty": 0

                }
                data.append(combined_data)
            for combined_data in data:
                order_id = combined_data['oid']
                rm_data_key = (order_id,combined_data['lid'])
                rm_data = rm_allocation.get(rm_data_key)

                allocation_data = allocated_dict.get(rm_data_key)
                adjusted_rmall_values = [(child['rmto'],child['rmc'],child['oq']) for child in rm_data]

                bsize,min_rm,rm_qty =  min(adjusted_rmall_values,key = lambda x:x[0]) if adjusted_rmall_values else (0,0,0)
                parent_code = next((allocation['parent_code'] for allocation in batchwise_component_allocations if allocation['item_code'] == min_rm and allocation['order_id'] == order_id), None)

                component_qty = bom_details_dict.get((min_rm,parent_code))
                #calculating the minimum batchsize in the rm

                batch_size = round((rm_qty / combined_data['oq']) * bsize,2) if combined_data['oq']!=0 and combined_data['oq'] is not None else 0
            
                combined_data['bs'] = item_batch_size_map.get(combined_data['ic'],1)
                combined_data['soh'] = allocation_data['total_soh']
                combined_data['sit'] = allocation_data['total_sit']
                combined_data['po'] = allocation_data['total_po']
                combined_data['or'] = allocation_data['total_or']
                combined_data['rm_qty'] = allocation_data['total_qt']

                fka_val = round(((allocation_data['total_soh'] + allocation_data['total_sit']) / allocation_data['total_qt']) * combined_data['oq'], 0) if allocation_data['total_qt'] > 0 and combined_data.get('oq') else 0

                #calculating the full kit availability percentage
                if combined_data['oq'] != 0 and combined_data['oq'] is not None:
                    fka_percentage = (fka_val / combined_data['oq'])*100
                else:
                    fka_percentage = 0
                combined_data['fk'] = round(fka_percentage,2)
            
            if graph_data_param:
                # Aggregate data by week
                weekly_data = []
                start_date = run_date
                end_date = horizon_start_date
                num_days = (end_date - start_date).days
                week_number_start_range = -1

                # Initialize a defaultdict to hold weekly data
                week_data_dict = defaultdict(lambda: {
                    'total_soh': 0,
                    'total_sit': 0,
                    'total_po': 0,
                    'total_or': 0,
                })

                # Iterate over the combined data once and aggregate it by week
                for combined_data in data:
                    week_number = (combined_data['rd'] - start_date).days // 7
                    if start_date <= combined_data['rd'] <= end_date:
                        self.aggregateDataByWeek(week_data_dict, combined_data, week_number)
                    elif week_number < 0:
                        self.aggregateDataByWeek(week_data_dict, combined_data, week_number_start_range)

                # Convert the aggregated week data into a list of dictionaries
                current_week_start = None
                current_week_end = None
                week_start_date = None
                week_end_date = ''
                past_orders = 'Orders With Release Date In Past'
                for week_number in range(week_number_start_range, (num_days // 7) + 1):
                    if week_number == week_number_start_range:
                        week_start_date = past_orders
                    else :
                        current_week_start = start_date + timedelta(days=week_number * 7)
                        current_week_end = current_week_start + timedelta(days=6)
                        week_start_date = (current_week_start - start_date).days
                        week_end_date = (current_week_end - start_date).days
                    week_data = {
                        'start_date': week_start_date,
                        'end_date': week_end_date,
                        'total_soh': week_data_dict[week_number]['total_soh'],
                        'total_sit': week_data_dict[week_number]['total_sit'],
                        'total_po': week_data_dict[week_number]['total_po'],
                        'shortage': week_data_dict[week_number]['total_or'],
                    }
                    weekly_data.append(week_data)
                return api_response(data=weekly_data, msg="Graph data fetched successfully", status_code=status.HTTP_200_OK)

            if export_param and (not graph_data_param):
                return ExcelExportData(data, report_name , eReportName.RMPMOrderWiseCoverage.value, headers)
            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(data, request)
            logger.info("Returning the paginated response")
            return paginator.get_paginated_response(paginated_response_data, msg='Fetched order wise coverage data', status_code=status.HTTP_200_OK)
        except Exception as e: 
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)

