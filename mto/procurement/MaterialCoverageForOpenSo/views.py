from datetime import  timedelta
from rest_framework.views import APIView
from rest_framework import status
from mto_app.common.commonfunctions import  CustomExcelExport
from mto_app.models import ( ProjectionOrder, BOMDetail, BatchwiseComponentAllocation , ProjectionOrderDetails, 
 EcoStock, ReportConfiguration , ItemMaster ,OrderData, KitAllocation )
from mto_app.common.commonfunctions import (api_response , fetch_leaf_nodes_with_plant, get_item_batchsize,filter_order_data_by_params, 
 GetUserDetails, DataPermissionFilterForOrderData ,
 is_batchwise_allocation,get_order_information , get_pagewise_data , MTOPagination , from_queryset_to_polars_df)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
from django.db.models import Sum, Q ,CharField, Value
from django.utils import timezone
import pandas as pd
from mto_app.utils import  eReportName, eChildName, DefaultPageConfig
import numpy as np
import itertools
from django.db.models.functions import Concat, Cast
from django.db.models import CharField
import polars as pl

logger = logging.getLogger(__name__)


class GetOpenSOSummaryDataView(APIView):
    @swagger_auto_schema(
        operation_description="Retrieve summary data for open orders"
    )

    def get(self, request): 
        return self.openSOSummaryData(request) 

    def put(self,request): 
        return self.openSOSummaryData(request,method = 'PUT') 

    def openSOSummaryData(self, request, format=None, method = 'GET'):
        try:
            if method == 'PUT':
                filter_data = request.data
            else:
                filter_data = None
            data = request.data
            product_permissions,location_permissions,is_admin = GetUserDetails(data)
            logger.info('Permission data is fetched from the payload')
            # from ccr_id all params are required for filter api
            orders = OrderData.objects.exclude(color__isnull=True).values('order_id', 'line_id','color', 'customer','order_value','due_date',
                'ccr__ccr_id', 'customer__cust_code', 'customer__cust_name', 'plant__plant_name', 'item__item_description', 'dept__dept_id', 
                'vf_order_type', 'item__item_code')

            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')
            
            if filter_data:
                orders = filter_order_data_by_params(orders, filter_data)
            
            query = Q()
            for order in orders:
                query |= Q(order_id=order['order_id'], line_item=order['line_id'])

            orders_df = pd.DataFrame(list(orders), columns =[
                'order_id', 'line_id','color', 'customer','order_value','due_date',
                'ccr__ccr_id', 'customer__cust_code', 'customer__cust_name', 'plant__plant_name', 'item__item_description', 'dept__dept_id', 
                'vf_order_type', 'item__item_code'
            ])
            logger.info("Fetched no of orders")

            # A clean estate is a valid state. The recovered implementation
            # builds the dashboard from colour/kit combinations, but its later
            # dataframe joins assumed at least one order and raised instead.
            # Preserve the same zero-valued summary shape without inventing an
            # operational order, BOM, stock, or allocation row.
            if orders_df.empty:
                empty_orders = pd.DataFrame(
                    columns=["on", "li", "due_date", "cust_code", "order_value", "kit", "col"]
                )
                summary_data = self.process_summary_data(empty_orders)
                reports = ReportConfiguration.objects.filter(
                    Q(colors__icontains='White') & Q(colors__icontains='Blue')
                )
                other_orders_grouped = self.process_grouped_data(empty_orders, reports)
                final_data = pd.concat(
                    [summary_data, other_orders_grouped], ignore_index=True
                ).to_dict(orient='records')
                return api_response(
                    msg='All records fetched successfully',
                    data=final_data,
                    status_code=status.HTTP_200_OK,
                )


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

            projection_orders = ProjectionOrder.objects.filter(order_id__in=projection_order_ids).prefetch_related('projection_order_code').values(
                'order_id','projection_order_code__line_item', 'projection_order_code__item_code', 'projection_order_code__balance_order_qty', 'plant_code' , 'projection_order_code__quantity'
                ,'projection_order_code__dispatch_quantity')
            logger.info("Fetched projection orders")

            projection_order_df = pd.DataFrame(list(projection_orders) , columns = [
                'order_id', 'cust_code', 'cust_name', 'order_date', 'plant_code',
                'projection_order_code__line_item', 'projection_order_code__item_code', 'projection_order_code__balance_order_qty' , 'projection_order_code__quantity' , 'projection_order_code__dispatch_quantity'
            ])
            # Call the common function to fetch leaf nodes
            leaf_item_codes = fetch_leaf_nodes_with_plant()

            # Fetch data from BatchwiseComponentAllocation
            batchwise_component_allocations = BatchwiseComponentAllocation.objects.filter(
                query
            ).values('order_id', 'line_item', 'item_code','order_remaining','order_qty','plant_code')
            logger.info("Fetched Batchwise Component Allocations data")

            batchwise_component_allocations_df = pd.DataFrame(list(batchwise_component_allocations), columns = [
                'order_id', 'line_item', 'item_code','order_remaining','order_qty','plant_code'
            ])

            # Get orders from batchwise_component_allocation which have leaf_item_codes as components
            batchwise_component_allocations_df = batchwise_component_allocations_df.merge(leaf_item_codes, left_on=['item_code','plant_code'], right_on=['component_item_code','plant_code'], how='inner').drop(columns=['component_item_code']).reset_index(drop=True)

            # batchwise_component_allocations_df = batchwise_component_allocations_df[batchwise_component_allocations_df['item_code'].isin(leaf_item_codes)]

            allocation_data = batchwise_component_allocations_df.groupby(['order_id','line_item']).agg({
                "order_qty" : "sum",
                "order_remaining" : "sum"
            }).rename(columns  ={ 
                "order_qty" : "order_qty_sum",
                "order_remaining" : "order_remaining_sum"
            })
            
            logger.info("Processing orders for color and kit determination.")

            kit_allocation_data = None
            kit_allocation_data = {}

            batchwise_allocation_flag = is_batchwise_allocation()
            projection_order_df.rename(columns = {'order_id': 'order_id_po'} , inplace= True)
            orders_df = orders_df.merge(projection_order_df , how = 'left' , left_on = ['order_id','line_id'] , right_on=['order_id_po','projection_order_code__line_item'], suffixes=('','_po'))
            orders_df = orders_df[orders_df['order_id_po'].notna()]
            orders_df['actual_order_quantity'] = np.maximum(orders_df['projection_order_code__quantity'].fillna(0) - orders_df['projection_order_code__dispatch_quantity'].fillna(0) , 0)

            kit_choices = ['NK','FK','PK']

            orders_df = orders_df.merge(allocation_data , how = 'inner' , left_on = ['order_id','line_id'] , right_on=['order_id','line_item'] , suffixes=('','_batchwise'))
            filtered_query = Q()
            for _ , row in orders_df.iterrows():
                filtered_query |= Q(order_id = row['order_id'] ,line_item = row['line_id'])
            if batchwise_allocation_flag:
                kit_conditions = [(orders_df['order_qty_sum'] == orders_df['order_remaining_sum']) , (orders_df['order_remaining_sum'] == 0 ), (orders_df['order_qty_sum'] > orders_df['order_remaining_sum']) & (orders_df['order_remaining_sum'] > 0)]
            else:
                kit_allocation_data = KitAllocation.objects.filter(filtered_query).values('order_id', 'line_item', 'plant_code', 'bom_level', 'no_of_kits')
                kit_allocation_data_df = pd.DataFrame(list(kit_allocation_data))
                orders_df['bom_level'] = 0
                orders_df = orders_df.merge(kit_allocation_data_df, left_on=['order_id','line_id','plant_code','bom_level'], right_on=['order_id','line_item','plant_code','bom_level'], how = 'left' , suffixes=('','_kit'))
                orders_df.loc[orders_df['no_of_kits'].isna(),'no_of_kits']  = 0 
                kit_conditions = [(orders_df['no_of_kits'] == 0),(orders_df['actual_order_quantity'] == orders_df['no_of_kits']) , (orders_df['actual_order_quantity'] > orders_df['no_of_kits']) & (orders_df['no_of_kits'] != 0) ]

            orders_df['kit_status'] = np.select(kit_conditions , kit_choices , default='')
            orders_df = orders_df.astype(object).where(pd.notna(orders_df), None)
            orders_df.loc[orders_df["order_value"].isna(),'order_value'] = 0
            data_with_color_kit = orders_df[~orders_df['color'].isin(["Blue", "White"])]
            other_orders = orders_df[orders_df['color'].isin(["Blue", "White"])]

            columns_map = {
                "order_id" : "on",
                "line_id" :"li",
                "due_date" : "due_date",
                "cust_code" : "cust_code",
                "order_value" : "order_value",
                "kit_status" : "kit",
                "color" : "col"
            }

            data_with_color_kit = data_with_color_kit.rename(columns = columns_map)[columns_map.values()]
            other_orders = other_orders.rename(columns = columns_map)[columns_map.values()]
            
            #For orders having color Yellow, Red, Green, Black
            logger.info("Summarizing data for orders with colors Yellow, Red, Green, Black.")
            summary_data = self.process_summary_data(data_with_color_kit)
            #Orders having color Blue and White
            logger.info("Processing orders with colors Blue and White.")
            reports = ReportConfiguration.objects.filter(Q(colors__icontains='White') & Q(colors__icontains='Blue'))
            other_orders_grouped = self.process_grouped_data(other_orders, reports)
            final_data  = pd.concat([summary_data , other_orders_grouped], ignore_index=True)
            final_data  = final_data.to_dict(orient = 'records')
            logger.info("All records fetched successfully")
            return api_response(msg='All records fetched successfully', data = final_data, status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)
        
    #For orders having color Yellow, Red, Green, Black
    def process_summary_data(self , data_with_color_kit):
        colors = ["Green", "Red", "Black", "Yellow"]
        kits = ["PK", "NK", "FK"]
        all_combinations = pd.DataFrame(list(itertools.product(colors, kits)), columns=["col", "kit"])
        summary_data_partition = data_with_color_kit.groupby(['col','kit']).agg({
            "on" : "count",
            "cust_code" : pd.Series.nunique,
            "order_value" : "sum"
        }).rename(columns = {
            "on" : "ordcnt",
            "cust_code" : "custcnt",
            "order_value" : "ordval"
        })
        summary_data_partition = all_combinations.merge(summary_data_partition, on=["col", "kit"], how="left")
        summary_data_partition[["ordcnt", "custcnt", "ordval"]] = summary_data_partition[["ordcnt", "custcnt", "ordval"]].fillna(0)
        summary_data_partition["bkt"] = 0 
        summary_data_partition["S"] = 0
        summary_data_partition["E"] = 0 
        return summary_data_partition

    def process_grouped_data(self , other_orders , reports):
        today = timezone.now().date()
        colors = ["Blue", "White"]
        kits = ["PK", "NK", "FK"]
        other_orders = other_orders[~other_orders['due_date'].isna()]
        other_orders['due_date'] = pd.to_datetime(other_orders['due_date'])
        other_orders['date_difference'] = (other_orders['due_date'] - pd.to_datetime(today)).dt.days
        other_orders["bkt"] = 0 
        other_orders["S"] = 0
        other_orders["E"] = 0 
        for report in reports:
            report_condition = (
                (other_orders['date_difference'] >= report.start) &
                (other_orders['date_difference'] <= report.end)
            )
            other_orders.loc[report_condition, 'bkt'] = report.flag
            other_orders.loc[report_condition, 'S'] = report.start
            other_orders.loc[report_condition, 'E'] = report.end
        
        grouped  = other_orders.groupby(['col','kit','bkt','S','E'], as_index=False).agg({
            "on" : "count",
            "cust_code" : pd.Series.nunique,
            "order_value" : "sum"
        }).rename(columns = {
            "on" : "ordcnt",
            "cust_code" : "custcnt",
            "order_value" : "ordval"
        })
        report_keys = [(r.flag, r.start, r.end) for r in reports]
        all_combinations = pd.DataFrame(
            [(col, kit, flag, start, end) for (col, kit, (flag, start, end)) in itertools.product(colors, kits, report_keys)],
            columns=["col", "kit", "bkt", "S", "E"]
        )

        # Step 5: Merge and fill missing with zeros
        other_orders_grouped = pd.merge(all_combinations, grouped, on=["col", "kit", "bkt", "S", "E"], how="left")
        other_orders_grouped[["ordcnt", "custcnt", "ordval"]] = other_orders_grouped[["ordcnt", "custcnt", "ordval"]].fillna(0).astype(int)
        return other_orders_grouped

    #Orders having color Blue and White


