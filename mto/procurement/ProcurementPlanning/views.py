from collections import  defaultdict
from datetime import date
from rest_framework.views import APIView
from rest_framework import status
from mto_app.common.commonfunctions import  CustomExcelExport
from mto_app.models import (AdditionalStock, AllocationSequence, BatchwiseProcurementComponentAllocation, BatchwiseProductionComponentAllocation, 
DBRSettings, MTAStockGITData, MasterItemProductionBatchsize, ProjectionOrder, BOMHeader, BOMDetail, CalculateBOMRequirement, BatchwiseComponentAllocation 
, ProjectionOrderDetails, PendingOrder, BatchwiseOrderAllocation, EcoStock , ItemMaster ,OrderData, 
SimulationConfiguration, SimulationHistory)
from mto_app.common.commonfunctions import (api_response , CustomPagination, fetch_leaf_nodes_with_plant, fetch_leaf_nodes,get_item_batchsize,filter_order_data_by_params, 
 sort_color_priority , GetUserDetails, DataPermissionFilterForOrderData )
from ..serializers import BatchwiseComponentAllocationSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Prefetch
import logging
from django.db.models import Sum, Q 
from django.db import transaction
from mto_app.utils import eReportName, eChildName , eVFOrderType
import pandas as pd


logger = logging.getLogger(__name__)

