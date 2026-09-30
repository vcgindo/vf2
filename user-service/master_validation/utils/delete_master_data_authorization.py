import pandas as pd
from django.db.models import Q
from ..db_config.db_mappings import MASTER_ID_TO_PREFINAL_MODEL_MAPPING,MASTER_ID_TO_FINAL_MODEL_MAPPING
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from ..utils.responses import GetMasterDataResponses
from ..utils.replace_headers import replace_headers_with_keys, replace_headers_with_keys_streaming
from ..utils.get_master_query_builder import get_query_builder
from api.models import LocationMasterModels, SKUMasterModels, SeasonatilyMaster
from ..models.final_models import ISTYieldMasterModel

def data_authorization(master_id, data, user_product_permissions, user_location_permissions):
    if master_id in ['27']:  # sku master
        user_product_permissions.drop(columns = ['id'], inplace = True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        authorized_data = pd.merge(user_product_permissions, data, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        unauthorized_data = pd.merge(user_product_permissions, data, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'outer', indicator=True)
        unauthorized_data = unauthorized_data[unauthorized_data['_merge'] == 'right_only']
        return authorized_data, unauthorized_data
    
    if master_id in ['21']:  # location master
        user_location_permissions.drop(columns = ['id'], inplace = True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        authorized_data = pd.merge(user_location_permissions, data, on=['wh_type','wh_region','wh_location_group'], how = 'inner')
        unauthorized_data = pd.merge(user_location_permissions, data, on=['wh_type','wh_region','wh_location_group'], how = 'outer', indicator=True)
        unauthorized_data = unauthorized_data[unauthorized_data['_merge'] == 'right_only']
        return authorized_data, unauthorized_data
    
    if master_id in ['16']:  # deployment master
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        sku_master = pd.DataFrame(SKUMasterModels.objects.all().values())
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        authorized_sku_codes = list(pd.merge(user_product_permissions, sku_master[['sku_code','product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']], on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'left')['sku_code'])
        
        authorized_data = data[data['sku_code'].isin(authorized_sku_codes) & (data['wh_code'].isin(authorized_wh_codes))]
        unauthorized_data = data[~data['sku_code'].isin(authorized_sku_codes) | (~data['wh_code'].isin(authorized_wh_codes))]
        return authorized_data, unauthorized_data
    if master_id in ['18']:  # ISTYield
        user_product_permissions.drop(columns = ['id'], inplace = True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        authorized_data = pd.merge(user_product_permissions, data,
                               on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        unauthorized_data = pd.merge(user_product_permissions, data,
                               on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'outer', indicator=True)
        unauthorized_data = unauthorized_data[unauthorized_data['_merge'] == 'right_only']
        return authorized_data, unauthorized_data
    if master_id in ['26']:  # seasonaity master
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        authorized_data = pd.merge(user_product_permissions, data, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        authorized_data = authorized_data[authorized_data['wh_code'].isin(authorized_wh_codes)]
        unauthorized_data = data.merge(authorized_data, how='outer', indicator=True).query('_merge == "left_only"').drop('_merge', axis=1)
        
        return authorized_data, unauthorized_data
    if master_id in ['20']:  # location capacity master
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        authorized_data = pd.merge(user_product_permissions, data, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        authorized_data = authorized_data[authorized_data['wh_code'].isin(authorized_wh_codes)]
        unauthorized_data = data.merge(authorized_data, how='outer', indicator=True).query('_merge == "left_only"').drop('_merge', axis=1)
        
        return authorized_data, unauthorized_data
    
    if master_id in ['24']:  # pivotal master
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        authorized_data = pd.merge(user_product_permissions, data, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        authorized_data = authorized_data[authorized_data['wh_code'].isin(authorized_wh_codes)]
        unauthorized_data = data.merge(authorized_data, how='outer', indicator=True).query('_merge == "left_only"').drop('_merge', axis=1)
        
        return authorized_data, unauthorized_data
    
    if master_id in ['15']:  # contact
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        authorized_data = data[data['wh_code'].isin(authorized_wh_codes)]
        unauthorized_data = data.merge(authorized_data, how='outer', indicator=True).query('_merge == "left_only"').drop('_merge', axis=1)
        return authorized_data, unauthorized_data
    
    if master_id in ['23']:  # location priority
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        authorized_ph1 = list(user_product_permissions['product_hierarchy_1'].unique())
        authorized_data = data[data['wh_code'].isin(authorized_wh_codes)]
        authorized_data = authorized_data[authorized_data['product_hierarchy_1'].isin(authorized_ph1)]
        unauthorized_data = data.merge(authorized_data, how='outer', indicator=True).query('_merge == "left_only"').drop('_merge', axis=1)
        return authorized_data, unauthorized_data
    
    if master_id in ['17']: # discount period master
        columns = data.columns
        return data, pd.DataFrame(columns=columns)