# Open SO Details Data for Material Coverage Page
class GetOpenSODetailsView(APIView):
    @swagger_auto_schema(
        operation_description="Retrieve Open SO Details",
        manual_parameters=[
            openapi.Parameter('Color', openapi.IN_QUERY, description="Comma-separated list of colors", type=openapi.TYPE_STRING),
            openapi.Parameter('KitStatus', openapi.IN_QUERY, description="Status of the kit", type=openapi.TYPE_STRING),
            openapi.Parameter('S', openapi.IN_QUERY, description="Start date", type=openapi.TYPE_INTEGER),
            openapi.Parameter('E', openapi.IN_QUERY, description="End date", type=openapi.TYPE_INTEGER),
            openapi.Parameter('export', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Excel export parameters'), 
            openapi.Parameter('report_name', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='report name parameter'),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            400: "Bad Request: Error retrieving data"
        }
    )
    def put(self,request):
        return self.getOpenSoDetailsData(request,method = 'PUT')
    
    def  get(self,request):
        return self.getOpenSoDetailsData(request)

    def getOpenSoDetailsData(self, request, method = 'GET'):
        try:
            if method == 'PUT':
                data = request.data
            else:
                data = None 
            headers = data.get('headers',{}) if data else None
            export = request.GET.get('export')
            export_param = bool(int(export)) if export is not None else False
            isChildren_param = request.GET.get('isChildren')
            isChildren = bool(int(isChildren_param)) if isChildren_param else False

            report_name = request.GET.get('report_name')
            all_orders_flag = (request.GET.get('AOD') == 'true')
            allColors = ['Black', 'Red', 'Yellow', 'Green', 'White', 'Blue','']  # All colors for MTO orders
            all_kit_status = ['PK', 'NK', 'FK']  # All kit status
            colors = None
            page = int(request.GET.get('page', DefaultPageConfig.default_page_number.value))
            page_size = int(request.GET.get('page_size', DefaultPageConfig.default_page_size.value))
            kit_status = None
            if (not all_orders_flag): 
                colors=request.GET.get('Color').split(',')
                kit_status = request.GET.get('KitStatus')
                s = int(request.GET.get('S'))
                e = int(request.GET.get('E'))
            filter_data = request.data

            orders = None
            if all_orders_flag:
                colors = allColors  
                kit_status = all_kit_status
                all_orders_flag = (request.GET.get('AOD') == 'true')
                s = 0
                e = 30
                today = timezone.now().date()
                start_date = today + timedelta(days=s)
                end_date = today + timedelta(days=e)

                # Create a filter for white/blue (date-filtered) and others (no date filter)
                white_blue_filter = Q(color__in=['White', 'Blue']) & Q(due_date__range=(start_date, end_date))
                other_colors_filter = Q(color__in=colors) & ~Q(color__in=['White', 'Blue'])

                final_filter = white_blue_filter | other_colors_filter

                orders = OrderData.objects.filter(final_filter).values(
                    'order_id', 'item', 'line_id', 'color', 'actual_released_date', 'due_date', 'order_key',
                    'item__attributes', 'item__item_code', 'item__item_description', 'item__item_type__item_type',
                    'item__item_type__item_type_id', 'total_qty', 'pending_qty', 'pending_ccr_qty',
                    'plant__plant_id', 'plant__plant_name', 'dept__dept_id', 'dept__dept_name',
                    'customer__cust_code', 'customer__attribute', 'customer__cust_name',
                    'market_based_order_type', 'route__route_code', 'route__route_id', 'route__route_name',
                    'expected_due_date', 'order_value', 'ccr__ccr_id', 'ccr__ccr_code', 'ccr__ccr_name',
                    'ccr__capacity_per_day', 'computed_dd', 'order_attributes', 'line_order_attributes',
                    'vf_order_type','bpp'
                ).order_by('-bpp')
            # Check if 'White' or 'Blue' are in the colors list
            elif 'White' in colors or 'Blue' in colors:
                # Calculate date range based on today's date
                today = timezone.now().date()
                start_date = today + timedelta(days=s)
                end_date = today + timedelta(days=e)
                
                orders = OrderData.objects.filter(color__in=colors, due_date__range=[start_date, end_date]).values(
                    'order_id', 'item', 'line_id', 'color', 'actual_released_date', 'due_date','order_key', 'item__attributes', 'item__item_code',
                    'item__item_description', 'item__item_type__item_type', 'item__item_type__item_type_id', 'total_qty',
                    'pending_qty', 'pending_ccr_qty', 'plant__plant_id', 'plant__plant_name',
                    'dept__dept_id', 'dept__dept_name', 'customer__cust_code',
                    'customer__attribute', 'customer__cust_name', 'market_based_order_type',
                    'route__route_code', 'route__route_id', 'route__route_name', 'expected_due_date',
                    'order_value', 'ccr__ccr_id', 'ccr__ccr_code', 'ccr__ccr_name', 'ccr__capacity_per_day',
                    'computed_dd', 'order_attributes', 'line_order_attributes', 'vf_order_type','bpp'
                ).order_by('-bpp')
            else:
                # Query MTOOrderData for other colors without date range
                orders = OrderData.objects.filter(color__in=colors).values(
                    'order_id', 'item', 'line_id', 'color', 'actual_released_date', 'due_date','order_key', 'item__attributes', 'item__item_code',
                    'item__item_description', 'item__item_type__item_type', 'item__item_type__item_type_id', 'total_qty',
                    'pending_qty', 'pending_ccr_qty', 'plant__plant_id', 'plant__plant_name',
                    'dept__dept_id', 'dept__dept_name', 'customer__cust_code',
                    'customer__attribute', 'customer__cust_name', 'market_based_order_type',
                    'route__route_code', 'route__route_id', 'route__route_name', 'expected_due_date',
                    'order_value', 'ccr__ccr_id', 'ccr__ccr_code', 'ccr__ccr_name', 'ccr__capacity_per_day',
                    'computed_dd', 'order_attributes', 'line_order_attributes', 'vf_order_type','bpp'
                ).order_by('-bpp')

            orders = filter_order_data_by_params(orders, filter_data)
            order_attr_map = {
                data['order_key']: {
                    **(data.get('order_attributes') or {}),
                    **(data.get('line_order_attributes') or {}),
                    **(data.get('item_attributes') or {}),
                    **(data.get('computed_line_attributes') or {})
                }
                for data in orders if data.get('order_key')
            }
            query = Q()
            for order in orders:
                query |= Q(order_id=order['order_id'], line_item=order['line_id'])
            
            # this from queryset to polars df will conver the ORM to a dataframe and also a empty dataframe with columns if the data is not present
            orders_df = from_queryset_to_polars_df(orders,['order_id', 'item', 'line_id', 'color', 'actual_released_date', 'due_date','order_key', 'item__attributes', 'item__item_code',
                    'item__item_description', 'item__item_type__item_type', 'item__item_type__item_type_id', 'total_qty',
                    'pending_qty', 'pending_ccr_qty', 'plant__plant_id', 'plant__plant_name',
                    'dept__dept_id', 'dept__dept_name', 'customer__cust_code',
                    'customer__attribute', 'customer__cust_name', 'market_based_order_type',
                    'route__route_code', 'route__route_id', 'route__route_name', 'expected_due_date',
                    'order_value', 'ccr__ccr_id', 'ccr__ccr_code', 'ccr__ccr_name', 'ccr__capacity_per_day',
                    'computed_dd', 'order_attributes', 'line_order_attributes', 'vf_order_type','bpp'])
            item_codes = orders_df.select('item').to_series().to_list()
            logger.info("Fetched no of orders")
            if orders_df.is_empty():
                logger.info("No data available")
                return api_response(msg='No data available', data=[], status_code=status.HTTP_200_OK)

            item_batch_size_map = get_item_batchsize(item_codes)

            # Step 1 and 2: Fetch projection order IDs associated with the given order ID and line ID directly
            projection_order_plant_codes = ProjectionOrderDetails.objects.filter(
                query
            ).values_list(
                'order_plant_code', flat=True
            ).distinct()
            logger.info("Fetched projection orders plant")
            
            projection_orders = ProjectionOrder.objects.filter(order_plant_code__in=projection_order_plant_codes).select_related('projection_order_code').values(
                'order_id', 'cust_code', 'cust_name', 'order_date', 'plant_code',
                'projection_order_code__line_item', 'projection_order_code__item_code', 'projection_order_code__balance_order_qty' , 'projection_order_code__quantity' , 'projection_order_code__dispatch_quantity'
            )
            
            #fetched the dataframe for the projection orders
            projection_order_df =  from_queryset_to_polars_df(projection_orders,  [
                'order_id', 'cust_code', 'cust_name', 'order_date', 'plant_code',
                'projection_order_code__line_item', 'projection_order_code__item_code', 'projection_order_code__balance_order_qty' , 'projection_order_code__quantity' , 'projection_order_code__dispatch_quantity'
            ])
            logger.info("Fetched projection orders")

            # renamed column to identify such that i can determine the projection order are there for order df 
            projection_order_df = projection_order_df.rename( {'order_id' : 'order_id_po'})

            projection_order_df = projection_order_df.with_columns([
                pl.col('order_id_po').alias('order_id_po_raw'),
                pl.col('projection_order_code__line_item').alias('projection_order_code__line_item_raw')
            ])
            orders_df = orders_df.join(projection_order_df, left_on=['order_id', 'line_id'], right_on=['order_id_po', 'projection_order_code__line_item_raw'], how='left')
            orders_df = orders_df.filter(pl.col('order_id_po_raw').is_not_null())
            
            # calculating the actual order quantity for the orders
            orders_df = orders_df.with_columns(
            pl.when(
                (pl.col('projection_order_code__quantity').fill_null(0) -
                pl.col('projection_order_code__dispatch_quantity').fill_null(0)) < 0
            )
            .then(0)
            .otherwise(
                pl.col('projection_order_code__quantity').fill_null(0) -
                pl.col('projection_order_code__dispatch_quantity').fill_null(0)
            )
            .alias('actual_order_quantity')
            )

            
            # Call the common function to fetch leaf nodes
            leaf_item_codes = fetch_leaf_nodes_with_plant(polars=True)

            # Fetch data from BatchwiseComponentAllocation
            batchwise_component_allocations = BatchwiseComponentAllocation.objects.filter(
                query
            ).values('order_id', 'line_item', 'item_code','plant_code', 'order_qty','simulated_qty','stock_on_hand','stock_in_qc','stock_in_transit','parent_code','order_remaining','purchase_gap','item_srl_no')
            logger.info("Fetched Batchwise Component Allocations data")
            
            # fetched the batchwise data in the dataframe
            allocation_dict_df = from_queryset_to_polars_df(batchwise_component_allocations,[
                'order_id', 'line_item', 'item_code', 'order_qty','simulated_qty','stock_on_hand','stock_in_qc','stock_in_transit','parent_code'
                ,'order_remaining','purchase_gap','item_srl_no','plant_code'
            ])

            # Get all orders from batchwise_component_allocation which have component as leaf nodes
            allocation_dict_df = allocation_dict_df.join(leaf_item_codes,left_on=['item_code','plant_code'], right_on=['component_item_code','plant_code'], how='inner')
            allocation_dict_df = allocation_dict_df.with_row_count(name="row_nr")
            allocation_dict_df = allocation_dict_df.with_columns(
            (pl.col('stock_on_hand') + pl.col('stock_in_qc') + pl.col('stock_in_transit')).alias('rmall')
            )

            # getting the rm which are minimum for the order
            min_rmall_idx = allocation_dict_df.group_by(['order_id', 'line_item']).agg(
                pl.col('rmall').min().alias('min_rmall')
            )

            # Use those indices to get the desired rows 
            min_rm_allocation_dict_df = allocation_dict_df.join(min_rmall_idx, left_on=['order_id','line_item','rmall'], right_on=['order_id','line_item','min_rmall'])
            min_rm_allocation_dict_df = (
                min_rm_allocation_dict_df
                .sort("row_nr")  # ensures consistent ordering
                .unique(subset=["order_id", "line_item"], keep="first")
            )
            
            # maintaining this for calculating the number of full kit for the orders
            minRMData = min_rm_allocation_dict_df.rename({
                'item_code' : 'rm', 
                'order_qty' : 'rmqty',
                'rmall' : 'rmall',
                'simulated_qty' : 'eas',
                'purchase_gap' : 'pg',
                'item_srl_no':'item_srl_no'
            })
            
            # understanding the full kit status based on the total rmqty and order remaining for the orders
            allocation_data = allocation_dict_df.group_by(['order_id', 'line_item']).agg([
            pl.col('order_qty').sum().alias('order_qty_sum'),
            pl.col('order_remaining').sum().alias('order_remaining_sum')
            ])
            

            projection_order_item_codes = projection_order_df['projection_order_code__item_code'].to_list()
            all_item_codes = list(leaf_item_codes) + list(projection_order_item_codes)

            item_descriptions_and_attributes_df = from_queryset_to_polars_df(ItemMaster.objects.filter(item_code__in=all_item_codes).values('item_code', 'item_description','attributes'), [
                'item_code', 'item_description','attributes'
            ])
            logger.info("Fetched Item descriptions from ItemMaster")
            
            # getting the description for each rm 
            allocation_dict_df = allocation_dict_df.join(item_descriptions_and_attributes_df, left_on='item_code', right_on='item_code', how='left')            

            # Fetch all necessary BOMDetail objects in a single query
            bom_details = BOMDetail.objects.annotate(srl_no = Concat(
                Cast('bom_srl_no', CharField()),
                Value('_'),
                Cast('item_srl_no', CharField())
            )).values(
                'component_item_code', 'bom_srl_no__parent_item_code', 'component_qty','srl_no','bom_srl_no__plant_code'
            )
            logger.info("Fetched BOMDetail data")

            bom_detail_dict = from_queryset_to_polars_df(bom_details,['component_item_code', 'bom_srl_no__parent_item_code', 'component_qty','srl_no','bom_srl_no__plant_code']).rename({'bom_srl_no__plant_code':'plant_code'})
            bom_detail_dict = bom_detail_dict.join(leaf_item_codes, on=['component_item_code','plant_code'], how='inner')
            

            # getting the component qty such that full kit can be calculated
            minRMData = minRMData.join(bom_detail_dict, left_on=['rm', 'parent_code', 'item_srl_no'],
                                   right_on=['component_item_code', 'bom_srl_no__parent_item_code', 'srl_no'], how='left')
            minRMData = minRMData.drop(['plant_code_right'])
            kit_allocation_data = None
            kit_allocation_data = {}

            batchwise_allocation_flag = is_batchwise_allocation()


            order_allocation_data = allocation_data.rename( {'order_id' : 'order_id_batchwise','line_item' : 'line_item_batchwise'})

            # renaming the column name such that the column can be mantained
            order_allocation_data = order_allocation_data.with_columns([
                pl.col('order_id_batchwise').alias('order_id_batchwise_raw'),
                pl.col('line_item_batchwise').alias('line_item_batchwise_raw')
            ])

            #filtering the orders such that if it is not available in batchwise full kit should not be calculated , joining with the allocation data for the orders 
            orders_df = orders_df.join(order_allocation_data , how = 'left' , left_on = ['order_id','line_id'] , right_on=['order_id_batchwise','line_item_batchwise']  )
            orders_df = orders_df.filter(pl.col('order_id_batchwise_raw').is_not_null() & pl.col('line_item_batchwise_raw').is_not_null())
            if batchwise_allocation_flag:
                # merging for calculating the full kit based on the component qty
                orders_df = orders_df.join(minRMData, left_on = ['order_id','line_id'], right_on = ['order_id','line_item'] , how = 'left' )
                orders_df = orders_df.drop(['plant_code_right'])

                # conditional statement for the fka calculation
                orders_df = orders_df.with_columns(
                pl.when((pl.col('component_qty').is_not_null()) & (pl.col('component_qty') != 0))
                .then((pl.col('rmall') / pl.col('component_qty')).round(0))
                .otherwise(0)
                .alias('fka')
            )
                # determining FK based on the order qty and order remaining sum for the children of the orders
                orders_df = orders_df.with_columns(
                pl.when(pl.col('order_qty_sum') == pl.col('order_remaining_sum')).then(pl.lit('NK'))
                .when(pl.col('order_remaining_sum') == 0).then(pl.lit('FK'))
                .when(
                    (pl.col('order_qty_sum') > pl.col('order_remaining_sum')) &
                    (pl.col('order_remaining_sum') > 0)
                ).then(pl.lit('PK'))
                .otherwise(pl.lit('')).alias('kit_value')
                )
                orders_df = orders_df.drop(['rm','rmqty','pg'])
            else:
                # for partial allocation 
                kit_allocation_data = KitAllocation.objects.filter(query).values('order_id', 'line_item', 'plant_code', 'bom_level', 'no_of_kits')
                kit_allocation_data_df = from_queryset_to_polars_df(kit_allocation_data,[
                    'order_id', 'line_item', 'plant_code', 'bom_level', 'no_of_kits'
                ])

                # attaching the bom level as for the no of kits from the kit allocation
                orders_df = orders_df.with_columns(pl.lit(0).alias("bom_level"))

                # getting the no of kits by merging the kit allocation data in the order df and that no of kits will be the full kit available
                orders_df = orders_df.join(kit_allocation_data_df, left_on=['order_id','line_id','plant_code','bom_level'], right_on=['order_id','line_item','plant_code','bom_level'], how = 'left' )
                orders_df = orders_df.with_columns(pl.col('no_of_kits').fill_null(0))
                orders_df = orders_df.with_columns(pl.col('no_of_kits').alias('fka'))
                orders_df = orders_df.with_columns(
                    pl.when(pl.col('no_of_kits') == 0).then(pl.lit('NK'))
                    .when(pl.col('actual_order_quantity') == pl.col('no_of_kits')).then(pl.lit('FK'))
                    .when((pl.col('actual_order_quantity') > pl.col('no_of_kits')) & (pl.col('no_of_kits') > 0)).then(pl.lit('PK'))
                    .otherwise(pl.lit('')).alias('kit_value')
                )
            logger.info("Fetched kit allocation details")
            

            orders_df = orders_df.with_columns([
            pl.when(pl.col('kit_value') == 'FK').then(pl.lit('Full Kit'))
            .when(pl.col('kit_value') == 'PK').then(pl.lit('Partial Kit'))
            .when(pl.col('kit_value') == 'NK').then(pl.lit('No Kit'))
            .otherwise(pl.lit('')).alias('fk_status'),

            pl.when(pl.col('kit_value') == 'FK').then(pl.lit('Purple'))
            .when((pl.col('kit_value') == 'NK') | (pl.col('kit_value') == 'PK')).then(pl.lit('Orange'))
            .otherwise(pl.lit('')).alias('rm_color')
            ])
            # orders_df = orders_df.fill_nan(None).fill_null(None)
            if not all_orders_flag:
                orders_df = orders_df.filter(pl.col('kit_value') == kit_status)
            if not export_param:
                record_count , nop = get_order_information(orders_df, page , page_size)
                orders_df = get_pagewise_data(orders_df , page , page_size)

            
            #calculating full kit availibility percentage using formula (fka/oq)*100
            logger.info('calculating full kit availibility percentage')
            orders_df = orders_df.with_columns(
                    pl.when(pl.col("actual_order_quantity") > 0.00)
                        .then(
                            pl.min_horizontal(pl.col("fka") / pl.col("actual_order_quantity") * 100,pl.lit(100.0)).round(2)
                            )
                        .otherwise(0.00)
                    .alias("full_kit_availibility_percentage"))
            
            logger.info('calculated full kit availibility percentage')
            #fetching eco stock data
            logger.info("fetching eco stock data")
            eco_stock_data = EcoStock.objects.filter(
                type__in=['StockInHand', 'StockInQC', 'StockInTransit']
            ).prefetch_related('plant_code').values('item_code','plant_code__plant_code','plant_code').annotate(eco_total_qty=Sum('quantity')).values('item_code','plant_code','plant_code__plant_code')
            logger.info("Fetched EcoStock data")

            eco_stock_dict = from_queryset_to_polars_df(eco_stock_data,['item_code','plant_code','eco_total_qty','plant_code__plant_code'])
            eco_stock_dict = eco_stock_dict.join(leaf_item_codes, left_on=['item_code','plant_code__plant_code'],right_on=['component_item_code','plant_code'],how='inner')
            allocation_dict_df = allocation_dict_df.join(orders_df , left_on = ['order_id','line_item'], right_on=['order_id','line_id'] , how='left')
            allocation_dict_df = allocation_dict_df.join(eco_stock_dict, left_on = ['item_code','plant__plant_id'],right_on=['item_code','plant_code'],how = 'left')
            allocation_dict_df = allocation_dict_df.with_columns(pl.col('eco_total_qty').fill_null(0).alias('rma'))
            allocation_dict_df = allocation_dict_df.rename({
                "rm_color" : "clr",
                "item_description" : "rmd",
                'item_code' : 'rm', 
                'order_qty' : 'rmqty',
                'rmall' : 'rmall',
                'purchase_gap' : 'pg',
            })
            allocations_by_order = allocation_dict_df.group_by(['order_id', 'line_item']).agg([
            pl.struct(["rm", "rmd", "clr", "rmqty", "pg", "rmall", "attributes"]).alias("children")
            ])
            allocations_by_order = allocations_by_order.with_columns(
                pl.col("children").map_elements(self.expand_children_with_attributes, return_dtype=pl.Object)
            )
            orders_df = orders_df.join(allocations_by_order, left_on=['order_id', 'line_id'], right_on=['order_id', 'line_item'], how='left')
            
            orders_df = orders_df.join(item_descriptions_and_attributes_df , left_on = ['projection_order_code__item_code'] , right_on = ['item_code'], how = 'left')
            columns_map = {
                "color" : "cp",
                "projection_order_code__line_item" : "oli",
                "order_id" : "on",
                "item" : "ic",
                "actual_order_quantity" : "oq",
                "fka" : "fka",
                "cust_name" : "cn",
                "cust_code" : "cc",
                "order_date" : "ord",
                "due_date" : "odd",
                "children" : "children",
                "plant__plant_id" : "pl",
                "plant_code" : "pln",
                "order_key" : "order_key",
                "fk_status" : "fk_status",
                "item__item_description" : "fgd",
                "item__item_code" : "fgc",
                "actual_released_date" : "ordRD",
                "full_kit_availibility_percentage":"fkapr"

            }

            orders_df = orders_df.rename( columns_map)
            column_list = list(columns_map.values())
            orders_df = orders_df[column_list]

            filtered_data = orders_df.to_dicts()
            for data in filtered_data:
                data.update(order_attr_map.get(data['order_key'], {}))
                data['bs'] = item_batch_size_map.get(data.get('ic',""))
            
            if export is not None:
                if filtered_data is None or len(filtered_data) == 0:
                    logger.info("No data available")
                    return api_response(msg='No data available', data=[], status_code=status.HTTP_200_OK)

                return CustomExcelExport(
                    filtered_data,
                    report_name,
                    headers,
                    isGrouped=True,
                    isChildren=isChildren,
                    child_element=eChildName.children.value,
                    name_of_report_parent=eReportName.material_so.value,
                    name_of_report_child=eReportName.material_so_child.value
                    )
            paginator = MTOPagination()
            paginated_response_data = paginator.create_paginated_response(request, filtered_data, nop , record_count)

            logger.info("Returning the paginated response")
            return api_response(data = paginated_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)

    def expand_children_with_attributes(self,children_list):
        expanded = []
        for child in children_list:
            base = dict(child)
            attrs = base.pop("attributes", {}) or {}
            base.update(attrs)
            expanded.append(base)
        return expanded
