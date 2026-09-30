from collections import  defaultdict
from rest_framework.views import APIView
from rest_framework import status
from mto_app.models import ( BatchwiseComponentAllocation ,PendingOrder, EcoStock, ItemMaster ,OrderData)
from mto_app.common.commonfunctions import (api_response , CustomPagination, fetch_leaf_nodes,filter_order_data_by_params, 
ExcelExportData , sort_color_priority , GetUserDetails, DataPermissionFilterForOrderData ,
get_color_mapping,get_order_information , get_pagewise_data , MTOPagination )
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging
from django.db.models import Sum, Value, IntegerField, Case, When
import pandas as pd
from mto_app.utils import eReportName
import numpy as np

logger = logging.getLogger(__name__)

# Get material requirement data            
class GetMaterialRequirementDataView(APIView):
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

    def getColorPercentages(self , row):
        color_percentages = {}
        color_mapping = get_color_mapping()
        total_orders = row['nooi']
        color_percentages = {color_mapping.get(color, color):round((count / total_orders) * 100, 2) for color, count in row["colors"].items()}
        return color_percentages

    def get(self, request): 
        return self.materialRequirementData(request) 

    def put(self,request): 
        return self.materialRequirementData(request,method = 'PUT')
    
    def materialRequirementData(self, request, format=None, method = 'GET'):
        try:
            headers = None
            if method == 'PUT':
                filter_data = request.data
                headers = filter_data.get('headers',{}) if filter_data else None
            else:
                filter_data = None

            export = request.GET.get('export')
            export_param = bool(int(export)) if export else None
            report_name = request.GET.get('report_name')
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))

            release_date = request.GET.get('releaseDate')
            logger.info(f"Received GET request with releaseDate: {release_date}")
            request_data = request.data
            if not release_date:
                logger.error("releaseDate parameter is required")
                return api_response(error="releaseDate parameter is required", status_code=status.HTTP_400_BAD_REQUEST)
            
            product_permissions,location_permissions,is_admin = GetUserDetails(request_data)
            logger.info('Permission data is fetched from the payload')  

            # from ccr_id field all are required for filter api
            orders = OrderData.objects.filter(planned_release_date__lte=release_date).values('order_id', 'line_id', 'color', 'planned_release_date',
                'ccr__ccr_id', 'customer__cust_code', 'customer__cust_name', 'plant__plant_name', 'item__item_description',
                'dept__dept_id', 'order_value', 'vf_order_type', 'item__item_code')
            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            order_color_map = {(order['order_id'], order['line_id']): order['color'] for order in orders}
            logger.info("Fetched no of orders")

            if filter_data:
                orders = filter_order_data_by_params(orders, filter_data)

            # Call the common function to fetch leaf nodes (RM present at leaf node)
            leaf_item_codes = fetch_leaf_nodes()
            if orders:
                orders_df = pd.DataFrame(list(orders))
                # Fetch ItemMaster descriptions
                item_master = ItemMaster.objects.filter(item_code__in=leaf_item_codes)

                # Creating the dataframe for item master to directly merge the description based on item code
                item_master_df = pd.DataFrame(list(item_master.values('item_code', 'item_description','attributes')), columns = ['item_code', 'item_description','attributes'])
                logger.info("Fetched ItemMaster descriptions")

                order_id_list = orders_df['order_id'].unique().tolist()
                line_id_list = orders_df['line_id'].unique().tolist()

                eco_stock = EcoStock.objects.filter(item_code__in=leaf_item_codes,).values('item_code').annotate(
                    in_stk=Case(
                        When(type='StockInHand', then=Sum('quantity')),
                        default=Value(0),
                        output_field=IntegerField(),
                    ),
                    in_transit=Case(
                        When(type__in=['StockInQC', 'StockInTransit'], then=Sum('quantity')),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
                eco_stock_df = pd.DataFrame(list(eco_stock))

                # aggregating based on the item code and adding the stock and transit
                eco_stock_df = eco_stock_df.groupby('item_code').agg(in_stk = ('in_stk','sum') , in_transit = ('in_transit','sum'))

                pending_po = PendingOrder.objects.filter(item_code__in = leaf_item_codes, type__in = 'Pending_PO' ).values('item_code', 'type', 'order_qty')
                
                # creating the dataframe for pending po if there else use the column name
                pending_po_df = pd.DataFrame(list(pending_po),columns=['item_code', 'type', 'order_qty'])
                logger.info("Fetched EcoStock and PendingOrder data")

                # if not pending_po_df.empty:
                #merging the qty based on the item code in the eco stock 
                eco_stock_df = eco_stock_df.merge(pending_po_df, on='item_code', how='left', suffixes=('', '_po'))
                if 'order_qty_po' not in eco_stock_df.columns:
                    eco_stock_df['order_qty_po'] = 0
                eco_stock_df['ppo'] = eco_stock_df['order_qty_po'].fillna(0).astype(int)

                batchwise_component_allocations = BatchwiseComponentAllocation.objects.filter(
                    order_id__in=order_id_list,
                    line_item__in=line_id_list,
                    item_code__in=leaf_item_codes
                ).values('order_id', 'line_item', 'item_code','order_remaining')
                logger.info("Fetched Batchwise Component Allocations data")

                #converting the batchwise component into df 
                batchwise_component_allocations_df = pd.DataFrame(list(batchwise_component_allocations),columns=['order_id', 'line_item', 'item_code', 'order_remaining'])
                
                # attaching the colors such that in one iteration i can get the color and count the orders
                batchwise_component_allocations_df = batchwise_component_allocations_df.merge(orders_df[['order_id', 'line_id', 'color']], left_on=['order_id', 'line_item'],  
                right_on=['order_id','line_id'],how='left')
                
                # grouping the batchwise data based on item code and counting the number of orders impacted and sum of order remaining
                allocation_summary_df = batchwise_component_allocations_df.groupby('item_code').agg(
                    nooi=('order_id', 'count'),  # Count of unique order IDs
                    rmr=('order_remaining', 'sum')  # Sum of order_remaining
                ).reset_index()
                
                color_mapping = get_color_mapping()
                
                # attaching the colors as default for all the order which will be having the item code in allocation summary
                allocation_summary_df['colors'] = allocation_summary_df['item_code'].apply(lambda x: defaultdict(int))
                allocation_summary_df['colors'] = allocation_summary_df['colors'].apply(lambda x: {color: 0 for color in color_mapping.values()})
                logger.info("Created allocation summary DataFrame")


                color_counts = {key : value for key , value in batchwise_component_allocations_df.groupby('item_code')}
                # counting the item code and the order with the specific color in this section of the code
                for item_code , row_group in color_counts.items():
                    for index, row in row_group.iterrows():
                        if item_code in  allocation_summary_df['item_code'].values:
                            color = row['color']
                            if color in color_mapping:
                                mapped_color = color_mapping[color]
                                idx = allocation_summary_df.index[allocation_summary_df['item_code'] == item_code][0]
                                allocation_summary_df.at[idx, 'colors'][mapped_color] += 1

                logger.info("Defined color mapping dictionary")
                
                allocation_summary_df['cp'] = [[] for _ in range(len(allocation_summary_df))]  # Initialize 'cp' column with empty lists
                
                # attaching the color percentages or the number of order contributing towards the color priority of the item code 
                for index , row in allocation_summary_df.iterrows():
                    color_percentages = self.getColorPercentages(row)
                    allocation_summary_df.at[index, 'cp'] = [color_percentages]            
                logger.info("Created color percentages for each item code")

                data = allocation_summary_df.to_dict(orient='records')
                data.sort(key=sort_color_priority)
                allocation_summary_df  = pd.DataFrame(list(data))

                # applying the pagination on the generated data because the color priority based sorting is required 
                record_count  , nop = get_order_information(allocation_summary_df , page , page_size) 
                allocation_summary_df = get_pagewise_data(allocation_summary_df , page , page_size)

                # renaming the column to be send in the response 
                allocation_summary_df.rename(columns = {'item_code': 'rmc', 'nooi': 'nooi', 'rmr': 'rmr'}, inplace=True)
                allocation_summary_df['msrm'] = allocation_summary_df['rmr']
                allocation_summary_df['rd'] = release_date
                allocation_summary_df['net_r'] = 0
                allocation_summary_df['rmh'] = 0
                allocation_summary_df['rmt'] = 0
                allocation_summary_df['ppo'] = 0

                # attaching the item description to the item code in the allocation summary 
                allocation_summary_df = allocation_summary_df.merge(item_master_df , left_on='rmc', right_on='item_code', how='left', suffixes=('', '_eco'))
                allocation_summary_df['rmd'] = allocation_summary_df['item_description'].fillna('')
                data_df = pd.DataFrame(allocation_summary_df,columns=['cp', 'rmc', 'rmd', 'nooi', 'rmr', 'msrm', 'rd', 'net_r', 'rmh', 'rmt', 'ppo','attributes'])
                attributes_df = pd.json_normalize(data_df['attributes'])
                data_df = pd.concat([data_df.drop(columns=['attributes']), attributes_df], axis=1)
                data_df = data_df.merge(eco_stock_df , left_on='rmc', right_on='item_code', how='left', suffixes=('', '_eco'))
                data_df['rmh'] = data_df['in_stk'].fillna(0).astype(int)
                data_df['rmt'] = data_df['in_transit'].fillna(0).astype(int)
                data_df['ppo'] = data_df['ppo'].fillna(0).astype(int)
                data_df['net_r'] = np.maximum(data_df['rmr'] - data_df['rmh'] - data_df['ppo'],0)
                data_df = data_df.astype(object).where(pd.notna(data_df), None)
                logger.info("merged additional attributes in data")

                data = data_df.to_dict(orient='records')
            else:
                data = []
                record_count, nop = 0, 0
                logger.info("No orders found after applying filters")

            if export_param:
                if report_name and headers:
                    return ExcelExportData(data, report_name, eReportName.materialRequirement.value, headers)
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

            paginator = MTOPagination()
            paginated_response_data = paginator.create_paginated_response(request , data , nop , record_count)

            logger.info("Prepared response data successfully")
            return api_response(data = paginated_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)

    # def materialRequirementData_old(self, request, format=None, method = 'GET'):
    #     try:
    #         headers = None
    #         if method == 'PUT':
    #             filter_data = request.data
    #             headers = filter_data.get('headers',{}) if filter_data else None
    #         else:
    #             filter_data = None

    #         export = request.GET.get('export')
    #         export_param = bool(int(export)) if export else None
    #         report_name = request.GET.get('report_name')

    #         release_date = request.GET.get('releaseDate')
    #         logger.info(f"Received GET request with releaseDate: {release_date}")
    #         data = request.data
    #         if not release_date:
    #             logger.error("releaseDate parameter is required")
    #             return api_response(error="releaseDate parameter is required", status_code=status.HTTP_400_BAD_REQUEST)
            
    #         product_permissions,location_permissions,is_admin = GetUserDetails(data)
    #         logger.info('Permission data is fetched from the payload')  

    #         # from ccr_id field all are required for filter api
    #         orders = OrderData.objects.filter(planned_release_date__lte=release_date).values('order_id', 'line_id', 'color', 'planned_release_date',
    #             'ccr__ccr_id', 'customer__cust_code', 'customer__cust_name', 'plant__plant_name', 'item__item_description',
    #             'dept__dept_id', 'order_value', 'vf_order_type', 'item__item_code')
    #         orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
    #         logger.info('Filtered the order data based on the permissions of the user')

    #         order_color_map = {(order['order_id'], order['line_id']): order['color'] for order in orders}
    #         logger.info("Fetched no of orders")

    #         if filter_data:
    #             orders = filter_order_data_by_params(orders, filter_data)

    #         # Call the common function to fetch leaf nodes (RM present at leaf node)
    #         leaf_item_codes = fetch_leaf_nodes()

    #         # Fetch ItemMaster descriptions
    #         item_master_map = {item.item_code: item.item_description for item in ItemMaster.objects.filter(item_code__in=leaf_item_codes)}
    #         logger.info("Fetched ItemMaster descriptions")

    #         order_id_list = [order['order_id'] for order in orders]
    #         line_id_list = [order['line_id'] for order in orders]

    #         eco_stock = EcoStock.objects.filter(item_code__in=leaf_item_codes,).values('item_code').annotate(
    #             in_stk=Case(
    #                 When(type='StockInHand', then=Sum('quantity')),
    #                 default=Value(0),
    #                 output_field=IntegerField(),
    #             ),
    #             in_transit=Case(
    #                 When(type__in=['StockInQC', 'StockInTransit'], then=Sum('quantity')),
    #                 default=Value(0),
    #                 output_field=IntegerField(),
    #             )
    #         )

    #         pending_po = PendingOrder.objects.filter(item_code__in = leaf_item_codes, type__in = 'Pending_PO' ).values('item_code', 'type', 'order_qty')

    #         for stock in eco_stock:
    #             stock['ppo'] = 0
    #             if pending_po:
    #                 for ppo in pending_po:
    #                     if stock['item_code'] == ppo['item_code']:
    #                         stock['ppo'] = ppo['order_qty']

    #         # Fetch data from BatchwiseComponentAllocation records based on orders and leaf nodes
    #         batchwise_component_allocations = BatchwiseComponentAllocation.objects.filter(
    #             order_id__in=order_id_list,
    #             line_item__in=line_id_list,
    #             item_code__in=leaf_item_codes
    #         ).values('order_id', 'line_item', 'item_code','order_remaining')
    #         logger.info("Fetched Batchwise Component Allocations data")

    #          # Prepare allocation summary
    #         allocation_summary = defaultdict(lambda: {
    #             "nooi": 0,
    #             "rmr": 0,
    #             "colors": defaultdict(int)
    #         })
    #         color_mapping = get_color_mapping()
    #         logger.info("Defined color mapping dictionary")

    #         for allocation in batchwise_component_allocations:
    #             item_code = allocation['item_code']
    #             order_remaining = allocation['order_remaining']
    #             order_id = allocation['order_id']
    #             line_item = allocation['line_item']
    #             color = order_color_map.get((order_id, line_item), None)

    #             allocation_summary[item_code]["nooi"] += 1
    #             allocation_summary[item_code]["rmr"] += order_remaining

    #             for color_name in color_mapping:
    #                 if color_mapping[color_name] not in allocation_summary[item_code]["colors"]:
    #                     allocation_summary[item_code]["colors"][color_mapping[color_name]] = 0
    #             #Fetch color based on item_code 
    #             if color:
    #                 allocation_summary[item_code]["colors"][color] += 1

    #         # Define a mapping dictionary for colors
            

    #         # Create the response data
    #         data = []
    #         for item_code, summary in allocation_summary.items():
    #             description = item_master_map.get(item_code)

    #             #Calculate color percentage for colors 
    #             total_orders = summary["nooi"]
    #             color_percentages = {color_mapping.get(color, color):round((count / total_orders) * 100, 2) for color, count in summary["colors"].items()}

    #             data.append({
    #                 "cp": [color_percentages],
    #                 "rmc": item_code,
    #                 "rmd": description if description else '',
    #                 "nooi": summary["nooi"],
    #                 "rmr": summary["rmr"] if summary["rmr"] else 0, 
    #                 "msrm": summary["rmr"],
    #                 "rd": release_date,
    #                 "net_r": 0,
    #                 "rmh": 0,
    #                 "rmt": 0,
    #                 "ppo": 0
    #             })
    #         data.sort(key=sort_color_priority)
    #         for rm in data:
    #             for stock in eco_stock:
    #                 if rm['rmc'] == stock['item_code']:
    #                     rm["rmh"] = stock['in_stk']
    #                     rm["rmt"] = stock['in_transit']
    #                     rm["ppo"] = stock['ppo']
    #         logger.info("merged additional attributes in data")

    #         for rm in data:
    #             rm['net_r'] = rm['rmr'] - rm['rmh'] - rm['ppo']
    #         logger.info("net requirement attribute is updated data")

    #         # Sort the data based on "rmc": item_code in alphabetical order
    #         # data.sort(key=lambda x: sort_key(x["rmc"]))

    #         if export_param:
    #             if report_name and headers:
    #                 return ExcelExportData(data,report_name,headers)
    #             else:
    #                 return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

    #         paginator = CustomPagination()
    #         paginated_response_data = paginator.paginate_queryset(data, request)

    #         logger.info("Prepared response data successfully")
    #         return paginator.get_paginated_response(paginated_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
    #     except Exception as e:
    #         logger.error(f"Exception occurred: {str(e)}")
    #         return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)


# Get material requirement data for release date only      
class GetMaterialRequirementDayWiseDataView(APIView):
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
        return self.materialRequirementDayWiseData(request) 

    def put(self,request): 
        return self.materialRequirementDayWiseData(request,method = 'PUT') 

    def materialRequirementDayWiseData(self, request, format=None, method = 'GET'):
        try:
            headers = None
            if method == 'PUT':
                filter_data = request.data
                headers = filter_data.get('headers',{}) if filter_data else None
            else:
                filter_data = None

            export = request.GET.get('export')
            export_param = bool(int(export)) if export else None
            report_name = request.GET.get('report_name')

            release_date = request.GET.get('releaseDate')
            logger.info(f"Received GET request with releaseDate: {release_date}")
            data = request.data
            if not release_date:
                logger.error("releaseDate parameter is required")
                return api_response(error="releaseDate parameter is required", status_code=status.HTTP_400_BAD_REQUEST)
            product_permissions,location_permissions,is_admin = GetUserDetails(data)
            logger.info('Permission data is fetched from the payload')
            # from ccr_id field all are required for filter api
            orders = OrderData.objects.filter(planned_release_date = release_date).values('order_id', 'line_id', 'color', 'planned_release_date',
                'ccr__ccr_id', 'customer__cust_code', 'customer__cust_name', 'plant__plant_name', 'item__item_description',
                'dept__dept_id', 'order_value', 'vf_order_type', 'item__item_code')
            orders = DataPermissionFilterForOrderData(orders,product_permissions,location_permissions,is_admin)
            logger.info('Filtered the order data based on the permissions of the user')

            order_color_map = {(order['order_id'], order['line_id']): order['color'] for order in orders}
            logger.info("Fetched no of orders")

            if filter_data:
                orders = filter_order_data_by_params(orders, filter_data)

            # Call the common function to fetch leaf nodes (RM present at leaf node)
            leaf_item_codes = fetch_leaf_nodes()

            # Fetch ItemMaster descriptions
            item_master_map = {item.item_code: item for item in ItemMaster.objects.filter(item_code__in=leaf_item_codes)}
            logger.info("Fetched ItemMaster descriptions")

            order_id_list = [order['order_id'] for order in orders]
            line_id_list = [order['line_id'] for order in orders]

            eco_stock = EcoStock.objects.filter(item_code__in=leaf_item_codes,).values('item_code').annotate(
                in_stk=Case(
                    When(type='StockInHand', then='quantity'),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                in_transit=Case(
                    When(type__in=['StockInQC', 'StockInTransit'], then=Sum('quantity')),
                    default=Value(0),
                    output_field=IntegerField(),                                                       
                )
            )

            pending_po = PendingOrder.objects.filter(item_code__in = leaf_item_codes).values('item_code', 'type', 'order_qty')

            for stock in eco_stock:
                stock['ppo'] = 0
                if pending_po:
                    for ppo in pending_po:
                        if stock['item_code'] == ppo['item_code']:
                            stock['ppo'] = ppo['order_qty']

            # Fetch data from BatchwiseComponentAllocation records based on orders and leaf nodes
            batchwise_component_allocations = BatchwiseComponentAllocation.objects.filter(
                order_id__in=order_id_list,
                line_item__in=line_id_list,
                item_code__in=leaf_item_codes
            ).values('order_id', 'line_item', 'item_code','order_remaining')
            logger.info("Fetched Batchwise Component Allocations data")
            
            color_mapping = get_color_mapping()
            logger.info("Defined color mapping dictionary")

             # Prepare allocation summary
            allocation_summary = defaultdict(lambda: {
                "nooi": 0,
                "rmr": 0,
                "colors": defaultdict(int)
            })

            for allocation in batchwise_component_allocations:
                item_code = allocation['item_code']
                order_remaining = allocation['order_remaining']
                order_id = allocation['order_id']
                line_item = allocation['line_item']
                color = order_color_map.get((order_id, line_item), None)

                allocation_summary[item_code]["nooi"] += 1
                allocation_summary[item_code]["rmr"] += order_remaining

                for color_name in color_mapping:
                    if color_mapping[color_name] not in allocation_summary[item_code]["colors"]:
                        allocation_summary[item_code]["colors"][color_mapping[color_name]] = 0
                #Fetch color based on item_code 
                if color:
                    allocation_summary[item_code]["colors"][color] += 1

            # Define a mapping dictionary for colors
            # Create the response data
            data = []
            for item_code, summary in allocation_summary.items():
                item_master_instance = item_master_map.get(item_code)
                description = item_master_instance.item_description if item_master_instance else None
                attributes = item_master_instance.attributes if item_master_instance else {}

                #Calculate color percentage for colors 
                total_orders = summary["nooi"]
                color_percentages = {color_mapping.get(color, color):round((count / total_orders) * 100, 2) for color, count in summary["colors"].items()}
                item_data = {
                    "cp": [color_percentages],
                    "rmc": item_code,
                    "rmd": description if description else '',
                    "nooi": summary["nooi"],
                    "rmr": summary["rmr"],
                    "msrm": summary["rmr"],
                    "rd": release_date,
                    "net_r": 0,
                    "rmh": 0,
                    "rmt": 0,
                    "ppo": 0
                }
                item_data.update(attributes)  # Merge attributes into the main dictionary
                data.append(item_data)
            data.sort(key=sort_color_priority)   #this is required to be discussed again
            for rm in data:
                for stock in eco_stock:
                    if rm['rmc'] == stock['item_code']:
                        rm["rmh"] = stock['in_stk']
                        rm["rmt"] = stock['in_transit']
                        rm["ppo"] = stock['ppo']

            for rm in data:
                rm['net_r'] = rm['rmr'] - rm['rmh'] - rm['ppo']

            # Sort the data based on "rmc": item_code in alphabetical order
            # data.sort(key=lambda x: sort_key(x["rmc"]))

            if export_param:
                if report_name and headers:
                    return ExcelExportData(data, report_name, eReportName.materialRequirement.value, headers)
                else:
                    return api_response(msg=f'report name or header is not provided', status_code=status.HTTP_400_BAD_REQUEST)

            paginator = CustomPagination()
            paginated_response_data = paginator.paginate_queryset(data, request)

            logger.info("Prepared response data successfully")
            return paginator.get_paginated_response(paginated_response_data, msg="Data fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST)
