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



class SavePoogiReasonMasterTaskView(APIView):
    @swagger_auto_schema(
        operation_description="Save Poogi Reason master task for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties= {             
                'mid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Id'),# 503
                'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User id'),
                'reasonData':  openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'majcd': openapi.Schema(type=openapi.TYPE_STRING, description='Major Reason Code'),
                            'majdsc': openapi.Schema(type=openapi.TYPE_STRING, description='Major Reason Description'),
                            'pl': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                            'ie': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is existing major reason'),
                            'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Deleted'),
                            'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Updated'),
                            'majid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Major Reason Id'),
                            'minData':  openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(type=openapi.TYPE_OBJECT,
                                    properties={
                                        'mincd': openapi.Schema(type=openapi.TYPE_STRING, description='Minor Reason Code'),
                                        'mindsc': openapi.Schema(type=openapi.TYPE_STRING, description='Minor Reason Description'),
                                        'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Deleted'),
                                        'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Updated'),
                                        'minid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Minor Reason Id'),
                                    },
                                    required=['mincd', 'mindsc', 'id', 'iu','minid']
                                )
                            )
                        },
                        required=['majcd', 'majdsc', 'pl', 'ie','id', 'iu', 'majid','minData']
                    )
                )
            },
            required=['mid', 'unm', 'uid', 'reasonData']

        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def put(self, request):
        try:
            # this api will save data in TaskInstances and TaskPoogiMajorReason and TaskPoogiMinorReason model
            # read data sent in parameters
            user_id = request.data.get('uid')
            user_name = request.data.get('unm')
            param_master_id = request.data.get('mid') #503
            reasons_to_be_added = request.data.get('reasonData', [])
            approvers = request.data.get('all_users')
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
            action_type_instance = TaskActionTypeMaster.objects.filter(action_type_desc='Add').first()
            logger.info('Fetched action type instance')

            plant_instances = PlantMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid plant instances')

            #create task buffer data instances
            with transaction.atomic():
                    TaskInstances.objects.create(
                        task_id=new_task_id,
                        created_on=datetime.now(),
                        task_name='Add - Poogi Reason Master',
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

                    for major_reason in reasons_to_be_added:                    
                        plant_instance = plant_instances.filter(plant_id = major_reason['pl']).first()
                        major_instance = None
                        if major_reason['ie'] or major_reason['id'] or major_reason['iu']:
                            major_instance = POOGIMajorReason.objects.filter(is_valid = True, major_reason_id = major_reason['majid']).first()
                        TaskPoogiMajorReason.objects.create(
                                                    task_instance = new_task_instance,
                                                    major_reason_code = major_reason['majcd'],
                                                    major_reason_desc = major_reason['majdsc'],
                                                    plant = plant_instance,
                                                    is_existing = major_reason['ie'],
                                                    is_deleted = major_reason['id'],
                                                    is_updated = major_reason['iu'],
                                                    major = major_instance,
                                                    status = task_status_instance,
                                                    comments = None,
                                                    approver_id = None,
                                                    approver_name = None,
                                                    is_approved = False,
                                                    approved_on = None
                                                )
                        new_major_reason_task_instance = TaskPoogiMajorReason.objects.order_by('id').last()
                        poogi_minor_reason_task_instances = []
                        for minor_reason in major_reason['minData']:
                            minor_reason_instance = None
                            if minor_reason['id'] or minor_reason['iu']:
                                minor_reason_instance = POOGIMinorReason.objects.filter(is_valid = True, minor_reason_id = minor_reason['minid']).first()
                            poogi_minor_reason_task_instance = TaskPoogiMinorReason(
                                                        task_major_reason = new_major_reason_task_instance,
                                                        minor_reason_code = minor_reason['mincd'],
                                                        minor_reason_desc = minor_reason['mindsc'],
                                                        is_deleted = minor_reason['id'],
                                                        is_updated = minor_reason['iu'],
                                                        minor = minor_reason_instance,
                                                        status = task_status_instance,
                                                        comments = None,
                                                        approver_id = None,
                                                        approver_name = None,
                                                        is_approved = False,
                                                        approved_on = None
                                                    )
                            poogi_minor_reason_task_instances.append(poogi_minor_reason_task_instance)
                        TaskPoogiMinorReason.objects.bulk_create(poogi_minor_reason_task_instances)

                    logger.info('Poogi Reason master tasks created')
            logger.info('Poogi Reason master task Instance and Tasks saved')

            return api_response(msg='Poogi Reason master tasks saved successfully', status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.error(f"Exception occurred in SavePoogiReasonMasterTaskView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class GetPoogiReasonMasterTaskByIdView(APIView):    
    @swagger_auto_schema(
        operation_description='Get Poogi Reason Task by Id for Master Management UI',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        try:
            logger.info("Get Poogi Reason Task by id for Master Management UI started")    

            # read data sent in parameters
            task_id = request.GET.get('taskId') # requesterId_datetime
            logger.info('Read parameters for API')

            filter_condition = {}
            if task_id is not None:
                filter_condition = {'task_instance__task_id' : task_id}

            response_data = []
            #create response data            
            tasks = TaskPoogiMajorReason.objects.prefetch_related('plant').prefetch_related('task_instance').filter(**filter_condition).prefetch_related('status').values('id', 'task_instance__id', 'task_instance__task_id', 'task_instance__master_mapper_id',
                                                                                                                                                                               'major_reason_code', 'major_reason_desc', 'plant_id', 'plant__plant_code', 'plant__plant_name', 'status__task_status_id', 'status__task_status_desc', 'comments', 'is_approved', 'approver_id', 'approver_name', 'approved_on','is_updated','is_deleted','major_id')
            
            logger.info('Fetched tasks from TaskPoogiMajorReason')

            #create mijot reason task id list
            major_reason_task_id_list = []
            for major_task in tasks:
                major_reason_task_id_list.append(major_task['id'])

            all_minor_reason_tasks = TaskPoogiMinorReason.objects.filter(task_major_reason_id__in=major_reason_task_id_list).prefetch_related('status').values(
                    'id','minor_reason_code', 'minor_reason_desc', 'status__task_status_id', 'status__task_status_desc', 'comments', 'is_approved', 'approver_id','approver_name', 'approved_on','is_updated','is_deleted','minor_id')
            logger.info('Fetched minor reasons for all major resons in list')

            for task in tasks:
                row =   {
                            'trmId': task['id'],  
                            'majcd': task['major_reason_code'],
                            'majdsc': task['major_reason_desc'],
                            'pl': task['plant_id'],
                            'plcd': task['plant__plant_code'],
                            'plnm': task['plant__plant_name'],
                            'st': task['status__task_status_id'],
                            'stnm': task['status__task_status_desc'],
                            'cm': task['comments'],
                            'ia': task['is_approved'],
                            'aid': task['approver_id'],
                            'anm': task['approver_name'],
                            'aon': task['approved_on'],
                            'tid': task['task_instance__task_id'],
                            'ti_id': task['task_instance__id'],
                            'mmid': task['task_instance__master_mapper_id'],
                            'iu': task['is_updated'],
                            'id': task['is_deleted'],
                            'majId': task['major_id'],
                            'minData':[]
                        }
               
                minor_reason_tasks = all_minor_reason_tasks.filter(task_major_reason_id=task['id'])
                minData = []
                for min_task in minor_reason_tasks:
                    minor_reason = {
                                        'mintid': min_task['id'],
                                        'mincd': min_task['minor_reason_code'],
                                        'mindsc': min_task['minor_reason_desc'],
                                        'st': min_task['status__task_status_id'],
                                        'stnm': min_task['status__task_status_desc'],
                                        'cm': min_task['comments'],
                                        'ia': min_task['is_approved'],
                                        'aid': min_task['approver_id'],
                                        'anm': min_task['approver_name'],
                                        'aon': min_task['approved_on'],
                                        'iu': min_task['is_updated'],
                                        'id': min_task['is_deleted'],
                                        'minid': min_task['minor_id'],

                                    }
                    minData.append(minor_reason)
                row['minData'] = minData
                
                response_data.append(row)
            logger.info("Response data created")

            return api_response(data = response_data, msg="Poogi reason task data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetTaskByIdView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class AddPOOGIReasonMasterView(APIView):
    @swagger_auto_schema(
        operation_description="Add POOGI Reason",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'tid': openapi.Schema(type=openapi.TYPE_STRING, description='Task Id'),# requesterId_datetime                    
                    'ti_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Task Instance Id'),# 1 , 2...
                    'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User Id'),
                    'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),                  
                    'mmid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master mapper Id'),# 3 for Poogi Reason Master  
                    'reasonData':  openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'trmId': openapi.Schema(type=openapi.TYPE_STRING, description='Poogi major reason Master Task Id'),
                                'majcd': openapi.Schema(type=openapi.TYPE_STRING, description='Major Reason Code'),
                                'majdsc': openapi.Schema(type=openapi.TYPE_STRING, description='Major Reason Description'),
                                'pl': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                                'ia': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Approved'),
                                'ie': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Existing major Reason'),
                                'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Deleted'),
                                'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Updated'),
                                'majid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Major Reason Id'), 
                                'cm': openapi.Schema(type=openapi.TYPE_STRING, description='Comment if reason is rejected'),                          
                                'minData':  openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'mintid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Min reason task id'),
                                            'mincd': openapi.Schema(type=openapi.TYPE_STRING, description='Minor Reason Code'),
                                            'mindsc': openapi.Schema(type=openapi.TYPE_STRING, description='Minor Reason Description'),
                                            'ia': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Approved'),
                                            'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Deleted'),
                                            'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Updated'),
                                            'minid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Minor Reason Id'),
                                            'cm': openapi.Schema(type=openapi.TYPE_STRING, description='Comment if reason is rejected'),
                                        },
                                        required=['mintid','mincd','mindsc','ia','ie','id','iu','minid']
                                    )
                                )
                            },
                            required=['trmId','majcd','majdsc','pl','ia','id','iu','minid']
                        )
                    )
                },
                required=['maj_cd', 'maj_desc', 'pl','ia','minData']
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
            logger.info("Add POOGI Reason Processing started")
            # update task intance   /  task POOGI master /  Major MInor reason Master tables

            #get current datetime
            date_time = datetime.now()

            # read data sent in parameters
            for data in request.data.get('data'):
                task_id = data.get('tid')
                task_instance_id = data.get('ti_id')
                user_id = data.get('uid')   
                user_name = data.get('unm')
                master_mapper_id = data.get('mmid')
                reasons_to_be_added = data.get('reasonData', [])
            logger.info('Read parameters for API')

            task_action_status_instances = TaskActionStatusMaster.objects.all()
            logger.info('Fetched task_action_status_instances from TaskActionStatusMaster')

            task_action_status_dict = {instance.task_status_desc: instance for instance in task_action_status_instances}

            task_action_status_instance_Approved = task_action_status_dict['Approved'] #3
            task_action_status_instance_Rejected = task_action_status_dict['Rejected']#4
            task_action_status_instance_Partially_Approved = task_action_status_dict['Partially Approved']#2
            logger.info('fetched action status instance for action Approved, Rejected and Partially Approved')

            poogi_major_reason_master_tasks = TaskPoogiMajorReason.objects.filter(task_instance_id = task_instance_id) #all major reasons against this tasks
            logger.info('Fetched all major reasons against this task instance')
            
            #update POOGIMajorReason # no need to send poogi reason data # get poogi reason data from poogi major reason task table and insert into Poogi major Reason
            poogi_major_reason_count = POOGIMajorReason.objects.count()
            max_maj_r_id = 0
            if 0 < poogi_major_reason_count:
                max_maj_r_id =  POOGIMajorReason.objects.order_by('major_reason_id').last().major_reason_id
                logger.info('Fetched max major reason id from POOGIMajorReason Master')
            new_maj_r_id = max_maj_r_id + 1

            fields_to_update_poogi_reason_tasks = {'is_approved',
                                                   'approver_id',
                                                   'approver_name',
                                                   'status',
                                                   'approved_on',
                                                   'comments'
                                                   }

            fields_to_update_poogi_minor_reason = {'minor_reason_code',
                                                   'minor_reason_desc'
                                                   }
            fields_to_update_poogi_major_reason = {'major_reason_code',
                                                   'major_reason_desc'
                                                   }

            plant_instances = PlantMaster.objects.filter(is_valid = True)
            min_reason_id_list = []
            for reason in reasons_to_be_added:
                for minR in reason['minData']:
                    min_reason_id_list.append(minR['mintid'])

            minor_reason_tasks = TaskPoogiMinorReason.objects.filter(id__in = min_reason_id_list)
            
            #start creating major minor reasons and update their statuses in respective table
            approved_major_reason_count = 0
            with transaction.atomic():
                major_reasons_to_be_deleted = []
                major_reasons_to_be_updated = []
                major_reason_tasks_to_update = []

                minor_reasons_to_be_deleted = []
                minor_reasons_to_be_updated = []
                minor_reason_tasks_to_update = []                
                min_reasons_to_create = []
                for reason in reasons_to_be_added:
                    approved_min_r_cnt = 0

                    major_reason_task = poogi_major_reason_master_tasks.filter(id = reason['trmId']).first() # reason['trmId'] is task poogi major reason master id
                    major_reason_task.approver_id = user_id
                    major_reason_task.approver_name =  user_name
                    major_reason_task.approved_on = date_time
                    major_reason_task.comments = reason['cm']
                    
                    if reason['ia'] is True:
                        approved_major_reason_count +=1
                        if reason['ie'] or reason['id'] or reason['iu'] is True:
                            major_reason_instance = POOGIMajorReason.objects.filter(major_reason_id = reason['majid']).first()
                            if reason['id'] is True:
                                major_reason_instance.is_valid = False
                                major_reasons_to_be_deleted.append(major_reason_instance) #if major reason is deleted . delete its corresponding minor reasons
                                minor_reason_instances = POOGIMinorReason.objects.filter(is_valid= True, major_reason_id = major_reason_instance.major_reason_id)
                                for min_r in minor_reason_instances:
                                    min_r.is_valid =False
                                    minor_reasons_to_be_deleted.append(min_r)
                            if reason['iu'] is True:
                                major_reason_instance.major_reason_code = reason['majcd']
                                major_reason_instance.major_reason_desc = reason['majdsc']
                                major_reasons_to_be_updated.append(major_reason_instance)
                        else:
                            plant_instance = plant_instances.filter(plant_id = reason['pl']).first()
                            POOGIMajorReason.objects.create(
                                                major_reason_id = new_maj_r_id, 
                                                major_reason_code = reason['majcd'],
                                                major_reason_desc = reason['majdsc'],
                                                is_valid = True,
                                                plant = plant_instance
                            )                            
                            logger.info('major reason created')
                            major_reason_instance = POOGIMajorReason.objects.filter(major_reason_id = new_maj_r_id).first()                            
                        major_reason_task.is_approved = True
                        major_reason_task.status = task_action_status_instance_Approved
                                               
                    else:
                        major_reason_task.is_approved = False
                        major_reason_task.status = task_action_status_instance_Rejected

                    for minR in reason['minData']: # add minor reasons
                        minor_reason_task = minor_reason_tasks.filter(id = minR['mintid']).first()
                        
                        minor_reason_task.approver_id = user_id
                        minor_reason_task.approver_name =  user_name                            
                        minor_reason_task.approved_on = date_time
                        minor_reason_task.comments = minR['cm']
                        
                        if minR['ia'] is True:
                            if minR['id'] or minR['iu'] is True:
                                minor_reason_instance = POOGIMinorReason.objects.filter(minor_reason_id = minR['minid']).first()
                                if minR['id'] is True:
                                    minor_reason_instance.is_valid  = False
                                    minor_reasons_to_be_deleted.append(minor_reason_instance)
                                if minR['iu'] is True:
                                    minor_reason_instance.minor_reason_code = minR['mincd']
                                    minor_reason_instance.minor_reason_desc = minR['mindsc']
                                    minor_reasons_to_be_updated.append(minor_reason_instance)
                            else:                              
                                min_reason_to_create = POOGIMinorReason(
                                            minor_reason_code = minR['mincd'],
                                            minor_reason_desc = minR['mindsc'],
                                            is_valid = True,
                                            major_reason = major_reason_instance
                                )
                                min_reasons_to_create.append(min_reason_to_create)
                                
                            approved_min_r_cnt +=1                            
                            minor_reason_task.is_approved = True
                            minor_reason_task.status = task_action_status_instance_Approved                            
                        else: 
                            minor_reason_task.is_approved = False
                            minor_reason_task.status = task_action_status_instance_Rejected
                            
                        minor_reason_tasks_to_update.append(minor_reason_task)
                        
                    if (reason['ie'] is True) and (reason['id'] or reason['iu'] is False) and (reason['ia'] is False):
                        if approved_min_r_cnt < len(reason['minData']):
                            major_reason_task.is_approved = False
                            major_reason_task.status = task_action_status_instance_Rejected
                        if approved_min_r_cnt == len(reason['minData']):
                            approved_major_reason_count +=1
                            major_reason_task.is_approved = True
                            major_reason_task.status = task_action_status_instance_Approved
                        else:
                            major_reason_task.is_approved = False
                            major_reason_task.status = task_action_status_instance_Partially_Approved
                    major_reason_tasks_to_update.append(major_reason_task)

                    new_maj_r_id += 1

                if 0 < len(major_reasons_to_be_updated):
                    POOGIMajorReason.objects.bulk_update(major_reasons_to_be_updated, fields_to_update_poogi_major_reason)
                if 0 < len(major_reasons_to_be_deleted):
                    POOGIMajorReason.objects.bulk_update(major_reasons_to_be_deleted, ['is_valid'])
                if 0 < len(major_reason_tasks_to_update):
                    TaskPoogiMajorReason.objects.bulk_update(major_reason_tasks_to_update, fields_to_update_poogi_reason_tasks)
                if 0 < len(min_reasons_to_create):
                    POOGIMinorReason.objects.bulk_create(min_reasons_to_create)        
                if 0 < len(minor_reasons_to_be_updated):
                    POOGIMinorReason.objects.bulk_update(minor_reasons_to_be_updated, fields_to_update_poogi_minor_reason)
                if 0 < len(minor_reasons_to_be_deleted):
                    POOGIMinorReason.objects.bulk_update(minor_reasons_to_be_deleted, ['is_valid'])
                if 0 < len(minor_reason_tasks_to_update):
                    TaskPoogiMinorReason.objects.bulk_update(minor_reason_tasks_to_update, fields_to_update_poogi_reason_tasks)
                logger.info('Major Minor reasons task created/updated/deleted')                    

                #update task Instance
                task_instances = []
                task_instance = TaskInstances.objects.filter(task_id = task_id, id = task_instance_id, master_mapper_id = master_mapper_id).first()
                task_instances.append(task_instance)
                logger.info('Fetched task instance to be updated and assigned task status')
                for task_instance in task_instances:
                    if approved_major_reason_count == len(reasons_to_be_added) or approved_major_reason_count > 0 :
                        task_instance.task_status = task_action_status_instance_Approved
                    elif approved_major_reason_count == 0:
                        task_instance.task_status = task_action_status_instance_Rejected
                    
                TaskInstances.objects.bulk_update(task_instances, ['task_status'])
                logger.info('Task Instance updated')

            logger.info('Added poogi reasons to major reason master and minor reason master')

            return api_response(msg='Reasons(s) added successfully', status_code=status.HTTP_200_OK)
           
        except Exception as ex:
            logger.error(f"Exception occurred in AddPOOGIReasonMasterView: {str(ex)}")
            return api_response(error=f"Exception occurred in AddPOOGIReasonMasterView : {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class SavePoogiReasonDraftView(APIView):
    @swagger_auto_schema(
        operation_description="Save Poogi Reason draft for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'mid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Id'),# 503
                    'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                    'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User Id'),
                    'at': openapi.Schema(type=openapi.TYPE_STRING, description='Action Type'),
                    'reasonData':  openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'majcd': openapi.Schema(type=openapi.TYPE_STRING, description='Major Reason Code'),
                                'majdsc': openapi.Schema(type=openapi.TYPE_STRING, description='Major Reason Description'),
                                'pl': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                                'err': openapi.Schema(type=openapi.TYPE_STRING, description='Major Reason Error'),
                                'ie': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Existing Major Reason'),
                                'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Deleted'),
                                'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Updated'),
                                'majid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Major Reason Id'),
                                'minData':  openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT,
                                                         properties={
                                                             'mincd': openapi.Schema(type=openapi.TYPE_STRING, description='Minor Reason Code'),
                                                             'mindsc': openapi.Schema(type=openapi.TYPE_STRING, description='Minor Reason Description'),
                                                             'err': openapi.Schema(type=openapi.TYPE_STRING, description='Minor Reason Error'),
                                                             'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Deleted'),
                                                             'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Updated'),
                                                             'minid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Minor Reason Id'),
                                                         },
                                                         required=['mincd','mindsc','err','id','iu','minid']
                                                         )
                                )
                            },
                            required=['majcd','majdsc','pl','err','ie','id','iu','minData','majid']
                        )
                    )
                },
                required=['mid', 'unm', 'uid', 'reasonData']
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
                reasons_to_be_added = data.get('reasonData', [])
            logger.info('Read parameters for API')

             # get master mapper instance
            master_mapper_instance = MasterMapper.objects.filter(is_valid = True, master_id = param_master_id).first()
            logger.info('Fetched Master Mapper instance')

            #get current date time
            date_time = datetime.now().strftime("%Y%m%d%H%M%S")
            new_draft_id = user_id +'_'+ date_time
            logger.info('current date time is assigned to a variable')

            #get action type instance
            action_type_instance = TaskActionTypeMaster.objects.filter(action_type_desc=action_type).first()
            logger.info('Fetched action type instance')

            plant_instances = PlantMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid plant instances')
            with transaction.atomic():
                    DraftInstances.objects.create(
                                                    draft_id= new_draft_id,
                                                    action_type=action_type_instance,
                                                    user_name= user_name,
                                                    user_id= user_id,
                                                    created_on = datetime.now(),
                                                    last_modified_on=datetime.now(),
                                                    search_keys = master_mapper_instance.display_name,
                                                    master_mapper = master_mapper_instance
                                                    )
                    #create draft reason data instances
                    new_row_id = 1
                    minor_reason_draft_data_instances = []
                    for major_reason in reasons_to_be_added:
                        plant_instance = plant_instances.filter(plant_id = major_reason['pl']).first()
                        major_instance = None
                        if major_reason['ie'] or major_reason['id'] or major_reason['iu']:
                            major_instance = POOGIMajorReason.objects.filter(is_valid = True, major_reason_id = major_reason['majid']).first()
                        PoogiMajorReasonDraft.objects.create(
                                                    row_id=new_row_id,
                                                    major_reason_code = major_reason['majcd'],
                                                    major_reason_desc = major_reason['majdsc'],
                                                    plant = plant_instance,
                                                    draft_instance_id = new_draft_id,
                                                    error = major_reason['err'],
                                                    is_existing = major_reason['ie'],
                                                    is_deleted = major_reason['id'],
                                                    is_updated = major_reason['iu'],
                                                    major = major_instance
                                                )                        

                        major_reason_draft_instance = PoogiMajorReasonDraft.objects.filter(draft_instance_id = new_draft_id, row_id = new_row_id).first()
                        new_row_id +=1
                        min_res_row_id = 1
                        for min_res in major_reason['minData']:
                            minor_reason_instance = None
                            if min_res['id'] or min_res['iu']:
                                minor_reason_instance = POOGIMinorReason.objects.filter(is_valid = True, minor_reason_id = min_res['minid']).first()
                            minor_reason_draft_data_instance = PoogiMinorReasonDraft(
                                row_id = min_res_row_id,
                                minor_reason_code = min_res['mincd'],
                                minor_reason_desc = min_res['mindsc'],
                                major_reason_draft = major_reason_draft_instance,
                                error = min_res['err'],
                                is_deleted = min_res['id'],
                                is_updated = min_res['iu'],
                                minor = minor_reason_instance
                            )
                            min_res_row_id +=1
                            minor_reason_draft_data_instances.append(minor_reason_draft_data_instance)
                    PoogiMinorReasonDraft.objects.bulk_create(minor_reason_draft_data_instances)
            logger.info('Draft instance and poogi reason draft created')

            return api_response(msg='Poogi Reason Draft saved successfully', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Exception occurred SavePoogiReasonDraftView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class GetPoogiReasonDraftDataView(APIView):
    pagination = CustomPagination
    @swagger_auto_schema(
        operation_description="Get Poogi Reason Draft data for Master Management UI",
        manual_parameters=[
            openapi.Parameter('did', openapi.IN_QUERY, description="Draft Id", type=openapi.TYPE_STRING), # Draft Instance Id
            openapi.Parameter('mid', openapi.IN_QUERY, description="Master Id", type=openapi.TYPE_INTEGER) #3
        ],
         responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )

    def get(self, request):
        try:
            logger.info("Get Poogi Reason draft data for Master Management UI started")    
            poogi_reason_draft_id =  request.GET.get('did')

            #get poogi draft data
            poogi_major_reason_draft_data = PoogiMajorReasonDraft.objects.filter(draft_instance_id=poogi_reason_draft_id).prefetch_related('plant').values(
                'id','row_id', 'major_reason_code', 'major_reason_desc','plant__plant_id','plant__plant_code','plant__plant_name','draft_instance_id', 'error','is_deleted','is_updated','is_existing')
            logger.info('Fetched buffer draft data')

            #create response data
            response_data = []
            for major_reason in poogi_major_reason_draft_data:
                row =   {  
                            'rid': major_reason['row_id'],
                            'majcd': major_reason['major_reason_code'],
                            'majdsc': major_reason['major_reason_desc'],
                            'plid': major_reason['plant__plant_id'],
                            'plcd': major_reason['plant__plant_code'],
                            'plnm': major_reason['plant__plant_name'],
                            'did': major_reason['draft_instance_id'],
                            'err': major_reason['error'],
                            'ie': major_reason['is_existing'],
                            'id': major_reason['is_deleted'],
                            'iu': major_reason['is_updated'],
                            'minData': []
                        }

                minor_reason_tasks = PoogiMinorReasonDraft.objects.filter(major_reason_draft_id=major_reason['id']).values(
                    'id','row_id','minor_reason_code', 'minor_reason_desc', 'error','is_deleted')
                minData = []
                for min_task in minor_reason_tasks:
                    minor_reason = {
                                        'minid': min_task['id'],
                                        'minrid': min_task['row_id'],
                                        'mincd': min_task['minor_reason_code'],
                                        'mindsc': min_task['minor_reason_desc'],
                                        'err': min_task['error'],
                                        'id': min_task['is_deleted'],
                                        'iu': major_reason['is_updated'],
                                    }
                    minData.append(minor_reason)
                row['minData'] = minData
                response_data.append(row)
            logger.info("Response data created")
            
            return api_response(response_data, msg="Poogi Reason draft data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetPoogiReasonDraftDataView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)


class GetPoogiReasonMasterForMasterMgmtView(APIView):
    @swagger_auto_schema(
        operation_description="Get Poogi Reason Master data for Master Mgmt UI",
         manual_parameters=[
            openapi.Parameter('masterId', openapi.IN_QUERY, description="Master Id", type=openapi.TYPE_INTEGER), #503
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
           
            poogi_major_reason_data = POOGIMajorReason.objects.filter(is_valid = True).prefetch_related('plant').annotate(plcd= F('plant__plant_code'),plnm=F('plant__plant_name')).values('major_reason_id','major_reason_code','major_reason_desc','plant_id','plcd','plnm')
            logger.info('Fetched Poogi Major reasons')

            poogi_minor_reason_data = POOGIMinorReason.objects.filter(is_valid = True).values('minor_reason_id','minor_reason_code','minor_reason_desc','major_reason_id')
            logger.info('Fetched poogi minor reasons')
            filtered_poogi_minor_reason_data = filter_poogi_reason_data_by_params_master_mgmt(poogi_minor_reason_data, filter_data)
            logger.info('Fetched filtered poogi reason data')
            filtered_poogi_major_reason_data = filter_poogi_reason_data_by_params_master_mgmt(poogi_major_reason_data, filter_data)
            logger.info('Fetched filtered poogi reason data')

            filtered_poogi_reason_data = []
            for majReason in filtered_poogi_major_reason_data:
                majId = majReason['major_reason_id']
                minor_reasons = [item for item in filtered_poogi_minor_reason_data if item['major_reason_id'] == majId]
                if 0 < len(minor_reasons):
                    majReason['minData']= minor_reasons
                    filtered_poogi_reason_data.append(majReason)

            # map table fields and get data according to col_code for each field 
            field_to_code_mapping = {entry['table_field']: entry['col_code'] for entry in mdm_config_data}
            col_code_wise_reason_data = []
            for reason_entry in filtered_poogi_reason_data:
                new_entry = {}
                for key, value in reason_entry.items():
                    # If the key matches a table_field, replace it with col_code
                    new_key = field_to_code_mapping.get(key, key)
                    new_entry[new_key] = value
                    col_code_wise_min_reason_data = []
                    new_min_entry = {}
                    if 'minData' == key:
                        for dict in value:
                            new_min_entry = {}
                            for key, value in dict.items():
                                # If the key matches a table_field, replace it with col_code
                                new_min_key = field_to_code_mapping.get(key, key)
                                new_min_entry[new_min_key] = value
                            col_code_wise_min_reason_data.append(new_min_entry)
                        new_entry['minData'] = col_code_wise_min_reason_data
                col_code_wise_reason_data.append(new_entry)
            logger.info("created a poogi reason data collection based on column code")

            return api_response(col_code_wise_reason_data, msg="Master Poogi Reason data fetched successfully", status_code=status.HTTP_200_OK)         

        except Exception as e:
            logger.error(f"Exception occurred GetPoogiReasonMasterForMasterMgmtView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

def filter_poogi_reason_data_by_params_master_mgmt(queryset, filters):
          
    poogi_reason_filters = {
        'major_reason_code': filters.get('majcd', {}),
        'major_reason_desc': filters.get('majdsc', {}),
        'minor_reason_code': filters.get('mincd', {}),
        'minor_reason_desc': filters.get('mindsc', {}),
        'plnm': filters.get('plnm', {})
    }
    if poogi_reason_filters:
        return filter_data_by_params(queryset, poogi_reason_filters)
    else:
        return queryset
        