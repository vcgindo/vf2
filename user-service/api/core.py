import pandas as pd
import psycopg2
from typing import List
import os
from os.path import join, dirname
from dotenv import load_dotenv
from api.models import Permission as PermissionUser
from api.serializer.profile import *
from common.utils import get_user_permissions
from common.api_gateway_utils import ALL_PERMISSIONS
from api.common.api_varibale import APIVariable
from common.user_role import UserRole
import copy
from api_gateway.service_config.config import service_map
from api.mdm_navigation import with_mdm_menu_aliases
dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)


DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")


class ResponseUser:
    def __init__(
        self,
        token=None,
        user=None,
        location_permission=True,
        role_full=False,
        product_permission=True,
        data_permission=True,
        response_roles=True,
        response_user=True,
        language="vi",
        data=None,
        response_data=True,
        url_permission=False,
        feature_permission = False,
        *args,
        **kws
    ):
        self.result = dict()
        self.token = token
        self.user = user
        self.language = language
        self.data = data
        self.response_user = response_user
        self.response_data = response_data
        self.response_roles = response_roles
        self.product_permission = product_permission
        self.location_permission = location_permission
        self.data_permission = data_permission
        self.url_permission = url_permission
        self.feature_permission = feature_permission
        self.role_full = role_full
        self.config(**kws)

    def config(self, **kws):
        for config, value in kws.items():
            self.result[config] = value
    
    def get_landing_page(self,roles,urls):
        admin_roles =[role for role in roles if role['code'] == UserRole.ADMIN]
        distribution_admin_exists = any(admin['application_id']==1 for admin in admin_roles)
        vector_consultant_exists = len([role for role in roles if role['code'] == 'VectorConsultant'])>0
        master_updater_exists = len([role for role in roles if role['code'] == 'MasterUpdater'])>0
        dbm_manager_exists = len([role for role in roles if role['code'] == 'DBMManager'])>0
        bpr_manager_exists = len([role for role in roles if role['code'] == 'BPRManager'])>0
        master_approver_exists = len([role for role in roles if role['code'] == 'MasterApprover'])>0

        
        if distribution_admin_exists or vector_consultant_exists or dbm_manager_exists or bpr_manager_exists:
            return '/supply-chain-intelligence-hub/planning' 
        if master_updater_exists:
            return '/master-data-management/control-panel'
        if master_approver_exists:
            return '/master-data-management/task-pending'

        return '/supply-chain-intelligence-hub/planning'

    def response(self, msg,wrng=None):
        """ added optional parameter wrng when active directory cred will be expiring """
        # self.result["token"] = self.token
        if self.response_user:
            user_data = {
                "id": self.user["id"],
                "email": self.user["email"],
                "name": self.user["name"],
                "is_admin": self.user["is_admin"],
                "theme_ui": self.user["theme_ui"]
            }
            self.result["user"] = user_data
        if self.response_roles:
            roles = dict()
            list_roles = []
            for role_id in self.user["role_id"]:
                if self.role_full:
                    del_per = role_id
                else:
                    del_per = {
                        "id": role_id["id"],
                        "name": role_id["name"],
                        "code": role_id["code"],
                        "application_id":role_id["application_id"]
                    }
                list_roles.append(del_per)
            roles["permission"] = list_roles
            all_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
            product_permissions = []
            location_permissions = []
            for permission in all_permissions:
                # Create a deep copy of the permission object for product permissions
                product_permission = copy.deepcopy(permission)
                product_permission['permission'] = product_permission.get('product_permission', [])
                del product_permission['product_permission']
                del product_permission['location_permission']
                product_permissions.append(product_permission)

                # Create a deep copy of the permission object for location permissions
                location_permission = copy.deepcopy(permission)
                location_permission['permission'] = location_permission.get('location_permission', [])
                del location_permission['location_permission']
                del location_permission['product_permission']
                location_permissions.append(location_permission)

            if self.product_permission:
                product_permission = []
                if self.user['is_admin']:
                    product_permission = product_permissions
                else:
                    product_permission = ALL_PERMISSIONS.generateProductAndLocationPermissions(self.user["id"],all_permissions,'product')
                roles["product_permission"] = product_permission

            if self.location_permission:
                location_permission = []
                if self.user['is_admin']:
                    location_permission = location_permissions
                else:
                    location_permission = ALL_PERMISSIONS.generateProductAndLocationPermissions(self.user["id"],all_permissions,'location')
                roles["location_permission"] = location_permission

            self.result["roles"] = roles
        if self.response_data:
            self.result["data"] = self.data
        if self.url_permission:
            url_permission = []
            if self.user["is_admin"]:
                url_per = PermissionUser.objects.all()
                for url in url_per:
                    url_permission.append(url.url.strip())
            else:
                for role_id in self.user["role_id"]:
                    for permission_id in role_id["permission_id"]:
                        url_permission.append(permission_id["url"].strip())
            self.result["url_permission"] = with_mdm_menu_aliases(url_permission)
        if self.feature_permission:
            features_list = []
            all_features = FeatureMaster.objects.filter(is_active = True)
            if self.user["is_admin"]:
                for feature in all_features:
                    features_list.append(feature.feature)
            else:
                for feature in self.user["role_id"]:
                    for feature_id in feature["feature_id"]:
                        if feature_id["is_active"] == True:
                            features_list.append(feature_id["feature"]) 
            self.result["feature_permission"] = list(set(features_list))
        
        self.result["language"] = self.language
        self.result["msg"] = msg
        self.result['wrng']=wrng
        self.result['landing_page'] = self.get_landing_page(roles['permission'],list(set(url_permission)))

        return self.result

