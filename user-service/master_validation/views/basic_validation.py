from django.shortcuts import render
from rest_framework.views import APIView
import os
import pandas as pd
import json
import time
from django.db import connection, transaction, DatabaseError

from rest_framework.permissions import IsAuthenticated

from common.permissions import require_roles_permission
from common.user_role import UserRole
import io
from api.serializer.profile import UserProfileSerializer
from api.core import ResponseUser

from rest_framework import status

from pathlib import Path

from rest_framework.response import Response

from apps.settings import USER_STORIES_STORAGE
from ..validators.commons.master_id_mapping import MASTER_ID_TO_DTYPE,MASTER_ID_TO_VALIDATION
from ..validators.retail_validation_rules.validation_rules_for_all_masters import rules
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse


from ..services import DatabaseSyncServices
from ..models.excel_upload import *
from common.utils import max_power_of_ten_divisor
from ..utils.read_temporaryfile_to_disk import read_uploaded_master_file

from ..utils.replace_headers import replace_headers_with_keys_streaming
from rest_framework.decorators import authentication_classes, permission_classes
from ..docs.basic_validation import basic_validation_docs
import math
from channels.db import database_sync_to_async 

def get_csv_path(root_path,file_name):
    return os.path.join(str(root_path),file_name)

@database_sync_to_async
def get_process_and_update_total_rows(process_id, total_rows):
    process = ExcelUpload.objects.get(process_id=process_id)
    process.total_rows = total_rows
    process.save()
    return process

@database_sync_to_async
def update_progress(process_id, progress):
    ExcelUpload.objects.filter(process_id=process_id).update(progress=progress)

@database_sync_to_async
def delete_process(process_id):
    ExcelUpload.objects.filter(process_id=process_id).delete()


async def iterator(df, validation_fn, key_to_header_map, screen_type, validation_rules, process_id):
    update_interval = math.ceil(max_power_of_ten_divisor(len(df))/10)
    await get_process_and_update_total_rows(process_id, len(df))

    for index, row in df.iterrows():
        if (index + 1) % update_interval == 0 or index == len(df) - 1:
            await update_progress(process_id, index + 1)
        yield validation_fn(row, index, key_to_header_map, screen_type, validation_rules)

    await delete_process(process_id)



    
# Create your views here.

class MasterValidationView(APIView):
    permission_classes = [IsAuthenticated]
    global key_to_header_map
    @basic_validation_docs()
    # @require_roles_permission(roles=[UserRole.ADMIN, UserRole.REQUESTOR])
    def post(self, request, *args, **kwargs):
        """
        This view handles both the masters from vectorflow as well as the retail applicaiton
        Process: 
        1) load ui configuration
        2) call the respective validation functoin according to each master
        3) return the required response with the appropriate warnings and errors
        """
        ui_config = json.loads(request.data['ui_config'])
        screen_type = json.loads(request.data['screen_type'])['screenType']
        master_id = str(request.get_full_path().split('/')[-1])
        uploaded_file = request.FILES['file']
 
        #Create Excel Upload Progress
        process_id = json.loads(request.data['process_id'])['processId']
        last_object = ExcelUpload.objects.last()
        last_id = last_object.id if last_object else 0  # If no objects exist, start from 0
        new_id = last_id + 1
        ExcelUpload.objects.create(id=new_id, process_id=process_id)
        if int(master_id) < 14:       # NMS masters    

            raw_master_df = read_uploaded_master_file(uploaded_file)
            #Replace Header With Keys
            key_to_header_map = replace_headers_with_keys_streaming(raw_master_df,ui_config, master_id)
    
            ValidationClass = MASTER_ID_TO_VALIDATION[master_id]

            stream = iterator(raw_master_df,ValidationClass(raw_master_df).validation,key_to_header_map,screen_type,{},process_id)

            response =  StreamingHttpResponse(stream,status=200, content_type='text/event-stream')
            response['Cache-Control']= 'no-cache'

        else:               # retail masters
            validation_rules = rules[master_id]
            master_df = read_uploaded_master_file(uploaded_file)        
            master_df.rename(columns = {'cogs_/_mrp':'cogs_mrp',
                                        'shippment_cost_per_pc':'shipment_cost_per_pc'}, inplace=True)
            ValidationClass = RetailMaster(master_df, validation_rules)
            key_to_header_map = replace_headers_with_keys_streaming(master_df,ui_config, master_id)
            master_df = ValidationClass.sanitize_master(master_df)
            response = ValidationClass.validation(master_df,key_to_header_map,validation_rules,process_id)
            response = json.loads(response)
            response = JsonResponse(response, safe = False)
            response['Cache-Control']= 'no-cache'
            
        return response