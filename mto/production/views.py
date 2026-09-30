from mto_app.models import ( BatchwiseProductionComponentAllocation, ItemMaster)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import ( api_response)
#Create your views here.

logger = logging.getLogger(__name__)

# Get BM Trend API

class GetBOMLevelWiseAllocationDataView(APIView):
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

    def get(self,request):
        try:
            order_id = request.GET.get('oid')
            line_id = request.GET.get('lid')
            if not order_id and not line_id:
                return api_response(msg='The order id and line id cannot be null')
            level_wise_component_allocation = BatchwiseProductionComponentAllocation.objects.filter(order_id = order_id,line_item = line_id).values(
                    'srl_no', 'order_id', 'line_item', 'item_code', 'plant_code', 'parent_code', 'bom_level',
                    'order_qty', 'stock_on_hand', 'stock_in_qc', 'stock_in_transit', 'order_remaining',
                    'identifier', 'simulated_qty', 'open_po', 'item_srl_no'
                )
            logger.info('component allocations for the orders has been fetched')

            item_descriptions = {order['item_code'] : order['item_description'] for order in ItemMaster.objects.filter(item_code__in = [order['item_code'] for order in level_wise_component_allocation]).values()}
    


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
                            'id' : item_descriptions.get(order['item_code']),
                            'bl' : order['bom_level'] - 1, 
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
                                    'id' : item_descriptions.get(order['item_code']),
                                    'bl' : order['bom_level'] - 1, 
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
                                    'id' : item_descriptions.get(order['item_code']),
                                    'bl' : order['bom_level'] - 1, 
                                    'qty': order['order_qty'],
                                    'soh': order['stock_on_hand'],
                                    'wip': order['stock_in_qc'] + order['stock_in_transit'],
                                    'gap': order['order_qty'] - (order['stock_on_hand'] + order['stock_in_qc'] + order['stock_in_transit']),
                                    'child': []
                                }):
                                    parent_found = True
                                    break
                    
            data = []
            rm_key = (order_id,line_id)
            rm_data = rm_allocated.get(rm_key)
            for key,value in rm_data.items():
                data.append(value)
            return api_response(data=data,msg='data has been fetched successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.error(f'There has been exception in fetching the level wise data due to {str(ex)}')
            return api_response(msg=f'There has been exception in fetching the level wise data due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)