class ProcurementPlanningView(APIView):
    pagination_class = CustomPagination

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'releaseDate',
                openapi.IN_QUERY,
                description="Pass the release date",
                type=openapi.TYPE_STRING,
                
            ),
            openapi.Parameter(
                'ca',
                openapi.IN_QUERY,
                description='Pass the all order parameter',
                type=openapi.TYPE_INTEGER
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

    def get(self, request): 
        return self.procurementPlanningData(request) 

    def put(self,request): 
        return self.procurementPlanningData(request,method = 'PUT') 
    

    def procurementPlanningData(self, request, format=None, method = 'GET'):
        try:
            headers = None
            if method == 'PUT':
                filter_data = request.data
                headers = filter_data.get('headers',{}) if filter_data else None
            else:
                filter_data = None
            data = request.data
            export = request.GET.get('export')
            export_param = bool(int(export)) if export else None

            isChildren_param = request.GET.get('isChildren')
            isChildren = bool(int(isChildren_param)) if isChildren_param else False

            report_name = request.GET.get('report_name')

            excel_scope = request.GET.get('excel_scope')
            completely_available = request.GET.get('ca')

            if excel_scope == 'all':
                completely_available_param = None
            else:
                completely_available_param = bool(int(completely_available)) if completely_available else None
            
            release_date = request.GET.get('releaseDate')
            logger.info(f"Received GET request with releaseDate: {release_date}")

            show_all_items_flag = DBRSettings.objects.filter(flag='showAllItems').values_list('value', flat=True).first()
            if show_all_items_flag is None:
                show_all_items_flag = False  
            else:
                show_all_items_flag = bool(int(show_all_items_flag))

            product_permissions,location_permissions,is_admin = GetUserDetails(data)
            logger.info('Permission data is fetched from the payload')
            # Fetch OrderData for filter
            filters = Q(vf_order_type=eVFOrderType.MTA.value)
            if release_date:
                filters |= Q(
                    vf_order_type=eVFOrderType.MTO.value,
                    planned_release_date__lte=release_date
            )
            orders = OrderData.objects.filter(filters).values_list('order_id', 'line_id',
                'ccr__ccr_id', 'customer__cust_code', 'customer__cust_name', 'plant__plant_name', 'item__item_description',
                'dept__dept_id', 'order_value', 'vf_order_type', 'item__item_code','actual_released_date')
            
            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            if filter_data:
                orders = filter_order_data_by_params(orders, filter_data)

            
            query = Q()
            for order in orders:
                query |= Q(order_id=order[0], line_item=order[1])

            response_data = []
            if len(orders) > 0:
                # Filter ProjectionOrderData based on the extracted order_ids
                order_related_item_codes = ProjectionOrderDetails.objects.filter(query).values_list('item_code', flat=True).distinct()
                item_codes = list(set(order_related_item_codes))
                logger.info("Fetched Item codes related to orders")

                leaf_item_codes = fetch_leaf_nodes_with_plant()
                logger.info('fetched the leaf item codes for the parent items')
                # Fetch order_ids from CalculateBOMRequirement table based on final_component_item_codes
                order_id_mapping = CalculateBOMRequirement.objects.filter(query).values('component_item_code', 'order_id','line_item','plant_code')
                order_id_mapping = pd.DataFrame(order_id_mapping)
                if show_all_items_flag:
                    order_id_mapping = leaf_item_codes.merge(order_id_mapping, how='left', on=['component_item_code','plant_code'])
                else:
                    order_id_mapping = leaf_item_codes.merge(order_id_mapping, how='inner', on=['component_item_code','plant_code'])
                component_to_order_map = {}
                for _,entry in order_id_mapping.iterrows():
                    component_to_order_map.setdefault((entry['component_item_code'], entry['plant_code']), []).append((entry['order_id'], entry['line_item']))
                logger.info("Fetched Component to order map data")

                # fetch children(order) related details
                all_order_ids = {(order_id, line_id) for order_ids in component_to_order_map.values() for order_id, line_id in order_ids}
                # unique_order_ids = {order_id for order_id, line_id in all_order_ids}
                
                mto_orderdata_map = {(mo['order_id'], mo['line_id']): mo for mo in OrderData.objects.filter(order_id__in=[order_id for order_id, line_id in all_order_ids],
                                    line_id__in=[line_id for order_id, line_id in all_order_ids]).values('order_id', 'line_id','color',
                                     'due_date', 'actual_released_date', 'bpp' , 'plant__plant_name','vf_order_type')}
                
                # Step 1 and 2: Fetch projection order IDs associated with the given order ID and line ID directly
                projection_order_plant_codes = ProjectionOrderDetails.objects.filter(
                    query
                ).values_list(
                    'order_plant_code', flat=True
                )

                # Directly fetch the order_ids from ProjectionOrder using distinct order_plant_codes in a single query
                projection_order_ids = ProjectionOrder.objects.filter(
                    order_plant_code__in=projection_order_plant_codes
                ).values_list('order_id', flat=True).distinct()

                projection_order_map = {po['order_id']: po for po in ProjectionOrder.objects.filter(order_id__in=projection_order_ids).values('order_id', 'cust_name', 'cust_code')}
                
                all_component_allocations = BatchwiseComponentAllocation.objects.filter(
                    query).values('order_id', 'item_code', 'line_item', 'order_qty', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit', 'order_remaining','srl_no','plant_code')
                
                logger.info("Fetched Batchwise Component Allocations data")
                all_component_allocations_df = pd.DataFrame(all_component_allocations)
                all_component_allocations_df = all_component_allocations_df.merge(leaf_item_codes,left_on=['item_code','plant_code'], right_on=['component_item_code','plant_code'], how = 'inner').drop(columns=['component_item_code'])
                component_allocation_map = {}
                for _,allocation in all_component_allocations_df.iterrows() :
                    component_allocation_map.setdefault((allocation['order_id'], allocation['line_item'], allocation['item_code']), []).append(allocation.to_dict())
                logger.info("Fetched Component allocation map details")

                pending_orders = PendingOrder.objects.filter(type="Purchase").values('item_code', 'order_qty', 'plant_code')
                pending_orders_df = pd.DataFrame(pending_orders, columns = ['item_code', 'order_qty', 'plant_code'])
                pending_orders_df = pending_orders_df.merge(leaf_item_codes, left_on=['item_code','plant_code'], right_on=['component_item_code','plant_code'], how = 'left').drop(columns=['component_item_code'])
                pending_orders_map = {}
                for po in pending_orders_df.itertuples() :
                    pending_orders_map[po.item_code]= pending_orders_map[po.order_qty]
                item_master_map = {item['item_code']: item for item in ItemMaster.objects.filter(item_code__in=leaf_item_codes['component_item_code'].drop_duplicates().to_list()).values('item_code', 'item_description','attributes')}
                bomdetail_map = {bd['component_item_code']: bd['component_uom'] for bd in BOMDetail.objects.filter(component_item_code__in=leaf_item_codes).values('component_item_code', 'component_uom')}
                logger.info("Fetched maps for pending orders, Item master, and BOM details")

                for key, order_ids in component_to_order_map.items():
                    component_item_code = key[0]
                    plant_code = key[1]
                    item_master_instance = item_master_map.get(component_item_code)
                    description = item_master_instance['item_description'] if item_master_instance else ''
                    attributes = item_master_instance['attributes'] if item_master_instance else {}
                    component_detail = bomdetail_map.get(component_item_code)
                    total_pending_order_qty = pending_orders_map.get(component_item_code, 0)
                    rm_object = {
                        "cp": [],
                        "rm": component_item_code,
                        "pl": plant_code,
                        "rmd": description if description else '',
                        "nooi": 0,
                        "uom": component_detail if component_detail else '',
                        "req": 0,
                        "gap": 0,
                        "ppo": total_pending_order_qty,
                        "eas": 0,
                        "children": []
                    }
                    rm_object.update(attributes if attributes else {})

                    (rm_object, total_oq, total_soh, total_siqc, total_sit, color_count) = self.process_order_data(order_ids, component_item_code, rm_object, mto_orderdata_map, projection_order_map, component_allocation_map)

                    rm_object["req"] = total_oq if total_oq else 0
                    rm_object["soh"] = total_soh if total_soh else 0
                    rm_object["siqc"] = total_siqc if total_siqc else 0
                    rm_object["sit"] = total_sit if total_sit else 0
                    rm_object["tsfs"] = total_soh if total_soh else 0
                    rm_object['gap'] = rm_object['req'] - rm_object['soh'] - rm_object['siqc'] - rm_object['sit']

                    # skip those rm's which has total qty zero
                    if show_all_items_flag is False:
                        if rm_object["req"] == 0:
                            continue

                    total_orders = sum(color_count.values())
                    if total_orders > 0:
                        color_percentages = {color: round((count / total_orders) * 100) for color, count in color_count.items()}
                    else:
                        color_percentages = {color: 0 for color in color_count}

                    rm_object["cp"] = [color_percentages]
                    
                    if completely_available_param is None:
                        response_data.append(rm_object)
                    elif completely_available_param and rm_object['gap'] == 0:
                        response_data.append(rm_object)
                    elif not completely_available_param and rm_object['gap'] != 0:
                        response_data.append(rm_object)
                logger.info("Procurement report data prepared successfully")

            response_data.sort(key=sort_color_priority)
            logger.info("Sorting the response data based on color priority")

            if export_param:
                if report_name and headers:
                    return CustomExcelExport(
                        response_data,
                        report_name,
                        headers,
                        isGrouped=True,
                        isChildren=isChildren,
                        child_element=eChildName.children.value,
                        name_of_report_parent=eReportName.proc_planning.value,
                        name_of_report_child=eReportName.proc_planning_child.value
                    )
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(response_data, request)

            return paginator.get_paginated_response(paginated_response_data, msg="Procurement Reports fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as e:
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)
        
    
    #Returns a list to store component_item_codes not present in BOMHeader table
    def find_component_item_codes(self, bom_srl_no_to_component_item_code):
        final_component_item_codes = set()
        all_component_item_codes = {item_code for codes in bom_srl_no_to_component_item_code.values() for item_code in codes}

        bom_headers = BOMHeader.objects.filter(parent_item_code__in=all_component_item_codes)
        logger.info("Fetched BOM headers for component item codes")

        parent_to_bom_srl_no = {header.parent_item_code: header.bom_srl_no for header in bom_headers}

        component_codes_with_headers = set(parent_to_bom_srl_no.keys())
        component_codes_without_headers = all_component_item_codes - component_codes_with_headers

        final_component_item_codes.update(component_codes_without_headers)

        prefetch_details = Prefetch('bom_headers', queryset=BOMDetail.objects.only('bom_srl_no', 'component_item_code'))
        bom_headers = BOMHeader.objects.filter(bom_srl_no__in=parent_to_bom_srl_no.values()).prefetch_related(prefetch_details)
        logger.info("Prefetched BOM details")

        new_component_codes = set()
        for header in bom_headers:
            for detail in header.bom_headers.all():
                new_component_codes.add(detail.component_item_code)

        new_bom_headers = BOMHeader.objects.filter(parent_item_code__in=new_component_codes).values_list('parent_item_code', flat=True)
        new_bom_headers_set = set(new_bom_headers)
        final_component_item_codes.update(new_component_codes - new_bom_headers_set)
        logger.info("Final component item codes after processing BOM details")

        return list(final_component_item_codes)

    # Fetch child(order) and rm related details
    def process_order_data(self, order_ids, component_item_code, rm_object, mto_orderdata_map, projection_order_map, component_allocation_map):
        total_oq = 0
        total_soh = 0
        total_siqc = 0
        total_sit = 0
        unique_combinations = set()
        color_count = {"B": 0, "R": 0, "Y": 0, "G": 0, "W": 0, "Bl": 0}

        unique_order_ids = set()
        rm_object['nooi'] = 0
        if  len(order_ids) == 0:
            return rm_object, total_oq, total_soh, total_siqc, total_sit, color_count
        for order in order_ids:
            mto_orderdata = mto_orderdata_map.get(order)
            order_details = projection_order_map.get(order[0])
            key_tuple = (*order, component_item_code)
            allocation_data_list = component_allocation_map.get(key_tuple, [])

            for allocation_data in allocation_data_list:
                unique_combination = (allocation_data['order_id'], allocation_data['line_item'], allocation_data['order_qty'], allocation_data['stock_on_hand'], allocation_data['stock_in_qc'], allocation_data['stock_in_transit'], allocation_data['order_remaining'], allocation_data['srl_no'])
                if unique_combination in unique_combinations:
                    continue
                unique_combinations.add(unique_combination)
                oq = allocation_data['order_qty']
                soh = allocation_data['stock_on_hand']
                siqc = allocation_data['stock_in_qc']
                sit = allocation_data['stock_in_transit']
                total_oq += oq
                total_soh += soh
                total_siqc += siqc
                total_sit += sit

                unique_order_ids.add((allocation_data['order_id'], allocation_data['line_item']))

                color = mto_orderdata['color'] if mto_orderdata else ''
                if color == "Black":
                    color_count["B"] += 1
                elif color == "Red":
                    color_count["R"] += 1
                elif color == "Yellow":
                    color_count["Y"] += 1
                elif color == "Green":
                    color_count["G"] += 1
                elif color == "White":
                    color_count["W"] += 1
                elif color == "Blue":
                    color_count["Bl"] += 1

                rm_object["children"].append({
                    "on": allocation_data['order_id'],
                    "lid": allocation_data['line_item'],
                    "oq": allocation_data['order_qty'],
                    "cn": order_details['cust_name'] if order_details else '',
                    "cc": order_details['cust_code'] if order_details else '',
                    "odd": mto_orderdata['due_date'] if mto_orderdata else '',
                    "ord": mto_orderdata['actual_released_date'] if mto_orderdata else '',
                    "clr": color,
                    "bpp": mto_orderdata['bpp'] if mto_orderdata else '',
                    "aq": soh + siqc + sit,
                    "pend": allocation_data['order_remaining'],
                    "sno": allocation_data['srl_no'],
                    "pn" : mto_orderdata['plant__plant_name'] if mto_orderdata else '',
                    "ot" : mto_orderdata['vf_order_type'] if mto_orderdata else ''
                })

        rm_object["nooi"] = len(unique_order_ids)
        return rm_object, total_oq, total_soh, total_siqc, total_sit, color_count


# Patch API to update simulated quantity
class BatchwiseComponentAllocationUpdateAtSimulationView(APIView):
    serializer_class = BatchwiseComponentAllocationSerializer
    
    @swagger_auto_schema(
        operation_description="Update the simulated quantity for batchwise component allocations",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'sno': openapi.Schema(type=openapi.TYPE_INTEGER, description='Serial number'),
                    'on': openapi.Schema(type=openapi.TYPE_STRING, description='Order ID'),
                    'lid': openapi.Schema(type=openapi.TYPE_STRING, description='Line item'),
                    'item': openapi.Schema(type=openapi.TYPE_STRING, description='Item code'),
                    'easa': openapi.Schema(type=openapi.TYPE_INTEGER, description='Simulated quantity')
                },
                required=['sno', 'on', 'lid', 'item', 'easa']
            )
        ),
        responses={
            200: openapi.Response(description='All found records updated successfully'),
            400: openapi.Response(description='Some records were not found')
        }
    )
    def patch(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data.get('data'), many=True)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            # Create a queryset for filtering based on the unique constraints
            query = Q()
            for item in data:
                query |= Q(srl_no=item['sno'], order_id=item['on'], line_item=item['lid'], item_code=item['item'])

            # Fetch relevant objects and directly create a dictionary
            allocations_dict = {
                (allocation.srl_no, allocation.order_id, allocation.line_item, allocation.item_code): allocation
                for allocation in BatchwiseComponentAllocation.objects.filter(query)
            }
            logger.info('Fetched records and created dictionary')
            
            allocations_to_update = []
            for item in data:
                key = (item['sno'], item['on'], item['lid'], item['item'])
                allocation = allocations_dict.get(key)
                if allocation:
                    allocation.simulated_qty = item['easa']
                    allocations_to_update.append(allocation)

            BatchwiseComponentAllocation.objects.bulk_update(allocations_to_update, ['simulated_qty'])
            logger.info('All records updated successfully')
            return api_response(msg='All records updated successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            return api_response(msg=f'Error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)

