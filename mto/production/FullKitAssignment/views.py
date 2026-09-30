
from decimal import ROUND_HALF_UP, Decimal
from functools import reduce
import math
from operator import  or_
from mto_app.models import (BatchwiseOrderAllocation, BatchwiseProductionComponentAllocation, BatchwiseProductionOrderAllocation, BatchwiseProductionSimulationComponentAllocation, 
CCRMaster,  CalculateBOMRequirement, CalculateProductionBOMRequirement,  EcoStock, ExcludedOrders, FOL_Data, CCRItemTypeMapping, FreeRMStock, OrderData, BatchwiseComponentAllocation
,RouteDetails,ItemMaster,MasterItemProductionBatchsize,DBRSettings, AllocationSequence , LineCCRDetails)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from django.db import transaction
from mto_app.common.commonfunctions import (ExcelExportData, api_response, CustomPagination, filter_order_data_by_params,get_item_batchsize
,GetUserDetails,DataPermissionFilterForOrderData,getOTIFStatusValue,DataPermissionFilter,GetUserDetails,DataPermissionFilterForOrderData , 
get_order_information , get_pagewise_data,CustomExcelExport,get_ccr_fol_gap,get_ccr_fol_gap_mapping )
from django.db.models import Q,  Sum
from mto_app.common.commonfunctions import fetch_leaf_nodes
from collections import defaultdict
from mto_app.utils import eReportName


logger = logging.getLogger(__name__)

