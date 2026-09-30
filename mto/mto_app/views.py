from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status

from .serializers import BufferMasterSerializer, CCRMasterSerializer, DeptMasterSerializer, OrderTypeMasterSerializer, PlantHolidayListSerializer, UIReportConfigurationsSerializer, PlantMasterSerializer,UserwiseUIReportConfigurationsSerializer
from .common.commonfunctions import CustomPagination, api_response, filter_data_by_params, get_order_data,get_ccr_fol_gap_mapping, ePageName
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import F, Max
from django.db import transaction
from django.conf import settings
from .models import *
import logging
from datetime import datetime
from enum import Enum
import json
import os
from django.http import FileResponse
from rest_framework.response import Response
from mto_app.utils import AttributeTypes
from collections import defaultdict
from datetime import date
import bisect
import math

logger = logging.getLogger(__name__)


class SystemTypeEnum(Enum):
    MTO = "MTO"
    MTA = "MTA"

def is_request_input_valid(page_name, release_date, all_orders, is_assigned, color, start_range, end_range, rm_horizon, sup_horizon):
    result = api_response(status_code=status.HTTP_200_OK)

    if page_name is None:
        logger.error("Page name parameter is required")
        result = api_response(error="Page name paramter is required", status_code=status.HTTP_400_BAD_REQUEST)

    # Check for "Proc_Material_Requirement" and release_date
    if page_name == ePageName.PROC_MATERIAL_REQUIREMENT.value and not release_date:
        result =  api_response(error="release_date is a required parameter", status_code=status.HTTP_400_BAD_REQUEST)

    # Check for "Proc_Procurement_Planning" and release_date
    if page_name == ePageName.PROC_PROCUREMENT_PLANNING.value and not release_date:
        result = api_response(error="release_date is a required parameter", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Check for "Prod_Dynamic_Release_Management" and ao
    if page_name == ePageName.PROD_DYNAMIC_RELEASE_MANAGEMENT.value and not all_orders:
        result = api_response(error="ao is a required parameter", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Check for "Poogi_Reason_For_Delayed_Orders" and ao
    if page_name == ePageName.POOGI_REASON_FOR_DELAYED_ORDERS.value and not is_assigned:
        result = api_response(error="isAssigned is a required parameter", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Check for "Material_Coverage_for_Open_Sales_Order" and ensure Color, S, E are provided
    if page_name == ePageName.MATERIAL_COVERAGE_FOR_OPEN_SO.value:
        if not color or not start_range or not end_range:
            result = api_response(
                error="Color, S, and E are required parameters for Material_Coverage_for_Open_Sales_Order",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
    # Check for "Proc_Expediting_RM_And_Suppliers" and ensure rm_horizon or sup_horizon is provided
    if page_name == ePageName.PROC_EXPEDITING_RM_AND_SUPPLIERS.value:
        if not rm_horizon and not sup_horizon:
            result = api_response(
                error="Either rm_horizon or sup_horizon is required for Material_Coverage_for_Open_Sales_Order",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
    maxAllowedHorizon = 90
    if page_name == ePageName.PROC_EXPEDITING_RM_AND_SUPPLIERS.value:
        if rm_horizon:
            if int(rm_horizon) > maxAllowedHorizon:
                result = api_response(msg="Data beyond 90 days cannot be shown", status_code=status.HTTP_400_BAD_REQUEST)
        if sup_horizon:
            if int(sup_horizon) > maxAllowedHorizon:
                result = api_response(msg="Data beyond 90 days cannot be shown", status_code=status.HTTP_400_BAD_REQUEST)
    
    return result

class GetFilterDataView(APIView):
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'page_name',
                openapi.IN_QUERY,
                description="Pass page type to know for which API filter needs to be applied",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                'release_date',
                openapi.IN_QUERY,
                description="Optional release date to filter the data",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                'Color',
                openapi.IN_QUERY,
                description="Colors to filter orders",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                'S',
                openapi.IN_QUERY,
                description="Start range for due date",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                'E',
                openapi.IN_QUERY,
                description="End range for due date",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                'FromDate',
                openapi.IN_QUERY,
                description="from which date data need to be collected",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                'ToDate',
                openapi.IN_QUERY,
                description="to which date data need to be collected, this will be the last date of current month",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                'ao',
                openapi.IN_QUERY,
                description="parameter for all orders",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                'rm_horizon',
                openapi.IN_QUERY,
                description="RM Horizon",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                'supplier_horizon',
                openapi.IN_QUERY,
                description="Supplier Horizon",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
            openapi.Parameter(
                'isAssigned',
                openapi.IN_QUERY,
                description="Get orders based on POOGI reason assigned or not",
                type=openapi.TYPE_INTEGER,
                required=False,
            ),
        ],
        responses={200: 'Success', 404: 'Not Found'}
    )
    def get(self, request, format=None):
        return self.get_filter_data(request, format=None)
    
    def post(self, request, format=None):
        return self.get_filter_data(request, format=None)
        
    def get_filter_data(self, request, format=None):
        try:
            page_name = request.GET.get('page_name')
            release_date = request.GET.get('release_date')
            all_orders = request.GET.get('ao')
            color = request.GET.get('Color')
            start_range = request.GET.get('S')
            end_range = request.GET.get('E')
            rm_horizon = request.GET.get('rm_horizon')
            sup_horizon = request.GET.get('supplier_horizon')
            is_assigned = request.GET.get('isAssigned')

            # function to check request input is valid or not
            result = is_request_input_valid(page_name,release_date, all_orders, is_assigned, color, start_range, end_range, rm_horizon, sup_horizon)
            if result.status_code != status.HTTP_200_OK:
                return result
            
            #function to filter out order data based on page name
            order_data = get_order_data(page_name, request, release_date=release_date)
            logger.info("Fetched order data from MTOOrderData")

            order_info_map = {(order['order_id'], order['line_id']): {'order_value': order['order_value'],'cust_code': order['customer'],'major_reason': order['major_reason'], 'minor_reason': order['minor_reason'],'dept': order['dept'], 'vf_order_type': order['vf_order_type'], 'order_type': order['order_type']} for order in order_data}
            line_attributes_map = {(line['order_id'], line['line_id']): line['line_order_attributes'] for line in order_data}

            # Fetch item descriptions from ItemMaster based on item codes from orders
            all_item_codes = set(order['item'] for order in order_data)
            sku_descriptions = {sku['item_code']: sku['item_description'] for sku in ItemMaster.objects.filter(item_code__in=all_item_codes).values('item_code', 'item_description')}
            logger.info("Fetched SKU descriptions from ItemMaster")

            # Get unique plant_ids from mto_data
            if page_name == ePageName.PROC_DAY_WISE_COVERAGE.value or page_name == ePageName.POOGI_REASON_FOR_DELAYED_ORDERS.value:
                plant_ids= set(order['plant'] for order in order_data)
            else:
                plant_ids = order_data.values_list('plant', flat=True).distinct()
            
            # Fetch plant_name from PlantMaster based on plant_ids
            plant_data = PlantMaster.objects.filter(plant_id__in=plant_ids).values('plant_id', 'plant_name')
            logger.info("Fetched plant name from PlantMaster")
            plant_info_map = {plant['plant_id']: plant['plant_name'] for plant in plant_data}

            # Fetch buffer information from OrderBufferMapping and BufferMaster
            if page_name == ePageName.PROC_DAY_WISE_COVERAGE.value or page_name == ePageName.POOGI_REASON_FOR_DELAYED_ORDERS.value:
                order_keys = set(order['order_key'] for order in order_data)
            else:
                order_keys = order_data.values_list('order_key', flat=True).distinct()
            buffer_mappings = OrderBufferMapping.objects.filter(order__order_key__in=order_keys).values('order__order_id', 'order__line_id', 'buffer_id')
            buffer_ids = set(mapping['buffer_id'] for mapping in buffer_mappings)
            buffer_data = BufferMaster.objects.filter(buffer_id__in=buffer_ids).values('buffer_id', 'buffer_size', 'buffer_type__buffer_type')

            buffer_info_map = {(mapping['order__order_id'], mapping['order__line_id']): {'pbsz': None, 'pcbsz': None} for mapping in buffer_mappings}

            for buffer in buffer_data:
                buffer_type = buffer['buffer_type__buffer_type']
                for mapping in buffer_mappings:
                    if mapping['buffer_id'] == buffer['buffer_id']:
                        if buffer_type == 'Production':
                            buffer_info_map[(mapping['order__order_id'], mapping['order__line_id'])]['pbsz'] = buffer['buffer_size']
                        elif buffer_type == 'Procurement':
                            buffer_info_map[(mapping['order__order_id'], mapping['order__line_id'])]['pcbsz'] = buffer['buffer_size']

            logger.info("Fetched buffer related information from OrderBufferMapping and BufferMaster")

            #Get unique route_ids from order_data
            if page_name == ePageName.PROC_DAY_WISE_COVERAGE.value or page_name == ePageName.POOGI_REASON_FOR_DELAYED_ORDERS.value:
                route_ids = set(order['route'] for order in order_data)
            else:
                route_ids = order_data.values_list('route_id', flat=True).distinct()

            # Fetch route, ccr, and ccr_grp details from RouteDetails based on route_ids
            route_details = RouteDetails.objects.filter(route_id__in=route_ids).values('route_id', 'ccr_id', 'ccr_grp_id','ccr__dept_id')
            route_info_map = {}
            for detail in route_details:
                route_id = detail['route_id']
                if route_id not in route_info_map:
                    route_info_map[route_id] = []
                route_info_map[route_id].append({
                    "rid": detail['route_id'],
                    "ccrid": detail['ccr_id'],
                    "grpid": detail['ccr_grp_id'],
                    "deptid": detail['ccr__dept_id']
                })
            logger.info("Fetched route, ccr, and ccr_grp details from RouteDetails based on route_ids")

            #Fetch customer related information
            if page_name == ePageName.PROC_DAY_WISE_COVERAGE.value or page_name == ePageName.POOGI_REASON_FOR_DELAYED_ORDERS.value:
                customer_codes = set(order['customer'] for order in order_data)
            else:
                customer_codes = order_data.values_list('customer', flat=True).distinct()
            customer_data = CustomerMaster.objects.filter(id__in=customer_codes).values('id', 'cust_code', 'cust_name', 'attribute')
            customer_transformed_data = []
            for customer in customer_data:
                customer_info = {
                    "cc": customer['cust_code'],
                    "cn": customer['cust_name']
                }
                if customer['attribute']:
                    customer_info.update(customer['attribute'])      # directly update json value of object
                customer_transformed_data.append(customer_info)

            logger.info("Fetched customer related information")

            order_attributes_data = []
            for orders in order_data:
                order_info = {
                    "id": orders['order_id']
                }
                if orders['order_attributes']:
                    order_info.update(orders['order_attributes'])
                order_attributes_data.append(order_info)

            transformed_data = [
                {
                    "id": item['order_id'],
                    "lid": item['line_id'],
                    "ic": item['item'],
                    "ide": sku_descriptions.get(item['item'], ""),
                    "ov": order_info_map.get((item['order_id'], item['line_id']), {}).get('order_value'),
                    "cc": order_info_map.get((item['order_id'], item['line_id']), {}).get('cust_code'),
                    "ot": order_info_map.get((item['order_id'], item['line_id']), {}).get('order_type'),
                    "pn": plant_info_map.get(item['plant']),
                    "route": item['route'],
                    "pbsz": buffer_info_map.get((item['order_id'], item['line_id']), {}).get('pbsz'),  # Adding production buffer size
                    "pcbsz": buffer_info_map.get((item['order_id'], item['line_id']), {}).get('pcbsz'),  # Adding procurement buffer size
                    "majid": order_info_map.get((item['order_id'], item['line_id']), {}).get('major_reason'),
                    "minid": order_info_map.get((item['order_id'], item['line_id']), {}).get('minor_reason'),
                    "deptid": order_info_map.get((item['order_id'], item['line_id']), {}).get('dept'),
                    "ms": order_info_map.get((item['order_id'], item['line_id']), {}).get('vf_order_type'),
                }
                for item in order_data
            
            ]

            # Adding the line attributes if they exist
            for item in transformed_data:
                line_attributes = line_attributes_map.get((item['id'], item['lid']), {})
                if line_attributes:
                    item.update(line_attributes)

            # Add mappings details to the response data
            mappings = [
                {
                    "rid": detail['route_id'],
                    "ccrid": detail['ccr_id'],
                    "grpid": detail['ccr_grp_id'],
                    "deptid": detail['ccr__dept_id']
                }
                for detail in route_details
            ]
            logger.info("Added mappings detail")

            # Add ccr details to the response data
            ccr_data = CCRMaster.objects.all().values('ccr_id', 'ccr_name')
            ccrs = {
                detail['ccr_id']: {
                    "nm": detail['ccr_name']
                }
                for detail in ccr_data
            }
            logger.info("Added Master CCR details")

            # Add ccr group details to the response data
            ccr_grp_data = CCRGroupMaster.objects.all().values('ccr_group_id', 'ccr_group_name')
            ccrgroups = {
                detail['ccr_group_id']: {
                    "nm": detail['ccr_group_name']
                }
                for detail in ccr_grp_data
            }
            logger.info("Added Master CCR Group details")

            # Add deptartment details to the response data
            dept_data = DeptMaster.objects.all().values('dept_id', 'dept_name')
            dept = {
                detail['dept_id']: {
                    "nm": detail['dept_name']
                }
                for detail in dept_data
            }
            logger.info("Added Department details")

            # Add major reason details to the response data
            major_reason_data = POOGIMajorReason.objects.all().values('major_reason_id','major_reason_code')
            major_reason = {
                detail['major_reason_id']: {
                    "name": detail['major_reason_code'],
                    "min": []
                }
                for detail in major_reason_data
            }
            logger.info("Added major reason details")

            # Add minor details to the related major reason
            minor_reason_data = POOGIMinorReason.objects.all().values('minor_reason_id','minor_reason_code','major_reason_id')
            for detail in minor_reason_data:
                major_reason_id = detail['major_reason_id']
                minor_reason_info = {
                    "id": detail['minor_reason_id'],
                    "name": detail['minor_reason_code']
                }
                if major_reason_id in major_reason:
                    major_reason[major_reason_id]["min"].append(minor_reason_info)

            logger.info("Added minor reason details")

            # Add hdr key data details to the response data
            hdr_key_data = AttributeConfiguration.objects.filter(attribute_type__in=[AttributeTypes.Customer.value, AttributeTypes.Order.value, AttributeTypes.Line.value],is_active = True).values('attribute_name','attribute_type', 'short_name', 'filter_sequence','is_number')
            cattr = []
            oattr = []
            lattr = []

            for attribute in hdr_key_data:
                attr_info = {"key": attribute['short_name'], "name": attribute['attribute_name'], "filter_sequence": attribute['filter_sequence'],'is_number': attribute['is_number']}
                if attribute['attribute_type'] == "customer":
                    cattr.append(attr_info)
                elif attribute['attribute_type'] == "order":
                    oattr.append(attr_info)
                elif attribute['attribute_type'] == "line":
                    lattr.append(attr_info)

            # Sort the attributes based on the filter_sequence
            cattr.sort(key=lambda x: x['filter_sequence'])
            oattr.sort(key=lambda x: x['filter_sequence'])
            lattr.sort(key=lambda x: x['filter_sequence'])

            # Remove the filter_sequence key from each attribute after sorting
            for attr_list in [cattr, oattr, lattr]:
                for attr in attr_list:
                    attr.pop('filter_sequence', None)

            hdrkeymap = {
                "cattr": cattr,
                "oattr": oattr,
                "lattr": lattr
            }
            logger.info("Added hdr key map details")

            system_type = DBRSettings.objects.get(flag="SystemType").value
            # Create the enum based on the system type
            if system_type == "2":
                system_type_enum = [SystemTypeEnum.MTO.value, SystemTypeEnum.MTA.value]
            elif system_type == "1":
                system_type_enum = [SystemTypeEnum.MTA.value]
            elif system_type == "0":
                system_type_enum = [SystemTypeEnum.MTO.value]
            else:
                system_type_enum = []

            logger.info("Fetched system type based on DBRSettings model")

            logger.info('All records updated successfully')
            return api_response(msg='All records fetched successfully', data={"customers": customer_transformed_data, "ordLineItems": transformed_data, "ordAttr": order_attributes_data, "mappings": mappings, "ccrs": ccrs, "ccrgroups": ccrgroups, "dept": dept, "mjar": major_reason, "hdrkeymap": hdrkeymap, "system_type": system_type_enum}, status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred: {str(e)}")
            return api_response(error=f"Object does not exist: {str(e)}", status_code=status.HTTP_400_BAD_REQUEST) 
        
        

class GetAllReportDataView(APIView):
    @swagger_auto_schema(
        operation_description="Get all report details data",
        responses={
            200: openapi.Response(description="ok"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        try:
            reports_path = os.path.join(settings.BASE_DIR, "Downloads", "ReportPaths.json")
            with open(reports_path, 'r') as file:
                json_file = file.read()
                report_data = json.loads(json_file)
            if report_data is not None:
                return api_response(data = report_data,msg="Report data has been fetched successfully",status_code=status.HTTP_200_OK)
        except Exception as e:
            return api_response(msg=f'An exception has occurred in getting all report data due to {str(e)}',status_code=status.HTTP_400_BAD_REQUEST)
            
class DownloadReportFileView(APIView):
    @swagger_auto_schema(
        operation_description="Download report data",
        manual_parameters=[
            openapi.Parameter('report_name', openapi.IN_QUERY, description="Report Name to download file", type=openapi.TYPE_STRING)
        ],
        responses={
            200: openapi.Response(description="File downloaded successfully"),
            404: openapi.Response(description="File not found"),
            400: openapi.Response(description="Bad Request")
        }
    )
    def get(self, request):
        try:
            report_name = request.GET.get('report_name')

            if not report_name:
                return api_response(msg="Report name is required", status_code=status.HTTP_400_BAD_REQUEST)

            reports_path = os.path.join(settings.BASE_DIR, "Downloads", "ReportPaths.json")
            logger.info("Reports path details loaded")

            with open(reports_path, 'rb') as file:
                report_data = json.load(file)            
            if report_data and report_name in report_data:
                current_report = report_data[report_name]
                file_name = current_report.get("downloadName")
                file_path = current_report.get("path")

                if os.path.exists(file_path):
                    file_bytes = open(file_path, 'rb')
                    content_type = current_report.get("fileType", 'application/octet-stream')
                    if file_name.endswith('.zip'):
                        content_type = 'application/zip'
                    response = FileResponse(file_bytes, content_type=content_type)
                    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
                    logger.info("File has been attached to the headers of the repsonse")

                    return response
                else:
                    logger.info("File with the given report name is not found")
                    return api_response(msg="File not found for the given report name", status_code=status.HTTP_404_NOT_FOUND)
            else:
                return api_response(msg = "File not found", status_code=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logging.error(f"An exception occurred: {str(e)}")
            return api_response(msg =f'An exception occurred: {str(e)}', status_code=status.HTTP_400_BAD_REQUEST)


class GetAllPermission(APIView):
    def get(self, request):
        return api_response({'location' : [{
            "id": 1,
                "location_heirarchy_1": "Dept1",
                "location_heirarchy_2": "",
                "location_heirarchy_3": ""
        }] , 'product' : [{
            "id": 1,
                "product_hierarchy_1": "RM1",
                "product_hierarchy_2": "",
                "product_hierarchy_3": ""
        }]} , msg= "permission data fetched successfully", status_code=status.HTTP_200_OK)

class GetMTOHeadersView(APIView):
    @swagger_auto_schema(
        operation_description="Get all headers for permissions",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        try:
            permission_type = MTOPermissionType.objects.values('type_id','type_name').order_by('sequence')
            logger.info('Fetched MTO Permission Type')
            permission_headers = MTOPermissionHeader.objects.values('mto_permission_type_id','header_id','header_name').order_by('level')
            logger.info('Fetched MTO Permission Headers')
            dict_permission_header = {}
            for type in permission_type:
                permission_header_data = permission_headers.filter(mto_permission_type_id = type['type_id'])
                dict_permission_header[type['type_name']] = []
                for header in permission_header_data:
                   dict_permission_header[type['type_name']].append(header['header_name'])

            logger.info('Created dictionary as output data')   

            return api_response(data= dict_permission_header, msg='MTO Permission Headers fetched successfully', status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.error(f"Exception occurred while fetching MTO Permission headers: {str(ex)}")
            return api_response(error=str(ex), status_code=status.HTTP_400_BAD_REQUEST)

class GetMTOPermissionDetailsView(APIView):
    @swagger_auto_schema(
        operation_description="Get MTO Permission Details",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        try:
            # Get MTO Permission Details
            permission_type = MTOPermissionType.objects.values('type_id','type_name').order_by('sequence')
            logger.info('Fetched MTO Permission Type')
            permission_details = MTOPermissionDetails.objects.annotate(id = F('permission_details_id')).values('id','level1','level2','level3','mto_permission_type_id')
            logger.info('Fetched MTO Permission Details')

            response_data = {}
            for type in permission_type:
                response_data[type['type_name']] = []
                if 'order' in type['type_name'].lower():
                    permission_details_for_type = permission_details.filter(mto_permission_type_id = type['type_id']).annotate(product_hierarchy_1 = F('level1'), product_hierarchy_2 = F('level2'), product_hierarchy_3 = F('level3')).values('id','product_hierarchy_1','product_hierarchy_2','product_hierarchy_3')
                else:
                    permission_details_for_type = permission_details.filter(mto_permission_type_id = type['type_id']).annotate(location_heirarchy_1 = F('level1'), location_heirarchy_2 = F('level2'), location_heirarchy_3 = F('level3')).values('id','location_heirarchy_1','location_heirarchy_2','location_heirarchy_3')
                response_data[type['type_name']].append(permission_details_for_type)

            return api_response(data=response_data, msg='MTO permission details fetched successfully', status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred while fetching MTO permission details: {str(ex)}")
            return api_response(error=str(ex), status_code=status.HTTP_400_BAD_REQUEST)

class GetMaxFolDateForCcrView(APIView):
    @swagger_auto_schema(
        operation_description="Fetch maximum FOL date per CCR and plant based on today's date and horizon values.",
        responses={
            200: openapi.Response(description="Successful Response"),
            404: openapi.Response(description="No Records Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        try:
            todays_date = date.today()
            fol_raw_data = FOL_Data.objects.values('ccr_id', 'fol_in_days', 'ccr__fol_horizon')
            fol_data = {
                fol['ccr_id']: {
                    'fol_in_days': fol['fol_in_days'],
                    'fol_horizon': fol['ccr__fol_horizon']
                }
                for fol in fol_raw_data
            }
            
            dailyWorkingCalendarData = DailyWorkingCalendar.objects.filter(
                ccr_id__in=fol_data.keys(),
                working_date__gte=todays_date
            ).values('plant_id', 'ccr_id', 'lno', 'working_date')

            calendar_map = defaultdict(lambda: defaultdict(list))  # plant_id → ccr_id → list of (lno, date)
            lno_date_map = {}  # (plant_id, ccr_id, lno) → working_date

            for row in dailyWorkingCalendarData:
                plant_id = row['plant_id']
                ccr_id = row['ccr_id']
                lno = row['lno']
                wdate = row['working_date']

                calendar_map[plant_id][ccr_id].append((lno, wdate))
                lno_date_map[(plant_id, ccr_id, lno)] = wdate

            result = defaultdict(dict)
            for plant_id, ccrs in calendar_map.items():
                for ccr_id, lno_dates in ccrs.items():
                    sorted_by_date = sorted(lno_dates, key=lambda x: x[1])
                    sorted_dates = [d for _, d in sorted_by_date]
                    sorted_lnos = [lno for lno, _ in sorted_by_date]

                    # Find today's or next available date using binary search
                    pos = bisect.bisect_left(sorted_dates, todays_date)
                    if pos >= len(sorted_dates):
                        continue  # No working date after today

                    today_lno = sorted_lnos[pos]

                    ccr_info = fol_data.get(ccr_id, {})
                    fol_days = math.ceil(ccr_info.get('fol_in_days', 0) or 0)
                    fol_horizon = ccr_info.get('fol_horizon', 0)
                    calculated_lno = today_lno + fol_days

                    if fol_horizon < (calculated_lno - today_lno):
                        calculated_lno = today_lno +  fol_horizon

                    # Find corresponding date for calculated_lno
                    target_date = lno_date_map.get((plant_id, ccr_id, calculated_lno))
                    if target_date:
                        result[str(plant_id)][str(ccr_id)] = target_date

            return api_response(data=result, msg="Data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Exception occurred at GetMaxFolDateForCcrView: {str(e)}")