# Get API to fetch Prod Data After Simulation
class GetProdDataAfterSimulationView(APIView):
    pagination_class = CustomPagination

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'releaseDate',
                openapi.IN_QUERY,
                description="Pass the release date",
                type=openapi.TYPE_STRING,
                
            ),
            openapi.Parameter(
                'eas',
                openapi.IN_QUERY,
                description="Pass the release date",
                type=openapi.TYPE_INTEGER,
                
            ),
        ],
        responses={200: 'Success', 404: 'Not Found'}
    )
    def get(self, request, format=None):
        try:
            release_date = request.GET.get('releaseDate')
            eas_flag = request.GET.get('eas')
            eas_data_param = bool(int(eas_flag)) if eas_flag else None
            logger.info(f"Received GET request with releaseDate: {release_date}")

            if not release_date:
                logger.error("releaseDate parameter is required")
                return api_response(error="releaseDate parameter is required", status_code=status.HTTP_400_BAD_REQUEST)

            orders = OrderData.objects.filter(actual_released_date__lte=release_date).values('order_id', 'line_id','color', 'actual_released_date','due_date')
            order_ids = [order['order_id'] for order in orders]
            line_ids = [order['line_id'] for order in orders]
            distinct_order_ids = set(order_ids)
            distinct_line_ids = set(line_ids)
            logger.info("Fetched no of orders")

            # Step 1 and 2: Fetch projection order IDs associated with the given order ID and line ID directly
            projection_order_plant_codes = ProjectionOrderDetails.objects.filter(
                order_id__in=distinct_order_ids,
                line_item__in=distinct_line_ids
            ).values_list(
                'order_plant_code', flat=True
            )

            # Directly fetch the order_ids from ProjectionOrder using distinct order_plant_codes in a single query
            projection_order_ids = ProjectionOrder.objects.filter(
                order_plant_code__in=projection_order_plant_codes
            ).values_list('order_id', flat=True).distinct()

            projection_orders = ProjectionOrder.objects.filter(order_id__in=projection_order_ids).prefetch_related('projection_order_code').values(
                'order_id', 'cust_code', 'cust_name', 'order_date', 
                'projection_order_code__line_item', 'projection_order_code__item_code', 'projection_order_code__balance_order_qty'
            )
            
            projection_order_dict = {(po['order_id'], po['projection_order_code__line_item']): po for po in projection_orders}
            logger.info("Fetched projection orders")

            # Call the common function to fetch leaf nodes
            leaf_item_codes = fetch_leaf_nodes()

            # Fetch data from BatchwiseComponentAllocation
            batchwise_component_allocations = BatchwiseComponentAllocation.objects.filter(
                order_id__in=order_ids,
                line_item__in=[po['projection_order_code__line_item'] for po in projection_orders]
            ).values('order_id', 'line_item', 'item_code', 'order_qty','simulated_qty','stock_on_hand','stock_in_qc','stock_in_transit','parent_code')
            logger.info("Fetched Batchwise Component Allocations data")
            
            # Organize BatchwiseComponentAllocation data by order_id and line_item
            allocation_dict = {}
            for allocation in batchwise_component_allocations:
                allocation_key = (allocation['order_id'], allocation['line_item'])
                if allocation['item_code'] in leaf_item_codes:
                    if allocation_key not in allocation_dict:
                        allocation_dict[allocation_key] = []
                    allocation_dict[allocation_key].append({
                        "rm": allocation['item_code'],
                        "rmqty": allocation['order_qty'],
                        "rmall": allocation['stock_on_hand'] + allocation['stock_in_qc'] + allocation['stock_in_transit'] + allocation['simulated_qty'],
                        "eas": allocation['simulated_qty'] or 0
                    })

            # Fetch data from BatchwiseOrderAllocation
            batchwise_order_allocations = BatchwiseOrderAllocation.objects.filter(
                order_id__in=order_ids,
                line_item__in=[po['projection_order_code__line_item'] for po in projection_orders],
                item_code__in=[po['projection_order_code__item_code'] for po in projection_orders]
            ).values('order_id', 'line_item','item_code', 'stock_on_hand','stock_in_qc','stock_in_transit')
            logger.info("Fetched Batchwise Order Allocations data")

            # Organize BatchwiseOrderAllocation data by order_id item_code and item_code
            kbs_dict = {}
            for allocation in batchwise_order_allocations:
                kbs_key = (allocation['order_id'], allocation['line_item'], allocation['item_code'])
                kbs_value = allocation['stock_on_hand'] + allocation['stock_in_qc'] + allocation['stock_in_transit']
                kbs_dict[kbs_key] = kbs_value
            
            # Fetch item descriptions from ItemMaster
            all_item_codes = set([po['projection_order_code__item_code'] for po in projection_orders])
            all_item_codes.update(leaf_item_codes)
            item_descriptions = {item['item_code']: item['item_description'] for item in ItemMaster.objects.filter(item_code__in=all_item_codes).values('item_code', 'item_description')}
            logger.info("Fetched SKU descriptions from ItemMaster")

            # Fetch data from EcoStock
            eco_stock_data = EcoStock.objects.filter(
                item_code__in=leaf_item_codes,
                type__in=['StockInHand', 'StockInQC', 'StockInTransit']
            ).values('item_code').annotate(total_qty=Sum('quantity'))
            logger.info("Fetched EcoStock data")

            eco_stock_dict = {es['item_code']: es['total_qty'] for es in eco_stock_data}

            # Fetch all necessary BOMDetail objects in a single query
            bom_details = BOMDetail.objects.filter(component_item_code__in=leaf_item_codes).values(
                'component_item_code', 'bom_srl_no__parent_item_code', 'component_qty'
            )
            logger.info("Fetched BOMDetail data")

            bom_detail_dict = {}
            for detail in bom_details:
                key = (detail['component_item_code'], detail['bom_srl_no__parent_item_code'])
                bom_detail_dict[key] = detail['component_qty']

            data = []
            for order in orders:
                order_id = order["order_id"]
                line_id = order["line_id"]
                projection_order = projection_order_dict.get((order_id, line_id), {})
                if not projection_order:
                    continue # Skip if projection_order is empty
                kbs_key = (order_id, line_id, projection_order.get("projection_order_code__item_code"))
                kbs_value = kbs_dict.get(kbs_key, 0)

                batch_size = get_item_batchsize(projection_order.get("projection_order_code__item_code"))
                batch_size_value = 0
                batch_size_value = batch_size.get(projection_order.get("projection_order_code__item_code"),1)

                if not eas_data_param:
                    childrens = allocation_dict.get((order_id, projection_order.get("projection_order_code__line_item")), [])
                    eas = True
                    if childrens:
                        for child in childrens:
                            eas_value = child['eas']
                            if eas_value == 0 and child['rmall'] != child['rmqty']:
                                eas = False
                        if not eas:
                            continue
                    if not childrens:
                        continue

                combined_data = {
                    "cp": order["color"],
                    "oli": projection_order.get("projection_order_code__line_item"),
                    "on": order_id,
                    "item": projection_order.get("projection_order_code__item_code"),
                    "id": item_descriptions.get(projection_order.get("projection_order_code__item_code"), ""),
                    "oq": projection_order.get("projection_order_code__balance_order_qty"),
                    "bs": batch_size_value,
                    "kbs": kbs_dict.get(kbs_key, 0),
                    "fka": 0,
                    "cn": projection_order.get("cust_name"),
                    "cc": projection_order.get("cust_code"),
                    "od": projection_order.get("order_date"),
                    "odd": order['due_date'],
                    "ord": order["actual_released_date"],
                    "children": allocation_dict.get((order_id, projection_order.get("projection_order_code__line_item")), [])
                }
                data.append(combined_data)
            
            # Now perform the batch size calculations
            logger.info("Performing batch size calculations")
            for combined_data in data:
                order_id = combined_data["on"]
                line_id = combined_data["oli"]
                projection_order = projection_order_dict.get((order_id, line_id), {})
                # Calculate batch size
                children_data = allocation_dict.get((order_id, projection_order.get("projection_order_code__line_item")), [])
                if not children_data:
                    continue  # Skip if projection_order is empty or line_item is empt
                adjusted_rmall_values = [(child['rmall'] - child['eas'], child['rm'], child['rmall']) for child in children_data]
                bs_value, min_rm, min_rmall = min(adjusted_rmall_values, key=lambda x: x[0])

                # Find parent_code based on min_rm_item_code
                parent_code = next((allocation['parent_code'] for allocation in batchwise_component_allocations if allocation['item_code'] == min_rm and allocation['order_id'] == order_id), None)

                # Fetch component_qty from bom_detail_dict and calculate fka_value
                component_qty = bom_detail_dict.get((min_rm, parent_code))
                fka_value = round(min_rmall / component_qty, 2) if component_qty else 0

                combined_data["fka"] = fka_value

                for child in combined_data["children"]:
                    if combined_data["fka"] == 0:
                        child["clr"] = "Red"
                    elif combined_data["fka"] > 0 and combined_data["fka"] == combined_data["bs"]:
                        child["clr"] = "Green"

                    child["rmd"] = item_descriptions.get(child["rm"], "")
                    child["rma"] = eco_stock_dict.get(child["rm"], 0)
                    
            # Define the custom sorting order based on colors
            color_order = {"Black": 0,"Red": 1,"Yellow": 2,"Green": 3,"White": 4,"Blue": 5}

            # Sort the data based on the 'cp' (color) field
            data.sort(key=lambda x: color_order.get(x["cp"], float('inf')))
            
            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(data, request)

            logger.info("Returning the paginated response")
            return paginator.get_paginated_response(paginated_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)


