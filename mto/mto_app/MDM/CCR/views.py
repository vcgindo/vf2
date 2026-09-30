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



class GetCCRMasterForMasterMgmtView(APIView):
    @swagger_auto_schema(
        operation_description="Get CCR Master data for Master Mgmt UI",
         manual_parameters=[
            openapi.Parameter('masterId', openapi.IN_QUERY, description="Master Id", type=openapi.TYPE_INTEGER), #502
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
            logger.info('Fetched Filter data')
             #read MDM confog data
            master_mapper_data = MasterMapper.objects.filter(is_valid = True, master_id = param_master_id).values('id')
            master_mapper_id = master_mapper_data[0]['id']
            logger.info('Fetched Master Mapper Id')

            #read MDM confog data
            mdm_config_data = MDMConfiguration.objects.filter(is_valid = True, master_mapper_id = master_mapper_id).values('col_code','table_field')
            logger.info('Fetched MDM Config data')
            ccr_data = CCRMaster.objects.values('ccr_id', 'ccr_code', 'ccr_name', 'capacity_per_day', 'working_hours_per_day', 'schedule_horizon',
                                 'fol_horizon', 'residual_buffer', 'ccr_attr1', 'ccr_attr2', 'ccr_attr3', 'ccr_attr4', 'ccr_attr5', 
                                  'ccr_attr6', 'ccr_attr7', 'ccr_attr8', 'ccr_attr9', 'ccr_attr10', 'ccr_group', 'plant', 'dept', 
                                   'cumulative_wip_limit','plant__plant_name','dept__dept_name','ccr_group__ccr_group_name', 'is_valid')
            logger.info('Fetched ccr master data')
    
           #get filtered buffer data
            filtered_ccr_data = filter_ccr_data_by_params_master_mgmt(ccr_data, filter_data)
            logger.info('Fetched filtered buffer data')

            # map table fields and get data according to col_code for each field 
            field_to_code_mapping = {entry['table_field']: entry['col_code'] for entry in mdm_config_data}
            col_code_wise_ccr_data = []
            for ccr_entry in filtered_ccr_data:
                new_entry = {}
                for key, value in ccr_entry.items():
                    # If the key matches a table_field, replace it with col_code
                    new_key = field_to_code_mapping.get(key, key)
                    new_entry[new_key] = value
                col_code_wise_ccr_data.append(new_entry)
            logger.info("created a buffer data collection based on column code")

            return api_response(col_code_wise_ccr_data, msg="Master CCR data fetched successfully", status_code=status.HTTP_200_OK)         

        except Exception as e:
            logger.error(f"Exception occurred GetCCRMasterForMasterMgmtView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

def filter_ccr_data_by_params_master_mgmt(queryset, filters):
    ccr_filters = {
        'ccr_code': filters.get('ccd', {}),
        'ccr_name': filters.get('cnm', {}),
        'capacity_per_day': filters.get('cpd', {}),
        'working_hrs_per_day': filters.get('whpd', {}),
        'scheduling_horizon': filters.get('sh', {}),
        'fol_horizon': filters.get('fh', {}),
        'residual_buffer' : filters.get('rb', {}),
        'ccr_attr1' : filters.get('a1', {}),
        'ccr_attr2' : filters.get('a2', {}),
        'ccr_attr3' : filters.get('a3', {}),
        'ccr_attr4' : filters.get('a4', {}),
        'ccr_attr5' : filters.get('a5', {}),
        'ccr_attr6' : filters.get('a6', {}),
        'ccr_attr7' : filters.get('a7', {}),
        'ccr_attr8' : filters.get('a8', {}),
        'ccr_attr9' : filters.get('a9', {}),
        'ccr_attr10' : filters.get('a10', {}),
        'plant' : filters.get('pl', {}),
        'dept' : filters.get('dp', {}),
        'ccr_group' : filters.get('cgid', {}),
        'plant__plant_name' : filters.get('plnm', {}),
        'dept__dept_name' : filters.get('dpnm', {}),
        'ccr_group__ccr_group_name' : filters.get('cgnm', {}),
        'cumulative_wip_limit' : filters.get('cwl',{}),
        'is_valid' : filters.get('iv',{})
    }
    if ccr_filters:
        return filter_data_by_params(queryset, ccr_filters)
    else:
        return queryset

class SaveCCRMasterTaskView(APIView):
    @swagger_auto_schema(
        operation_description="Save CCR Master task for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Id'), # 502
                'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User id'),
                'ccrData':  openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'ccd': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Code'),
                            'cnm': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Name'),
                            'cpd': openapi.Schema(type=openapi.TYPE_NUMBER, description='Capacity per day'),
                            'whpd': openapi.Schema(type=openapi.TYPE_NUMBER, description='Working hrs per day'),
                            'sh': openapi.Schema(type=openapi.TYPE_INTEGER, description='Scheduling Horizon'),
                            'fh': openapi.Schema(type=openapi.TYPE_INTEGER, description='FOL Horizon'),
                            'rb': openapi.Schema(type=openapi.TYPE_NUMBER, description='Residual Buffer'),
                            'plid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                            'dpid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Department Id'),
                            'cgid': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Group Id'),
                            'a1': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 1'),
                            'a2': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 2'),
                            'a3': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 3'),
                            'a4': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 4'),
                            'a5': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 5'),
                            'a6': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 6'),
                            'a7': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 7'),
                            'a8': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 8'),
                            'a9': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 9'),
                            'a10': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 10'),
                            'cwl': openapi.Schema(type=openapi.TYPE_INTEGER, description='Cumulative WIP Limit'),
                            'cid' : openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Id'),
                            'iv' : openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Active'),
                        },
                        required=['ccd', 'cnm', 'cpd', 'whpd', 'sh', 'fh', 'rb', 'plid',
                                  'dpid','cgid', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'a10','cwl','cid','iv']
                    )
                )
            },
            required=['mid', 'unm', 'uid', 'ccrData']

        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    

    def put(self, request):
        try:
            # this api will save data in TaskInstances and TaskCCRMaster model
            # read data sent in parameters
            user_id = request.data.get('uid')
            user_name = request.data.get('unm')
            param_master_id = request.data.get('mid')  # 502
            ccrs_to_be_added = request.data.get('ccrData', [])
            approvers = request.data.get('all_users')
            action_type = request.data.get('at')
            logger.info('Read parameters for API')

            #get comma separated approver id list from approvers
            approver_id_list = ','.join(str(approver['id']) for approver in approvers)

            # get master mapper instance
            master_mapper_instance = MasterMapper.objects.filter(is_valid=True, master_id=param_master_id).first()
            logger.info('Fetched Master Mapper instance')

            # get task status instance
            task_status_instance = TaskActionStatusMaster.objects.filter(task_status_desc='Pending').first()
            logger.info('Fetched Task Status instance')

            # get current date time
            date_time = datetime.now().strftime("%Y%m%d%H%M%S")
            new_task_id = user_id + '_' + date_time
            logger.info('current date time is assigned to a variable')

            # get action type instance
            action_type_instance = TaskActionTypeMaster.objects.filter(action_type_desc=action_type).first()
            logger.info('Fetched action type instance')

            # create draft buffer data instances
            ccr_grp_instances = CCRGroupMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid  CCR Group instances')
            plant_instances = PlantMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid  Plant instances')
            dept_instances = DeptMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid  Department instances')
            ccr_task_instances = []
            with transaction.atomic():
                    TaskInstances.objects.create(
                        task_id=new_task_id,
                        created_on=datetime.now(),
                        task_name=f"{action_type} - CCR Master",
                        approver_ids=approver_id_list,
                        requester_id=user_id,
                        requester_name=user_name,
                        task_status=task_status_instance,
                        master_mapper=master_mapper_instance,
                        action_type=action_type_instance
                    )
                    logger.info('Task Instance created')
                    new_task_instance = TaskInstances.objects.filter(task_id = new_task_id).first()
                    logger.info('Fetched new Task Instance')

                    for ccr in ccrs_to_be_added:
                        ccr_instance = None
                        if ccr['cid'] is not None:
                            ccr_instance = CCRMaster.objects.filter(ccr_id = ccr['cid']).first()
                        ccr_grp_instance = ccr_grp_instances.filter(ccr_group_id = ccr['cgid']).first()
                        logger.info('Fetched CCR Group instance')
                        plant_instance = plant_instances.filter(plant_id = ccr['plid']).first()
                        logger.info('Fetched plant instance')
                        dept_instance = dept_instances.filter(dept_id = ccr['dpid']).first()
                        logger.info('Fetched department instance')
                        ccr_task_instance =  TaskCCRMaster(
                                                    task_instance = new_task_instance,
                                                    ccr_code = ccr['ccd'],
                                                    ccr_name = ccr['cnm'],
                                                    capacity_per_day = ccr['cpd'],
                                                    working_hrs_per_day = ccr['whpd'],
                                                    scheduling_horizon = ccr['sh'],
                                                    fol_horizon = ccr['fh'],
                                                    residual_buffer = ccr['rb'],
                                                    plant = plant_instance,
                                                    dept = dept_instance,
                                                    ccr_group = ccr_grp_instance,
                                                    ccr_attr1 = ccr['a1'],
                                                    ccr_attr2 = ccr['a2'],
                                                    ccr_attr3 = ccr['a3'],
                                                    ccr_attr4 = ccr['a4'],
                                                    ccr_attr5 = ccr['a5'],
                                                    ccr_attr6 = ccr['a6'],
                                                    ccr_attr7 = ccr['a7'],
                                                    ccr_attr8 = ccr['a8'],
                                                    ccr_attr9 = ccr['a9'],
                                                    ccr_attr10 = ccr['a10'],
                                                    cumulative_wip_limit = ccr['cwl'],
                                                    status = task_status_instance,
                                                    comments = None,
                                                    approver_id = None,
                                                    approver_name = None,
                                                    is_approved = False,
                                                    approved_on = None,
                                                    ccr = ccr_instance,
                                                    is_active = ccr['iv']
                                                )
                        ccr_task_instances.append(ccr_task_instance)
                    
                    TaskCCRMaster.objects.bulk_create(ccr_task_instances)
                    logger.info('CCR master tasks created')
            logger.info('CCR master tasks saved')

            return api_response(msg='CCR master tasks saved successfully', status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in SaveCCRMasterTaskView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)


