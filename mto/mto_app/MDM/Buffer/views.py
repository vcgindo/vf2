from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework import status

from ...serializers import BufferMasterSerializer, CCRMasterSerializer, DeptMasterSerializer, OrderTypeMasterSerializer, PlantHolidayListSerializer, UIReportConfigurationsSerializer, PlantMasterSerializer,UserwiseUIReportConfigurationsSerializer
from ...common.commonfunctions import CustomPagination, api_response, filter_data_by_params, get_order_data,get_ccr_fol_gap_mapping, ePageName
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import F, Max
from django.db import transaction
from ...models import *
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


class AddBufferMasterView(APIView):
    @swagger_auto_schema(
        operation_description="Add buffer to buffer master",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'tid': openapi.Schema(type=openapi.TYPE_STRING, description='Task Id'),#requesterId_datetime
                    'ti_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Task Instance Id'), # 1 , 2...
                    'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User Id'),
                    'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                    'mmid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master mapper Id'), # 1 for Buffer Master
                    'buffData':  openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'tbmId': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Master Task Id'), #1/2/3/....
                                'bcd': openapi.Schema(type=openapi.TYPE_STRING, description='Buffer Code'),
                                'bd': openapi.Schema(type=openapi.TYPE_STRING, description='Buffer Name'),
                                'bsz': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Size'),
                                'slt': openapi.Schema(type=openapi.TYPE_INTEGER, description='SLT'),
                                'mlt': openapi.Schema(type=openapi.TYPE_INTEGER, description='MLT'),
                                'bt_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Type Id'),
                                'ib': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Blue Buffer'),
                                'ia': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Approved'),
                                'bid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Id'),
                                'iv': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Is Valid"), # Active / Inactive,                                
                                'cm': openapi.Schema(type=openapi.TYPE_STRING, description='Comment if any row is rejected')
                            },
                            required=['bcd', 'bsz','bd','slt','mlt','ib','bt_id','bid','iv','cm']
                        )
                    )
                },
                required=['mid','uid', 'unm','mmid','buffData']
            )
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def put(self, request):
        try:
            logger.info("Add Buffer to Master Processing started")
            # update task intance   /  task buffer master /  buffer master

            #get current datetime
            date_time = datetime.now()

            # read data sent in parameters
            for data in request.data.get('data'):
                task_id = data.get('tid')
                task_instance_id = data.get('ti_id')
                user_id = data.get('uid')
                user_name = data.get('unm')
                master_mapper_id = data.get('mmid')
                buffers_to_be_added = data.get('buffData', [])
            logger.info('Read parameters for API')

            task_action_status_instance_Approved = TaskActionStatusMaster.objects.filter(task_status_desc = 'Approved').first() #3
            task_action_status_instance_Rejected = TaskActionStatusMaster.objects.filter(task_status_desc = 'Rejected').first() #4
            task_action_status_instance_Partially_Approved = TaskActionStatusMaster.objects.filter(task_status_desc = 'Partially Approved').first() #2
            logger.info('Fetched action status instance for action Approved, Rejected and Partially Approved')

            buffer_master_tasks = TaskBufferMaster.objects.filter(task_instance_id = task_instance_id)
            logger.info('Fetched task from TaskBufferMaster model')

            #update BufferMaster # sending buffer data should not be required
            # get buffer data from buffer task table and insert into buffer master
            max_buffer_id =  BufferMaster.objects.order_by('buffer_id').last().buffer_id
            logger.info('Fetched max buffer id from Buffer Master')

            # set new buffer id
            if max_buffer_id:
                new_buffer_id = max_buffer_id + 1
            else:
                new_buffer_id = 1
            
            buffer_type_instances = BufferTypeMaster.objects.filter(is_valid = True)
            logger.info('fetched all valid buffer type instances')
            buffers_to_create = []
            buffers_to_update = []
            buffer_master_tasks_to_update = []
            for buffer in buffers_to_be_added:
                buffer_master_task = buffer_master_tasks.filter(id = buffer['tbmId']).first()
                buffer_master_task.approver_id = user_id
                buffer_master_task.approver_name =  user_name
                buffer_master_task.approved_on = date_time
                buffer_master_task.comments = buffer['cm']
                if buffer['ia'] is True:
                    if buffer['bid'] is None:
                        buffer_type_instance = buffer_type_instances.filter(buffer_type_id = buffer['bt_id']).first()
                        logger.info('fetched buffer type instance from  buffer_type_instances')
                    
                        buffers_to_create.append(
                                        BufferMaster(
                                            buffer_id = new_buffer_id,
                                            buffer_code = buffer['bcd'],
                                            buffer_desc = buffer['bd'],
                                            buffer_size = buffer['bsz'],
                                            slt = buffer['slt'],
                                            mlt = buffer['mlt'],
                                            is_blue = buffer['ib'],
                                            is_valid = True,
                                            buffer_type = buffer_type_instance
                                        )
                                )
                        new_buffer_id += 1
                    else:
                        buffer_instance = BufferMaster.objects.filter(buffer_id = buffer['bid']).first()
                        buffer_instance.is_valid = buffer['iv']
                        buffers_to_update.append(buffer_instance)

                    buffer_master_task.is_approved = True
                    buffer_master_task.status = task_action_status_instance_Approved             
                else:
                    buffer_master_task.is_approved = False
                    buffer_master_task.status = task_action_status_instance_Rejected

                buffer_master_tasks_to_update.append(buffer_master_task)

            fields_to_update_buffer_tasks = {   'is_approved',
                                                'approver_id',
                                                'approver_name',
                                                'status',
                                                'approved_on',
                                                'comments'
                                            }
            logger.info('collected new buffers to be added')

            #update task Instance
            task_instances = TaskInstances.objects.filter(task_id = task_id, id = task_instance_id, master_mapper_id = master_mapper_id)
            for task in task_instances:
                if len(buffers_to_create) == len(buffers_to_be_added) or (len(buffers_to_create) > 0):
                    task.task_status = task_action_status_instance_Approved
                elif len(buffers_to_create) == 0:
                    task.task_status = task_action_status_instance_Rejected           

            logger.info('Fetched task instance to be updated and assigned task status')

            with transaction.atomic():
                TaskInstances.objects.bulk_update(task_instances, ['task_status'])
                TaskBufferMaster.objects.bulk_update(buffer_master_tasks_to_update, fields_to_update_buffer_tasks)
                if len(buffers_to_create) > 0:
                    BufferMaster.objects.bulk_create(buffers_to_create)
                if(len(buffers_to_update) > 0):
                    BufferMaster.objects.bulk_update(buffers_to_update, ['is_valid'])

            logger.info('Added buffers to buffer master')

            return api_response(msg='Buffer(s) added successfully', status_code=status.HTTP_200_OK)
           
        except Exception as ex:
            logger.error(f"Exception occurred in AddBufferMasterView: {str(ex)}")
            return api_response(error=f"Exception occurred in AddBufferMasterView : {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)



class GetBufferDraftDataView(APIView):
    pagination = CustomPagination
    @swagger_auto_schema(
        operation_description="Get Buffer Draft data for Master Management UI",
        manual_parameters=[
            openapi.Parameter('did', openapi.IN_QUERY, description="Draft Id", type=openapi.TYPE_STRING),
            openapi.Parameter('mid', openapi.IN_QUERY, description="Master Id", type=openapi.TYPE_INTEGER)
        ],
         responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            logger.info("Get buffer draft data for Master Management UI started")    
            buffer_draft_instance_id =  request.GET.get('did')
            logger.info('Read Draft id from parameter')

            #get buffer draft data
            buffer_draft_data = BufferMasterDraft.objects.filter(draft_instance_id = buffer_draft_instance_id).prefetch_related('buffer_type').values('row_id','buffer_code','buffer_size','buffer_desc','slt','mlt','is_blue','buffer_type__buffer_type_id','buffer_type__buffer_type','buffer_type__buffer_type_desc','draft_instance_id','error','buffer_id','is_active')
            logger.info('Fetched buffer draft data')

            #create response data
            response_data = []
            for buffer in buffer_draft_data:
                row =   {  
                            'rid': buffer['row_id'],
                            'bcd': buffer['buffer_code'],
                            'bsz': buffer['buffer_size'],
                            'bd': buffer['buffer_desc'],
                            'slt': buffer['slt'],
                            'mlt': buffer['mlt'],
                            'ib': buffer['is_blue'],
                            'bt': buffer['buffer_type__buffer_type_id'],
                            'err': buffer['error'],
                            'bid': buffer['buffer_id'],
                            'iv': buffer['is_active']
                        }
                response_data.append(row)
            logger.info("Response data created")

            return api_response(response_data, msg="Buffer draft data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetBufferDraftDataView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class SaveBufferMasterTaskView(APIView):
    @swagger_auto_schema(
        operation_description="Save BufferMaster task for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Id'), #501
                'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User Name'),
                'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User Id'),                
                'buffData':  openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'bcd': openapi.Schema(type=openapi.TYPE_STRING, description='Buffer Code'),
                            'bsz': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Size'),
                            'bd': openapi.Schema(type=openapi.TYPE_STRING, description='Buffer Description'),
                            'slt': openapi.Schema(type=openapi.TYPE_INTEGER, description='SLT'),
                            'mlt': openapi.Schema(type=openapi.TYPE_INTEGER, description='MLT'),
                            'ib': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Blue Buffer'),
                            'bt': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Type Id'),
                            'bid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Id'),
                            'iv': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Valid'), # Active/ Inactive Status
                        },
                        required=['bcd', 'bsz', 'bd', 'slt', 'mlt', 'ib', 'bt','bid','iv']
                    )
                )
            },
            required=['mid', 'unm', 'uid', 'buffData']

        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def put(self, request):
        try:
            # this api will save data in TaskInstances and TaskBufferMaster model
            # read data sent in parameters
            approvers = request.data.get('all_users')
            user_id = request.data.get('uid')
            user_name = request.data.get('unm')
            param_master_id = request.data.get('mid') #501
            buffers_to_be_added = request.data.get('buffData', [])
            action_type = request.data.get('at')
            logger.info('Read parameters for API')

            #get comma separated approver id list from approvers
            approver_id_list = ','.join(str(approver['id']) for approver in approvers)
            # get master mapper instance
            master_mapper_instance = MasterMapper.objects.filter(is_valid = True, master_id = param_master_id).first()
            logger.info('Fetched Master Mapper instance')

            #get task status instance
            task_status_instance = TaskActionStatusMaster.objects.filter(task_status_desc = 'Pending').first()
            logger.info('Fetched Task Status instance')
            
            #get current date time
            date_time = datetime.now().strftime("%Y%m%d%H%M%S")
            new_task_id = user_id +'_'+ date_time
            logger.info('current date time is assigned to a variable')

            #get action type instance
            action_type_instance = TaskActionTypeMaster.objects.filter(action_type_desc=action_type).first()
            logger.info('Fetched action type instance')

            #create draft buffer data instances
            buffer_task_instances = []         
            buffer_type_instances = BufferTypeMaster.objects.filter(is_valid = True)
            with transaction.atomic():
                    TaskInstances.objects.create(
                        task_id=new_task_id,
                        created_on=datetime.now(),
                        task_name= f"{action_type} - Buffer Master",
                        approver_ids = approver_id_list,
                        requester_id=user_id,
                        requester_name=user_name,
                        task_status=task_status_instance,
                        master_mapper=master_mapper_instance,
                        action_type=action_type_instance
                    )
                    logger.info('Task Instance created')
                    new_task_instance = TaskInstances.objects.filter(task_id = new_task_id).first()
                    logger.info('Fetched new Task Instance')

                    for buffer in buffers_to_be_added:
                        buffer_instance = None
                        if buffer['bid'] is not None:
                            buffer_instance = BufferMaster.objects.filter(buffer_id = buffer['bid']).first()
                        buffer_type_instance = buffer_type_instances.filter(buffer_type_id = buffer['bt']).first()
                        buffer_task_instance =  TaskBufferMaster(
                                                    task_instance = new_task_instance,
                                                    buffer_code = buffer['bcd'],
                                                    buffer_size = buffer['bsz'],
                                                    buffer_desc = buffer['bd'],
                                                    slt = buffer['slt'],
                                                    mlt = buffer['mlt'],
                                                    is_blue = buffer['ib'],
                                                    buffer = buffer_instance,
                                                    is_active = buffer['iv'],
                                                    buffer_type = buffer_type_instance,
                                                    status = task_status_instance,
                                                    comments = None,
                                                    approver_id = None,
                                                    approver_name = None,
                                                    is_approved = False,
                                                    approved_on = None
                                                )
                        buffer_task_instances.append(buffer_task_instance)

                    TaskBufferMaster.objects.bulk_create(buffer_task_instances)
                    logger.info('Buffer master tasks created')
            logger.info('Buffer master task Instance and Tasks saved')

            return api_response(msg='Buffer master tasks saved successfully', status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.error(f"Exception occurred in SaveBufferMasterTaskView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)


           
class GetBufferMasterForMasterMgmtView(APIView):
    @swagger_auto_schema(
        operation_description="Get BufferMaster data for Master Mgmt UI",
         manual_parameters=[
            openapi.Parameter('masterId', openapi.IN_QUERY, description="Master Id", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def put(self, request):
        try:
            param_master_id = request.GET.get('masterId')
            logger.info('Read master id sent in parameter')
        
            filter_data = request.data
             #read MDM confog data
            master_mapper_data = MasterMapper.objects.filter(is_valid = True, master_id = param_master_id).values('id')
            master_mapper_id = master_mapper_data[0]['id'] #1
            logger.info('Fetched Master Mapper Id')

            #read MDM confog data
            mdm_config_data = MDMConfiguration.objects.filter(is_valid = True, master_mapper_id = master_mapper_id).values('col_code','table_field')
            logger.info('Fetched MDM Config data')
            buffer_data = BufferMaster.objects.values('buffer_id','buffer_code','buffer_desc','buffer_size','slt','mlt','is_blue','buffer_type_id','buffer_type__buffer_type','is_valid')
            logger.info('Fetched buffer master data')

            #get filtered buffer data
            filtered_buffer_data = filter_buffer_data_by_params_master_mgmt(buffer_data, filter_data)
            logger.info('Fetched filtered buffer data')

            # map table fields and get data according to col_code for each field 
            field_to_code_mapping = {entry['table_field']: entry['col_code'] for entry in mdm_config_data}
            col_code_wise_buffer_data = []
            for buffer_entry in filtered_buffer_data:
                new_entry = {}
                for key, value in buffer_entry.items():
                    # If the key matches a table_field, replace it with col_code
                    new_key = field_to_code_mapping.get(key, key)
                    new_entry[new_key] = value
                col_code_wise_buffer_data.append(new_entry)
            logger.info("created a buffer data collection based on column code")

            return api_response(col_code_wise_buffer_data, msg="Master Buffer data fetched successfully", status_code=status.HTTP_200_OK)         

        except Exception as e:
            logger.error(f"Exception occurred GetBufferMasterForMasterMgmtView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

def filter_buffer_data_by_params_master_mgmt(queryset, filters):
          
    buffer_filters = {
        'buffer_code': filters.get('bcd', {}),
        'buffer_desc': filters.get('bd', {}),
        'buffer_size': filters.get('bsz', {}),
        'slt': filters.get('slt', {}),
        'mlt': filters.get('mlt', {}),
        'is_blue': filters.get('ib', {}),
        'buffer_type_id' : filters.get('bt', {}),
        'buffer_type__buffer_type' : filters.get('btype', {}),
        'is_valid' : filters.get('iv', {})
    }
    if buffer_filters:
        return filter_data_by_params(queryset, buffer_filters)
    else:
        return queryset

class SaveBufferMasterDraftView(APIView):
    @swagger_auto_schema(
        operation_description="Save BufferMaster  draft for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'mid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Id'), #501
                    'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                    'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User Id'),
                    'at': openapi.Schema(type=openapi.TYPE_STRING, description='Action Type'), # Add / Modify
                    'buffData':  openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'bcd': openapi.Schema(type=openapi.TYPE_STRING, description='Buffer Code'),
                                'bsz': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Size'),
                                'bd': openapi.Schema(type=openapi.TYPE_STRING, description='Buffer Description'),
                                'slt': openapi.Schema(type=openapi.TYPE_INTEGER, description='SLT'),
                                'mlt': openapi.Schema(type=openapi.TYPE_INTEGER, description='MLT'),
                                'ib': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Blue Buffer'),
                                'bt': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Type Id'),
                                'err': openapi.Schema(type=openapi.TYPE_STRING, description='Error'),
                                'bid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Buffer Id'),
                                'iv': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Valid'), # Active/Inactive
                            },
                            required=['bcd', 'bsz','bd','slt','mlt','ib','bt','bid','iv']
                        )
                    )
                },
                required=['mid', 'unm', 'uid', 'at', 'buffData']
            )
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def put(self, request):
        try:
            # read data sent in parameters
            for data in request.data.get('data'):
                user_name = data.get('unm')
                user_id = data.get('uid')
                param_master_id = data.get('mid')
                action_type = data.get('at')
                buffers_to_be_added = data.get('buffData', [])
            logger.info('Read parameters for API')
         
            # read MDM config data
            master_mapper_data = MasterMapper.objects.filter(is_valid = True, master_id = param_master_id).values('id','master_name','display_name').first()
            logger.info('Fetched Master Mapper data')

            # get master mapper instance
            master_mapper_instance = MasterMapper.objects.filter(is_valid = True, master_id = param_master_id)[0]
            logger.info('Fetched Master Mapper instance')

            #get current date time
            date_time = datetime.now().strftime("%Y%m%d%H%M%S")
            new_draft_id = user_id +'_'+ date_time
            logger.info('current date time is assigned to a variable')

            #get action type instance
            action_type_instance = TaskActionTypeMaster.objects.filter(action_type_desc = action_type)[0]
            logger.info('Fetched action type instance')

            with transaction.atomic():
                    DraftInstances.objects.create(
                                                    draft_id= new_draft_id,
                                                    action_type=action_type_instance,
                                                    user_name= user_name,
                                                    user_id= user_id,
                                                    created_on = datetime.now(),
                                                    last_modified_on=datetime.now(),
                                                    search_keys = master_mapper_data['display_name'],
                                                    master_mapper = master_mapper_instance
                                                    )
                    #create draft buffer data instances
                    row_id = 1
                    buffer_draft_data_instances = []
                    for buffer in buffers_to_be_added:
                        buffer_draft_data_instance = BufferMasterDraft(
                                                    row_id=row_id,
                                                    buffer_code = buffer['bcd'],
                                                    buffer_size = buffer['bsz'],
                                                    buffer_desc = buffer['bd'],
                                                    slt = buffer['slt'],
                                                    mlt = buffer['mlt'],
                                                    is_blue = buffer['ib'],
                                                    buffer_type_id = buffer['bt'],
                                                    draft_instance_id = new_draft_id,
                                                    error = buffer['err'],
                                                    buffer_id = buffer['bid'],
                                                    is_active = buffer['iv']
                                                )
                        buffer_draft_data_instances.append(buffer_draft_data_instance)
                        row_id +=1
                    BufferMasterDraft.objects.bulk_create(buffer_draft_data_instances)
            logger.info('Draft instance and buffer data draft created')

            return api_response(msg='Buffer Draft saved successfully', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Exception occurred SaveBufferMasterDraftView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class GetBufferTaskByIdView(APIView):
    @swagger_auto_schema(
        operation_description='Get Buffer Task by Id for Master Management UI',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        try:
            logger.info('Get Buffer Task by id for Master Management UI started')    

            # read data sent in parameters
            task_id = request.GET.get('taskId') # requesterId_datetime            
            logger.info('Read parameters for API')

            filter_condition = {}
            if task_id is not None:
                filter_condition = {'task_instance__task_id' : task_id}

            response_data = []
            #create response data            
            tasks = TaskBufferMaster.objects.prefetch_related('buffer_type').prefetch_related('task_instance').filter(**filter_condition).values('id','task_instance__id','task_instance__task_id','task_instance__master_mapper_id','buffer_code','buffer_desc','buffer_size','slt','mlt','is_blue','is_approved','buffer_type_id','buffer_type__buffer_type_desc','comments','approver_id','approver_name','approved_on','buffer_id','is_active','buffer_type__buffer_type')
            for task in tasks:
                row =   {
                            'tbmId': task['id'],  
                            'bcd': task['buffer_code'],
                            'bsz': task['buffer_size'],
                            'bd': task['buffer_desc'],
                            'slt': task['slt'],
                            'mlt': task['mlt'],
                            'ib': task['is_blue'],
                            'bt_id': task['buffer_type_id'],
                            'bt': task['buffer_type__buffer_type'],
                            'cm': task['comments'],
                            'ia': task['is_approved'],
                            'aid': task['approver_id'],
                            'anm': task['approver_name'],
                            'aon': task['approved_on'],
                            'ti_id': task['task_instance__id'],
                            'tid': task['task_instance__task_id'],
                            'mmid': task['task_instance__master_mapper_id'],
                            'bid': task['buffer_id'],
                            'iv': task['is_active']
                        }
                response_data.append(row)
            logger.info("Response data created")

            return api_response(data = response_data, msg="Buffer task data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetTaskByIdView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)
