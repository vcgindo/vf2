import pandas as pd
from django.db.models import Q
from ..db_config.db_mappings import MASTER_ID_TO_PREFINAL_MODEL_MAPPING,MASTER_ID_TO_FINAL_MODEL_MAPPING
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from ..utils.responses import GetMasterDataResponses
from ..utils.replace_headers import replace_headers_with_keys, replace_headers_with_keys_streaming
from ..utils.get_master_query_builder import get_query_builder
from api.models import LocationMasterModels, SKUMasterModels, SeasonatilyMaster, LocationsFilter, PivotalSizeMasterModels
from master_validation.models.final_models import LocationCapacityMasterModel
from ..models.final_models import ISTYieldMasterModel
from .generate_filter_query import create_dynamic_filter_query

def get_master_data_count(master_id, user_product_permissions,user_location_permissions, filters = None):
    if master_id in ['15']: # contact
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)

        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            all_objects = model.objects.filter( Q(wh_code__in = authorized_wh_codes) & filter_query)
        else: 
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes ))
        

        all_objects = pd.DataFrame(all_objects.values())    
        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)

    if master_id in ['23']: # location priority master
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        authorized_ph1 = list(user_product_permissions['product_hierarchy_1'].unique())
        
        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes ) & Q(product_hierarchy_1__in = authorized_ph1) & filter_query)
        else:
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes ) & Q(product_hierarchy_1__in = authorized_ph1))

    
        all_objects = pd.DataFrame(all_objects.values())    
        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)
    
    if master_id in ['16']: # deployment
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        sku_master = pd.DataFrame(SKUMasterModels.objects.all().values())
        sku_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        authorized_sku_codes = list(pd.merge(user_product_permissions, sku_master[['sku_code','product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']], on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'left')['sku_code'])

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes) & Q(sku_code__in = authorized_sku_codes) & filter_query)
        else:
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes) & Q(sku_code__in = authorized_sku_codes))


        all_objects = pd.DataFrame(all_objects.values())    
        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)
        
    if master_id in ['18']: # ISTYield
        ist_yield = pd.DataFrame(ISTYieldMasterModel.objects.all().values())
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]

        all_objects = pd.merge(user_product_permissions, ist_yield, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())[['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']]
                all_objects = pd.merge(filtered_data_df, all_objects, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
            else: 
                all_objects = pd.DataFrame()

        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)

    if master_id in ['21']: # Location Master
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]

        all_objects = pd.merge(user_location_permissions, location_master, on=['wh_type','wh_region','wh_location_group'], how = 'inner') 

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())
                all_objects = pd.merge(filtered_data_df, all_objects, on=['wh_code','wh_type','wh_region','wh_location_group'], how = 'inner')
            else:
                all_objects = pd.DataFrame()

    
        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)
    
    if master_id in ['26']: # seasonality Master
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        seasonality_master = pd.DataFrame(SeasonatilyMaster.objects.all().values())
        seasonality_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        all_objects = pd.merge(user_product_permissions, seasonality_master, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        all_objects = all_objects[all_objects['wh_code'].isin(authorized_wh_codes)]

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values()) 
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how='inner')
            else:
                all_objects = pd.DataFrame()
            
        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)
    
    if master_id in ['20']: # location capacity Master
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        location_capacity_master = pd.DataFrame(LocationCapacityMasterModel.objects.all().values())
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        all_objects = pd.merge(user_product_permissions, location_capacity_master, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        all_objects = all_objects[all_objects['wh_code'].isin(authorized_wh_codes)]

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query) 
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how='inner')
            else:
                all_objects = pd.DataFrame()

        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)
    
    if master_id in ['24']: # pivotal Master
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        pivotal_master = pd.DataFrame(PivotalSizeMasterModels.objects.all().values())
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        all_objects = pd.merge(user_product_permissions, pivotal_master, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        all_objects = all_objects[all_objects['wh_code'].isin(authorized_wh_codes)]

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query) 
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how='inner')
            else:
                all_objects = pd.DataFrame()
            
        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)
    
    if master_id in ['27']: # SKU Master
        sku_master = pd.DataFrame(SKUMasterModels.objects.all().values())
        sku_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        all_objects = pd.merge(user_product_permissions, sku_master, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())
                filtered_data_df.drop(columns = ['is_deleted', 'created_at','updated_at'], inplace=True)
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['sku_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how='inner')
            else:
                all_objects = pd.DataFrame()

        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)

    if master_id in ['17']: # discount period master
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        all_objects = pd.DataFrame(model.objects.all().values())

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['launch_period', 'terminal_date_for_full_price_sales'], how='inner')
            else:
                all_objects = pd.DataFrame()

        rec_count = str(len(all_objects))
        get_master_count_response_object = GetMasterDataResponses()
        return get_master_count_response_object.generate_rec_count_response(rec_count)





