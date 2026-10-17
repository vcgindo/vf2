# **DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
from api_gateway.service_config.config import service_map
import requests
from api.models import *
from api.serializer.profile import *
import pandas as pd
from asyncio.log import logger
from common.mta_catalogue import CatalogueUnavailable, enabled as local_mta_catalogue, payload as mta_catalogue_payload
from common.startup_probe import permission_request

def get_application_details_by_id(id):
    application = ApplicationMaster.objects.get(application_id=id)
    return application

def getAllUserDetails(request):
    data = []
    all_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
    # if request.user.is_admin:
    users = User.objects.all().exclude(
        pk=request.user.id
    ).order_by('name')

    # else:

    #     # user_permissions = get_user_permissions(request.user)
    #     current_user_permissions_product_df = pd.DataFrame(User_Application_Product_Permission.objects.filter(user_id=request.user.id).values('application_id','productfilter_id'))
    #     all_user_permissions_product_df = pd.DataFrame(User_Application_Product_Permission.objects.all().values('user_id','application_id','productfilter_id'))
    #     all_user_ids = all_user_permissions_product_df.get('user_id',None).unique()
    #     user_ids_product = []

    #     for id in all_user_ids:
    #         user_perm = all_user_permissions_product_df.loc[all_user_permissions_product_df['user_id'] == id]
    #         merged_df = pd.merge(current_user_permissions_product_df,user_perm,on=['application_id','productfilter_id'],how='right',indicator=True)
    #         merged_df = merged_df[merged_df['_merge'] == 'right_only']
    #         if len(merged_df) == 0:
    #             user_ids_product.append(id)

    #     current_user_permissions_location_df = pd.DataFrame(User_Application_Location_Permission.objects.filter(user_id=request.user.id).values('application_id','locationfilter_id'))
    #     all_user_permissions_location_df = pd.DataFrame(User_Application_Location_Permission.objects.all().values('user_id','application_id','locationfilter_id'))
    #     all_user_ids = all_user_permissions_location_df['user_id'].unique()
    #     user_ids_location = []

    #     for id in all_user_ids:
    #         user_perm = all_user_permissions_location_df.loc[all_user_permissions_location_df['user_id'] == id]
    #         merged_df = pd.merge(current_user_permissions_location_df,user_perm,on=['application_id','locationfilter_id'],how='right',indicator=True)
    #         merged_df = merged_df[merged_df['_merge'] == 'right_only']
    #         if len(merged_df) == 0:
    #             user_ids_location.append(id)
    

    #     #Find Users exisitng in both array
    #     matching_user_ids = list(set(user_ids_product).intersection(set(user_ids_location)))
        
    #     users = User.objects.filter(
    #         pk__in=[user_id for user_id in matching_user_ids]
    #     ).exclude(
    #         pk=request.user.id
    #     ).distinct().order_by('name')
    
    for user in users:
        serializer = UserDetailsSerializer(user)
        result = serializer.data
        # the product and location permission will now come on the click of the api
        # result['product_id'] = ALL_PERMISSIONS.generateProductAndLocationPermissions(user.id,all_permissions,'product')
        # result['location_id'] = ALL_PERMISSIONS.generateProductAndLocationPermissions(user.id,all_permissions,'location')
        data.append(result)
    return data
    
def get_user_product_and_location_permissions(user):
    try:
        all_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
        result = {
            'user_id': user.id,
        }
        result['product_id'] = ALL_PERMISSIONS.generateProductAndLocationPermissions(user.id,all_permissions,'product')
        result['location_id'] = ALL_PERMISSIONS.generateProductAndLocationPermissions(user.id,all_permissions,'location')
        return result
    except Exception as e:
        logger.exception("Error fetching user permissions")
        return {}

