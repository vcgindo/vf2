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



class GetCalendarDataForMasterMgmtView(APIView):
    @swagger_auto_schema(
        operation_description="Get Calendar data for Master Mgmt UI",
         manual_parameters=[
            openapi.Parameter('masterId', openapi.IN_QUERY, description="Master Id", type=openapi.TYPE_INTEGER), #504
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
            holiday_data = PlantHolidayList.objects.filter(is_valid = True).prefetch_related('plant').values('id', 'is_week_day', 'day_of_week', 'holiday_start_date', 'holiday_end_date', 'is_working_day', 'description',
                                                                                                                    'ccr_id', 'plant', 'plant__plant_name', 'repeatation_bucket', 'repeat_duration_in_weeks')
            logger.info('Fetched holiday list data')

    
           #get filtered buffer data
            filtered_calendar_data = filter_calendar_data_by_params_master_mgmt(holiday_data, filter_data)
            logger.info('Fetched filtered buffer data')

            # map table fields and get data according to col_code for each field 
            field_to_code_mapping = {entry['table_field']: entry['col_code'] for entry in mdm_config_data}
            col_code_wise_calendar_data = []
            for holiday_entry in filtered_calendar_data:
                new_entry = {}
                for key, value in holiday_entry.items():
                    # If the key matches a table_field, replace it with col_code
                    new_key = field_to_code_mapping.get(key, key)
                    new_entry[new_key] = value
                col_code_wise_calendar_data.append(new_entry)
            logger.info("created a calendar data collection based on column code")

            return api_response(col_code_wise_calendar_data, msg="Calendar data fetched successfully", status_code=status.HTTP_200_OK)         

        except Exception as e:
            logger.error(f"Exception occurred GetCalendarDataForMasterMgmtView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

def filter_calendar_data_by_params_master_mgmt(queryset, filters):
          
    calendar_filters = {
        'day_of_week': filters.get('dow', {}),
        'holiday_start_date': filters.get('sd', {}),
        'holiday_end_date': filters.get('ed', {}),
        'is_working_day': filters.get('iwd', {}),
        'description': filters.get('dsc', {}),
        'ccr_id' : filters.get('cid', {}),
        'plant' : filters.get('plid', {}),
        'plant__plant_name' : filters.get('plnm', {}),
        'repeatation_bucket' : filters.get('rb', {}),
        'repeat_duration_in_weeks' : filters.get('rw', {}),

    }
    if calendar_filters:
        return filter_data_by_params(queryset, calendar_filters)
    else:
        return queryset

class SaveCalendarTaskView(APIView):
    @swagger_auto_schema(
        operation_description="Save Calendar task for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Id'), # 502
                'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User id'),
                'cData':  openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'dow': openapi.Schema(type=openapi.TYPE_STRING, description='Day of week'),
                            'sd': openapi.Schema(type=openapi.TYPE_STRING, description='Holiday Start date'),
                            'ed': openapi.Schema(type=openapi.TYPE_STRING, description='Holiday end date'),
                            'iwd': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Working Day'),
                            'dsc': openapi.Schema(type=openapi.TYPE_STRING, description='Holiday Description'),
                            'ccr': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Id'),
                            'pl': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                            'rb': openapi.Schema(type=openapi.TYPE_STRING, description='Repeatation Buckect Weekly/Monthly'),
                            'rd': openapi.Schema(type=openapi.TYPE_INTEGER, description='Repeatation Duration in Weeks'),
                            'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is existing data updated'),
                            'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is existing data deleted'),
                            'hid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Holiday List table Id'),
                        },
                        required=[ 'dow', 'sd', 'ed', 'iwd', 'dsc', 'ccr', 'pl', 'rb', 'rd','iu', 'id', 'hid']
                    )
                )
            },
            required=['mid', 'unm', 'uid', 'cData']

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
            calendar_data_to_be_added = request.data.get('cData', [])
            approvers = request.data.get('all_users')
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
            action_type_instance = TaskActionTypeMaster.objects.filter(action_type_desc='Add').first()
            logger.info('Fetched action type instance')
            
            # create draft ccr data instances

            # ccr_instances = CCRMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid  CCR instances')
            plant_instances = PlantMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid  Plant instances')

            calendar_task_instances = []
            with transaction.atomic():
                    TaskInstances.objects.create(
                        task_id=new_task_id,
                        created_on=datetime.now(),
                        task_name='Add - Calendar Holiday',
                        approver_ids= approver_id_list,
                        requester_id=user_id,
                        requester_name=user_name,
                        task_status=task_status_instance,
                        master_mapper=master_mapper_instance,
                        action_type=action_type_instance
                    )
                    logger.info('Task Instance created')
                    new_task_instance = TaskInstances.objects.filter(task_id = new_task_id).first()
                    logger.info('Fetched new Task Instance')

                    for calendar_data in calendar_data_to_be_added:
                        # ccr_instance = ccr_instances.filter(ccr_id = calendar_data['ccr']).first()
                        ccr_ids = calendar_data.get('ccr')
                        if not isinstance(ccr_ids, list):
                            ccr_ids = [ccr_ids] if ccr_ids is not None else []
                        logger.info('Fetched CCR instance')

                        plant_instance = plant_instances.filter(plant_id = calendar_data['plid']).first()
                        logger.info('Fetched plant instance')

                        plant_holiday_day_instance = None
                        if calendar_data['hid'] is not None:
                            plant_holiday_day_instance = PlantHolidayList.objects.filter(id = calendar_data['hid']).first()


                        day_of_week_values = [f"{item.get('id', '')}-{item.get('mn', '').strip()}-{item.get('md', '').strip()}".strip('-')for item in calendar_data.get('dow', [])]
                        

                        calendar_task_instance =  TaskCalendarMaster(
                                                    task_instance = new_task_instance,
                                                    day_of_week = day_of_week_values,
                                                    holiday_start_date = calendar_data['sd'],
                                                    holiday_end_date = calendar_data['ed'],
                                                    is_working_day = calendar_data['iwd'],
                                                    description = calendar_data['dsc'],                                                    
                                                    repeatation_bucket = calendar_data['rb'],
                                                    repeat_duration_in_weeks = calendar_data['rd'],
                                                    plant = plant_instance,
                                                    status = task_status_instance,
                                                    comments = None,
                                                    approver_id = None,
                                                    approver_name = None,
                                                    is_approved = False,
                                                    approved_on = None,
                                                    is_updated = calendar_data['iu'],
                                                    is_deleted = calendar_data['id'],
                                                    plant_holiday = plant_holiday_day_instance,
                                                    ccr_id = calendar_data['ccr_id'] if 'ccr_id' in calendar_data else None
                                                )
                        calendar_task_instances.append(calendar_task_instance)
                    
                    TaskCalendarMaster.objects.bulk_create(calendar_task_instances)
                    logger.info('Calendar Holiday tasks created')
            logger.info('Calendar Holiday tasks saved')

            return api_response(msg='Calendar Holiday tasks saved successfully', status_code=status.HTTP_200_OK)
        except Exception as ex:
            logger.error(f"Exception occurred in SaveCalendarTaskView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class GetCalendarTaskByIdView(APIView):
    @swagger_auto_schema(
        operation_description='Get Calendar Task by Id for Master Management UI',
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No Record Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def get(self, request):
        try:
            logger.info('Get Calendar Task by id for Master Management UI started')    

            # read data sent in parameters
            task_id = request.GET.get('taskId') # requesterId_datetime            
            logger.info('Read parameters for API')

            filter_condition = {}
            if task_id is not None:
                filter_condition = {'task_instance__task_id' : task_id}

            response_data = []
            #create response data            
            tasks = TaskCalendarMaster.objects.prefetch_related('plant', 'task_instance').filter(**filter_condition).values(
                                'id', 'task_instance__id', 'task_instance__task_id', 'task_instance__master_mapper_id',
                                'is_week_day', 'day_of_week', 'holiday_start_date', 'holiday_end_date', 'is_working_day',
                                'description', 'repeatation_bucket', 'repeat_duration_in_weeks', 'ccr_id',
                                'plant_id', 'plant__plant_name', 'is_approved', 'approver_id', 'approver_name', 'approved_on',
                                'is_deleted', 'is_updated', 'plant_holiday_id', 'comments')
            
            for task in tasks:
                dow_raw = task.get('day_of_week', '')
                dow_list = []
                if dow_raw:
                    for entry in dow_raw:
                        parts = entry.strip().split('-')
                        if len(parts) == 3:
                            dow_list.append({'id' : parts[0],'mn': parts[1], 'md': parts[2]})
                        elif len(parts) == 2:
                            dow_list.append({'id' : parts[0],'mn': '', 'md': parts[1]})
                
                ccr_ids = task.get('ccr_id') or []
                row = {
                        'tcmId': task['id'],
                        'dow': dow_list,
                        'sd': task['holiday_start_date'],
                        'ed': task['holiday_end_date'],
                        'iwd': task['is_working_day'],
                        'dsc': task['description'],
                        'rb': task['repeatation_bucket'],
                        'rd': task['repeat_duration_in_weeks'],
                        'ccr_id': ccr_ids,
                        'plid': task['plant_id'],
                        'plnm': task['plant__plant_name'],
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
                        'hid': task['plant_holiday_id'],
                    }
                response_data.append(row)
            logger.info("Response data created")

            return api_response(data = response_data, msg="Calendar task data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetCalendarTaskByIdView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class AddCalendarMasterView(APIView):
    @swagger_auto_schema(
        operation_description="Add Calendar Holidays to Holiday List Table",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'tid': openapi.Schema(type=openapi.TYPE_STRING, description='Task Id'),
                'ti_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Task Instance Id'),
                'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User Id'),
                'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User Name'),
                'mmid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Mapper Id'),
                'cData': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'tcmId': openapi.Schema(type=openapi.TYPE_STRING, description='Calendar Master Task Id'),
                            'dow': openapi.Schema(type=openapi.TYPE_STRING, description='Day of week as JSON e.g. {\"mn\": \"first\", \"md\": \"Mo\"}'),
                            'sd': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Holiday Start Date'),
                            'ed': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Holiday End Date'),
                            'iwd': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Working Day'),
                            'dsc': openapi.Schema(type=openapi.TYPE_STRING, description='Holiday Description'),
                            'ccr': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Id'),
                            'pl': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                            'rb': openapi.Schema(type=openapi.TYPE_STRING, description='Repetition Bucket Weekly/Monthly'),
                            'rd': openapi.Schema(type=openapi.TYPE_INTEGER, description='Repetition Duration in Weeks'),
                            'ia': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Approved'),
                            'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Existing Data Updated'),
                            'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Existing Data Deleted'),
                            'hid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Holiday List Table Id if Updated or Deleted'),
                            'cm': openapi.Schema(type=openapi.TYPE_STRING, description='Comment if Any Row is Rejected'),
                        },
                        required=['tcmId',  'dow', 'sd', 'ed', 'iwd', 'dsc', 'ccr', 'pl', 'rb', 'rd', 'ia', 'iu', 'id', 'hid', 'cm']
                    )
                )
            },
            required=['tid', 'uid', 'unm', 'mmid', 'cData']
        ),
        responses={
            200: openapi.Response(description="Successful response"),
            404: openapi.Response(description="No data Found"),
            400: openapi.Response(description="Bad Request"),
        }
    )
    def put(self, request):
        try:
            logger.info("Add to Calendar Master Processing started")
            # update task intance   /  task Calendar master /  Plant Holiday List

            #get current datetime
            date_time = datetime.now()

            # read data sent in parameters
            task_id = request.data.get('tid')
            task_instance_id = request.data.get('ti_id')
            user_id = request.data.get('uid')
            user_name = request.data.get('unm')
            master_mapper_id = request.data.get('mmid')
            calendar_data_to_be_added = request.data.get('cData', [])
            logger.info('Read parameters for API')

            task_action_status_instances = TaskActionStatusMaster.objects.all()
            logger.info('Fetched task_action_status_instances from TaskActionStatusMaster')

            task_action_status_instance_Approved = task_action_status_instances.filter(task_status_desc = 'Approved').first() #3
            task_action_status_instance_Rejected = task_action_status_instances.filter(task_status_desc = 'Rejected').first() #4
            task_action_status_instance_Partially_Approved = task_action_status_instances.filter(task_status_desc = 'Partially Approved').first() #2
            logger.info('Fetched action status instance for action Approved, Rejected and Partially Approved')

            calendar_master_tasks = TaskCalendarMaster.objects.filter(task_instance_id = task_instance_id)
            logger.info('Fetched CCR master task instance')
           
            #update Calendar <aster # no need to send ccr data
            # get ccr data from buffer task table and insert into ccr master
            max_holiday_data_id =  PlantHolidayList.objects.order_by('id').last().id
            logger.info('Fetched max max_holiday_data_id from Plant Holiday List')

            # set new holiday data id
            if max_holiday_data_id:
                new_holiday_data_id = max_holiday_data_id + 1
            else:
                new_holiday_data_id = 1

            # ccr_instances = CCRMaster.objects.filter(is_valid = True)
            # logger.info('Fetched all valid CCR instances')
            plant_instances = PlantMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid Plant instances')

            calendar_data_to_create = []
            plant_holiday_records_to_delete = []
            plant_holiday_records_to_update = []
            calendar_master_tasks_to_update = []
            approved_record_count = 0
            for calendar_data in calendar_data_to_be_added:
                tcmId = calendar_data['tcmId'] #task calendar master id                
                task = calendar_master_tasks.filter(id = tcmId).first()
                task.approver_id = user_id
                task.approver_name =  user_name
                task.approved_on = date_time
                task.comments = calendar_data['cm']
                
                if calendar_data['ia'] is True:
                    approved_record_count +=1
                    if calendar_data['id'] or calendar_data['iu'] is True:
                        plant_holiday_instance = PlantHolidayList.objects.filter(id = calendar_data['hid']).first()
                        if calendar_data['id'] is True:
                            plant_holiday_instance.is_valid = False
                            plant_holiday_records_to_delete.append(plant_holiday_instance) #if major reason is deleted . delete its corresponding minor reasons                           
                        if calendar_data['iu'] is True:
                            plant_holiday_instance.is_working_day = calendar_data['iwd']
                            plant_holiday_instance.day_of_week = calendar_data['dow']
                            plant_holiday_instance.holiday_start_date = calendar_data['sd']
                            plant_holiday_instance.holiday_end_date = calendar_data['ed']
                            plant_holiday_instance.description = calendar_data['dsc']
                            plant_holiday_instance.repeat_duration_in_weeks = calendar_data['rd']
                            plant_holiday_instance.repeatation_bucket = calendar_data['rb']
                            plant_holiday_instance.ccr = calendar_data['ccr_id']
                            plant_holiday_records_to_update.append(plant_holiday_instance)
                    else:
                        # ccr_instance = ccr_instances.filter(ccr_id = calendar_data['ccr']).first()
                        plant_instance = plant_instances.filter(plant_id = calendar_data['plid']).first()
                        calendar_data_to_create.append(
                            PlantHolidayList(
                                day_of_week=calendar_data['dow'],
                                holiday_start_date=calendar_data['sd'],
                                holiday_end_date=calendar_data['ed'],
                                is_working_day=calendar_data['iwd'],
                                description=calendar_data['dsc'],
                                repeatation_bucket=calendar_data['rb'],
                                repeat_duration_in_weeks=calendar_data['rd'],
                                ccr_id=calendar_data['ccr_id'],
                                plant=plant_instance
                            )
                        )
                        new_holiday_data_id += 1

                    task.is_approved = True
                    task.status = task_action_status_instance_Approved
                                        
                else:
                    task.is_approved = False
                    task.status = task_action_status_instance_Rejected
                calendar_master_tasks_to_update.append(task)

            fields_to_update_plant_holiday_list = {'is_week_day',
                                                   'is_working_day',
                                                   'day_of_week',
                                                   'holiday_start_date',
                                                   'holiday_end_date',
                                                   'description',
                                                   'repeat_duration_in_weeks',
                                                   'repeatation_bucket',
                                                   'ccr_id'
                                                   }
            fields_to_update_calendar_tasks = {'is_approved',
                                               'approver_id',
                                               'approver_name',
                                               'status',
                                               'approved_on',
                                               'comments'
                                               }
            logger.info('collected new calendar tasks to be added')

            #update task Instance
            task_instances = TaskInstances.objects.filter(task_id = task_id, id = task_instance_id, master_mapper_id = master_mapper_id)
            for task in task_instances:
                if len(calendar_master_tasks) == approved_record_count:
                    task.task_status = task_action_status_instance_Approved
                elif 0 == approved_record_count:
                    task.task_status = task_action_status_instance_Rejected
                else:
                    task.task_status = task_action_status_instance_Partially_Approved
            logger.info('Fetched task instance to be updated and assigned task status')

            with transaction.atomic():
                TaskInstances.objects.bulk_update(task_instances, ['task_status'])
                TaskCalendarMaster.objects.bulk_update(calendar_master_tasks_to_update, fields_to_update_calendar_tasks)
                if len(calendar_data_to_create) > 0:
                    PlantHolidayList.objects.bulk_create(calendar_data_to_create)
                if len(plant_holiday_records_to_update) > 0:
                    PlantHolidayList.objects.bulk_update(plant_holiday_records_to_update, fields_to_update_plant_holiday_list)
                if len(plant_holiday_records_to_delete) > 0:
                    PlantHolidayList.objects.bulk_update(plant_holiday_records_to_delete,['is_valid'])
            logger.info('Added calendar/ holiday data to PlantHolidayList table')

            return api_response(msg='Calendar data added successfully to PlantHolidayList', status_code=status.HTTP_200_OK)
           
        except Exception as ex:
            logger.error(f"Exception occurred in AddCalendarMasterView: {str(ex)}")
            return api_response(error=f"Exception occurred in AddCalendarMasterView : {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

class SaveCalendarMasterDraftView(APIView):
    @swagger_auto_schema(
        operation_description="Save Calendar Master  draft for Master Mgmt UI",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Master Id'), #504
                'unm': openapi.Schema(type=openapi.TYPE_STRING, description='User name'),
                'uid': openapi.Schema(type=openapi.TYPE_STRING, description='User Id'),
                'at': openapi.Schema(type=openapi.TYPE_STRING, description='Action Type'), #Add / Modify
                'cData':  openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'dow': openapi.Schema(type=openapi.TYPE_ARRAY, description='Day of week',
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT,
                                        properties={
                                            'mn': openapi.Schema(type=openapi.TYPE_STRING, description='Month occurrence (e.g., first)'),
                                            'md': openapi.Schema(type=openapi.TYPE_STRING, description='Day of week (e.g., Mo)')
                                        },
                                        required=['mn', 'md']
                                    )
                                ),
                            'sd': openapi.Schema(type=openapi.TYPE_STRING, description='Holiday Start date'),
                            'ed': openapi.Schema(type=openapi.TYPE_STRING, description='Holiday end date'),
                            'iwd': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is Working Day'),
                            'dsc': openapi.Schema(type=openapi.TYPE_STRING, description='Holiday Description'),
                            'ccr': openapi.Schema(type=openapi.TYPE_INTEGER, description='CCR Id'),
                            'pl': openapi.Schema(type=openapi.TYPE_INTEGER, description='Plant Id'),
                            'rb': openapi.Schema(type=openapi.TYPE_STRING, description='Repeatation Buckect Weekly/Monthly'),
                            'rd': openapi.Schema(type=openapi.TYPE_INTEGER, description='Repeatation Duration in Weeks'),
                            'err' : openapi.Schema(type=openapi.TYPE_STRING, description='Error'),
                            'iu': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is existing data updated'),
                            'id': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Is existing data deleted'),
                            'hid': openapi.Schema(type=openapi.TYPE_INTEGER, description='Holiday List table Id'),
                        },
                        required=[ 'dow', 'sd', 'ed', 'iwd', 'dsc', 'ccr', 'pl', 'rb', 'rd', 'err','iu', 'id', 'hid']
                    )
                )
            },
            required=['mid', 'unm', 'uid', 'at', 'cData']
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
            user_name = request.data.get('unm')
            user_id = request.data.get('uid')
            param_master_id = request.data.get('mid')
            action_type = request.data.get('at')
            calendar_data_to_be_added = request.data.get('cData', [])
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
            action_type_instance = TaskActionTypeMaster.objects.filter(action_type_desc=action_type)[0]
            logger.info('Fetched action type instance')

            # ccr_instances = CCRMaster.objects.filter(is_valid = True)
            # logger.info('Fetched all valid CCR Group instances')
            plant_instances = PlantMaster.objects.filter(is_valid = True)
            logger.info('Fetched all valid Plant instances')

            with transaction.atomic():
                DraftInstances.objects.create(
                    draft_id=new_draft_id,
                    action_type=action_type_instance,
                    user_name=user_name,
                    user_id=user_id,
                    created_on=datetime.now(),
                    last_modified_on=datetime.now(),
                    search_keys=master_mapper_data['display_name'],
                    master_mapper=master_mapper_instance,
                )
                 # create draft Calendar data instances
                new_row_id = 1
                calendar_draft_data_instances = []
                plant_holiday_instance = None

                for calendar_data in calendar_data_to_be_added:
                    # ccr_instance = ccr_instances.filter(ccr_id=calendar_data['ccr']).first()
                    plant_instance = plant_instances.filter(plant_id=calendar_data['plid']).first()
                    if calendar_data['hid'] is not None:
                        plant_holiday_instance = PlantHolidayList.objects.filter(id = calendar_data['hid']).first()
                    calendar_draft_data_instance = CalendarMasterDraft(
                        row_id=new_row_id,
                        day_of_week=calendar_data.get('dow', []),
                        holiday_start_date=calendar_data['sd'],
                        holiday_end_date=calendar_data['ed'],
                        is_working_day=calendar_data['iwd'],
                        description=calendar_data['dsc'],
                        repeatation_bucket=calendar_data['rb'],
                        repeat_duration_in_weeks=calendar_data['rd'] if 'rd' in calendar_data else None,
                        plant=plant_instance,
                        draft_instance_id=new_draft_id,
                        error=calendar_data['err'] if 'err' in calendar_data else None,
                        is_updated = calendar_data['iu'],
                        is_deleted = calendar_data['id'],
                        plant_holiday = plant_holiday_instance,
                        ccr_id = calendar_data['ccr_id'] if 'ccr_id' in calendar_data else None,
                    )
                    calendar_draft_data_instances.append(calendar_draft_data_instance)
                    new_row_id += 1
                CalendarMasterDraft.objects.bulk_create(calendar_draft_data_instances)
            logger.info('Draft instance and calendar data draft created')

            return api_response(msg='Calendar data Draft saved successfully', status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Exception occurred SaveCalendarMasterDraftView: {str(e)}")
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)