class GetCCRTaskByIdView(APIView):
    pagination = CustomPagination
    @swagger_auto_schema(
        operation_description='Get CCR Task by Id for Master Management UI',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        try:
            logger.info("Get CCR Task by id for Master Management UI started")    

            # read data sent in parameters
            task_id = request.GET.get('taskId') # requesterId_datetime
            logger.info('Read parameters for API')

            filter_condition = {}
            if task_id is not None:
                filter_condition = {'task_instance__task_id' : task_id}

            response_data = []
            #create response data            
            tasks = TaskCCRMaster.objects.prefetch_related('ccr_group').prefetch_related('task_instance').filter(**filter_condition).prefetch_related('plant').prefetch_related('dept').values('id', 'task_instance__id', 'task_instance__task_id', 'task_instance__master_mapper_id', 'ccr_code', 'ccr_name', 'capacity_per_day', 'working_hrs_per_day', 'scheduling_horizon', 'fol_horizon',               
                                                                                                                                                                                                     'residual_buffer', 'ccr_attr1', 'ccr_attr2', 'ccr_attr3', 'ccr_attr4', 'ccr_attr5', 'ccr_attr6', 'ccr_attr7', 'ccr_attr8', 'ccr_attr9', 'ccr_attr10', 'cumulative_wip_limit', 'comments',
                                                                                                                                                                                                           'ccr_group__ccr_group_id', 'ccr_group__ccr_group_code', 'ccr_group__ccr_group_name', 'plant__plant_id', 'plant__plant_code', 'plant__plant_name', 'dept__dept_id', 'dept__dept_code', 'dept__dept_name','ccr_id','is_active',
                                                                                                                                                                                                           'is_approved','approver_id','approver_name','approved_on')
            for task in tasks:
                row =   {
                            'tcmId': task['id'],  
                            'ccd': task['ccr_code'],
                            'cnm': task['ccr_name'],
                            'cpd': task['capacity_per_day'],
                            'whpd': task['working_hrs_per_day'],
                            'sh': task['scheduling_horizon'],
                            'fh': task['fol_horizon'],
                            'rb': task['residual_buffer'],
                            'a1': task['ccr_attr1'],
                            'a2': task['ccr_attr2'],
                            'a3': task['ccr_attr3'],
                            'a4': task['ccr_attr4'],
                            'a5': task['ccr_attr5'],
                            'a6': task['ccr_attr6'],
                            'a7': task['ccr_attr7'],
                            'a8': task['ccr_attr8'],
                            'a9': task['ccr_attr9'],
                            'a10': task['ccr_attr10'],
                            'cwl' : task['cumulative_wip_limit'],
                            'cgid': task['ccr_group__ccr_group_id'],
                            'cgcd': task['ccr_group__ccr_group_code'],
                            'cgnm': task['ccr_group__ccr_group_name'],
                            'plid': task['plant__plant_id'],
                            'plcd': task['plant__plant_code'],
                            'plnm': task['plant__plant_name'],
                            'dpid': task['dept__dept_id'],
                            'dpcd': task['dept__dept_code'],
                            'dpnm': task['dept__dept_name'],
                            'cm': task['comments'],
                            'ia': task['is_approved'],
                            'aid': task['approver_id'],
                            'anm': task['approver_name'],
                            'aon': task['approved_on'],
                            'tid': task['task_instance__task_id'],
                            'ti_id': task['task_instance__id'],
                            'mmid': task['task_instance__master_mapper_id'],
                            'cid': task['ccr_id'],
                            'iv': task['is_active'],
                        }
                response_data.append(row)
            logger.info("Response data created")

            return api_response(data = response_data, msg="CCR Task data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetCCRTaskByIdView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class AddCCRMasterView(APIView):
    @swagger_auto_schema(
        operation_description="Add CCRs to ccr master",
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
                    'ccrData':  openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'tcmId': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Master Task Id'),
                                'ccd': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Code'),
                                'cnm': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Name'),
                                'cpd': openapi.Schema(type=openapi.TYPE_INTEGER, description='Capacity Per day'),
                                'whpd': openapi.Schema(type=openapi.TYPE_INTEGER, description='Working hrs per day'),
                                'sh': openapi.Schema(type=openapi.TYPE_INTEGER, description='Scheduling Horizon'),
                                'fh': openapi.Schema(type=openapi.TYPE_INTEGER, description='FOL Horizon'),
                                'rb': openapi.Schema(type=openapi.TYPE_NUMBER, description='Residual Buffer'),
                                'a1': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 1'),
                                'a2': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 2'),
                                'a3': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 3'),
                                'a4': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 4'),
                                'a5': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 5'),
                                'a6': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 6'),
                                'a7': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 7'),
                                'a8': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 8'),
                                'a9': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 9'),
                                'a10': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 10'),
                                'cgid': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Group Id'),
                                'plid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                                'dpid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Department Id'),
                                'cwl' : openapi.Schema(type=openapi.TYPE_INTEGER, description='Cumulative WIP Limit'),
                                'ia': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Approved'),
                                'cid': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Id'),
                                'iv': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Valid'), # Active / Inactive
                                'cm': openapi.Schema(type=openapi.TYPE_STRING, description='Comment if any task is rejected')
                            },
                            required=['tcmId', 'ccd','cnm','cpd','whpd','sh','fh','rb','a1','a2','a3','a4','a5','a6','a7','a8','a9','a10','cgid','plid','dpid','cwl','ia','cid','iv','cm']
                        )
                    )
                },
                required=['mid','uid', 'unm','mmid','ccrData']
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
            logger.info("Add CCR to Master Processing started")
            # update task intance   /  task ccr master /  ccr master

            #get current datetime
            date_time = datetime.now()

            # read data sent in parameters
            for data in request.data.get('data'):
                task_id = data.get('tid')
                task_instance_id = data.get('ti_id')
                user_id = data.get('uid')
                user_name = data.get('unm')
                master_mapper_id = data.get('mmid')
                ccrs_to_be_added = data.get('ccrData', [])
            logger.info('Read parameters for API')

            task_action_status_instances = TaskActionStatusMaster.objects.all()
            logger.info('Fetched task_action_status_instances from TaskActionStatusMaster')

            task_action_status_instance_Approved = task_action_status_instances.filter(task_status_desc = 'Approved').first() #3
            task_action_status_instance_Rejected = task_action_status_instances.filter(task_status_desc = 'Rejected').first() #4
            task_action_status_instance_Partially_Approved = task_action_status_instances.filter(task_status_desc = 'Partially Approved').first() #2
            logger.info('fetched action status instance for action Approved, Rejected and Partially Approved')

            ccr_master_tasks = TaskCCRMaster.objects.filter(task_instance_id = task_instance_id)
            logger.info('Fetched CCR master task instance')
           
            #update CCRMaster # no need to send ccr data
            # get ccr data from ccr task table and insert into ccr master
            max_ccr_id =  CCRMaster.objects.order_by('ccr_id').last().ccr_id
            logger.info('Fetched max ccr id from CCR Master')

            # set new buffer id
            if max_ccr_id:
                new_ccr_id = max_ccr_id + 1
            else:
                new_ccr_id = 1

            ccr_group_instances = CCRGroupMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid CCR Group instances')
            plant_instances = PlantMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid Plant instances')
            dept_instances = DeptMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid Department instances')
            
            ccrs_to_create = []
            ccrs_to_update = []
            ccr_master_task_to_update = []
            for ccr in ccrs_to_be_added:
                ccr_master_task = ccr_master_tasks.filter(id = ccr['tcmId']).first()
                ccr_master_task.approver_id = user_id
                ccr_master_task.approver_name =  user_name
                ccr_master_task.approved_on = date_time
                ccr_master_task.comments = ccr['cm']
                if ccr['ia'] is True:
                    if ccr['cid'] is None:
                        ccr_group_instance = ccr_group_instances.filter(ccr_group_id = ccr['cgid']).first()
                        plant_instance = plant_instances.filter(plant_id = ccr['plid']).first()
                        dept_instance = dept_instances.filter(dept_id = ccr['dpid']).first()
                        ccrs_to_create.append(
                                        CCRMaster(
                                            ccr_id = new_ccr_id,
                                            ccr_code = ccr['ccd'],
                                            ccr_name = ccr['cnm'],
                                            capacity_per_day = ccr['cpd'],
                                            working_hours_per_day = ccr['whpd'],
                                            schedule_horizon = ccr['sh'],
                                            fol_horizon = ccr['fh'],
                                            residual_buffer = ccr['rb'],
                                            ccr_attr1 = ccr['a1'],
                                            ccr_attr2 = ccr['a2'],
                                            ccr_attr3 = ccr['a3'],
                                            ccr_attr4 = ccr['a4'],
                                            ccr_attr5 = ccr['a5'],
                                            ccr_attr6 = ccr['a6'],
                                            ccr_attr7 = ccr['a7'],
                                            ccr_attr8 = ccr['a8'],
                                            ccr_attr9 = ccr['a9'],
                                            ccr_attr10 = ccr['a10'],
                                            is_valid = True,
                                            ccr_group = ccr_group_instance,
                                            plant = plant_instance,
                                            dept = dept_instance,
                                            cumulative_wip_limit = ccr['cwl']
                                        )
                                )
                        new_ccr_id += 1
                    else:
                        ccr_instance = CCRMaster.objects.filter(ccr_id = ccr['cid']).first()
                        ccr_instance.is_valid = ccr['iv']
                        ccrs_to_update.append(ccr_instance)

                    ccr_master_task.is_approved = True
                    ccr_master_task.status = task_action_status_instance_Approved
                else:
                    ccr_master_task.is_approved = False
                    ccr_master_task.status = task_action_status_instance_Rejected

                ccr_master_task_to_update.append(ccr_master_task)

            fields_to_update_ccr_tasks = {  'is_approved',
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
                if len(ccrs_to_create) == len(ccrs_to_be_added) or len(ccrs_to_create) > 0  :
                    task.task_status = task_action_status_instance_Approved
                elif len(ccrs_to_create) == 0:
                    task.task_status = task_action_status_instance_Rejected
                       

            logger.info('Fetched task instance to be updated and assigned task status')

            with transaction.atomic():
                TaskInstances.objects.bulk_update(task_instances, ['task_status'])
                TaskCCRMaster.objects.bulk_update(ccr_master_task_to_update, fields_to_update_ccr_tasks)
                if len(ccrs_to_create) > 0:
                    CCRMaster.objects.bulk_create(ccrs_to_create)
                if len(ccrs_to_update) > 0:
                    CCRMaster.objects.bulk_update(ccrs_to_update,['is_valid'])
            logger.info('Added ccrs to ccr master')

            return api_response(msg='CCR(s) added successfully', status_code=status.HTTP_200_OK)
           
        except Exception as ex:
            logger.error(f"Exception occurred in AddCCRMasterView: {str(ex)}")
            return api_response(error=f"Exception occurred in AddCCRMasterView : {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)


class SaveCCRMasterDraftView(APIView):
    @swagger_auto_schema(
        operation_description="Save CCR Master  draft for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'mid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Id'), #502
                    'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                    'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User Id'),
                    'at': openapi.Schema(type=openapi.TYPE_STRING, description='Action Type'), # Add /Modify
                    'ccrData':  openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'ccd': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Code'),
                                'cnm': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Name'),
                                'cpd': openapi.Schema(type=openapi.TYPE_INTEGER, description='Capacity Per day'),
                                'whpd': openapi.Schema(type=openapi.TYPE_NUMBER, description='Working hrs per day'),
                                'sh': openapi.Schema(type=openapi.TYPE_INTEGER, description='Scheduling Horizon'),
                                'fh': openapi.Schema(type=openapi.TYPE_INTEGER, description='FOL Horizon'),
                                'rb': openapi.Schema(type=openapi.TYPE_NUMBER, description='Residual Buffer'),
                                'a1': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 1'),
                                'a2': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 2'),
                                'a3': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 3'),
                                'a4': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 4'),
                                'a5': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 5'),
                                'a6': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 6'),
                                'a7': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 7'),
                                'a8': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 8'),
                                'a9': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 9'),
                                'a10': openapi.Schema(type=openapi.TYPE_STRING, description='CCR Attr 10'),
                                'cgid': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Group Id'),
                                'plid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                                'dpid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Department Id'),
                                'cwl' : openapi.Schema(type=openapi.TYPE_INTEGER, description='Cumulative WIP Limit'),
                                'err' : openapi.Schema(type=openapi.TYPE_STRING, description='Error'),
                                'cid' : openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Id'),
                                'iv' : openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Active'),
                            },
                            required=['ccd','cnm','cpd','whpd','sh','fh','rb','a1','a2','a3','a4','a5','a6','a7','a8','a9','a10','cgid','plid','dpid','cwl','cid','iv']
                        )
                    )
                },
                required=['mid', 'unm', 'uid', 'at', 'ccrData']
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
                ccrs_to_be_added = data.get('ccrData', [])
            logger.info('Read parameters for API')
         
            # read MDM confog data
            master_mapper_data = MasterMapper.objects.filter(is_valid = True, master_id = param_master_id).values('id','master_name','display_name').first()
            # master_mapper_id = master_mapper_data['id']
            logger.info('Fetched Master Mapper data')

            # get master mapper instance
            master_mapper_instance = MasterMapper.objects.filter(is_valid = True, master_id = param_master_id)[0]
            logger.info('Fetched Master Mapper instance')

            #get current date time
            date_time = datetime.now().strftime("%Y%m%d%H%M%S")
            new_draft_id = user_id +'_'+ date_time
            logger.info('Current date time is assigned to a variable')

            #get action type instance
            action_type_instance = TaskActionTypeMaster.objects.filter(action_type_desc = action_type)[0]
            logger.info('Fetched action type instance')

            ccr_group_instances = CCRGroupMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid CCR Group instances')
            plant_instances = PlantMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid Plant instances')
            dept_instances = DeptMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid Department instances')

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
                    new_row_id = 1
                    ccr_draft_data_instances = []
                    for ccr in ccrs_to_be_added:
                        ccr_instance = None
                        if ccr['cid'] is not None:
                            ccr_instance = CCRMaster.objects.filter(ccr_id = ccr['cid']).first()
                        ccr_group_instance = ccr_group_instances.filter(ccr_group_id = ccr['cgid']).first()
                        plant_instance = plant_instances.filter(plant_id = ccr['plid']).first()
                        dept_instance = dept_instances.filter(dept_id = ccr['dpid']).first()
                        ccr_draft_data_instance = CCRMasterDraft(
                                                    row_id=new_row_id,
                                                    ccr_code = ccr['ccd'],
                                                    ccr_name = ccr['cnm'],
                                                    capacity_per_day = ccr['cpd'],
                                                    working_hrs_per_day = ccr['whpd'],
                                                    scheduling_horizon = ccr['sh'],
                                                    fol_horizon = ccr['fh'],
                                                    residual_buffer = ccr['rb'],
                                                    ccr_attr1 = ccr['a1'],
                                                    ccr_attr2 = ccr['a2'],
                                                    ccr_attr3 = ccr['a3'],
                                                    ccr_attr4 = ccr['a4'],
                                                    ccr_attr5 = ccr['a5'],
                                                    ccr_attr6 = ccr['a6'],
                                                    ccr_attr7 = ccr['a7'],
                                                    ccr_attr8 = ccr['a8'],
                                                    ccr_attr9 = ccr['a9'],
                                                    ccr_attr10 = ccr['a10'],
                                                    ccr_group = ccr_group_instance,
                                                    plant = plant_instance,
                                                    dept = dept_instance,
                                                    cumulative_wip_limit = ccr['cwl'],
                                                    draft_instance_id = new_draft_id,
                                                    error = ccr['err'],
                                                    ccr = ccr_instance,
                                                    is_active= ccr['iv'],
                                                )
                        ccr_draft_data_instances.append(ccr_draft_data_instance)
                        new_row_id +=1
                    CCRMasterDraft.objects.bulk_create(ccr_draft_data_instances)
            logger.info('Draft instance and ccr data draft created')

            return api_response(msg='CCR Draft saved successfully', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Exception occurred SaveCCRMasterDraftView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class GetCCRDraftDataView(APIView):
    pagination = CustomPagination
    @swagger_auto_schema(
        operation_description="Get CCR Draft data for Master Management UI",
        manual_parameters=[
            openapi.Parameter('did', openapi.IN_QUERY, description="Draft Id", type=openapi.TYPE_STRING),
            openapi.Parameter('mid', openapi.IN_QUERY, description="Master Id", type=openapi.TYPE_INTEGER) #2
        ],
         responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            logger.info("Get CCR draft data for Master Management UI started")    
            ccr_draft_id =  request.GET.get('did')

            #get buffer draft data
            ccr_draft_data = CCRMasterDraft.objects.filter(draft_instance_id=ccr_draft_id).prefetch_related('ccr_group').values(
                'row_id', 'ccr_code', 'ccr_name', 'capacity_per_day', 'working_hrs_per_day', 'scheduling_horizon', 'fol_horizon', 'residual_buffer', 
                'ccr_attr1', 'ccr_attr2','ccr_attr3','ccr_attr4','ccr_attr5','ccr_attr6','ccr_attr7','ccr_attr8','ccr_attr9','ccr_attr10','cumulative_wip_limit',
                'ccr_group__ccr_group_id','ccr_group__ccr_group_code','ccr_group__ccr_group_name','plant__plant_id','plant__plant_code','plant__plant_name',
                'dept__dept_id','dept__dept_code','dept__dept_name','draft_instance_id', 'error','ccr_id','is_active')
            logger.info('Fetched buffer draft data')

            #create response data
            response_data = []
            for ccr in ccr_draft_data:
                row =   {  
                            'rid': ccr['row_id'],
                            'ccd': ccr['ccr_code'],
                            'cnm': ccr['ccr_name'],
                            'cpd': ccr['capacity_per_day'],
                            'whpd': ccr['working_hrs_per_day'],
                            'sh': ccr['scheduling_horizon'],
                            'fh': ccr['fol_horizon'],
                            'rb': ccr['residual_buffer'],
                            'a1': ccr['ccr_attr1'],
                            'a2': ccr['ccr_attr2'],
                            'a3': ccr['ccr_attr3'],
                            'a4': ccr['ccr_attr4'],
                            'a5': ccr['ccr_attr5'],
                            'a6': ccr['ccr_attr6'],
                            'a7': ccr['ccr_attr7'],
                            'a8': ccr['ccr_attr8'],
                            'a9': ccr['ccr_attr9'],
                            'a10': ccr['ccr_attr10'],
                            'cwl': ccr['cumulative_wip_limit'],
                            'cgid': ccr['ccr_group__ccr_group_id'],
                            'cgcd': ccr['ccr_group__ccr_group_code'],
                            'cgnm': ccr['ccr_group__ccr_group_name'],
                            'pl': ccr['plant__plant_id'],
                            'plcd': ccr['plant__plant_code'],
                            'plnm': ccr['plant__plant_name'],
                            'dp': ccr['dept__dept_id'],
                            'dpcd': ccr['dept__dept_code'],
                            'dpnm': ccr['dept__dept_name'],
                            'did': ccr['draft_instance_id'],
                            'err': ccr['error'],
                            'cid': ccr['ccr_id'],
                            'iv': ccr['is_active']
                        }
                response_data.append(row)
            logger.info("Response data created")

            return api_response(response_data, msg="CCR draft data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetCCRDraftDataView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

