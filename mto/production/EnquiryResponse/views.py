from functools import reduce
from operator import and_
from mto_app.models import ( CCRMaster, FOL_Data, CCRItemTypeMapping, BufferItemTypeMapping)
import logging
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework import status
from drf_yasg import openapi
from mto_app.common.commonfunctions import ( api_response, CustomPagination)
from django.db.models import Q


logger = logging.getLogger(__name__)

class EnquiryResponseView(APIView):
    pagination_class = CustomPagination

    @swagger_auto_schema(
        operation_description="Get data for Enquiry Response Screen",
        manual_parameters=[
            openapi.Parameter('itemType', openapi.IN_QUERY, description="Item Type", type=openapi.TYPE_INTEGER),
            openapi.Parameter('plant', openapi.IN_QUERY, description="Plant", type=openapi.TYPE_INTEGER),
            openapi.Parameter('dept', openapi.IN_QUERY, description="Department", type=openapi.TYPE_INTEGER),
            openapi.Parameter('ccrGp', openapi.IN_QUERY, description="CCR Group", type=openapi.TYPE_INTEGER),
            openapi.Parameter('ccr', openapi.IN_QUERY, description="CCR", type=openapi.TYPE_INTEGER)
        ],
         responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            logger.info("Enquiry Response View Porcessing started")
            #Read filter parameters
            param_item_type = request.GET.get('itemType')
            param_ccr = request.GET.get('ccr')
            param_ccr_group = request.GET.get('ccrGp')
            param_plant = request.GET.get('plant')
            param_dept = request.GET.get('dept')

            # Fetch ccr master data , ccr group name, plant name and dept name
            ccr_data =  CCRMaster.objects.filter(plant__is_valid = True).all().prefetch_related('ccr_group').prefetch_related('plant').prefetch_related('dept').values('ccr_id','ccr_code','ccr_name','ccr_group_id','ccr_group__ccr_group_name','plant_id','dept_id','plant__plant_name','dept__dept_name')
            logger.info("Fetched CCR master data")

            #Prepare a querylist for applying filter
            queryList  = []
            if param_ccr is not None:
                queryList.append(Q(ccr_id = param_ccr))
            if param_ccr_group is not None:
                queryList.append(Q(ccr_group_id = param_ccr_group))
            if param_plant is not None:
                queryList.append(Q(plant_id = param_plant))
            if param_dept is not None:
                queryList.append(Q(dept_id = param_dept))

            if len(queryList) > 0:
                combined_qer = reduce(and_, queryList)
                ccr_data = ccr_data.filter(combined_qer)
            logger.info("Query list formed based on parameters")

            #Get ccr ids into ccr_id_list
            ccr_id_list = [ccr['ccr_id'] for ccr in ccr_data]
            logger.info("CCR id list created")

            # Fetch Item Type (Product Group) for all CCRs
            ccr_item_types = CCRItemTypeMapping.objects.filter(ccr_id__in=ccr_id_list).prefetch_related('item_type').values('ccr_id','item_type__item_type_id','item_type__item_type')
            logger.info("Fetched Item Types for all CCRs")

            # Get ccr_item_types based on applied filter
            if param_item_type is not None:
                ccr_item_types = ccr_item_types.filter(item_type__item_type_id__in = param_item_type)
            logger.info("Item type filter applied on ccr_item_types collection")

            #Get ccr ids into ccr_id_list
            ccr_id_list = [ccr['ccr_id'] for ccr in ccr_item_types]
            logger.info("CCR id list created")

            #Get CCRData based on ItemType filter
            ccr_data = ccr_data.filter(ccr_id__in=ccr_id_list)
            logger.info("ccr data filtered based on item type parameter")

            #Prepare Item type id list to get corresponding buffers
            item_type_id_list = [item['item_type__item_type_id'] for item in ccr_item_types]
            logger.info("Item type filter applied on ccr_item_types collection")

            # Fetch Item Type (Product Group) and buffer mapping data
            item_types_buffer = BufferItemTypeMapping.objects.filter(item_type__in=item_type_id_list).prefetch_related('buffer').prefetch_related('buffer__buffer_type').values('item_type','buffer__buffer_size','buffer__buffer_type__buffer_type')
            buffer_item_type_map = {}
            for item in item_type_id_list:
                if item not in buffer_item_type_map:
                    buffer_item_type_map[item] = { 'id' : item,
                                                   'proc_size' : 0,
                                                   'prod_size' : 0,
                                                }

            for itemType in item_types_buffer:
                buffer_type = itemType['buffer__buffer_type__buffer_type'].lower()
                if 'prod' in buffer_type:
                    buffer_item_type_map[itemType['item_type']]['prod_size'] =itemType['buffer__buffer_size']
                elif 'proc' in buffer_type:
                    buffer_item_type_map[itemType['item_type']]['proc_size'] =itemType['buffer__buffer_size']

            logger.info("Fetched Item Types- Buffer mapping data")

            # create ccr-item_type-buffer mapping
            ccr_item_type_buffer_map = {}
            for data in ccr_item_types:
                if data['ccr_id'] not in ccr_item_type_buffer_map:
                    ccr_item_type_buffer_map[data['ccr_id']] = {}
                ccr_item_type_buffer_map[data['ccr_id']][data['item_type__item_type']] = buffer_item_type_map[data['item_type__item_type_id']]
            logger.info("Created CCR_ItemType_Buffer mapping")

            # Fetch FOL data for all CCRs
            fol_data = FOL_Data.objects.filter(ccr_id__in=ccr_id_list).values('ccr_id','fol_in_days')
            ccr_fol_map = {fol['ccr_id']: fol['fol_in_days'] for fol in fol_data}
            logger.info("Fetched fol data for all CCRs")

            #create response data
            response_data = []
            for ccr in ccr_data:
                ccr_name = ccr['ccr_name']
                ccr_group_name = ccr['ccr_group__ccr_group_name']
                plant_name = ccr['plant__plant_name']
                dept_name = ccr['dept__dept_name']
                fol = ccr_fol_map.get(ccr['ccr_id'])
                item_types = ccr_item_type_buffer_map.get(ccr['ccr_id'])

                data = {
                    'cid' : ccr['ccr_id'],
                    'plid' : ccr['plant_id'],
                    'plnm' : plant_name,
                    'dpid' : ccr['dept_id'],
                    'dpnm' : dept_name,
                    'gid' : ccr['ccr_group_id'],
                    'gnm' : ccr_group_name,
                    'cnm' : ccr_name,
                    'fol' : fol,
                    'it' : item_types
                }
                response_data.append(data)
            logger.info("Response data created")

            # sort response data if it has more than 1 record
            if len(response_data) > 1:
                response_data = sorted(response_data, key=lambda x: (x['fol'] is not None, x['fol']), reverse=True)
                logger.info("Response data arranged in descending order based on FOL")
                
            logger.info("Returning the paginated response for Enquiry response view")
            return api_response(response_data, msg="Enquiry response data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in Enquiry Response View: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)