class PRODUCT_LOCATION_MAPPER:
    def flat_to_nested_product(data):
        transformed = {}

        for product in data:
            hierarchy_1 = product['product_hierarchy_1']
            hierarchy_2 = product['product_hierarchy_2']
            hierarchy_3 = product['product_hierarchy_3']

            if hierarchy_1 not in transformed:
                transformed[hierarchy_1] = {}

            if hierarchy_2 not in transformed[hierarchy_1]:
                transformed[hierarchy_1][hierarchy_2] = []

            transformed[hierarchy_1][hierarchy_2].append({
                "product_hierarchy_3": hierarchy_3
            })
        return transformed

    def flat_to_nested_location(data):
        transformed = {}

        for product in data:
            hierarchy_1 = product['location_heirarchy_1']
            hierarchy_2 = product['location_heirarchy_2']
            hierarchy_3 = product['location_heirarchy_3']

            if hierarchy_1 not in transformed:
                transformed[hierarchy_1] = {}

            if hierarchy_2 not in transformed[hierarchy_1]:
                transformed[hierarchy_1][hierarchy_2] = []

            transformed[hierarchy_1][hierarchy_2].append({
                "location_heirarchy_3": hierarchy_3
            })
        return transformed

class ALL_PERMISSIONS:
    def getHeadersData():
        headers = {
        }
        # Fetching mto headers
        if service_map['mto']['active']:
            try:
                url = service_map['mto']['base_url'].rstrip('/') + '/GetMTOHeaders/'
                response = requests.request(
                    method='GET',
                    url=url,
                ).json()
                application_details = get_application_details_by_id(service_map['mto']['application_id'])
                response_data = response.get('data')
                if response_data is not None:
                    headers[application_details.application_id] = response_data
            except Exception as e:
                logger.exception("Error fetching mto headers")

        if service_map['mta']['active']:
            try:
                response = None
                url = service_map['mta']['base_url'].rstrip('/') + '/api/mta/GetHeadersData'
                response_data = requests.request(
                    method='GET',
                    url=url,
                )
                if response_data:
                    response = response_data.json()
                application_details = get_application_details_by_id(service_map['mto']['application_id'])
                if response is not None:
                    headers[application_details.application_id] = response
            except Exception as e:
                logger.exception("Error fetching mta headers")

        return headers

    def generateProductAndLocationPermissions(id,all_permissions,permission_type):
        product_permissions = User_Application_Product_Permission.objects.filter(user_id=id)
        location_permissions = User_Application_Location_Permission.objects.filter(user_id=id)
        data_permissions = User_Application_Data_Permission.objects.filter(user_id=id)
        #Hashmap That Contains mapping of Application Ids to the Current Users Product and Location Permission Ids
        permission_hash = {}

        #Fill the Hashmap with the  Valid permissions
        for prod_permission in product_permissions:
            if prod_permission.application_id not in permission_hash:
                permission_hash[prod_permission.application_id] = {
                    'product':[prod_permission.productfilter_id],
                    'location':[],
                    'data' : []
                }
            else:
                permission_hash[prod_permission.application_id]['product'].append(prod_permission.productfilter_id)
        
        for loc_permission in location_permissions:
            if loc_permission.application_id not in permission_hash:
                permission_hash[loc_permission.application_id] = {
                    'product':[],
                    'location':[loc_permission.locationfilter_id],
                    'data':[]
                }
            else:
                permission_hash[loc_permission.application_id]['location'].append(loc_permission.locationfilter_id)
        for doc_permission in data_permissions:
            if doc_permission.application_id not in permission_hash:
                permission_hash[doc_permission.application_id] = {
                    'product':[],
                    'location':[],
                    'data':[doc_permission.datafilter_id]
                }
            else:
                permission_hash[doc_permission.application_id]['data'].append(doc_permission.datafilter_id)
        updated_permissions = []

        #Filter out the Valid Permissions from All Permissions
        for permission_obj in all_permissions:
            
            if permission_obj['application_id'] in permission_hash.keys():
                valid_product_permissions = permission_hash[permission_obj['application_id']]['product']
                valid_location_permissions = permission_hash[permission_obj['application_id']]['location']
                valid_data_permissions = permission_hash[permission_obj['application_id']]['data']
                application_object = {
                    'application_id':permission_obj['application_id'],
                    'application_name':permission_obj['application_name'],
                    'permissions':[]
                }
                if permission_type == 'product' and isinstance(permission_obj, dict) and 'product_permission' in permission_obj:
                    application_object['permissions'] = [
                        x for x in permission_obj['product_permission'] 
                        if isinstance(permission_obj['product_permission'], list) and x['id'] in valid_product_permissions
                    ]

                if permission_type == 'location' and isinstance(permission_obj, dict) and 'location_permission' in permission_obj:
                    application_object['permissions'] = [
                        x for x in permission_obj['location_permission'] 
                        if isinstance(permission_obj['location_permission'], list) and x['id'] in valid_location_permissions
                    ]

                if permission_type == 'data' and isinstance(permission_obj, dict) and 'data_permission' in permission_obj:
                    application_object['permissions'] = [
                        x for x in permission_obj['data_permission'] 
                        if isinstance(permission_obj['data_permission'], list) and x['id'] in valid_data_permissions
                    ]
            
                updated_permissions.append(application_object)
       
        return updated_permissions

    def get_combined_permissions(nested=False,permission_type="both",withIds=False):
        all_permissions = []
        try:
            if service_map['mto']['active']:
                url=service_map['mto']['base_url'].rstrip('/') + '/GetMTOPermissionDetails/'
                response = permission_request('permission_mto',
                    method='GET',
                    url=url,
                ).json()
                response = response.get('data')
                response['Orders']  = response.get('Orders')[0] if response.get('Orders') else []
                response['Location'] = response.get('Location')[0] if response.get('Location') else []
                application_details = get_application_details_by_id(service_map['mto']['application_id'])
                if permission_type=="both":
                    permission_obj = {
                        "application_id":application_details.application_id,
                        "application_name":application_details.application_name,
                        "product_permission":PRODUCT_LOCATION_MAPPER.flat_to_nested_product(response['Orders']) if nested else response['Orders'],
                        "location_permission":PRODUCT_LOCATION_MAPPER.flat_to_nested_location(response['Location']) if nested else response['Location'],
                    }
                    if withIds:
                        permission_obj["product_permission_ids"] = response['Orders']
                        permission_obj["location_permission_ids"] = response['Location']
                    all_permissions.append(permission_obj)
                if permission_type=="product":
                    all_permissions.append({
                        "application_id":application_details.application_id,
                        "application_name":application_details.application_name,
                        "permission":PRODUCT_LOCATION_MAPPER.flat_to_nested_product(response['Orders']) if nested else response['Orders'],
                    })
                if permission_type=="location":
                    all_permissions.append({
                        "application_id":application_details.application_id,
                        "application_name":application_details.application_name,
                        "permission":PRODUCT_LOCATION_MAPPER.flat_to_nested_location(response['Location']) if nested else response['Location']
                    })
        except Exception as e: 
            logger.exception("Error fetching mto permissions")
        try:
            if service_map['mta']['active']:
                if local_mta_catalogue():
                    response = mta_catalogue_payload()
                else:
                    url=service_map['mta']['base_url'].rstrip('/') + '/api/mta/GetAllPermmision'
                    from common.mta_catalogue import remote_payload
                    response = remote_payload(permission_request('permission_mta', method='GET', url=url))
                application_details = get_application_details_by_id(service_map['mta']['application_id'])
                if permission_type=="both":
                    permission_obj={
                        "application_id":application_details.application_id,
                        "application_name":application_details.application_name,
                        "product_permission":PRODUCT_LOCATION_MAPPER.flat_to_nested_product(response['product']) if nested else response['product'],
                        "location_permission":PRODUCT_LOCATION_MAPPER.flat_to_nested_location(response['location']) if nested else response['location']
                    }
                    if withIds:
                        permission_obj["product_permission_ids"] = response['product']
                        permission_obj["location_permission_ids"] = response['location']
                    all_permissions.append(permission_obj)
                if permission_type=="product":
                    all_permissions.append({
                        "application_id":application_details.application_id,
                        "application_name":application_details.application_name,
                        "permission":PRODUCT_LOCATION_MAPPER.flat_to_nested_product(response['product']) if nested else response['product'],
                    })
                if permission_type=="location":
                    all_permissions.append({
                        "application_id":application_details.application_id,
                        "application_name":application_details.application_name,
                        "permission":PRODUCT_LOCATION_MAPPER.flat_to_nested_location(response['location']) if nested else response['location']
                    })
        except CatalogueUnavailable:
            # Local-mode failures must not become a successful empty catalogue.
            raise
        except Exception as e:
            if local_mta_catalogue():
                raise CatalogueUnavailable('mta_catalogue_assembly_unavailable') from e
            logger.exception("Error fetching mta permissions")
        return all_permissions