class ResponseProfile:
    def __init__(self, user):
        self.result = dict()
        self.user = UserProfileSerializer(user).data
        self.user_permission = get_user_permissions(user)
    
    def convert_data_permission(self, all_db, permission_user, columns: List[str]):
        temp = dict()
        for index, column in enumerate(columns):
            user = list(
                        set(
                            filter(
                                None,
                                [t[index] for t in permission_user]
                            )      
                        )
                    )
            db =  list(
                filter(
                    None,
                    all_db.values_list(f'{column}',flat=True).distinct()
                )
            )
            if len(user) == len(db):
                temp[f'{column}'] = ['All']
            else:
                temp[f'{column}'] = user
        return temp
    def get_roles(self):
        list_roles = []
        for role_id in self.user["role_id"]:
            list_roles.append(role_id["name"])
        return list_roles
    
    def get_distinct_heirarchies(self,permission,all_permissions,permission_type):
        all_permissions_df = pd.DataFrame(all_permissions)
        if all_permissions_df.empty:
            return {}
        if(permission_type == 'product'):
            all_permission_product = {
                'product_hierarchy_1':all_permissions_df['product_hierarchy_1'].unique() if not all_permissions_df['product_hierarchy_1'].empty else '',
                'product_hierarchy_2':all_permissions_df['product_hierarchy_2'].unique() if not all_permissions_df['product_hierarchy_2'].empty  else '',
                'product_hierarchy_3':all_permissions_df['product_hierarchy_3'].unique() if not all_permissions_df['product_hierarchy_3'].empty  else ''
            }
            permission_df = pd.DataFrame(permission)
            if permission_df.empty:
                permission_df = pd.DataFrame(columns=all_permissions_df.columns)
            return {
                'product_hierarchy_1':['All'] if len(all_permission_product['product_hierarchy_1'])==len(permission_df['product_hierarchy_1'].unique()) else permission_df['product_hierarchy_1'].unique(),
                'product_hierarchy_2':['All'] if len(all_permission_product['product_hierarchy_2'])==len(permission_df['product_hierarchy_2'].unique()) else permission_df['product_hierarchy_2'].unique(),
                'product_hierarchy_3':['All'] if len(all_permission_product['product_hierarchy_3'])==len(permission_df['product_hierarchy_3'].unique()) else permission_df['product_hierarchy_3'].unique()
            }
        if(permission_type == 'location'):
            all_permission_location = {
                'location_heirarchy_1':all_permissions_df['location_heirarchy_1'].unique() if not all_permissions_df['location_heirarchy_1'].empty  else '',
                'location_heirarchy_2':all_permissions_df['location_heirarchy_2'].unique() if not all_permissions_df['location_heirarchy_2'].empty  else '',
                'location_heirarchy_3':all_permissions_df['location_heirarchy_3'].unique() if not all_permissions_df['location_heirarchy_3'].empty  else ''
            }
            permission_df = pd.DataFrame(permission)
            if permission_df.empty:
                permission_df = pd.DataFrame(columns=all_permissions_df.columns)
            return {
                'location_heirarchy_1':['All'] if len(all_permission_location['location_heirarchy_1'])==len(permission_df['location_heirarchy_1'].unique()) else permission_df['location_heirarchy_1'].unique(),
                'location_heirarchy_2':['All'] if len(all_permission_location['location_heirarchy_2'])==len(permission_df['location_heirarchy_2'].unique()) else permission_df['location_heirarchy_2'].unique(),
                'location_heirarchy_3':['All'] if len(all_permission_location['location_heirarchy_3'])==len(permission_df['location_heirarchy_3'].unique()) else permission_df['location_heirarchy_3'].unique()
            }

        return {}

    def response(self):
        user_data = {
            "id": self.user["id"],
            "email": self.user["email"],
            "name": self.user["name"],
            "is_admin": self.user["is_admin"],
            'is_active' : self.user['is_active'],
            'is_deleted' : self.user['is_deleted'],
            "theme_ui" : self.user['theme_ui']
        }
        self.result["user"] = user_data

        userservice_config_data = UserserviceConfig.objects.values('flag','value')
        
        config_dict = {item["flag"]: item["value"] for item in userservice_config_data}
        config_dict["MTO_ACTIVE"] = service_map["mto"]["active"]
        config_dict["MTA_ACTIVE"] = service_map["mta"]["active"]

        self.result["config_data"] = config_dict
        
        all_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")

        product_permission = ALL_PERMISSIONS.generateProductAndLocationPermissions(self.user["id"],all_permissions,permission_type="product")

        product_permission_heirarchial = []
        for application in product_permission:
            application_obj = [x for x in all_permissions  if x['application_id']==application['application_id']]
            product_permission_heirarchial.append({
                'application_id':application['application_id'],
                'application_name':application['application_name'],
                **self.get_distinct_heirarchies(application['permissions'],application_obj[0]['product_permission'],permission_type="product")
            })

        location_permission = ALL_PERMISSIONS.generateProductAndLocationPermissions(self.user["id"],all_permissions,permission_type="location")
        location_permission_heirarchial = []
        for application in location_permission:
            application_obj = [x for x in all_permissions  if x['application_id']==application['application_id']]
            location_permission_heirarchial.append({
                'application_id':application['application_id'],
                'application_name':application['application_name'],
                **self.get_distinct_heirarchies(application['permissions'],application_obj[0]['location_permission'],permission_type="location")
            })
           
       
        roles = {
            'permission': self.get_roles(),
            'product_permission': product_permission_heirarchial,
            'location_permission': location_permission_heirarchial
        }
        self.result['roles'] = roles
        url_permission = []
        if self.user["is_admin"]:
            url_per = PermissionUser.objects.all()
            for url in url_per:
                url_permission.append(url.url.strip())
        else:
            for role_id in self.user["role_id"]:
                for permission_id in role_id["permission_id"]:
                    url_permission.append(permission_id["url"].strip())
        self.result["url_permission"] = with_mdm_menu_aliases(url_permission)

        features_list = []
        all_features = FeatureMaster.objects.filter(is_active = True)
        if self.user["is_admin"]:
            for feature in all_features:
                features_list.append(feature.feature)
        else:
            for feature in self.user["role_id"]:
                for feature_id in feature["feature_id"]:
                    if feature_id["is_active"] == True:
                        features_list.append(feature_id["feature"]) 
        self.result["feature_permission"] = list(set(features_list))

        return self.result