class GetCalendarMasterDraftView(APIView):
    pagination = CustomPagination
    @swagger_auto_schema(
        operation_description="Get Calenedar Master Draft for Master Management UI",
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
            logger.info("Get Calendar Master draft data for Master Management UI started")    
            calendar_draft_id =  request.GET.get('did')

            #get calendar draft data
            calendar_draft_data = CalendarMasterDraft.objects.filter(draft_instance_id=calendar_draft_id).prefetch_related('plant').values(
                                    'row_id', 'is_week_day', 'day_of_week', 'holiday_start_date', 'holiday_end_date', 'is_working_day', 'description',
                                    'ccr_id', 'plant_id', 'plant__plant_name', 'repeatation_bucket', 'repeat_duration_in_weeks'
                                    ,'draft_instance_id', 'error','plant_holiday_id',"is_updated","is_deleted")
            logger.info('Fetched calendar draft data')

            #create response data
            response_data = []
            for calendar_data in calendar_draft_data:
                row = {
                    'rid': calendar_data['row_id'],
                    'hid': calendar_data['plant_holiday_id'],
                    'dow': calendar_data['day_of_week'],
                    'sd': calendar_data['holiday_start_date'],
                    'ed': calendar_data['holiday_end_date'],
                    'iwd': calendar_data['is_working_day'],
                    'dsc': calendar_data['description'],
                    'rb': calendar_data['repeatation_bucket'],
                    'rd': calendar_data['repeat_duration_in_weeks'],
                    'ccr_id': calendar_data['ccr_id'],
                    'plid': calendar_data['plant_id'],
                    'plnm': calendar_data['plant__plant_name'],
                    'did': calendar_data['draft_instance_id'],
                    'err': calendar_data['error'],
                    'iu': calendar_data['is_updated'],
                    'id': calendar_data['is_deleted']
                }
                response_data.append(row)
            logger.info("Response data created")

            return api_response(response_data, msg="Calendar draft data fetched successfully", status_code=status.HTTP_200_OK)

        except Exception as ex:
            logger.error(f"Exception occurred in GetCalendarMasterDraftView: {str(ex)}")
            return api_response(error=f"Object does not exist: {str(ex)}", status_code=status.HTTP_400_BAD_REQUEST)