# API to Update or process stock allocation on simulation
class StockAllocationOnSimulationView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'username',
                openapi.IN_QUERY,
                description="Pass the user name",
                type=openapi.TYPE_STRING,
                
            ),
            openapi.Parameter(
                'is_simulated',
                openapi.IN_QUERY,
                description="Pass boolean value True or False for simulation",
                type=openapi.TYPE_BOOLEAN,
            ),
        ],
        responses={200: 'Success', 404: 'Not Found'}
    )
    def post(self, request, *args, **kwargs):
        try:
            # Fetch the list of all orders from Allocation Sequence table
            orders = AllocationSequence.objects.all().values('order_id','line_id','priority','sequence').order_by('priority', 'sequence')
            logger.info('Fetched orders from Allocation Sequence table')
            
            username = request.GET.get('username')
            if not username:
                logger.error("username parameter is required")
                return api_response(error="username parameter is required", status_code=status.HTTP_400_BAD_REQUEST)
            
            is_simulated = request.GET.get('is_simulated')
            if is_simulated is None:
                logger.error("is_simulated parameter is required")
                return api_response({"error": "is_simulated parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Convert is_simulated to a boolean
            is_simulated = is_simulated.lower() in ['true', '1', 'yes']

            if is_simulated is True:
                # Fetch excluded orders for the given username
                excluded_orders = set(ExcludedOrders.objects.filter(username=username).values_list('order_id', 'line_item'))

                # Filter out the excluded orders from the orders queryset
                orders = orders.exclude(order_id__in=[eo[0] for eo in excluded_orders], line_id__in=[eo[1] for eo in excluded_orders])
                logger.info('Excluded orders from the order data')

            # Extract order_id and line_id from allocation_orders
            allocation_order_ids = orders.values_list('order_id', 'line_id')

            order_data_items = OrderData.objects.filter(
                order_id__in=[oid for oid, lid in allocation_order_ids],
                line_id__in=[lid for oid, lid in allocation_order_ids]
            ).values('order_id', 'line_id', 'item','total_qty')

            logger.info('Fetched records from Order data table')
            
            # Create a dictionary to map (order_id, line_id) to items
            order_item_map = {(item['order_id'], item['line_id']): {'item': item['item'], 'total_qty': item['total_qty']} for item in order_data_items}

            # Append the item and total qty to respective orders
            filtered_orders = []
            for order in orders:
                key = (order['order_id'], order['line_id'])
                if key in order_item_map:
                    order['item'] = order_item_map[key]['item']
                    order['total_qty'] = order_item_map[key]['total_qty']
                    filtered_orders.append(order)

            orders = filtered_orders
            logger.info('Appended item and total qty to each order')

            # Extract item codes from orders
            item_codes = [order['item'] for order in orders]
            
            # Fetch data from EcoStock
            eco_stock_data = EcoStock.objects.filter(
                item_code__in=item_codes,
                type__in=['StockInHand', 'StockInQC', 'StockInTransit']
            ).values('item_code', 'type','plant_code__plant_code','identifier').annotate(total_qty=Sum('quantity'))
            logger.info("Fetched EcoStock data")
            
            # Create a dictionary to easily access eco stock data
            eco_stock_dict = {}
            for stock in eco_stock_data:
                item_code = stock['item_code']
                stock_type = stock['type']
                total_qty = stock['total_qty']
                identifier = stock['identifier']
                plant_code = stock['plant_code__plant_code']
                
                if item_code not in eco_stock_dict:
                    eco_stock_dict[item_code] = {'sih': 0, 'sqc': 0, 'sit': 0, 'plant_code': plant_code, 'identifier': identifier}
                
                if stock_type == 'StockInHand':
                    eco_stock_dict[item_code]['sih'] = total_qty
                elif stock_type == 'StockInQC':
                    eco_stock_dict[item_code]['sqc'] = total_qty
                elif stock_type == 'StockInTransit':
                    eco_stock_dict[item_code]['sit'] = total_qty
            
            item_batch_size_map = { data['item_code'] : data['batch_size'] for data in MasterItemProductionBatchsize.objects.filter(item_code__in = item_codes).values('item_code','batch_size')}
            bom_allocation_type = DBRSettings.objects.get(flag = 'BOM_Component_Allocation_Type')
            bom_allocation_flag = bool(int(bom_allocation_type.value)) if bom_allocation_type.value else 0
            # Append eco stock data to orders
            for order in orders:
                item_code = order['item']
                if item_code in eco_stock_dict:
                    sih = eco_stock_dict.get(item_code).get('sih')
                    sqc = eco_stock_dict.get(item_code).get('sqc')
                    sit = eco_stock_dict.get(item_code).get('sit')
                    plant_code = eco_stock_dict.get('plant_code',None)
                    identifier = eco_stock_dict.get('identifier',None)
                    order['sih'] = 0
                    order['sqc'] = 0
                    order['sit'] = 0
                    if not bom_allocation_flag and order['total_qty'] is not None: #----condition for full order allocation
                        if (sih + sqc + sit) >= order['total_qty']:
                            order_qty = order['total_qty']
                            allocate_soh = min(order_qty,sih)
                            order_qty -= allocate_soh
                            order['sih'] = allocate_soh
                            sih-=allocate_soh

                            allocate_sqc = min(order_qty,sqc)
                            order_qty -= allocate_sqc
                            order['sqc'] = allocate_sqc
                            sqc-=allocate_sqc

                            allocate_sit = min(order_qty,sit)
                            order_qty -= allocate_sit
                            order['sit'] = allocate_sit
                            sit-=allocate_sit
                    else: #---condition for batch allocation
                        item_batch_size = item_batch_size_map.get(order['item'],None)
                        if item_batch_size_map:
                            stock = sih + sqc + sit
                            if order['total_qty'] is not None and (order['total_qty'] % item_batch_size) == 0:
                                if stock>0 and stock <= order['total_qty'] and stock>item_batch_size:
                                    order_batch = math.floor(stock/item_batch_size) * item_batch_size
                                    allocable_soh = min(order_batch,sih)
                                    order_batch -= allocable_soh
                                    order['sih'] = allocable_soh
                                    sih -= allocable_soh

                                    allocable_sqc = min(order_batch,sqc)
                                    order_batch -= allocable_sqc
                                    order['sqc'] = allocable_sqc
                                    sqc -= allocable_sqc

                                    allocable_sit = min(order_batch,sit)
                                    order_batch -= allocable_sit
                                    order['sit'] = allocable_sit
                                    sit -= allocable_sit
                    order['plant_code'] = plant_code
                    order['identifier'] = identifier
                    eco_stock_dict[item_code]['sih'] = sih
                    eco_stock_dict[item_code]['sqc'] = sqc
                    eco_stock_dict[item_code]['sit'] = sit
                else:
                    order.update({'sih': 0, 'sqc': 0, 'sit': 0, 'plant_code': None, 'identifier': None})
            # Prepare BatchwiseProductionOrderAllocation instances
            batchwise_orders = []

            # Delete all existing records in BatchwiseProductionOrderAllocation table
            BatchwiseProductionOrderAllocation.objects.all().delete()
            
            for order in orders:
                plant_code = order['plant_code'] if order['plant_code'] is not None else "None"
                if order['total_qty']:
                    batchwise_order = BatchwiseProductionOrderAllocation(
                        order_id=order['order_id'],
                        line_item=order['line_id'],
                        item_code=order['item'],
                        plant_code=plant_code,
                        order_qty=order['total_qty'],
                        stock_on_hand=order['sih'] if order['sih'] else 0,
                        stock_in_qc=order['sqc'],
                        stock_in_transit=order['sit'],
                        order_remaining=order['total_qty'] - order['sih'] - order['sqc'] - order['sit'],
                        identifier=order['identifier'],
                        open_po=0
                    )
                    batchwise_orders.append(batchwise_order)
            
            logger.info('Records to the Batchwise Production Order Allocation Table added successfully')

            # Bulk create BatchwiseProductionOrderAllocation instances
            with transaction.atomic():
                BatchwiseProductionOrderAllocation.objects.bulk_create(batchwise_orders, batch_size=1000)

            #Add records to the Calulcate Production BOM Requirement Table
            production_bom_requirements = self.add_bom_requirement(orders)

            #Add records to the Batchwise Production Component Allocation/Simulation Table
            final_component_item_codes = self.add_component_allocations(is_simulated,production_bom_requirements)

            logger.info('All records added/updated successfully')
            return api_response(msg='All records added successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            return api_response(msg=f'Error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)
        
    #Add records to the Calculate Production BOM Requirement Table
    def add_bom_requirement(self, orders):
        # Extract order_ids and line_items from batchwise_orders
        batchwise_order_ids = [order['order_id'] for order in orders]
        batchwise_line_items = [order['line_id'] for order in orders]

        batchwise_order_allocations = BatchwiseOrderAllocation.objects.filter(
            order_id__in=batchwise_order_ids,
            line_item__in=batchwise_line_items
        ).values('order_id', 'line_item', 'item_code', 'order_remaining')
        
        # Initialize lists to store order_id, line_item, and priority
        allocations_dict = {
            (alloc['order_id'], alloc['line_item']): alloc
            for alloc in batchwise_order_allocations
        }

        matching_orders = []
        non_matching_orders = []

        for order in orders:
            if not order['total_qty']:
                continue
            order_id = order['order_id']
            line_item = order['line_id']
            expected_order_remaining = order['total_qty'] - order['sih'] - order['sqc'] - order['sit']
            # Use the dictionary for fast lookup
            matching_allocation = allocations_dict.get((order_id, line_item))
            if expected_order_remaining >= 0:
                if matching_allocation and matching_allocation['order_remaining']>0:
                    if matching_allocation['order_remaining'] == expected_order_remaining:
                        matching_orders.append({
                            'order_id': order_id,
                            'line_item': line_item,
                            'priority': order['priority'],
                            'order_remaining': expected_order_remaining,
                            'sequence': order['sequence']
                        })
                    else:
                        # multiplier = expected_order_remaining / matching_allocation['order_remaining']
                        
                        multiplier = round(matching_allocation['order_remaining'] / expected_order_remaining,2) if expected_order_remaining !=0 else 1
                        non_matching_orders.append({
                            'order_id': order_id,
                            'line_item': line_item,
                            'priority': order['priority'],
                            'order_remaining': multiplier,
                            'sequence': order['sequence']
                        })
        # Fetch CalculateBOMRequirement objects for matching_orders and non_matching_orders
        calculate_bom_requirements = CalculateBOMRequirement.objects.filter(
            Q(order_id__in=[order['order_id'] for order in matching_orders + non_matching_orders]) &
            Q(line_item__in=[order['line_item'] for order in matching_orders + non_matching_orders])
        )
        
        # Check if calculate_bom_requirements is empty
        if not calculate_bom_requirements.exists():
            logger.info('No BOM requirements found for the given orders.')
            return []
            # return api_response(msg='No BOM requirements found for the given orders in Calculate BOM Requirement table.', status_code=status.HTTP_400_BAD_REQUEST)

        # Delete all existing records in CalculateProductionBOMRequirement table
        CalculateProductionBOMRequirement.objects.all().delete()

        # Prepare CalculateProductionBOMRequirement instances
        production_bom_requirements = []

        for bom_requirement in calculate_bom_requirements:
            for order in matching_orders:
                if order['order_id'] == bom_requirement.order_id and order['line_item'] == bom_requirement.line_item:
                    production_bom_requirement = CalculateProductionBOMRequirement(
                        srl_no=bom_requirement.srl_no,
                        order_id=bom_requirement.order_id,
                        line_item=bom_requirement.line_item,
                        parent_item_code=bom_requirement.parent_item_code,
                        plant_code=bom_requirement.plant_code,
                        component_item_code=bom_requirement.component_item_code,
                        component_requirement=bom_requirement.component_requirement,
                        bom_level=bom_requirement.bom_level,
                        prev_srl_no=bom_requirement.prev_srl_no,
                        item_srl_no=bom_requirement.item_srl_no
                    )
                    production_bom_requirement.priority = order['priority']
                    production_bom_requirement.sequence = order['sequence']
                    production_bom_requirements.append(production_bom_requirement)

            for order in non_matching_orders:
                if order['order_id'] == bom_requirement.order_id and order['line_item'] == bom_requirement.line_item:
                    production_bom_requirement = CalculateProductionBOMRequirement(
                        srl_no=bom_requirement.srl_no,
                        order_id=bom_requirement.order_id,
                        line_item=bom_requirement.line_item,
                        parent_item_code=bom_requirement.parent_item_code,
                        plant_code=bom_requirement.plant_code,
                        component_item_code=bom_requirement.component_item_code,
                        component_requirement=bom_requirement.component_requirement * order['order_remaining'],
                        bom_level=bom_requirement.bom_level,
                        prev_srl_no=bom_requirement.prev_srl_no,
                        item_srl_no=bom_requirement.item_srl_no
                    )
                    production_bom_requirement.priority = order['priority']
                    production_bom_requirement.sequence = order['sequence']
                    production_bom_requirements.append(production_bom_requirement)

        # Sort production_bom_requirements by priority and sequence
        production_bom_requirements.sort(key=lambda x: (x.priority, x.sequence))

        # Bulk create CalculateProductionBOMRequirement instances
        with transaction.atomic():
            CalculateProductionBOMRequirement.objects.bulk_create(production_bom_requirements, batch_size=1000)

        logger.info('Records to the Production BOM Requirement Table added successfully')
        return production_bom_requirements

    #Add records to the Batchwise Production/Simulation Component Allocation Table
    def add_component_allocations(self, is_simulated, production_bom_requirements):
        component_details = [
            {
                'order_id': req.order_id,
                'line_item': req.line_item,
                'srl_no' : req.srl_no,
                'item_srl_no' : req.item_srl_no,
                'plant_code': req.plant_code,
                'priority': req.priority,
                'component_item_code': req.component_item_code,
                'component_requirement': req.component_requirement,
                'sequence': req.sequence
            }
            for req in production_bom_requirements
        ]
        # Create a list of Q objects for each pair of item_code and plant_code
        q_list = [
            Q(item_code=detail['component_item_code'], plant_code__plant_code=detail['plant_code'])
            for detail in component_details
        ]

        # Combine all Q objects into a single query using OR
        if len(q_list)>0:
            combined_q = reduce(or_, q_list)
        else:
            combined_q = None
        
        if not combined_q:
            return api_response(msg=f'Component and plant does not exist while allocating bom components',status_code=status.HTTP_501_NOT_IMPLEMENTED)    
    
        # Fetch data from EcoStock
        eco_stock = EcoStock.objects.filter(
            combined_q, type__in=['StockInHand', 'StockInQC', 'StockInTransit']
        ).values('item_code', 'type', 'plant_code__plant_code', 'quantity')
        logger.info('Fetched stocks records based on stock type and plant id')

        # Create a dictionary for easier lookup and update
        eco_stock_dict = {}
        for stock in eco_stock:
            key = (stock['item_code'], stock['plant_code__plant_code'], stock['type'])
            eco_stock_dict[key] = stock['quantity']

        # Create a list of Q objects for each pair of order_id, line_item, and srl_no
        batchwise_q_list = [
            Q(item_srl_no=detail['item_srl_no'], order_id=detail['order_id'], line_item=detail['line_item'])
            for detail in component_details
        ]
        # Combine all Q objects into a single query using OR
        if len(batchwise_q_list)>0:
            batchwise_combined_q = reduce(or_, batchwise_q_list)
        else:
            batchwise_combined_q = None
        
        if not batchwise_combined_q:
            return api_response(msg='There is no components for the orders',status_code=status.HTTP_501_NOT_IMPLEMENTED)
        
        # Fetch data from BatchwiseComponentAllocation records based on order id, line item, and srl_no
        batchwise_component_allocations = BatchwiseComponentAllocation.objects.filter(
            batchwise_combined_q
        )
        logger.info('Fetched batwise component allocation records based on srl no , order and line id')
        # Delete all existing records in Batchwise ProductionComponentAllocation/SimulationComponentAllocation table
        if is_simulated is True:
            BatchwiseProductionSimulationComponentAllocation.objects.all().delete()
        else:
            BatchwiseProductionComponentAllocation.objects.all().delete()

        batchwise_comp_alloc_orders = []

        # Create a dictionary to map (order_id, line_item) to component_requirement
        component_requirement_map = {
            (detail['order_id'], detail['line_item'], detail['item_srl_no']): (detail['component_requirement'], detail['priority'], detail['sequence'])
            for detail in component_details
        }

        bom_allocation_type = DBRSettings.objects.get(flag = 'BOM_Component_Allocation_Type')
        bom_allocation_flag = bool(int(bom_allocation_type.value)) if bom_allocation_type.value else 0
        
        for comp_alloc in batchwise_component_allocations:

            # Fetch component_requirement priority and sequence using order_id, line_item, and srl_no
            component_key = (comp_alloc.order_id, comp_alloc.line_item, comp_alloc.item_srl_no)
            component_requirement, priority, sequence= component_requirement_map.get(component_key, (0, None))

            # Initialize allocated quantities
            stock_on_hand_alloc = 0
            stock_in_qc_alloc = 0
            stock_in_transit_alloc = 0

            # Allocate required quantity from eco_stock
            remaining_requirement = component_requirement
            for stock_type in ['StockInHand', 'StockInQC', 'StockInTransit']:
                stock_key = (comp_alloc.item_code, comp_alloc.plant_code, stock_type)
                if stock_key in eco_stock_dict:
                    available_qty = eco_stock_dict[stock_key]
                    if not bom_allocation_flag:
                        if remaining_requirement > 0 and available_qty > 0:
                            allocation_qty = min(remaining_requirement, available_qty)
                            if stock_type == 'StockInHand':
                                stock_on_hand_alloc += allocation_qty
                            elif stock_type == 'StockInQC':
                                stock_in_qc_alloc += allocation_qty
                            elif stock_type == 'StockInTransit':
                                stock_in_transit_alloc += allocation_qty
                            remaining_requirement -= allocation_qty
                            eco_stock_dict[stock_key] -= allocation_qty

            batchwise_comp_alloc_order = BatchwiseProductionComponentAllocation(
                srl_no=comp_alloc.srl_no,
                order_id=comp_alloc.order_id,
                line_item=comp_alloc.line_item,
                item_code=comp_alloc.item_code,
                plant_code=comp_alloc.plant_code,
                parent_code=comp_alloc.parent_code,
                bom_level=comp_alloc.bom_level,
                order_qty=component_requirement,
                stock_on_hand=stock_on_hand_alloc,
                stock_in_qc=stock_in_qc_alloc,
                stock_in_transit=stock_in_transit_alloc,
                order_remaining=remaining_requirement,
                identifier=comp_alloc.identifier,
                simulated_qty=comp_alloc.simulated_qty,
                open_po=0,
                item_srl_no=comp_alloc.item_srl_no
            )
            batchwise_comp_alloc_order.priority = priority
            batchwise_comp_alloc_order.sequence = sequence
            batchwise_comp_alloc_orders.append(batchwise_comp_alloc_order)
        
        # Sort production_bom_requirements by priority and sequence
        batchwise_comp_alloc_orders.sort(key=lambda x: (x.priority, x.sequence))
        # Bulk create BatchwiseProductionComponentAllocation instances
        with transaction.atomic():
            if is_simulated is True:
                BatchwiseProductionSimulationComponentAllocation.objects.bulk_create(batchwise_comp_alloc_orders, batch_size=1000)
            else:
                BatchwiseProductionComponentAllocation.objects.bulk_create(batchwise_comp_alloc_orders, batch_size=1000)

        logger.info('Records to the Production Component Allocation Table added successfully')

# API to Update fullkit simulation
class FullKitOnSimulationView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'username',
                openapi.IN_QUERY,
                description="Pass the user name",
                type=openapi.TYPE_STRING,

            ),
            openapi.Parameter(
                'is_type',
                openapi.IN_QUERY,
                description="Pass the type whether save or cancel",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={200: 'Success', 404: 'Not Found'}
    )
    def post(self, request, *args, **kwargs):
        try:
            username = request.GET.get('username')
            if not username:
                logger.error("username parameter is required")
                return api_response(error="username parameter is required", status_code=status.HTTP_400_BAD_REQUEST)

            is_type = request.GET.get('is_type')
            if is_type is None:
                logger.error("is_type parameter is required")
                return api_response({"error": "is_type parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

            if is_type == "Save":
                BatchwiseProductionComponentAllocation.objects.all().delete()
                simulation_components = BatchwiseProductionSimulationComponentAllocation.objects.all()

                # Prepare a list of new BatchwiseProductionComponentAllocation objects
                new_components = [
                    BatchwiseProductionComponentAllocation(
                        srl_no=component.srl_no,
                        order_id=component.order_id,
                        line_item=component.line_item,
                        item_code=component.item_code,
                        plant_code=component.plant_code,
                        parent_code=component.parent_code,
                        bom_level=component.bom_level,
                        order_qty=component.order_qty,
                        stock_on_hand=component.stock_on_hand,
                        stock_in_qc=component.stock_in_qc,
                        stock_in_transit=component.stock_in_transit,
                        order_remaining=component.order_remaining,
                        identifier=component.identifier,
                        simulated_qty=component.simulated_qty,
                        open_po=0,
                        item_srl_no=component.item_srl_no
                    )
                    for component in simulation_components
                ]

                # Bulk create new BatchwiseProductionComponentAllocation objects
                BatchwiseProductionComponentAllocation.objects.bulk_create(new_components, batch_size=1000)

                BatchwiseProductionSimulationComponentAllocation.objects.all().delete()
                logger.info('Simulation saved successfully')

            elif is_type == "Delete":
                BatchwiseProductionSimulationComponentAllocation.objects.all().delete()

                 # Delete records from ExcludedOrders where username matches the input username
                ExcludedOrders.objects.filter(username=username).delete()
                logger.info('Simulation canceled successfully')

            logger.info('Full kit simulation done')
            return api_response(msg='Full kit simulation done', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            return api_response(msg=f'Error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)

            


# Get API to fetch balance order


class GetFullKitAssignmentDataWithGraphView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'is_fullkit',
                openapi.IN_QUERY,
                description="Pass boolean value True or False for full kit",
                type=openapi.TYPE_BOOLEAN,
            ),
            openapi.Parameter(
                'load_data_after_simulation',
                openapi.IN_QUERY,
                description="Pass boolean value True or False to get value for full kits available column",
                type=openapi.TYPE_BOOLEAN,
            ),
            openapi.Parameter(
                'load_graph_data',
                openapi.IN_QUERY,
                description="Pass boolean value True or False to load graph related values",
                type=openapi.TYPE_BOOLEAN,
            ),
            openapi.Parameter(
                'export', 
                openapi.IN_QUERY, 
                type=openapi.TYPE_INTEGER, 
                description='Excel export parameters'
            ), 
            openapi.Parameter(
                'report_name', 
                openapi.IN_QUERY, 
                type=openapi.TYPE_STRING, 
                description='report name parameter'
            ),
        ],
        responses={200: 'Success', 404: 'Not Found'}
    )
    def get(self,request):
        return self.getFullkitAssignmentData(request)
    
    def put(self,request):
        return self.getFullkitAssignmentData(request,method = 'PUT')

    def getFullkitAssignmentData(self, request,method = 'GET'):
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

            is_fullkit = request.GET.get('is_fullkit')
            load_data_after_simulation = request.GET.get('load_data_after_simulation')
            load_graph_data = request.GET.get('load_graph_data')
            filter_data = request.data
            
            if is_fullkit is None and load_data_after_simulation is None:
                logger.error("is_fullkit and load_data_after_simulation parameters are required")
                return api_response({"error": "is_fullkit and load_data_after_simulation parameters are required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Convert input params to a booleanitem , total_qty, color and due due from 
            is_fullkit = is_fullkit.lower() in ['true', '1', 'yes']
            load_data_after_simulation = load_data_after_simulation.lower() in ['true', '1', 'yes']
            load_graph_data = load_graph_data.lower() in ['true', '1', 'yes', 'false']
            
            excluded_orders = ExcludedOrders.objects.values('line_item','order_id')
            excluded_order_ids = [data['order_id'] for data in excluded_orders]
            exluded_line_ids = [data['line_item'] for data in excluded_orders]
            product_permissions,location_permissions,is_admin = GetUserDetails(filter_data)
            logger.info('Permission data is fetched from the payload')
            # Fetch necessary fields using only
            orders = OrderData.objects.exclude(order_id__in = excluded_order_ids,line_id__in = exluded_line_ids).filter(is_rm_released=False,route__isnull = False).only('order_id', 'line_id').values('order_id', 'line_id', 'item',
             'total_qty', 'color', 'due_date','route',
             'route__route_name',
             'order_entry_date','plant','plant__plant_name','order_key','customer__cust_code','customer__cust_name',
             'dept__dept_id','vf_order_type','order_value','ccr__ccr_id','item__item_description','item__item_code', 'item__item_type__item_type_id'
            )
            logger.info('Fetched Orders data records')
            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            orders = filter_order_data_by_params(orders,filter_data)

            # Create a dictionary for quick lookups
            orders_dict = {(order['order_id'], order['line_id']): order for order in orders}

            # Fetch item descriptions from ItemMaster based on item codes from orders
            all_item_codes = set(order['item'] for order in orders)
            sku_descriptions = {sku['item_code']: sku['item_description'] for sku in ItemMaster.objects.filter(item_code__in=all_item_codes).values('item_code', 'item_description')}
            logger.info("Fetched SKU descriptions from ItemMaster")

            # Call the common function to fetch leaf nodes (RM present at leaf node)
            leaf_item_codes = fetch_leaf_nodes()

            order_id_list = [order['order_id'] for order in orders]
            line_id_list = [order['line_id'] for order in orders]

            # Dictionary to store cumulative data
            cumulative_data = defaultdict(lambda: {'cum_ord_qty': 0, 'cum_rem_qty': 0,'stock_on_hand': 0,'stock_in_qc':0,'stock_in_transit':0})

            # Process in batches
            batch_size = 1000
            total_orders = len(order_id_list)
            allocation_pairs = set()

            with transaction.atomic():
                for start in range(0, total_orders, batch_size):
                    end = start + batch_size
                    batchwise_allocations = BatchwiseProductionComponentAllocation.objects.filter(
                        order_id__in=order_id_list[start:end],
                        line_item__in=line_id_list[start:end],
                        item_code__in=leaf_item_codes
                    ).only('order_id', 'line_item', 'item_code','order_qty', 'order_remaining', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit').values('order_id', 'line_item', 'item_code', 'order_qty', 'order_remaining', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit')
    
                    for allocation in batchwise_allocations:
                        key = (allocation['order_id'], allocation['line_item'])
                        cumulative_data[key]['cum_ord_qty'] += allocation['order_qty']
                        cumulative_data[key]['cum_rem_qty'] += allocation['order_remaining']
                        cumulative_data[key]['stock_on_hand'] += allocation.get('stock_on_hand', 0)
                        cumulative_data[key]['stock_in_qc'] += allocation.get('stock_in_qc', 0)
                        cumulative_data[key]['stock_in_transit'] += allocation.get('stock_in_transit', 0)
                        allocation_pairs.add((allocation['order_id'], allocation['line_item']))

            logger.info("Fetched Batchwise Component Allocations data")

            # Fetch data from BatchwiseProductionOrderAllocation based on the pairs from batchwise_allocations
            filter_conditions = Q()
            for order_id, line_item in allocation_pairs:
                filter_conditions |= Q(order_id=order_id, line_item=line_item)

            order_allocation_data = BatchwiseProductionOrderAllocation.objects.filter(
                filter_conditions
            ).only('order_id', 'line_item', 'order_remaining').values('order_id', 'line_item', 'order_remaining')

            logger.info('Fetched batchwise production order data')

            bom_requirement_data = CalculateProductionBOMRequirement.objects.filter(
                filter_conditions
            ).only('order_id', 'line_item', 'component_requirement','component_item_code').values('order_id', 'line_item', 'component_requirement','component_item_code')

            logger.info('Fetched calculate production BOM requirement data')

            # Calculate batch size
            batch_size_data = get_item_batchsize(all_item_codes)

            logger.info('Calculated batch size based on orderid and line item')

            # Calculate kit status
            griddata  = []
            added_combinations = set()
            for (order_id, line_item), data in cumulative_data.items():
                if (order_id, line_item) in added_combinations:
                    continue  # Skip if combination already added

                cum_ord_qty = data['cum_ord_qty']
                cum_rem_qty = data['cum_rem_qty']
                allocation = data['stock_on_hand'] + data['stock_in_qc'] + data['stock_in_transit']
                
                if cum_ord_qty == cum_rem_qty:
                    kit_status = "NK"
                elif cum_rem_qty == 0:
                    kit_status = "FK"
                else:
                    kit_status = "PK"
                order_info = orders_dict.get((order_id, line_item), {})

                allocation = Decimal(allocation)  
                cum_ord_qty = Decimal(cum_ord_qty)  

                if cum_ord_qty == 0: 
                    kits_before_simulation = 0  
                else:
                    kits_before_simulation = round(order_info.get('total_qty') * (allocation / cum_ord_qty), 0) if order_info.get('total_qty') else 0
                
                if kits_before_simulation <=0 :
                    continue
                item_description = sku_descriptions.get(order_info.get('item'), "Description not found")
                item_code = order_info.get('item')
                batch_size = batch_size_data.get((item_code), 1)
                griddata.append({
                    'on': order_id,
                    'li': line_item,
                    'ks': kit_status,
                    'ic': order_info.get('item'),
                    'ok' : order_info.get('order_key',None),
                    'plid' : order_info.get('plant'),
                    'pn' : order_info.get('plant__plant_name'),
                    'oq': order_info.get('total_qty'),
                    'cp': order_info.get('color'),
                    'odd': order_info.get('due_date'),
                    'r': order_info.get('route'),
                    'rn': order_info.get('route__route_name'),
                    'id': item_description,
                    'ord': order_info.get('order_entry_date'),
                    'bs': batch_size,
                    'kbs': kits_before_simulation,
                    'fka': kits_before_simulation,
                    'itid': order_info.get('item__item_type__item_type_id')
                })
                added_combinations.add((order_id, line_item))
            griddata.sort(key=lambda x: (x['ks'] != 'FK', x['on'], x['li']))
            # Create a route dictionary based on order_id and line_id to fetch ccr ids
            route_dict = {(data['on'], data['li']): data['r'] for data in griddata}

            # Fetch all ccr_ids grouped by route in one query
            distinct_routes = set(route_dict.values())
            route_ccr_pairs = RouteDetails.objects.filter(route__in=distinct_routes).values('route', 'ccr_id').distinct()

            # Map ccr_ids to their corresponding routes
            ccr_ids_by_route = defaultdict(list)
            for pair in route_ccr_pairs:
                ccr_ids_by_route[pair['route']].append(pair['ccr_id'])

            # Append the corresponding ccr_ids to each object in griddata
            for data in griddata:
                route = route_dict.get((data['on'], data['li']))
                data['ccr_ids'] = ccr_ids_by_route.get(route, []) if route else []

            if load_data_after_simulation is not None:
                if load_data_after_simulation:
                    batch_size = 1000
                    total_orders = len(order_id_list)
                    simulation_allocation_pairs = set()
                    full_kit_value = {}

                    with transaction.atomic():
                        for start in range(0, total_orders, batch_size):
                            end = start + batch_size
                            batchwise_simulation_alloc = BatchwiseProductionSimulationComponentAllocation.objects.filter(
                                order_id__in=order_id_list[start:end],
                                line_item__in=line_id_list[start:end],
                                item_code__in=leaf_item_codes
                            ).only('order_id', 'line_item', 'item_code', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit','order_qty').values('order_id', 'line_item', 'item_code', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit','order_qty')
                            for simulation_allocation in batchwise_simulation_alloc:
                                key = (simulation_allocation['order_id'], simulation_allocation['line_item'])
                                if key not in full_kit_value:
                                    full_kit_value[key] = {'stock_on_hand': 0, 'stock_in_qc': 0, 'stock_in_transit': 0,'order_qty' : 0}
                                full_kit_value[key]['stock_on_hand'] += simulation_allocation.get('stock_on_hand', 0)
                                full_kit_value[key]['stock_in_qc'] += simulation_allocation.get('stock_in_qc', 0)
                                full_kit_value[key]['stock_in_transit'] += simulation_allocation.get('stock_in_transit', 0)
                                full_kit_value[key]['order_qty'] += simulation_allocation.get('order_qty', 0)
                                simulation_allocation_pairs.add((simulation_allocation['order_id'], simulation_allocation['line_item']))
                    # Calculate full kits availability
                    calculated_full_kit_data = {}
                    for (order_id, line_item), data in full_kit_value.items():
                        order_remaining = next((item['order_remaining'] for item in order_allocation_data if item['order_id'] == order_id and item['line_item'] == line_item), 0)
                        total_allocation = data['stock_on_hand'] + data['stock_in_qc'] + data['stock_in_transit']
                        order_qty = data['order_qty']

                        if order_qty > 0:
                            calculated_value = (order_remaining  * (total_allocation/order_qty))
                            calculated_full_kit_data[(order_id, line_item)] = calculated_value
                        else:
                            calculated_full_kit_data[(order_id, line_item)] = 0

                    for kit in griddata:
                        key = (kit['on'], kit['li'])
                        
                        if key in calculated_full_kit_data:
                            full_kit_calculated = round(calculated_full_kit_data[key],0)
                            if full_kit_calculated == kit['oq']:
                                kit['ks'] = "FK"
                                kit['fka'] = full_kit_calculated

                logger.info('Fetched full kits available data based on Production Simulation table')

            if is_fullkit is not None:
                if is_fullkit:
                    griddata  = [kit for kit in griddata if kit['ks'] == 'FK']

            #Fetch graph related details
            graphdata = {'underloaded': [], 'overloaded': [], 'balanced': []}
            if load_graph_data is not None:
                if load_graph_data:
                    # Extract all unique routes from griddata 
                    unique_routes = list({kit['r'] for kit in griddata})

                    # Fetch unique ccr_id from RouteDetails
                    route_details = RouteDetails.objects.filter(route__in=unique_routes).values('ccr_id', 'route').distinct()
                    unique_ccr_ids = [data['ccr_id'] for data in route_details]
                    ccr_route_map = {data['ccr_id'] : data['route'] for data in route_details}
                    
                    # Fetch records from CCRMaster based on unique ccr_id
                    ccr_master_data = CCRMaster.objects.filter(ccr_id__in=unique_ccr_ids).values('ccr_id', 'cumulative_wip_limit', 'ccr_name', 'working_hours_per_day')
                    ccr_data_dict = {ccr['ccr_id']: {'ccr_id': ccr['ccr_id'],'cumulative_wip_limit': ccr['cumulative_wip_limit'], 'ccr_name': ccr['ccr_name'], 'working_hours_per_day': ccr['working_hours_per_day'],'route' : ccr_route_map.get(ccr['ccr_id'],None)} for ccr in ccr_master_data}

                    # Fetch stpl_in_days from FOL_Data based on unique ccr_id
                    fol_data = FOL_Data.objects.filter(ccr_id__in=unique_ccr_ids).values('ccr_id', 'stpl_in_days')
                    for fol in fol_data:
                        if fol['ccr_id'] in ccr_data_dict:
                            ccr_data_dict[fol['ccr_id']]['stpl_in_days'] = fol['stpl_in_days']

                    # Fetch touch_time_in_mins from CCRItemTypeMapping based on unique ccr_id
                    ccr_item_type_data = CCRItemTypeMapping.objects.filter(ccr_id__in=unique_ccr_ids).values('ccr_id', 'touch_time_in_mins')
                    for ccr_item_data in ccr_item_type_data:
                        if ccr_item_data['ccr_id'] in ccr_data_dict:
                            ccr_data_dict[ccr_item_data['ccr_id']]['touch_time_in_mins'] = ccr_item_data['touch_time_in_mins']

                    # Calculate quantity per day for each ccr_id
                    for ccr_id, ccr_data in ccr_data_dict.items():
                        working_hours_per_day = ccr_data.get('working_hours_per_day', 0)
                        touch_time_in_mins = ccr_data.get('touch_time_in_mins', 1)  # Default to 1 to avoid division by zero
                        ccr_data['quantity_per_day'] = (working_hours_per_day * 60) / touch_time_in_mins

                    # Fetch all route-ccr_id mappings in a single query
                    route_ccr_mapping = RouteDetails.objects.values_list('route', 'ccr_id')
                    route_ccr_dict = defaultdict(set)

                    # Populate route_ccr_dict with route-ccr_id mappings
                    for route, ccr_id in route_ccr_mapping:
                        route_ccr_dict[route].add(ccr_id)

                    # Initialize a dictionary to store total quantities for each ccr_id
                    # ccr_total_qty = defaultdict(int)

                    # # Set to track processed (route, ccr_id) combinations
                    # processed_combinations = set()

                    # for kit in griddata:
                    #     route = kit['r']
                    #     total_qty = kit['oq']
                        
                    #     # Fetch all ccr_ids associated with the current route from the pre-fetched dictionary
                    #     ccr_ids = route_ccr_dict.get(route, [])
                        
                    #     for ccr_id in ccr_ids:
                    #         # combination = (route, ccr_id)
                    #         # Only process the combination if it has not been processed before
                    #         # if combination not in processed_combinations:
                    #             ccr_total_qty[ccr_id] += total_qty
                    #             # processed_combinations.add(combination)

                    # # Add total quantity to ccr_data_dict and calculate allowed_full_kits
                    # for ccr_id, total_qty in ccr_total_qty.items():
                    #     if ccr_id in ccr_data_dict:
                    #         # Add total quantity to ccr_data_dict
                    #         ccr_data_dict[ccr_id]['total_qty'] = total_qty
                            
                    #         # Calculate allowed_full_kits
                    #         quantity_per_day = ccr_data_dict.get(ccr_id, {}).get('quantity_per_day', 1)  # Default to 1 to avoid division by zero
                    #         allowed_full_kits = total_qty / quantity_per_day
                    #         allowed_full_kits = Decimal(allowed_full_kits).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    #         ccr_data_dict[ccr_id]['allowed_full_kits'] = allowed_full_kits

                    order_keys = [kit['ok'] for kit in griddata]
                    ccr_order_loads = (
                        LineCCRDetails.objects
                        .filter(order__in=order_keys)
                        .values('ccr_id')
                        .annotate(total_load=Sum('order_load'))
                    )

                    ccr_order_load = {row['ccr_id']: row['total_load'] or 0 for row in ccr_order_loads}

                    # Add total order_load to ccr_order_load and calculate allowed_full_kits
                    for ccr_id, total_load in ccr_order_load.items():
                        if ccr_id in ccr_data_dict:
                            # Add total_load to ccr_data_dict
                            ccr_data_dict[ccr_id]['allowed_full_kits'] = total_load

                    # Remove keys from ccr_data_dict
                    for ccr_id in ccr_data_dict:
                        ccr_data_dict[ccr_id].pop('touch_time_in_mins', None)
                        ccr_data_dict[ccr_id].pop('working_hours_per_day', None)
                        ccr_data_dict[ccr_id].pop('quantity_per_day', None)
                        ccr_data_dict[ccr_id].pop('total_qty', None)

                    range_value = DBRSettings.objects.filter(flag='WIPThresholdLimit').values('value')
                    if range_value.exists():
                        range_value_str = range_value.first()['value']
                        range_value = Decimal(range_value_str)

                    # Classify ccr_data_dict objects into categories
                    underloaded = []
                    overloaded = []
                    balanced = []
                    route_load_map = {'ov' : [],'un' : [],'ba' : []}

                    ccr_fol_gap_mapping = get_ccr_fol_gap_mapping()

                    for ccr_id, data in ccr_data_dict.items():
                        allowed_full_kits = data.get('allowed_full_kits', 0)
                        cumulative_wip_limit = data.get('cumulative_wip_limit', 0) if data.get('cumulative_wip_limit') is not None else 0
                        stpl_in_days = data.get('stpl_in_days', 0)
                        route = data.get('route',None)
                        data['fol_gap'] = ccr_fol_gap_mapping.get(ccr_id,Decimal('0.00'))


                        if allowed_full_kits == 0:
                            continue 

                        # Calculate the total value
                        total_value = allowed_full_kits + stpl_in_days

                        # Calculate the deviation range based on the percentage of cumulative_wip_limit
                        deviation_range = (range_value / 100) * cumulative_wip_limit if range_value else 0
                        lower_limit = cumulative_wip_limit - deviation_range
                        upper_limit = cumulative_wip_limit + deviation_range

                        # Compare total_value with the calculated range
                        if total_value < lower_limit:
                            underloaded.append(data)
                            route_load_map['un'].append(ccr_id)
                        elif total_value > upper_limit:
                            overloaded.append(data)
                            route_load_map['ov'].append(ccr_id) 
                        else:
                            balanced.append(data)
                            route_load_map['ba'].append(ccr_id)
                           
                    
                    graphdata['underloaded'] = underloaded
                    graphdata['overloaded'] = overloaded
                    graphdata['balanced'] = balanced

            for data in griddata:
                ccr_list = data['ccr_ids']
                for ccr in ccr_list:
                    if ccr in route_load_map.get('ov', []):
                        data['ls'] = 'overaloaded'
                        break
                    elif ccr in route_load_map.get('un', []):
                        data['ls'] = 'underloaded'
                        break
                    else:
                        data['ls'] = 'balanced'
                        break
            
            griddata = sorted(griddata, key=lambda x: x['ls'], reverse=True)
            if load_graph_data:
                result = {
                    'griddata': griddata,
                    'graphdata': graphdata
                }
            else:
                result = {
                    'griddata': griddata
                }

            logger.info('Classified kit status into Underloaded, Overloaded, and Balanced categories')
            
            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(result['griddata'], request)

            if export_param:
                if report_name and headers:
                    return ExcelExportData(result['griddata'],report_name,eReportName.FullKitAssignment.value, headers)
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

            if load_graph_data:
                result_paginated = {
                    'griddata': paginated_response_data,
                    'graphdata': result['graphdata']
                }
            else:
                result_paginated = {
                    'griddata': paginated_response_data
                }

            logger.info('Fetched Full kit Assignment data successfully')
            return paginator.get_paginated_response(result_paginated, msg='Fetched Full kit Assignment data successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            return api_response(msg=f'Error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)
            
class ResetOrderView(APIView):

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'username',
                openapi.IN_QUERY,
                description="Pass the user name",
                type=openapi.TYPE_STRING,
                
            ),
        ],
        responses={200: 'Success', 404: 'Not Found'}
    )
    def delete(self, request, format=None):
        try:
            username = request.GET.get('username')
            logger.info(f"Received DELETE request with releaseDate: {username}")

            if not username:
                logger.error("releaseDate parameter is required")
                return api_response(error="releaseDate parameter is required", status_code=status.HTTP_400_BAD_REQUEST)
            
            # Delete records in FreeRMStock model
            FreeRMStock.objects.filter(username=username).delete()
            logger.info(f"Deleted records from FreeRMStock for username: {username}")

            # Delete records in ExcludedOrders model
            ExcludedOrders.objects.filter(username=username).delete()
            logger.info(f"Deleted records from ExcludedOrders for username: {username}")

            return api_response(msg='All records deleted successfully', status_code=status.HTTP_200_OK)    
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            return api_response(msg=f'Error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)

class ExcludeOrdersForFullkitAssignmentView(APIView):

    @swagger_auto_schema(
        operation_description="Add rm code and its data to free rm stock table",
        request_body = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'orders': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'on': openapi.Schema(type=openapi.TYPE_STRING, description='Order ID'),
                                'lid': openapi.Schema(type=openapi.TYPE_STRING, description='Line item'),
                            },
                            required=['on', 'lid']
                        )
                    ),
                    'username': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='Username'
                    )
                },
                required=['orders', 'username']
            ),

        responses={
            200: openapi.Response(description='All records added/updated successfully'),
            400: openapi.Response(description='Records were not found')
        }
    )
    def post(self, request, *args, **kwargs):

        try:
            # Call the common function to fetch leaf nodes
            data = request.data
            leaf_item_codes = fetch_leaf_nodes()

            with transaction.atomic():
                bulk_create_list = []
                bulk_update_list = []
                excluded_orders_list = []

                # Create a queryset for filtering based on the unique constraints
                query = Q()
                for order in data.get('orders'):
                    query |= Q(order_id=order['on'], line_item=order['lid'])

                # Fetch relevant BatchwiseComponentAllocation objects and aggregate in the query
                allocations = BatchwiseComponentAllocation.objects.filter(query, item_code__in=leaf_item_codes).values(
                    'item_code','order_id', 'line_item'
                ).annotate(
                    total_stock_on_hand=Sum('stock_on_hand'),
                    total_stock_in_qc=Sum('stock_in_qc'),
                    total_stock_in_transit=Sum('stock_in_transit')
                )
                logger.info('Fetched records and aggregated the data')

                # Create a dictionary to map allocations based on item_code
                allocations_dict = {}
                for allocation in allocations:
                    item_code = allocation['item_code']
                    username = data.get('username')
                    key = (item_code, username)
                    if key not in allocations_dict:
                        allocations_dict[key] = {
                            'total_stock_on_hand': 0,
                            'total_stock_in_qc': 0,
                            'total_stock_in_transit': 0,
                        }
                    allocations_dict[key]['total_stock_on_hand'] += allocation['total_stock_on_hand']
                    allocations_dict[key]['total_stock_in_qc'] += allocation['total_stock_in_qc']
                    allocations_dict[key]['total_stock_in_transit'] += allocation['total_stock_in_transit']

                    # Add to excluded orders list
                    excluded_orders_list.append(
                        ExcludedOrders(
                            order_id=allocation['order_id'],
                            line_item=allocation['line_item'],
                            username=data.get('username')
                        )
                    )

                # Fetch existing FreeRMStock records to check for updates
                existing_stock_records = FreeRMStock.objects.filter(
                    item_code__in=[item_code for item_code, _ in allocations_dict.keys()],
                    username=username
                )

                existing_stock_dict = {(stock.item_code, stock.username): stock for stock in existing_stock_records}

                for (item_code, username), stock in allocations_dict.items():
                    if (item_code, username) in existing_stock_dict:
                        # Update existing record
                        existing_stock = existing_stock_dict[(item_code, username)]
                        existing_stock.stock_on_hand = stock['total_stock_on_hand']
                        existing_stock.stock_in_qc = stock['total_stock_in_qc']
                        existing_stock.stock_in_transit = stock['total_stock_in_transit']
                        bulk_update_list.append(existing_stock)
                    else:
                        # Create new record
                        bulk_create_list.append(
                            FreeRMStock(
                                item_code=item_code,
                                stock_on_hand=stock['total_stock_on_hand'],
                                stock_in_qc=stock['total_stock_in_qc'],
                                stock_in_transit=stock['total_stock_in_transit'],
                                username=data.get('username')
                            )
                        )

                # Bulk update existing FreeRMStock objects
                FreeRMStock.objects.bulk_update(bulk_update_list, ['stock_on_hand', 'stock_in_qc', 'stock_in_transit'])

                # Bulk create new FreeRMStock objects
                FreeRMStock.objects.bulk_create(bulk_create_list)

                # Bulk create excluded orders
                ExcludedOrders.objects.bulk_create(excluded_orders_list, ignore_conflicts=True)

            logger.info('All records added/updated successfully')
            return api_response(msg='All records added/updated successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            return api_response(msg=f'Error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)
 

