from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status

from ..serializers import BufferMasterSerializer, CCRMasterSerializer, DeptMasterSerializer, OrderTypeMasterSerializer, PlantHolidayListSerializer, UIReportConfigurationsSerializer, PlantMasterSerializer,UserwiseUIReportConfigurationsSerializer
from ..common.commonfunctions import CustomPagination, api_response, filter_data_by_params, get_order_data,get_ccr_fol_gap_mapping, ePageName
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import F, Max
from django.db import transaction
from ..models import *
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


# Get API to fetch report configuration based on report name
class UIReportConfigurationsView(APIView):

    @swagger_auto_schema(
        operation_description="Get report configurations by report name",
        responses={
            200: UIReportConfigurationsSerializer(many=True),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        },
        manual_parameters=[
            openapi.Parameter(
                'report_name',
                openapi.IN_QUERY,
                description="Name of the report",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                'group',
                openapi.IN_QUERY,
                description="Group parameter",
                type=openapi.TYPE_INTEGER,
            ),
        ],
    )
    

    def get_column_details(self, col_details):
        return {
            "cc": col_details['col_code'],
            "cp": col_details['col_position'],
            "hd": col_details['header'],
            "v": col_details['visible'],
            "cla": col_details['cell_alignment'],
            "scc": col_details['short_col_code'],
            "dt": col_details['data_type']
        }

    def get(self, request):
        try:
            report_name = request.GET.get('reportName')
            is_group = request.GET.get('group')

            if not report_name:
                return api_response(msg="Report name is required", status_code=status.HTTP_400_BAD_REQUEST)

            is_group_param = bool(int(is_group)) if is_group else False

            # Fetch report configuration based on report name
            report_config = UIReportConfigurations.objects.filter(report_name = report_name).values('col_code',
                'col_position', 'header', 'visible', 'cell_alignment', 'short_col_code', 'header_grouping_id',
                'header_grouping__header_name', 'data_type').order_by('col_position')
            logger.info("Fetched report configuration from ui report configurations successfully")
            if not report_config:
                return api_response(msg="No records found", status_code=status.HTTP_404_NOT_FOUND)

            report_config_map = {data['col_code']: data for data in report_config}

            if is_group_param:
                result = {}
                for data in report_config:   
                    header_name = None
                    if data['header_grouping_id']:
                        header_name = data['header_grouping__header_name']
                    if header_name not in result and header_name is not None:
                        result[header_name] = {
                            "cc": header_name,
                            "ch": [], 
                        }
                    col_details =  None
                    if data['header_grouping_id']:
                        col_details = report_config_map.get(data['col_code'])
                        if col_details:
                            result[header_name]['ch'].append(self.get_column_details(col_details))

                grouped_attributes = list(result.values())
                return api_response(data=grouped_attributes, msg="Report Configuration fetched successfully", status_code=status.HTTP_200_OK)
            else:
                # Return simple report config if group param is False
                result = [self.get_column_details(item) for item in report_config]
                return api_response(data=result, msg="Report Configuration fetched successfully", status_code=status.HTTP_200_OK)
            
        except Exception as e:
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class CCRMasterView(APIView):
    @swagger_auto_schema(
        operation_description="Get records from CCRMaster table",
        responses={
            200: CCRMasterSerializer(many=True),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            ccr_data = CCRMaster.objects.filter(is_valid = True).all()
            serializer = CCRMasterSerializer(ccr_data, many=True)
            if serializer.data:
                logger.info("Fetched CCR data from CCRMaster")
                return api_response(data=serializer.data, msg="CCRMaster data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at CCRMasterView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class PlantMasterView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from PlantMaster table",
        responses={
            200: PlantMasterSerializer(many=True),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            plant_data = PlantMaster.objects.filter(is_valid = True).all()
            serializer = PlantMasterSerializer(plant_data, many=True)
            if serializer.data:
                logger.info("Fetched Plant data from PlantMaster")
                return api_response(data=serializer.data, msg="PlantMaster data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at PlantMasterView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class BufferMasterView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from BufferMaster table",
        responses={
            200: BufferMasterSerializer(many=True),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            buffer_data = BufferMaster.objects.filter(is_valid = True).all()
            serializer = BufferMasterSerializer(buffer_data, many=True)
            if serializer.data:
                logger.info("Fetched buffer data from BufferMaster")
                return api_response(data=serializer.data, msg="BufferMaster data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred BufferMasterView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class PlantHolidayListView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from PlantHolidayList table",
        responses={
            200: PlantHolidayListSerializer(many=True),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            plant_holiday_list_data = PlantHolidayList.objects.all()
            serializer = PlantHolidayListSerializer(plant_holiday_list_data, many=True)
            if serializer.data:
                logger.info("Fetched Plant Holiday data from PlantHolidayList")
                return api_response(data=serializer.data, msg="PlantHolidayList data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at PlantHolidayListView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class POOGIMajorMinorReasonView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from POOGIMajorReason table",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        },
        manual_parameters=[
            openapi.Parameter(
                'userName',
                openapi.IN_QUERY,
                description="userName of logged in user",
                type=openapi.TYPE_STRING,
            ),
        ],
    )

    def get(self, request, format=None):
        try:
            user_name = request.GET.get('userName')
            logger.info(f"Received GET request with userName: {user_name}")
            if not user_name:
                logger.error("userName parameter is required")
                return api_response(error="userName parameter is required", status_code=status.HTTP_400_BAD_REQUEST)

            plant_ids = UserPlantDeptMapping.objects.filter(user_name = user_name).values_list('plant', flat=True)
            poogi_major_reasons = POOGIMajorReason.objects.filter(plant__in = plant_ids).prefetch_related('poogi_minor_reason_poogi_major_reason').prefetch_related('plant').values('major_reason_id', 'major_reason_code'
                , 'major_reason_desc', 'plant__plant_name', 'poogi_minor_reason_poogi_major_reason__minor_reason_id', 'poogi_minor_reason_poogi_major_reason__minor_reason_code', 'poogi_minor_reason_poogi_major_reason__minor_reason_desc')
            all_major_minor_reasons = {}
            for data in poogi_major_reasons:
                mjr_id = data["major_reason_id"]

                if mjr_id not in all_major_minor_reasons:
                    all_major_minor_reasons[mjr_id] = {
                        'mjr_id': data['major_reason_id'],
                        'mjr_code': data['major_reason_code'],
                        'mjr_desc': data['major_reason_desc'],
                        'plant_name': data['plant__plant_name'],
                        'min_r': []
                    }
                all_major_minor_reasons[mjr_id]['min_r'].append(
                    {
                        "id" : data['poogi_minor_reason_poogi_major_reason__minor_reason_id'],
                        "code" : data['poogi_minor_reason_poogi_major_reason__minor_reason_code'],
                        "desc" : data['poogi_minor_reason_poogi_major_reason__minor_reason_desc']    
                    }
                )
            response_data = list(all_major_minor_reasons.values())
            if all_major_minor_reasons:
                logger.info("Fetched Major and minor reasons from POOGIMajorReason and POOGIMinorReason")
                return api_response(data=response_data, msg="POOGI Major and Minor Reasons data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at POOGIMajorMinorReasonView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class DeptMasterView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from DeptMaster table",
        responses={
            200: DeptMasterSerializer(many=True),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            dept_data = DeptMaster.objects.filter(is_valid = True).all()
            serializer = DeptMasterSerializer(dept_data, many=True)
            if serializer.data:
                logger.info("Fetched buffer data from DeptMaster")
                return api_response(data=serializer.data, msg="DeptMaster data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at DeptMasterView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)
        

class OrderTypeMasterView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from Order Type Master table",
        responses={
            200: OrderTypeMasterSerializer(many=True),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            ord_type_data = OrderTypeMaster.objects.all()
            serializer = OrderTypeMasterSerializer(ord_type_data, many=True)
            if serializer.data:
                logger.info("Fetched Order type data from Order Type Master")
                return api_response(data=serializer.data, msg="Order Type Master data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at OrderTypeMasterView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class RunDateTimeView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from RunDateTime table",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            date = RunDateTime.objects.order_by('-run_date_success').first()
            response_data = None

            if date and date.run_date_success:
                run_date = date.run_date_success.date() # get only date and remove time stamp
                response_data = str(run_date)

            if response_data:
                logger.info("Fetched run date from RunDateTime")
                return api_response(data=response_data, msg="RunDateTime data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at RunDateTimeView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class UserwiseUIReportConfigurationView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from UserwiseUiReportConfiguration table",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        },
        manual_parameters=[
            openapi.Parameter('userName', openapi.IN_QUERY, description="logged in user name", type=openapi.TYPE_STRING),
            openapi.Parameter('reportNameId', openapi.IN_QUERY, description="report for which logged in user have saved the settings", type=openapi.TYPE_STRING)
        ],
    )

    def get(self, request):
        try:
            user_name = request.GET.get('userName')
            report_name_id = request.GET.get('reportNameId')
            response_data = UserwiseUIReportConfigurations.objects.filter(report_name_id = report_name_id, user_name = user_name).values('columns_settings')
            if response_data:
                logger.info("Fetched userwise UI report configuration data from User wise UI Report configuration")
                return api_response(data=response_data, msg="User wise UI Report configuration data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at UserwiseUiReportConfiguration: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class UpdateUserwiseUIReportConfigurationView(APIView):
    serializer_class = UserwiseUIReportConfigurationsSerializer

    @swagger_auto_schema(
        operation_description="Get records from UserwiseUiReportConfiguration table",
        responses={
            200: openapi.Response(description="Successful response"),
            400: openapi.Response(description="Bad Request"),
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'un': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                    'rn_id': openapi.Schema(type=openapi.TYPE_STRING, description='Report name id'),
                    'cs': openapi.Schema(type=openapi.TYPE_STRING, description='columns settings')
                },
                required=['un', 'rn_id', 'cs']
            )
        ),
    )

    def put(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data.get('data'), many=True)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            user_name = ''
            report_name_id = ''
            column_setting = ''
            for item in data:
                user_name = item['un']
                report_name_id = item['rn_id']
                column_setting=item['cs']
            existing_record = UserwiseUIReportConfigurations.objects.filter(user_name = user_name, report_name_id = report_name_id)
            if existing_record:
                UserwiseUIReportConfigurations.objects.filter(user_name = user_name, report_name_id = report_name_id).update(columns_settings = column_setting, updated_on = datetime.now())
            else:
                UserwiseUIReportConfigurations.objects.create(user_name = user_name, report_name_id = report_name_id, columns_settings = column_setting, updated_on = datetime.now())
            logger.info('All records updated successfully')
            return api_response(msg='All records updated successfully', status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error occurred at Update userwise UI report configuration: {e}')
            return api_response(msg=f'Error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)


class CCRGroupMasterView(APIView):
    @swagger_auto_schema(
        operation_description="Get records from CCRGroupMaster",
        manual_parameters=[
                openapi.Parameter('wh',openapi.IN_QUERY,type=openapi.TYPE_INTEGER,description='parameter for requirement of working hour')
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        try:
            working_hours_params = request.GET.get('wh')
            isWorkingHourrequired = bool(int(working_hours_params)) if working_hours_params is not None else False
            ccr_group_data = CCRGroupMaster.objects.filter(is_valid = True).all().prefetch_related('Master_CCRGroup')
            ccr_group_master_dict = {}
            for data in ccr_group_data:
                if data.ccr_group_name not in ccr_group_master_dict:
                    ccr_group_master_dict[data.ccr_group_name] = {
                        'ccr_group_code' : data.ccr_group_code,
                        'ccr_group_id' : data.ccr_group_id,
                        'ccrs' : []
                    }
                for ccr in data.Master_CCRGroup.all():
                    if ccr.is_valid == True:
                        ccr_info = {
                            'ccr_id': ccr.ccr_id,
                            'ccr_code': ccr.ccr_code,
                            'ccr_name': ccr.ccr_name,
                            'plant' : ccr.plant.plant_id if ccr.plant is not None else None
                        }
                        if isWorkingHourrequired:
                            ccr_info['whpd'] = ccr.working_hours_per_day
                    
                        ccr_group_master_dict[data.ccr_group_name]['ccrs'].append(ccr_info)

            return api_response(data = ccr_group_master_dict,msg="All the ccr group master data has been fetched", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred in CCRGroupMasterView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class MarketOperatingLeadTimeMasterView(APIView):
    @swagger_auto_schema(
        operation_description="Get records from Market Operating Lead Time Master",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        try:
            market_lead_time_data = MarketOperatingLeadTimeMaster.objects.values('item_type','item_type__item_type','market_based_order_type','lead_time')
            result = []
            for data in market_lead_time_data:
                combined_data = {
                    'itid' : data['item_type'],
                    'it' : data['item_type__item_type'],
                    'mbot' : data['market_based_order_type'],
                    'lt' : data['lead_time'] 
                }
                result.append(combined_data)
            return api_response(data=result,msg='Master data for market operating lead time has been fetched',status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at MarketOperatingLeadTimeMasterView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class CCRItemTypeMapView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from CCRItemTypeMap table",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            ccr_item_type_mapping = CCRItemTypeMapping.objects.annotate(ccrId=F('ccr__ccr_id'),it=F('item_type__item_type_id'), tt=F('touch_time_in_mins')).values('ccrId','it','tt')

            if ccr_item_type_mapping:
                logger.info("Fetched CCR - Item Type Mapping")
                return api_response(data=ccr_item_type_mapping, msg="CCR - Item Type Mapping fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No CCR - Item Type Mapping found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred in CCRItemTypeMapView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class DailyWorkingCalendarView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from Daily Working calendar table",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            daily_working_calendar = DailyWorkingCalendar.objects.annotate(wd=F('working_date'),ccrId=F('ccr__ccr_id'),PlId=F('plant__plant_id')).values('lno','wd','ccrId','PlId')
            
            if daily_working_calendar:
                logger.info("Fetched Daily Working calendar data")
                return api_response(data=daily_working_calendar, msg="Daily Working calendar fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No Daily Working calendar data found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred in DailyWorkingCalendarView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class FOLDataView(APIView):

    @swagger_auto_schema(
        operation_description="Get FOL data",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            fol_data = FOL_Data.objects.annotate(ccrId=F('ccr__ccr_id'),fol_ed=F('fol_end_date'),ocu=F('occupied_qty_in_units'),ocm=F('occupied_qty_in_mins'),fol=F('fol_in_days'),stpl=F('stpl_in_days')).values('ccrId','fol_ed','ocu','ocm','fol','stpl')
            data = {data['ccrId'] : data for data in fol_data}

            # Fetch fol_gap mapping
            ccr_fol_gap_mapping = get_ccr_fol_gap_mapping()
            for ccr_id, row in data.items():
                row['fol_gap'] = ccr_fol_gap_mapping.get(ccr_id, Decimal('0.00'))
            
            if data:
                logger.info("FOL data fetched")
                return api_response(data=data, msg="FOL data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No FOL data found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred in FOLDataView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class RouteDetailsView(APIView):
 
    @swagger_auto_schema(
        operation_description="Get route details data",
        manual_parameters=[
            openapi.Parameter('r_id', openapi.IN_QUERY, description="Route Id", type=openapi.TYPE_INTEGER)
        ],
         responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
 
    def get(self,request):
        param_route_id = request.GET.get('r_id')
        try:
            if param_route_id is not None:
                route_details = RouteDetails.objects.filter(route_id = param_route_id).annotate(ccrId=F('ccr'),routeId=F('route'),ccrGrpId=F('ccr_grp'),ps=F('position')).values('routeId','ccrId','ccrGrpId','ps')
            else:
                route_details = RouteDetails.objects.annotate(ccrId=F('ccr'),routeId=F('route'),ccrGrpId=F('ccr_grp'),ps=F('position')).values('routeId','ccrId','ccrGrpId','ps')
            if route_details:
                logger.info("Route details fetched")
                return api_response(data=route_details, msg="Route details fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No Route details found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f'An Exception has occurred while fetching Route details {str(e)}')
            return api_response(msg=f'An Exception has occurred while fetching Route details because of {str(e)}',status_code=status.HTTP_400_BAD_REQUEST)

class GetDBRSettingsView(APIView):
    @swagger_auto_schema(
        operation_description='Get the DBR settings',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        try:
            dbr_settings = DBRSettings.objects.values('flag','value')
            data = []
            for settings in dbr_settings:
                combined_data = {
                    'flag' : settings['flag'],
                    'value' : settings['value']
                }
                data.append(combined_data)
            return api_response(data=data,msg='DBR settings has been fetched successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            return api_response(msg=f'An exception has occurred in fetching dbr settings due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)

class GetBufferTypeMasterView(APIView):
    @swagger_auto_schema(
        operation_description='Get Buffer type master',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self,request):
        try:
            buffer_types = BufferTypeMaster.objects.filter(is_valid=True).values('buffer_type_id','buffer_type','buffer_type_desc')
            response_data = []
            for buffer_type in buffer_types:
                data = {
                    'id' : buffer_type['buffer_type_id'],
                    'nm' : buffer_type['buffer_type'],
                    'dsc' : buffer_type['buffer_type_desc']
                }
                response_data.append(data)

            return api_response(data=response_data,msg='Buffer Type Master has been fetched successfully',status_code=status.HTTP_200_OK)
        except Exception as ex:
            return api_response(msg=f'An exception has occurred in fetching Buffer Type Master due to {str(ex)}',status_code=status.HTTP_400_BAD_REQUEST)


class CloseTypeMasterView(APIView):
    @swagger_auto_schema(
        operation_description="Get records from CloseTypeMaster table",
        responses={
            200: openapi.Response(description="Successfully fetched all records"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            close_type_data = CloseTypeMaster.objects.filter(is_valid = True).values()
            if close_type_data:
                logger.info("Fetched close type data from close type master")
                return api_response(data=close_type_data, msg="close type master data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at close type master: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class UserwiseUIReportConfigurationUpdatedView(APIView):

    @swagger_auto_schema(
        operation_description="Get records from UserwiseUiReportConfiguration table and UIReportConfiguration table",
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        },
        manual_parameters=[
            openapi.Parameter('userName', openapi.IN_QUERY, description="logged in user name", type=openapi.TYPE_STRING),
            openapi.Parameter('reportNameId', openapi.IN_QUERY, description="report for which logged in user have saved the settings", type=openapi.TYPE_STRING),
            openapi.Parameter('reportName', openapi.IN_QUERY, description="report name to fetch default report configuration", type=openapi.TYPE_STRING),
            openapi.Parameter('group', openapi.IN_QUERY, description="boolean parameter to fetch grouped report configuration", type=openapi.TYPE_STRING)
        ],
        required=['reportName']
    )

    def get(self, request):
        try:
            user_name = request.GET.get('userName')
            report_name_id = request.GET.get('reportNameId')
            report_name = request.GET.get('reportName')
            if not report_name:
                return api_response(msg="Report name is required", status_code=status.HTTP_400_BAD_REQUEST)

            userwise_response_data = UserwiseUIReportConfigurations.objects.filter(report_name_id = report_name_id, user_name = user_name).values('columns_settings')
            ui_report_config = UIReportConfigurationsView()
            report_data = ui_report_config.get(request)
            if report_data.status_code != status.HTTP_200_OK:
                return report_data
            ui_report_data = report_data.data.get('data')
            if userwise_response_data and ui_report_data:
                userwise_response_data = list(userwise_response_data)[0]
                userwise_response_data['default_coldef'] = ui_report_data
                logger.info("Fetched userwise UI report configuration data from User wise UI Report configuration")
                return api_response(data=userwise_response_data, msg="User wise UI Report configuration data fetched successfully", status_code=status.HTTP_200_OK)
            elif ui_report_data:
                report_data = {'columns_settings': None, 'default_coldef': ui_report_data}
                return api_response(data=report_data, msg="User wise UI Report configuration data fetched successfully", status_code=status.HTTP_200_OK)
            else:
                return api_response(msg="No records found", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Exception occurred at UserwiseUIReportConfigurationUpdatedView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)