# Post API for Procurement Simulation
class ProcurementSimulationView(APIView):
    
    @swagger_auto_schema(
        operation_description="Perform Procurement Simulation",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                'stock': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'ic': openapi.Schema(type=openapi.TYPE_STRING, description='Item Code'),
                            'as': openapi.Schema(type=openapi.TYPE_NUMBER, description='Additional Stock')
                        },
                        required=['ic', 'as']
                    )
                )
            }
        ),
        responses={
            200: openapi.Response(description='Performed Procurement Simulation successfully'),
            400: openapi.Response(description='Records were not found')
        }
    )
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            stocks = data.get('stock', [])
            username = data.get('username')

            #Save username and today's date to simulation history
            simulation_history = SimulationHistory(
                run_date=date.today(),
                username=username
            )
            simulation_history.save()
            logger.info('Added simulation history')

            # Delete all existing records in Additional Stock table
            AdditionalStock.objects.all().delete()
            
            #Save all input data to additional stock model
            additional_stocks = [
                AdditionalStock(item_code=order['ic'], additional_stock=order['as'])
                for order in stocks
            ]
            AdditionalStock.objects.bulk_create(additional_stocks)
            logger.info('Added additional stocks')

            # Call the common function to fetch leaf nodes
            leaf_item_codes = fetch_leaf_nodes()

            # Get all unique item codes from input stocks
            input_item_codes = set(order['ic'] for order in stocks)

            # Check if item codes are present in leaf_item_codes
            valid_item_codes = input_item_codes.intersection(leaf_item_codes)

            # Fetch records from BatchwiseComponentAllocation table based on valid item codes
            batchwise_components = []
            unique_order_line_items = []
            if valid_item_codes:
                batchwise_components = BatchwiseProductionComponentAllocation.objects.filter(
                    Q(item_code__in=valid_item_codes)
                )

                # Convert queryset to list of dictionaries for all values
                batchwise_components = list(batchwise_components.values())

                # Extract unique order_id and line_item pairs
                order_line_set = set((comp['order_id'], comp['line_item']) for comp in batchwise_components)
                unique_order_line_items = [{'order_id': oid, 'line_item': li} for oid, li in order_line_set]

            logger.info('Fetched records from Batchwise Production Component Allocation Table')

            # Filter OrderData based on unique_order_line_items
            matching_orders = OrderData.objects.filter(
                Q(order_id__in=[item['order_id'] for item in unique_order_line_items]) & 
                Q(line_id__in=[item['line_item'] for item in unique_order_line_items])
            ).values('order_id', 'line_id', 'item', 'total_qty', 'bpp', 'vf_order_type', 'wh_code')
            
            logger.info('Fetched Orders data records')

            # Logic to calculate priority of orders
            updated_records = []

            # Fetch all SimulationConfiguration objects
            all_configurations = list(SimulationConfiguration.objects.all())

            # Create separate lists for MTA and MTO orders
            mta_orders = [order for order in matching_orders if order['vf_order_type'] == 'MTA']
            mto_orders = [order for order in matching_orders if order['vf_order_type'] == 'MTO']

            # Fetch all relevant MTA stock data in a single query
            mta_stock_data = MTAStockGITData.objects.filter(
                sku_code__in=[order['item'] for order in mta_orders],
                wh_code__in=[order['wh_code'] for order in mta_orders]
            ).values('sku_code', 'wh_code', 'virtual_norm', 'norm', 'cbr_days', 'dispatch_color')
            logger.info('Fetched MTA Stock data records')

            mta_stock_dict = defaultdict(list)
            for stock in mta_stock_data:
                mta_stock_dict[(stock['sku_code'], stock['wh_code'])].append(stock)

            # Iterate over MTA orders to apply configurations
            for mta_order in mta_orders:
                mta_stock_orders = mta_stock_dict[(mta_order['item'], mta_order['wh_code'])]

                # Iterate over mta_stock_orders and apply configurations
                for mta_stock in mta_stock_orders:
                    cbr = mta_stock.get('cbr_days')
                    virnorm = mta_stock.get('virtual_norm')
                    norm = mta_stock.get('norm')
                    dc = mta_stock.get('dispatch_color')

                    # Filter configurations for MTA order type
                    applicable_configurations = [config for config in all_configurations if config.vf_ordertype == "MTA"]

                    # Apply Norm Calculation filter
                    if virnorm is not None and norm is not None:
                        if virnorm > norm:
                            applicable_configurations = [config for config in applicable_configurations if config.norm_calc == 'VNgrN']
                        elif virnorm == norm:
                            applicable_configurations = [config for config in applicable_configurations if config.norm_calc == 'VNeqN']

                    # Apply CBR filter
                    if cbr is not None:
                        applicable_configurations = [
                            config for config in applicable_configurations
                            if (config.cbr_min is None or config.cbr_min <= cbr) and
                            (config.cbr_max is None or config.cbr_max > cbr)
                        ]

                    # Apply Dispatch Color filter
                    if dc is not None:
                        applicable_configurations = [config for config in applicable_configurations if dc.lower() in config.dispatch_color.lower()]

                    # Check if any configurations match the criteria
                    if applicable_configurations:
                        priority_value = applicable_configurations[0].priority
                        mta_order['priority'] = priority_value
                        updated_records.append(mta_order)
                        break

            logger.info('Calculated priority of each order')

            # Iterate over MTO orders to apply configurations
            for mto_order in mto_orders:
                bpp = mto_order.get('bpp')

                # Filter configurations for MTO order type
                applicable_configurations = [config for config in all_configurations if config.vf_ordertype == "MTO"]

                # Apply BPP filter to configurations
                if bpp is not None:
                    applicable_configurations = [
                        config for config in applicable_configurations
                        if (config.bpp_min is None or config.bpp_min <= bpp) and
                        (config.bpp_max is None or config.bpp_max > bpp)
                    ]

                # Check if any configurations match the criteria
                if applicable_configurations:
                    priority_value = applicable_configurations[0].priority
                    mto_order['priority'] = priority_value
                    updated_records.append(mto_order)

            # Sort the updated_records by priority
            updated_records.sort(key=lambda x: x['priority'])
            logger.info('Updated records based on priority')

            # Map item_code to additional_stock
            item_code_to_additional_stock = {stock['ic']: stock['as'] for stock in stocks}

            # Delete all existing records in Additional Stock table
            BatchwiseProcurementComponentAllocation.objects.all().delete()

            # Save records in BatchwiseProcurementComponentAllocation table
            allocation_records = []
            for record in updated_records:
                for component in batchwise_components:
                    if component['order_id'] == record['order_id'] and component['line_item'] == record['line_id']:
                        order_qty = component['order_qty']
                        stock_on_hand = component['stock_on_hand']
                        stock_in_qc = component['stock_in_qc']
                        stock_in_transit = component['stock_in_transit']
                        order_remaining = component['order_remaining']
                        
                        # Calculate remaining requirement
                        remaining_requirement = order_qty - stock_on_hand - stock_in_qc - stock_in_transit
                        
                        # Determine additional stock allocation
                        additional_stock_allocation = 0
                        if remaining_requirement > 0:
                            additional_stock_allocation = min(remaining_requirement, item_code_to_additional_stock.get(component['item_code'], 0))
                            item_code_to_additional_stock[component['item_code']] -= additional_stock_allocation
                            if item_code_to_additional_stock[component['item_code']] < 0:
                                item_code_to_additional_stock[component['item_code']] = 0
                        
                        # Update order_remaining
                        updated_order_remaining = order_qty - stock_on_hand - stock_in_qc - stock_in_transit - additional_stock_allocation

                        allocation = BatchwiseProcurementComponentAllocation(
                            srl_no=component['srl_no'],
                            order_id=component['order_id'],
                            line_item=component['line_item'],
                            item_code=component['item_code'],
                            plant_code=component['plant_code'],
                            parent_code=component['parent_code'],
                            bom_level=component['bom_level'],
                            order_qty=component['order_qty'],
                            stock_on_hand=component['stock_on_hand'],
                            stock_in_qc=component['stock_in_qc'],
                            stock_in_transit=component['stock_in_transit'],
                            additional_stock=additional_stock_allocation,
                            order_remaining=updated_order_remaining,
                            identifier=component['identifier'],
                            simulated_qty=component['simulated_qty'],
                            open_PO=component['open_PO'],
                            item_srl_no=component['item_srl_no']
                        )
                        allocation_records.append(allocation)

            BatchwiseProcurementComponentAllocation.objects.bulk_create(allocation_records)
            logger.info('Added records in Batchwise Procurement Component Allocation table')

            logger.info('Performed Procurement Simulation successfully')
            return api_response(msg='Performed Procurement Simulation successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred: {e}')