def get_master_data_records(master_id, ui_config,user_product_permissions,user_location_permissions, page_number, page_size, filters = None):
    if master_id in ['15']:  # contact
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            all_objects = model.objects.filter( Q(wh_code__in = authorized_wh_codes) & filter_query)
        else:
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes ))


        all_objects = pd.DataFrame(all_objects.values())
        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)
    
    if master_id in ['23']:  # location priority master
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        authorized_ph1 = list(user_product_permissions['product_hierarchy_1'].unique())

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes ) & Q(product_hierarchy_1__in = authorized_ph1) & filter_query)
        else:
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes ) & Q(product_hierarchy_1__in = authorized_ph1))


        all_objects = pd.DataFrame(all_objects.values())
        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)
    
    if master_id in ['16']:  # Deployment
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        sku_master = pd.DataFrame(SKUMasterModels.objects.all().values())
        sku_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        authorized_sku_codes = list(pd.merge(user_product_permissions, sku_master[['sku_code','product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']], on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'left')['sku_code'])

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes) & Q(sku_code__in = authorized_sku_codes) & filter_query)
        else:
            all_objects = model.objects.filter(Q(wh_code__in = authorized_wh_codes) & Q(sku_code__in = authorized_sku_codes))


        all_objects = pd.DataFrame(all_objects.values())
        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)
    
    if master_id in ['18']:  # ISTYield
        user_product_permissions.drop(columns = ['id'], inplace = True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        ist_yield = pd.DataFrame(ISTYieldMasterModel.objects.all().values())
        all_objects = pd.merge(user_product_permissions, ist_yield,
                               on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())[['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']] 
                all_objects = pd.merge(filtered_data_df, all_objects, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
            else:
                all_objects = pd.DataFrame()

        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)
    
    
    if master_id in ['21']:  # location master
        user_location_permissions.drop(columns = ['id'], inplace = True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        all_objects = pd.merge(user_location_permissions, location_master, on=['wh_type','wh_region','wh_location_group'], how = 'inner')


        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())[['wh_code','wh_type','wh_region','wh_location_group']] 
                all_objects = pd.merge(filtered_data_df, all_objects, on=['wh_code','wh_type','wh_region','wh_location_group'], how = 'inner')
            else:
                all_objects = pd.DataFrame()


        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)
    
    if master_id in ['26']:  # seasonaity master
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        sku_master = pd.DataFrame(SKUMasterModels.objects.all().values())
        sku_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        seasonality_master = pd.DataFrame(SeasonatilyMaster.objects.all().values())
        seasonality_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        all_objects = pd.merge(user_product_permissions, seasonality_master, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        all_objects = all_objects[all_objects['wh_code'].isin(authorized_wh_codes)]

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())[['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']] 
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how='inner')
            else:
                all_objects = pd.DataFrame()
            

        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)

    if master_id in ['20']:  # location capacity master
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        sku_master = pd.DataFrame(SKUMasterModels.objects.all().values())
        sku_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        location_capacity_master = pd.DataFrame(LocationCapacityMasterModel.objects.all().values())
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        all_objects = pd.merge(user_product_permissions, location_capacity_master, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        all_objects = all_objects[all_objects['wh_code'].isin(authorized_wh_codes)]

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())[['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']] 
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how='inner')
            else:
                all_objects = pd.DataFrame()

        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)
    
    if master_id in ['24']:  # pivotal master
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        sku_master = pd.DataFrame(SKUMasterModels.objects.all().values())
        sku_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        user_location_permissions.drop(columns = ['id'], inplace=True)
        user_product_permissions.drop(columns = ['id'], inplace=True)
        location_master = pd.DataFrame(LocationMasterModels.objects.all().values())
        location_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        pivotal_master = pd.DataFrame(model.objects.all().values())
        pivotal_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        authorized_wh_codes = list(pd.merge(user_location_permissions, location_master[['wh_code','wh_type','wh_region','wh_location_group']], on=['wh_type','wh_region','wh_location_group'], how = 'left')['wh_code'])
        
        all_objects = pd.merge(user_product_permissions, pivotal_master, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')
        all_objects = all_objects[all_objects['wh_code'].isin(authorized_wh_codes)]

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)    
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())[['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']] 
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['wh_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how='inner')
            else:
                all_objects = pd.DataFrame()

        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)
    
    if master_id in ['27']:  # sku master
        user_product_permissions.drop(columns = ['id'], inplace = True)
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        sku_master = pd.DataFrame(model.objects.all().values())
        sku_master.drop(columns = ['is_deleted','created_at','updated_at'], inplace=True)
        all_objects = pd.merge(user_product_permissions, sku_master, on=['product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how = 'inner')

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())[['sku_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3']]
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['sku_code', 'product_hierarchy_1','product_hierarchy_2','product_hierarchy_3'], how='inner')
            else:
                all_objects = pd.DataFrame()

        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)

    if master_id in ['17']: # discount period master
        model = MASTER_ID_TO_FINAL_MODEL_MAPPING[master_id]
        
        all_objects = list(model.objects.all().values())
        all_objects = pd.DataFrame(all_objects)

        if filters is not None:
            filter_query = create_dynamic_filter_query(filters)
            filtered_data = model.objects.filter(filter_query)
            if len(filtered_data) != 0:
                filtered_data_df = pd.DataFrame(filtered_data.values())[['launch_period', 'terminal_date_for_full_price_sales']]
                all_objects = pd.merge ( filtered_data_df, all_objects, on=['launch_period', 'terminal_date_for_full_price_sales'], how='inner')
            else:
                all_objects = pd.DataFrame()

        all_objects = replace_headers_with_keys(all_objects, ui_config, master_id)
        for obj in all_objects:
            obj['TMDTFPS'] = obj['TMDTFPS'].strftime('%Y-%m-%d %H:%M:%S') 
        paginator = Paginator(all_objects,page_size)
        try:
            data = paginator.page(page_number)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)
        get_master_response_object = GetMasterDataResponses()
        return get_master_response_object.generate_rec_response(data.object_list)   