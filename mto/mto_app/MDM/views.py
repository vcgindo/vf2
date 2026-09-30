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
from .Buffer.views import GetBufferTaskByIdView
from .CCR.views import GetCCRTaskByIdView
from .Poogi.views import GetPoogiReasonMasterTaskByIdView
from .Calendar.views import GetCalendarTaskByIdView

logger = logging.getLogger(__name__)

class GetMasterManagementDataView(APIView):

    @swagger_auto_schema(
        operation_description="Get data for Master Management UI",
         responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            logger.info("Get data for Master Management UI started")    

            #get masters from Master_Mapper
            master_mapper_data = MasterMapper.objects.filter(is_valid = True).values('master_id','display_name')
            logger.info("Fetched Master mapper data")

            # Fetch column configuration data
            mdm_config_data =  MDMConfiguration.objects.filter(is_valid = True, visible = True).prefetch_related('master_mapper').values('id','display_name','visible','col_code','col_position','data_type','master_mapper__master_id')
            logger.info("Fetched MDM Configuration data")       

            #create mapper id and column confing map
            master_mapper_column_config_map = {}
            for data in mdm_config_data:
                if data['master_mapper__master_id'] not in master_mapper_column_config_map:
                    master_mapper_column_config_map[data['master_mapper__master_id']] = []         
                req_columns = {
                    'displayName' : data['display_name'],
                    'key' : data['col_code'],
                    'col_Position' : data['col_position'],
                    'visible' : data['visible'],
                    'dataType' : data['data_type']
                }                    
                master_mapper_column_config_map[data['master_mapper__master_id']].append(req_columns)
            logger.info("Created Master-Mapper Column-Config mapping")
            
            #create response data
            response_data = []
            for data in master_mapper_data:
                row =   {   
                            'id' : data['master_id'],
                            'name' : data['display_name'],
                            'fields' : master_mapper_column_config_map.get(data['master_id'])
                        }
                response_data.append(row)
            logger.info("Response data created")
            return api_response(response_data, msg="Master Management UI data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetMasterManagementDataView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)
 
class GetTasksView(APIView):
    @swagger_auto_schema(
        operation_description="Get Task Instances for Master Management UI",
         responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            logger.info("Get Task Instances for Master Management UI started") 

            task_instances = TaskInstances.objects.prefetch_related('master_mapper').annotate(mmid=F('master_mapper__id'), mid=F('master_mapper__master_id'), mnm=F('master_mapper__master_name'), dnm=F('master_mapper__display_name')).prefetch_related('task_status').annotate(
                tsd=F('task_status__task_status_desc')).values('id', 'task_id', 'task_name', 'approver_ids', 'requester_id', 'requester_name', 'task_status', 'tsd', 'created_on', 'mmid', 'mid', 'mnm', 'dnm')
            
            TaskCCRMaster_map = self.get_task_approver_map(TaskCCRMaster)
            TaskBufferMaster_map = self.get_task_approver_map(TaskBufferMaster)
            TaskPoogiMajorReason_map = self.get_task_approver_map(TaskPoogiMajorReason)
            TaskCalendarMaster_map = self.get_task_approver_map(TaskCalendarMaster)

            combined_approver_map = {
                 **TaskCCRMaster_map,
                 **TaskBufferMaster_map,
                 **TaskPoogiMajorReason_map,
                 **TaskCalendarMaster_map,
            }

            #create response data
            response_data = []
            for instance in task_instances:
                approvers = combined_approver_map.get(instance['id'])
                row =   {  
                            'tid': instance['task_id'],
                            'tnm': instance['task_name'],
                            'a_ids': instance['approver_ids'],
                            'r_id': instance['requester_id'],
                            'r_nm': instance['requester_name'],
                            'st': instance['task_status'],
                            'std':instance['tsd'],
                            'co': instance['created_on'],
                            'mm_id': instance['mmid'],
                            'mid': instance['mid'],
                            'mnm': instance['mnm'],
                            'mdnm': instance['dnm'],
                            'approved_by' : approvers[0] if approvers else None
                        }
                response_data.append(row)
            logger.info("Response data created")

            return api_response(response_data, msg="Task Instances fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetTasksView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)
            
    def get_task_approver_map(self,model):
        approver_map = defaultdict(list)
        data = model.objects.values_list('task_instance_id', 'approver_id')

        for task_instance_id, approver_id in data:
            approver_map[task_instance_id].append(approver_id)

        return dict(approver_map)


class GetDraftInstancesView(APIView):
    @swagger_auto_schema(
        operation_description="Get Draft instances for Master Management UI",
        manual_parameters=[
            openapi.Parameter('uid', openapi.IN_QUERY, description="logged in user id", type=openapi.TYPE_STRING)
        ],
         responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            logger.info("Get Draft Instances for Master Management UI started")

            param_user_id = request.GET.get('uid')
            logger.info('Read user Id parameter from Input')

            if not param_user_id:
                logger.error("User Id parameter is required")
                return api_response(error="User Id parameter is required", status_code=status.HTTP_400_BAD_REQUEST)
          
            draft_instances = DraftInstances.objects.filter(user_id = param_user_id).prefetch_related('master_mapper').annotate(mmid = F('master_mapper__id'), mid= F('master_mapper__master_id'), mnm = F('master_mapper__master_name'), dnm=F('master_mapper__display_name')).prefetch_related('action_type').values('draft_id','action_type__action_type_desc','user_id','user_name','last_modified_on','search_keys','created_on','mmid','mid','mnm','dnm')

            #create response data
            response_data = []
            for instance in draft_instances:
                row =   {  
                            'did': instance['draft_id'],
                            'at': instance['action_type__action_type_desc'],
                            'uid': instance['user_id'],
                            'unm': instance['user_name'],
                            'lm': instance['last_modified_on'],
                            'sk': instance['search_keys'],
                            'co': instance['created_on'],
                            'mmid': instance['mmid'],
                            'mid': instance['mid'],
                            'mnm': instance['mnm'],
                            'dnm': instance['dnm']
                        }
                response_data.append(row)
            logger.info("Response data created")

            return api_response(response_data, msg="Draft Instances fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetDraftInstancesView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)


class GetTaskByIdView(APIView):
    pagination = CustomPagination
    @swagger_auto_schema(
        operation_description='Get Task by Id for Master Management UI',
        manual_parameters=[
            openapi.Parameter('tid', openapi.IN_QUERY,
                              type=openapi.TYPE_STRING, description='task id'), # requesterId_datetime           
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        try:
            # this api will return no.of records against particular task instance. 
            # If task instance is not provided the this api will return all task data of provided master (mmid)
            logger.info("Get Task by id for Master Management UI started")    

            # read data sent in parameters
            task_id = request.GET.get('tid') # requesterId_datetime
            master_mapper_id = request.GET.get('mmid')
            logger.info('Read parameters for API')

            #get task instaces
            filter_condition = {}
            if task_id is not None:
                filter_condition = {'task_id' : task_id}
            #master_mapper_id = master_mapper_id,
            task_instance = TaskInstances.objects.filter(**filter_condition).prefetch_related('master_mapper').values('id','task_id','master_mapper__master_name','master_mapper__display_name')
            logger.info('Fetched task data based on task id and master mapper id')

            #get master name
            master_name = task_instance[0]['master_mapper__display_name']
            logger.info('Get master name into master_name')

            #create response data
            if 'buff' in master_name.lower():
                buffer_task_view = GetBufferTaskByIdView()
                buffer_task_request = request
                buffer_task_request.GET = request.GET.copy()
                buffer_task_request.GET['taskId'] = task_id
                task_data_response = buffer_task_view.get(request=buffer_task_request)
                if task_data_response.status_code != status.HTTP_200_OK:
                    raise Exception("Buffer task data fetching failed")
            if 'ccr' in master_name.lower():
                ccr_task_view = GetCCRTaskByIdView()
                ccr_task_request = request
                ccr_task_request.GET = request.GET.copy()
                ccr_task_request.GET['taskId'] = task_id
                task_data_response = ccr_task_view.get(request=ccr_task_request)
                if task_data_response.status_code != status.HTTP_200_OK:
                    raise Exception("CCR task data fetching failed")
            if 'poogi' in master_name.lower():
                poogi_reason_task_view = GetPoogiReasonMasterTaskByIdView()
                poogi_reason_task_request = request
                poogi_reason_task_request.GET = request.GET.copy()
                poogi_reason_task_request.GET['taskId'] = task_id
                task_data_response = poogi_reason_task_view.get(request=poogi_reason_task_request)
                if task_data_response.status_code != status.HTTP_200_OK:
                    raise Exception("Poogi Reason task data fetching failed")
            if 'calendar' in master_name.lower() or 'holiday' in master_name.lower():
                calendar_task_view = GetCalendarTaskByIdView()
                calendar_task_request = request
                calendar_task_request.GET = request.GET.copy()
                calendar_task_request.GET['taskId'] = task_id
                task_data_response = calendar_task_view.get(request=calendar_task_request)
                if task_data_response.status_code != status.HTTP_200_OK:
                    raise Exception("Calendar task data fetching failed")            

            logger.info("Response data created")

            return api_response(task_data_response.data.get('data'), msg="Task Instances fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetTaskByIdView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class DeleteDraftView(APIView):
    @swagger_auto_schema(
        operation_description="Delete Buffer Master Draft for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'did': openapi.Schema(type=openapi.TYPE_STRING, description='Draft Instance Id')
            },
            required=['did']   #'mid',
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
        
    
    def put(self, request):
        try:
            # this api will update buffer draft saved
            # read data sent in parameters
            if request.data is not None:
                draft_instance_id = request.data.get('did')
            logger.info('Read parameters for API')

            draft_details = DraftInstances.objects.filter(draft_id=draft_instance_id).prefetch_related('master_mapper').values('draft_id','master_mapper_id','master_mapper__master_name')
    
            with transaction.atomic():
                for draft in draft_details:
                    master_name = draft['master_mapper__master_name'].lower()

                if 'buffer' in master_name:
                    BufferMasterDraft.objects.filter(draft_instance_id=draft_instance_id).delete()                    
                elif 'ccr' in master_name:
                    CCRMasterDraft.objects.filter(draft_instance_id=draft_instance_id).delete()
                elif 'poogi' in master_name:
                    poogi_major_reason_drafts = PoogiMajorReasonDraft.objects.filter(draft_instance_id=draft_instance_id).values('id')
                    poogi_major_reason_draft_id_list =[]
                    for major_instance in poogi_major_reason_drafts:
                        poogi_major_reason_draft_id_list.append(major_instance['id'])
                    PoogiMinorReasonDraft.objects.filter(major_reason_draft_id__in=poogi_major_reason_draft_id_list).delete()
                    PoogiMajorReasonDraft.objects.filter(draft_instance_id=draft_instance_id).delete()
                elif 'calendar' in master_name:
                    CalendarMasterDraft.objects.filter(draft_instance_id=draft_instance_id).delete()

                DraftInstances.objects.filter(draft_id=draft_instance_id).delete()
                logger.info(''+master_name + ' draft and draft instance deleted')

            return api_response(msg= master_name + ' draft deleted successfully', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Exception occurred DeleteBufferMasterDraftView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)