class ProcurementPlanningSimulationView(APIView):
    
    @swagger_auto_schema(
        operation_description="Perform Procurement Planning",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'stock': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'ic': openapi.Schema(type=openapi.TYPE_STRING, description='Item Code'),
                            'as': openapi.Schema(type=openapi.TYPE_NUMBER, description='Additional Stock')
                        },
                        required=['ic', 'as']
                    )
                )
            }
        ),
        responses={
            200: openapi.Response(description='Performed Procurement Planning successfully'),
            400: openapi.Response(description='Records were not found')
        }
    )
    def post(self, request, *args, **kwargs):
        data = request.data
        try:
            stocks = data.get('stock', [])
            # Fetch Allocation Configuration 
            system_type = DBRSettings.objects.get(flag="BOM_Component_Allocation_Type").value
            logger.info('Fetched value from DBR Setting table')

            # Fetch the list of all orders from Allocation Sequence table
            allocation_orders = AllocationSequence.objects.all().values('order_id','line_id','priority','sequence').order_by('priority', 'sequence')
            logger.info('Fetched orders from Allocation Sequence table')

            # Extract order_id and line_id from allocation_orders
            allocation_order_ids = allocation_orders.values_list('order_id', 'line_id')

            # if system type is FullOrderwise
            if system_type == '0':
                logger.info('system type is FullOrderwise')
                allocations_to_update = []

                # Extract item codes from stocks
                item_codes = [stock['ic'] for stock in stocks]
                stock_dict = {stock['ic']: stock['as'] for stock in stocks}

                # Fetch BatchwiseComponentAllocation records based on order_id, line_id, and item_code
                batchwise_allocations = BatchwiseComponentAllocation.objects.filter(
                    order_id__in=[order_id for order_id, _ in allocation_order_ids],
                    line_item__in=[line_id for _, line_id in allocation_order_ids],
                    item_code__in=item_codes
                ).values('id','order_id', 'line_item', 'item_code', 'order_remaining', 'simulated_qty','bom_level')
                logger.info('BatchwiseComponentAllocation records based on order_id, line_id, and item_code')

                # Reset simulated_qty to 0 for all records in batchwise_allocations
                for allocation in batchwise_allocations:
                    allocation['simulated_qty'] = 0

                # Iterate through allocation orders based on priority and sequence
                for allocation_order in allocation_orders:
                    order_id = allocation_order['order_id']
                    line_id = allocation_order['line_id']

                    # Filter the relevant batchwise allocations and sort by bom_level
                    relevant_allocations = sorted(
                        [
                            allocation for allocation in batchwise_allocations 
                            if allocation['order_id'] == order_id and allocation['line_item'] == line_id
                        ],
                        key=lambda x: x['bom_level']  # Sort by bom_level (lower levels first)
                    )
                    
                    # Process each allocation
                    for allocation in relevant_allocations:
                        item_code = allocation['item_code']
                        order_remaining = allocation['order_remaining']
                        simulated_qty = allocation['simulated_qty']
                        available_stock = stock_dict.get(item_code, 0)

                        # Calculate the required quantity to match the order_remaining
                        required_qty = order_remaining - simulated_qty

                        if available_stock >= required_qty > 0:
                            # Allocate the exact quantity needed to match order_remaining
                            allocation['simulated_qty'] += required_qty
                            stock_dict[item_code] -= required_qty

                        # Track this allocation for bulk update
                        allocations_to_update.append(
                            BatchwiseComponentAllocation(
                                id=allocation['id'],
                                simulated_qty=allocation['simulated_qty']
                            )
                        )
                        logger.info('Perform full orderwise allocation')

                # Perform a bulk update in a single transaction
                with transaction.atomic():
                    BatchwiseComponentAllocation.objects.bulk_update(allocations_to_update, ['simulated_qty'])
                    logger.info('Perform bulk updation of simulated quantity')

            # if system type is Batchwise
            else:
                logger.info('system type is Batchwise')
                order_line_filter = Q()
                order_id_line_id_set = set()

                for order_id, line_id in allocation_order_ids:
                    order_line_filter |= Q(order_id=order_id, line_id=line_id)
                    order_id_line_id_set.add((order_id, line_id))

                # Fetch OrderData where order_id and line_id match those in allocation_order_ids
                get_order_item = OrderData.objects.filter(order_line_filter).values('order_id', 'line_id', 'item_id')
                item_ids = [item['item_id'] for item in get_order_item]
                logger.info('Fetched parent irem code from OrderData based on order_id and line_id')

                # Extract item codes from stocks
                item_codes = [stock['ic'] for stock in stocks]
                stock_dict = {stock['ic']: stock['as'] for stock in stocks}

                # Extract order_ids, line_ids, and item_ids from get_order_item
                order_id_line_id_pairs = [(item['order_id'], item['line_id'], item['item_id']) for item in get_order_item]

                order_filter = Q()
                for order_id, line_id, item_id in order_id_line_id_pairs:
                    order_filter |= Q(order_id=order_id, line_item=line_id, parent_code=item_id)

                # Fetch BatchwiseComponentAllocation records based on order_id, line_id, and item_code
                batchwise_allocations = BatchwiseComponentAllocation.objects.filter(
                    order_filter,
                    item_code__in=item_codes
                ).values('id','order_id', 'line_item', 'item_code', 'order_remaining', 'simulated_qty','bom_level','item_srl_no','parent_code')
                logger.info('Fetch records based on order_id, line_id, item code and parent code')
                            
                batchwise_allocations.update(simulated_qty=0)

                #Fetch order ids and line ids whose RMs are not present in Batchwise Component Allocation table
                batchwise_allocations_set = set((allocation['order_id'], allocation['line_item']) for allocation in batchwise_allocations)
                missing_order_line_ids = order_id_line_id_set - batchwise_allocations_set

                if missing_order_line_ids:
                    logger.warning(f'Missing order_id and line_id pairs in batchwise_allocations: {missing_order_line_ids}')
                
                batch_size = MasterItemProductionBatchsize.objects.filter(item_code__in=item_ids).values('item_code', 'batch_size')
                logger.info('Fetched batch size from Master Item Production Batch size table')

                # Create a dictionary from batch_size with item_code as key and batch_size as value
                batch_size_dict = {bs['item_code']: bs['batch_size'] for bs in batch_size}

                item_srl_no_list = []

                # Fetch all BOMDetail records for the relevant item_code, bom_srl_no, and item_srl_no
                bom_details_query = Q()
                for item_code, bom_srl_no, item_srl_no in item_srl_no_list:
                    bom_details_query |= Q(
                        component_item_code=item_code,
                        bom_srl_no=bom_srl_no,
                        item_srl_no=item_srl_no
                    )

                # Perform a single query to fetch all relevant BOMDetail records
                bom_details = BOMDetail.objects.filter(bom_details_query).values(
                    'component_item_code', 'bom_srl_no', 'item_srl_no', 'component_qty'
                )
                logger.info("Fetched component qty from Bom Detail table based on bom srl no and item srl no")

                # Map the results to the component_qty_dict
                component_qty_dict = {
                    (bom_detail['component_item_code'], f"{bom_detail['bom_srl_no']}_{bom_detail['item_srl_no']}"): bom_detail['component_qty']
                    for bom_detail in bom_details
                }

                remaining_stock_dict = stock_dict.copy()
                allocations_to_update = []

                # Assign available stock ('as') to each batchwise allocation where 'item_code' matches the key in stock_dict
                for allocation_order in allocation_orders:
                    order_id = allocation_order['order_id']
                    line_id = allocation_order['line_id']
                    
                    # Filter relevant batchwise allocations for the current order and line
                    relevant_allocations = [
                        allocation for allocation in batchwise_allocations
                        if allocation['order_id'] == order_id and allocation['line_item'] == line_id
                    ]

                    alloc_batch_sizes = []
                    
                    # Process only the first allocation that matches the item_code in stock_dict
                    for allocation in relevant_allocations:
                        item_code = allocation['item_code']
                        parent_code = allocation['parent_code']
                        item_srl_no = allocation['item_srl_no']
                        available_stock = remaining_stock_dict.get(item_code, 0)

                        # Assign available stock
                        allocation['stock'] = available_stock
                        
                        # Assign batch_size
                        allocation['batch_size'] = batch_size_dict.get(parent_code)

                        # Assign component_qty based on item_code and item_srl_no
                        allocation['qty'] = component_qty_dict.get((item_code, item_srl_no), None)

                        # Calculate alloc_batch_size (stock / order_remaining)
                        order_remaining = allocation['order_remaining']
                        alloc_batch_size = round(available_stock / order_remaining, 3) if order_remaining else 0
                        allocation['alloc_batch_size'] = alloc_batch_size

                        # Append alloc_batch_size to the list
                        alloc_batch_sizes.append(alloc_batch_size)

                        logger.info("Fetched stock, batch_size, qty and alloc_batch_size")

                    # Calculate the minimum alloc_batch_size for this order_id and line_id
                    if alloc_batch_sizes:
                        min_batch_size = min(alloc_batch_sizes)
                    else:
                        min_batch_size = 0
                    logger.info("Calculated minimum alloc_batch_size")

                    # Assign min_batch_size to all relevant allocations
                    for allocation in relevant_allocations:
                        allocation['min_batch_size'] = min_batch_size
                        allocation['alloc'] = round(allocation['order_remaining'] * min_batch_size, 3)

                        # Calculate qty_producable (alloc / qty)
                        qty = allocation.get('qty', 1)
                        allocation['qty_producable'] = round(allocation['alloc'] / qty, 3) if qty else 0

                        batch_size = allocation['batch_size'] or 1
                        allocation['qty_prod_per_batch'] = (allocation['qty_producable'] // batch_size) * batch_size

                        # Calculate final_alloc by multiplying qty_prod_per_batch with qty
                        allocation['final_alloc'] = round(allocation['qty_prod_per_batch'] * qty, 3)

                        logger.info("Calculated min_batch_size, qty producable and final allocation")

                        item_code = allocation['item_code']
                        available_stock = remaining_stock_dict.get(item_code, allocation['stock'])

                        if allocation['final_alloc'] >= allocation['order_remaining']:
                            allocation['simulated_qty'] = allocation['order_remaining']
                            updated_stock = allocation['final_alloc'] - allocation['order_remaining']
                        else:
                            allocation['simulated_qty'] = allocation['final_alloc']
                            updated_stock = allocation['simulated_qty']

                        # Update the available stock in remaining_stock_dict
                        remaining_stock_dict[item_code] = available_stock - allocation['simulated_qty']

                        allocations_to_update.append(
                            BatchwiseComponentAllocation(
                                id=allocation['id'],
                                simulated_qty=allocation['simulated_qty']
                            )
                        )
                        logger.info("Updated remaining stock and simulated qty based on allocation")

                # Update allocations in bulk
                with transaction.atomic():
                    BatchwiseComponentAllocation.objects.bulk_update(allocations_to_update, ['simulated_qty'])
                    logger.info('Perform bulk updation of simulated quantity')

            return api_response(msg='Performed Procurement Planning successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred: {e}')
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)
