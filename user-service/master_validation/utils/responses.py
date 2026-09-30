
from rest_framework import status
import pandas as pd
class GetMasterDataResponses:
    def __init__(self):
        self.rec_count_response = {
        "recordCount": "",
        "data": None,
        "status": 0,
        "msg": "record count",
        "errorCount": None,
        "error": None,
        "conflictErrorCount": None,
        "conflictError": None
    }
        
    def generate_rec_count_response(self, count):
        response = self.rec_count_response
        response['recordCount'] = count
        return response
    def generate_rec_response(self, data, ):
       return {"recordCount":len(data),
               "data":data} 

class MasterValidationResponses:
    
    def __init__(self):
        self.response_data = {
        "taskId": 1,
        "status": 200,
        "msg": 'msg',
        "errorCount": None,
        "errorType":None,
        "data" : [],
        "error": [],
        "conflictErrorCount": 0,
        "conflictError": [],
        "missingDataErrorCount": 0,
        "missingDataError": []
        }
        
        self.type_error_object = {
        "errorType" : '',
        "errorData":[]
        }
    
    def create_type_error_object(self, key, val):
        type_error_object = self.type_error_object
        type_error_object['errorType'] = key
        type_error_object['errorData'] = val
        return type_error_object
    
    
    def construct_response(self,data,error_objects, error_count, error_type):
        response_data = self.response_data
        response_data['data'] = data
        response_data['error'] = error_objects
        response_data['errorCount'] = str(error_count)
        
        # response_data['conflictErrorCount'] = response_data['errorCount']
        # response_data['conflictError'] = response_data['error']
        
        if len(response_data['data']) != 0 and int(response_data['errorCount'] ) != 0:
            response_data['status'] = status.HTTP_200_OK
            response_data['msg'] = 'HTTP_207_MULTI_STATUS'
        elif len(response_data['data']) == 0 and int(response_data['errorCount'] ) != 0:
            if error_type == 'conflict':
                response_data['status'] = status.HTTP_200_OK
                response_data['msg'] = 'HTTP_409_CONFLICT'
            elif error_type == 'missing_data':
                response_data['status'] = status.HTTP_200_OK
                response_data['msg'] = 'HTTP_404_NOT_FOUND'
        elif len(response_data['data']) != 0 and int(response_data['errorCount'] ) == 0:
            response_data['status'] = status.HTTP_200_OK
            response_data['msg'] = 'HTTP_200_OK'
        return response_data
        
    def construct_config_response(self, config_data):
        added_masters = {}
        response = {}
        data = []
        ui_config = {}
        
        config_data_df = pd.DataFrame(config_data)
        config_data_df = config_data_df.drop(['id','table_field','cell_allignment'], axis=1)
        config_data_df.rename(columns={
                                  'master_id':'id',
                                  'master_name':'name',
                                  'header':'displayName',
                                  'col_code':'key',
                                  'col_position':'col_Position',
                                  'is_add':'isAdd',
                                  'is_edit':'isEdit',
                                  'is_filter':'isFilter',
                                  'is_download':'isDownload',
                                  'is_applicable':'isApplicable'                                
                                  }, inplace=True)
        groups = config_data_df.groupby(['id','name'])
        for name, group in groups:
            
            config = {}
            group.drop(['id','name'], axis=1, inplace=True)
            fields = group.to_dict(orient='records')
            
            config['id'] = str(name[0])
            config['name'] = name[1]
            config['fields'] = fields
            
            data.append(config)
            
        ui_config["data"] = data
        ui_config['recordCount'] = str(len(groups))
        ui_config["status"] = 200
        ui_config["msg"] = None
        ui_config["errorCount"] = None
        ui_config["error"] = None
        ui_config["conflictErrorCount"] = None
        ui_config["conflictError"] = None
        return ui_config