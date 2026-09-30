
from rest_framework import serializers
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from api.models import User, ForgotPasswordToken
from api.error_code import NotExistCode, NotPermissionCode, AuthCode
from api.utils import Util
from common.errors import ResponseError403Exception, ResponseError400Exception
from django.core import exceptions
import re
from api.models import *
from api.common.api_varibale import APIVariable
from common.send_mail import mail_forgot_password
from django.contrib.auth.password_validation import validate_password
from common.api_gateway_utils import ALL_PERMISSIONS
import pandas as pd
from common.response_code import construct_response_code
import copy
from django.db import transaction
from common.exceptions import ValidationError
from common.http_status_code import HttpStatusCode
import numpy as np
from common.user_role import UserRole
import logging

logger = logging.getLogger(__name__)

class ProductPermissionSerializer(serializers.Serializer):
    product_hierarchy_1 = serializers.CharField()
    product_hierarchy_2 = serializers.CharField(allow_blank=True,required=False)
    product_hierarchy_3 = serializers.CharField(allow_blank=True,required=False)
class ProductSerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    permissions = serializers.ListField(child=ProductPermissionSerializer())

class LocationPermissionSerializer(serializers.Serializer):
    location_heirarchy_1 = serializers.CharField()
    location_heirarchy_2 = serializers.CharField(allow_blank=True,required=False)
    location_heirarchy_3 = serializers.CharField(allow_blank=True,required=False)

class ApplicationSerializer(serializers.Serializer):
    application_id =  serializers.CharField(required=True)
    application_name = serializers.CharField(required=True)

class LocationsSerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    permissions = serializers.ListField(child=LocationPermissionSerializer())

class DataSerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    permissions = serializers.ListField(child=serializers.DictField())

class UserRegistrationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=15)
    password = serializers.CharField(max_length=15, required=False, min_length=8)
    roles = serializers.ListField(child=serializers.IntegerField())
    product_permissions = ProductSerializer(many=True, required=False)
    location_permissions = LocationsSerializer(many=True, required=False)
    data_permissions = DataSerializer(many=True, required = False)

    class Meta:
        model = User
        fields = [
            "email",
            "name",
            "password",
            "tc",
            "roles",
            "product_permissions",
            "location_permissions",
            "data_permissions"
        ]
        extra_kwargs = {"password": {"write_only": True}}

    def _valid(self, all_permissions,current_permissions,permission_type):
        invalid_permissions = []
        error = ""
     
        #Below Code checks if the Permissions Exists in All Permissions Application Wise

        for application in current_permissions:
            requester_obj = []
            if all_permissions:
                requester_obj = [x for x in all_permissions if hasattr(x,"application_id") and x["application_id"] == application['application_id']]
            
            if requester_obj:
                requester_obj = requester_obj[0]
            
            if requester_obj:
                if self.context.is_admin:
                    all_permissions_df = pd.DataFrame(requester_obj['permission'])
                else:
                    all_permissions_df = pd.DataFrame(requester_obj['permissions'])
                
                requested_permissions_df = pd.DataFrame(application['permissions'])
        
                if permission_type=='Product':
                    if requested_permissions_df.empty:
                        requested_permissions_df = pd.DataFrame(columns=all_permissions_df.columns)
                    merged_df = pd.merge(requested_permissions_df,all_permissions_df,on=requested_permissions_df.columns.to_list(),how='left',indicator=True)
                    merged_df = merged_df[merged_df['_merge'] == 'left_only']  
                    df_with_nan = merged_df[merged_df.isnull().any(axis=1)].drop(['id', '_merge'], axis=1)
                    merged_df_cleaned = merged_df.dropna()
     

                    for idx, row in df_with_nan.iterrows():
                        columns_without_nan = row[~row.isna()].index.tolist()
                        remaining_df = pd.merge(pd.DataFrame(row).T,all_permissions_df,on=columns_without_nan,how='left',indicator=True)
                        remaining_df = remaining_df[remaining_df['_merge'] == 'left_only']
                        pd.concat([merged_df_cleaned,remaining_df],axis=0)             

                if permission_type=="Location":
                    if requested_permissions_df.empty:
                        requested_permissions_df = pd.DataFrame(columns=all_permissions_df.columns)
                    merged_df = pd.merge(requested_permissions_df,all_permissions_df,on=requested_permissions_df.columns.to_list(),how='left',indicator=True)
                    merged_df = merged_df[merged_df['_merge'] == 'left_only']
                    df_with_nan = merged_df[merged_df.isnull().any(axis=1)].drop(['id', '_merge'], axis=1)  
                    merged_df_cleaned = merged_df.dropna()

                    for idx, row in df_with_nan.iterrows():
                        columns_without_nan = row[~row.isna()].index.tolist()
                        remaining_df = pd.merge(pd.DataFrame(row).T,all_permissions_df,on=columns_without_nan,how='left',indicator=True)
                        remaining_df = remaining_df[remaining_df['_merge'] == 'left_only']
                        pd.concat([merged_df_cleaned,remaining_df],axis=0)
                
                if len(merged_df_cleaned) > 0:
                    merged_df_cleaned.drop(['id', '_merge'],inplace=True,axis=1)
                    merged_df_cleaned.fillna('',inplace=True)
                    merged_df_cleaned = merged_df.to_dict(orient='records')
                    invalid_permissions.append({'application_id':application['application_id'],'permissions':merged_df_cleaned})
 

        error += f"{permission_type} permissions "
        for app in invalid_permissions:
            for perm in app['permissions']:
                for index,key in enumerate(perm):
                    if perm[key]!='':
                        if index != 0:
                            error += ' > '
                        error += f"{perm[key]}"
                error+=', '

        if len(invalid_permissions) > 0:
            raise ResponseError400Exception(
                    construct_response_code("3", 403, 24, f"You are not authorized to assign following {error}")
                ) 

        return current_permissions

    def validate(self, attrs):
        password = attrs.get("password")
        if password:
            user = User(
                email=attrs.get("email"),
                password=password,
                name=attrs.get("name"),
                tc=attrs.get("tc"),
            )
            try:
                validate_password(password=password, user=user)
            except exceptions.ValidationError as e:
                serializer_errors = serializers.as_serializer_error(e)
                raise exceptions.ValidationError(
                    {"password": serializer_errors["non_field_errors"]}
                )
        else:
            attrs["password"] = User.all_objects.make_random_password(
                allowed_chars = APIVariable.allowed_chars
            )
        
        # product_permissions = attrs.get('product_permissions')
        # if product_permissions:
        #     self.list_product = self._valid(
        #         self.context.product_id.all(),
        #         ProductFilter.objects,
        #         product_permissions
        #     )
        # else:
        #     if self.context.is_admin:
        #         self.list_product = list(ProductFilter.objects.values_list('id', flat=True))
        #     else:
        #         self.list_product = list(self.context.product_id.all().values_list('id', flat=True))
        # if product_permissions != None:
        #     del attrs['product_permissions']
        # location_permissions = attrs.get('location_permissions')
        # if location_permissions:
        #     self.list_location = self._valid(
        #         self.context.location_id.all(),
        #         LocationsFilter.objects,
        #         location_permissions
        #     )
        # else:
        #     if self.context.is_admin:
        #         self.list_location = list(LocationsFilter.objects.values_list('id', flat=True))
        #     else:
        #         self.list_location = list(self.context.location_id.all().values_list('id', flat=True))
        # if location_permissions != None:
        #     del attrs['location_permissions']
        return attrs

    def validate_roles(self, attrs):
        for id in attrs:
            try:
                Roles.objects.get(id=id)
            except Exception as e:
                raise ResponseError400Exception(NotExistCode.ROLE_NOT_EXIST)
        return attrs

    def validate_name(self, attrs):
        pattern = APIVariable.allowed_username_chars
        if not re.match(pattern, attrs):
            raise ResponseError400Exception(AuthCode.USERNAME_NOT_VALID)
        user = User.all_objects.filter(name__iexact=attrs).first()
        if user:
            raise ResponseError400Exception(AuthCode.USERNAME_IS_EXIST)
        return attrs

       
    def create(self, validated_data):
        roles = (
            validated_data.pop('roles')
            if validated_data.get('roles') is not None
            else []
        )
        
        role_objs = Roles.objects.filter(id__in=roles).values('code')
        admin_roles = {UserRole.ADMIN, UserRole.MTOADMIN, UserRole.SUPERADMIN}  
        is_admin = any(role.get('code') in admin_roles for role in role_objs)
               
        user_app_prod_permission = []
        user_app_loc_permission = []

        try:
            user = User.all_objects.create_user(
                email=validated_data['email'],
                name=validated_data['name'],
                tc=validated_data['tc'],
                password=validated_data['password'],
                is_admin = is_admin
            )
            all_permission = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
            all_product_permissions = []
            for permission in all_permission:
                product_permission = copy.deepcopy(permission)
                product_permission['permission'] = product_permission.get('product_permission',[])
                del product_permission['product_permission']
                del product_permission['location_permission']
                all_product_permissions.append(product_permission)   

            # Add User and Product Permission Mapping to DB 
            for application in validated_data['product_permissions']:
                application_all_permissions = []
                if all_product_permissions:
                    application_all_permissions = [x for x in all_product_permissions if ('application_id' in x) and x['application_id'] == application['application_id']]
                if application_all_permissions:
                    application_all_permissions = application_all_permissions[0]
                else:
                    continue
                all_permissions_df = pd.DataFrame(application_all_permissions['permission'])
                if all_permissions_df.empty:
                    continue
                product_permission_df = pd.DataFrame(application['permissions'])
                if product_permission_df.empty:
                    product_permission_df = pd.DataFrame(columns=all_permissions_df.columns)
                merged_df = pd.merge(product_permission_df, all_permissions_df, on=product_permission_df.columns.to_list(), how='left', indicator=True)

                permission_ids = merged_df[merged_df['_merge'] == 'both']['id'].tolist()

                df_with_nan = merged_df[merged_df.isnull().any(axis=1)].drop(['id', '_merge'], axis=1)

                for idx, row in df_with_nan.iterrows():
                    columns_with_nan = row[~row.isna()].index.tolist()
                    merged_df = pd.merge(pd.DataFrame(row).T, all_permissions_df, on=columns_with_nan, how='left', indicator=True)
                    permission_ids += merged_df[merged_df['_merge'] == 'both']['id'].tolist()

                permission_ids = list(set([int(id) for id in permission_ids]))
                last_record  = User_Application_Product_Permission.objects.order_by('-id').first()
                if last_record:
                    last_id = last_record.id + 1 + len(user_app_prod_permission)
                else:
                    last_id = len(user_app_prod_permission) + 1
                for index , permission in enumerate(permission_ids):
                    user_app_prod_permission.append(User_Application_Product_Permission(user_id=user.id,application_id=application['application_id'],productfilter_id=permission))


            all_location_permissions = []
            for permission in all_permission:
                location_permission = copy.deepcopy(permission)
                location_permission['permission'] = location_permission.get('location_permission',[])
                del location_permission['product_permission']
                del location_permission['location_permission']
                all_location_permissions.append(location_permission)

            # Add User and Location Permission Mapping to DB 
            for application in validated_data['location_permissions']:
                application_all_permissions = []
                if all_location_permissions:
                    application_all_permissions = [x for x in all_location_permissions if ('application_id' in x) and x['application_id'] == application['application_id']]
                if application_all_permissions:
                    application_all_permissions = application_all_permissions[0]
                else:
                    continue
                all_permissions_df = pd.DataFrame(application_all_permissions['permission'])
                if all_permissions_df.empty:
                    continue
                location_permission_df = pd.DataFrame(application['permissions'])
                if location_permission_df.empty:
                    location_permission_df = pd.DataFrame(columns=all_permissions_df.columns)
                merged_df = pd.merge(location_permission_df, all_permissions_df, on=location_permission_df.columns.to_list(), how='left', indicator=True)

                permission_ids = merged_df[merged_df['_merge'] == 'both']['id'].tolist()

                df_with_nan = merged_df[merged_df.isnull().any(axis=1)].drop(['id', '_merge'], axis=1)

                for idx, row in df_with_nan.iterrows():
                    columns_with_nan = row[~row.isna()].index.tolist()
                    merged_df = pd.merge(pd.DataFrame(row).T, all_permissions_df, on=columns_with_nan, how='left', indicator=True)
                    permission_ids += merged_df[merged_df['_merge'] == 'both']['id'].tolist()

                permission_ids = list(set([int(id) for id in permission_ids]))
                last_record  = User_Application_Location_Permission.objects.order_by('-id').first()
                if last_record:
                    last_id = last_record.id + 1 + len(user_app_loc_permission)
                else:
                    last_id = len(user_app_loc_permission) + 1
                for index , permission in enumerate(permission_ids):
                    user_app_loc_permission.append(User_Application_Location_Permission(user_id=user.id,application_id=application['application_id'],locationfilter_id=permission))
            with transaction.atomic():
                if(len(user_app_prod_permission) > 0):
                    User_Application_Product_Permission.objects.bulk_create(user_app_prod_permission)
                
                if(len(user_app_loc_permission) > 0):
                    User_Application_Location_Permission.objects.bulk_create(user_app_loc_permission)
            
            user.role_id.add(*roles)

            return user

        except Exception as e:
            if user:  # Ensure user is deleted in case of exception
                user.delete()
            raise e  # Reraise the exception so it can be caught by the calling code

class EditUserSerializer(UserRegistrationSerializer):
    id = serializers.IntegerField()
    email = serializers.EmailField(max_length=255, required=False)
    name = serializers.CharField(max_length=15, required=False)
    tc = serializers.BooleanField(required=False)
    roles = serializers.ListField(child=serializers.IntegerField(), required=False)
    product_permissions = ProductSerializer(many=True, required=False)
    location_permissions = LocationsSerializer(many=True, required=False)
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'name', 
            'password',
            'tc',
            'roles',
            'product_permissions',
            'location_permissions'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }
    def validate_id(self,attrs):
        if attrs == self.context.id:
            raise ResponseError400Exception(AuthCode.CAN_NOT_UPDATE)
        return attrs
    
    def validate_roles(self, attrs):
        if attrs:
            return super().validate_roles(attrs)
        return attrs
    
    def validate(self, attrs):
        password = attrs.get('password')
        email = attrs.get('email')
        if email:
            user = User.all_objects.filter(email=email) \
            .exclude(pk=self.instance.id) \
            .first()
            if user:
                raise ResponseError400Exception(
                    AuthCode.EMAIL_IS_EXISTS
                )
        if password: 
            user = self.instance
            if email:
                name = attrs.get('name') if attrs.get('name') else user.name
                tc = attrs.get('tc') if attrs.get('tc') else user.tc
                user = User(
                    email=email, 
                    password=password,
                    name=name,
                    tc=tc)
                                
            try:
                validate_password(password=password, user=user)
            except exceptions.ValidationError as e:
                serializer_errors = serializers.as_serializer_error(e)
                raise exceptions.ValidationError(
                    {'password': serializer_errors['non_field_errors']}
                )
        all_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
        product_permissions = []
        location_permissions = []
        for permission in all_permissions:
            product_permission = copy.deepcopy(permission)
            product_permission['permission'] = product_permission.get('product_permission',[])
            del product_permission['product_permission']
            del product_permission['location_permission']
            product_permissions.append(product_permission)

            location_permission = copy.deepcopy(permission)
            location_permission['permission'] = location_permission.get('location_permission',[])
            del location_permission['product_permission']
            del location_permission['location_permission']
            location_permissions.append(location_permission)

        if self.context.is_admin:
            all_product_permissions = product_permissions
            all_location_permissions = location_permissions
        else:
            all_product_permissions = ALL_PERMISSIONS.generateProductAndLocationPermissions(self.instance.id,all_permissions,'product')
            all_location_permissions =ALL_PERMISSIONS.generateProductAndLocationPermissions(self.instance.id,all_permissions,'location')
        # product_permissions = attrs.get('product_permissions')
        # if product_permissions:
        #     self.list_product = self._valid(
        #         all_product_permissions,
        #         product_permissions,
        #         permission_type='Product'
        #     )
        # else:
        #     self.list_product = []
        
        # location_permissions = attrs.get('location_permissions')
        # if location_permissions:
        #     self.list_location = self._valid(
        #         all_location_permissions,
        #         location_permissions,
        #         permission_type='Location'
        #     )
        # else:
        #     self.list_location = []
        return attrs
    
    def validate_name(self, attrs):
        pattern = APIVariable.allowed_username_chars
        if not re.match(pattern, attrs):
            raise ResponseError400Exception(AuthCode.USERNAME_NOT_VALID)
        user = (
                User.all_objects.filter(name__iexact=attrs)
                .exclude(pk=self.instance.id)
                .first()
            )
        if user:
            raise ResponseError400Exception(AuthCode.USERNAME_IS_EXIST)
        return attrs
    
    def update(self, instance, validated_data):
        try:
            if validated_data.get('password'):
                instance.set_password(validated_data.get('password'))
            if validated_data.get('email'):
                instance.email = validated_data.get('email')
            if validated_data.get('name'):
                instance.name = validated_data.get('name')
            if validated_data.get('tc'):
                instance.tc = validated_data.get('tc')
            roles = (
                validated_data.pop('roles')
                if validated_data.get('roles') != None 
                else []
            )
            if roles:
                instance.role_id.clear()
                instance.role_id.add(*roles)
        
            user_app_prod_permission = []
            user_app_loc_permission = []
            all_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
            all_product_permissions = []
            for permission in all_permissions:
                product_permission = copy.deepcopy(permission)
                product_permission['permission'] = product_permission.get('product_permission',[])
                del product_permission['product_permission']
                del product_permission['location_permission']
                all_product_permissions.append(product_permission)  
            
            all_location_permissions = []
            for permission in all_permissions:
                location_permission = copy.deepcopy(permission)
                location_permission['permission'] = location_permission.get('location_permission',[])
                del location_permission['product_permission']
                del location_permission['location_permission']
                all_location_permissions.append(location_permission)

            #Add User and Product Permission Mapping to DB 
            for application in validated_data['product_permissions']:
                #Find Current Application All Permissions
                application_all_permissions = []
                if all_product_permissions:
                    application_all_permissions = [x for x in all_product_permissions if ('application_id' in x) and x['application_id'] == application['application_id']]
                
                if application_all_permissions:
                    application_all_permissions = application_all_permissions[0]
                else:
                    continue
                all_permissions_df = pd.DataFrame(application_all_permissions['permission'])
                if all_permissions_df.empty:
                        continue
                product_permission_df = pd.DataFrame(application['permissions'])
                #Remove Duplicate Records
                product_permission_df = product_permission_df.drop_duplicates(subset=product_permission_df.columns.to_list())
                if(product_permission_df.empty):
                    product_permission_df = pd.DataFrame(columns=all_permissions_df.columns)
                product_permission_df = product_permission_df.applymap(lambda x: np.nan if x == "null" else x).astype("object")
                #Merge the Request Permissions and Store their ids
                merged_df = pd.merge(product_permission_df,all_permissions_df,on=product_permission_df.columns.to_list(),how='left',indicator=True)
                permission_ids = merged_df[merged_df['_merge'] == 'both']['id'].to_list()

                df_with_nan = merged_df[merged_df.isnull().any(axis=1)].drop(['id', '_merge'], axis=1)

                for idx, row in df_with_nan.iterrows():
                    columns_with_nan = row[~row.isna()].index.tolist()
                    merged_df = pd.merge(pd.DataFrame(row).T,all_permissions_df,on=columns_with_nan,how='left',indicator=True)
                    permission_ids += merged_df[merged_df['_merge'] == 'both']['id'].tolist()

                permission_ids = list(set([int(id) for id in permission_ids]))
                last_record  = User_Application_Product_Permission.objects.order_by('-id').first()
                if last_record:
                    last_id = last_record.id + 1 + len(user_app_prod_permission)
                else:
                    last_id  = 0 
                #Insert the user and permission id mappings          
                for index,permission in enumerate(permission_ids):
                    user_app_prod_permission.append(User_Application_Product_Permission(user_id=validated_data['id'],application_id=application['application_id'],productfilter_id=permission))

            #Add User and Location Permission Mapping to DB 
            for application in validated_data['location_permissions']:
                #Find Current Application All Permissions
                application_all_permissions = []
                if all_location_permissions:
                    application_all_permissions = [x for x in all_location_permissions if ('application_id' in x) and x['application_id'] == application['application_id']]
                
                if application_all_permissions:
                    application_all_permissions = application_all_permissions[0]
                else:
                    continue
                all_permissions_df = pd.DataFrame(application_all_permissions['permission'])
                location_permission_df = pd.DataFrame(application['permissions'])
                if all_permissions_df.empty:
                        continue
                if location_permission_df.empty:
                    location_permission_df = pd.DataFrame(columns=all_permissions_df.columns)
                location_permission_df = location_permission_df.applymap(lambda x: np.nan if x == "null" else x).astype("object")
                merged_df = pd.merge(location_permission_df,all_permissions_df,on=location_permission_df.columns.to_list(),how='left',indicator=True)
                permission_ids = merged_df[merged_df['_merge'] == 'both']['id'].to_list()

                df_with_nan = merged_df[merged_df.isnull().any(axis=1)].drop(['id', '_merge'], axis=1)

                for idx, row in df_with_nan.iterrows():
                    columns_with_nan = row[~row.isna()].index.tolist()
                    merged_df = pd.merge(pd.DataFrame(row).T,all_permissions_df,on=columns_with_nan,how='left',indicator=True)
                    permission_ids += merged_df[merged_df['_merge'] == 'both']['id'].tolist()
                    
                permission_ids = list(set([int(id) for id in permission_ids]))
                last_record  = User_Application_Location_Permission.objects.order_by('-id').first()
                if last_record:
                    last_id = last_record.id + 1 + len(user_app_loc_permission)
                else:
                    last_id = 0
                #Insert the user and permission id mappings          
                for index,permission in enumerate(permission_ids):
                    user_app_loc_permission.append(User_Application_Location_Permission(user_id=validated_data['id'],application_id=application['application_id'],locationfilter_id=permission))

            with transaction.atomic():
                if(len(user_app_prod_permission) > 0):
                    User_Application_Product_Permission.objects.filter(user_id=validated_data['id']).delete()
                    User_Application_Product_Permission.objects.bulk_create(user_app_prod_permission)
                
                if(len(user_app_loc_permission) > 0):
                    User_Application_Location_Permission.objects.filter(user_id=validated_data['id']).delete()
                    User_Application_Location_Permission.objects.bulk_create(user_app_loc_permission)

            instance.save()
            return instance
        except Exception as e:
            raise ValidationError(f'Exception has occurred in updating the user due to {e}',code=HttpStatusCode.INTERNAL_SERVER_ERROR)
    
class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=255)

    class Meta:
        model = User
        fields = ["email", "password","is_active"]


class UserChangePWSerializer(serializers.Serializer):
    password = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )
    password2 = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )

    def validate(self, attrs):
        password = attrs.get("password")
        password2 = attrs.get("password2")
        user = self.context.get("user")
        if password != password2:
            raise serializers.ValidationError("Passwords don't match")
        validate_password(attrs["password"])

        user.set_password(password)
        user.save()
        return attrs


class UserChangePWSerializerNew(serializers.Serializer):
    old_password = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )
    new_password = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )


class UserChangePWFirstSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    old_password = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )
    new_password = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )
    new_password2 = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )


class SendPWDResetEmailSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)

    def validate(self, attrs):
        email = attrs.get("email")
        if '@' in email:
            kwargs = {'email__iexact': email}
        else:
            kwargs = {'name__iexact': email}
        user = User.objects.filter(**kwargs).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)
            url =f'{os.environ.get("BASE_CLIENT_URL")}{os.environ.get("CHANGE_PASSWORD_URL")}' 
            link = f"{url}?token={token}&userId={uid}"
            forgot_password_token = ForgotPasswordToken.objects.filter(user=user, is_deleted=False)
            if forgot_password_token.count() > 0:
                forgot_password_token.update(is_deleted=True)
            ForgotPasswordToken.objects.create(user=user, token=token)
            # Send email
            data = mail_forgot_password(user.email, user.name, link)
            Util.send_html_email(data)

            return attrs
        else:
            raise serializers.ValidationError(NotExistCode.USER_NOT_EXIST)

class ForgotPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(max_length=15, min_length=8)
    confirm_password = serializers.CharField(max_length=15, min_length=8)

    def validate(self, attrs):
        uid = self.context.get('uid')
        token = self.context.get('token')
        try:
            decoded_uid = urlsafe_base64_decode(smart_str(uid))
            user_id = force_bytes(decoded_uid).decode()
        except Exception as e:
            logger.exception("Unexpected error occurred")
            raise ResponseError400Exception(NotExistCode.USER_NOT_EXIST)
        user = User.objects.filter(id=user_id).first()
        if not user:
            raise ResponseError400Exception(NotExistCode.USER_NOT_EXIST)
        
        forgot_password_token = ForgotPasswordToken.objects.filter(user=user, token=token).first()
        if not PasswordResetTokenGenerator().check_token(user, token) or not forgot_password_token or forgot_password_token.is_deleted:
            raise ResponseError400Exception(NotExistCode.TOKEN_NOT_EXIST)
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        if ' ' in new_password:
            raise ResponseError400Exception(AuthCode.PASSWORD_NOT_CONTAIN_WHITESPACE)
        if new_password != confirm_password:
            raise ResponseError400Exception(AuthCode.PW_DOES_NOT_MATCH)
        validate_password(new_password)

        forgot_password_token.is_deleted = True
        forgot_password_token.save()
        user.set_password(new_password)
        user.save()
        return attrs



class UserResetPWDSerializer(serializers.Serializer):
    password = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )
    password2 = serializers.CharField(
        style={"input_type": "password"}, write_only=True, max_length=255
    )

    def validate(self, attrs):
        try:
            password = attrs.get("password")
            password2 = attrs.get("password2")
            uid = self.context.get("uid")
            token = self.context.get("token")
            if password != password2:
                raise serializers.ValidationError("Passwords don't match")
            id = smart_str(urlsafe_base64_decode(uid))
            user = User.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise serializers.ValidationError("Token is not Valid or Expired")
            validate_password(attrs["password"])

            user.set_password(password)
            user.save()
            return attrs
        except DjangoUnicodeDecodeError as identifier:
            PasswordResetTokenGenerator().check_token(user, token)
            raise serializers.ValidationError("Token is not Valid or Expired")


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    default_error_message = {"bad_token": ("Token is expired or invalid")}

    def validate(self, attrs):
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()

        except TokenError as e:
            self.fail("bad_token")


class AddDomainSerializer(serializers.Serializer):
    domain = serializers.CharField(max_length=255 , required=True)
    id = serializers.IntegerField(required=False)
    sitename = serializers.CharField(max_length=255, required=False)
    class Meta:
        model = AllowedDomain
        fields = ["domain", "sitename", "id"]

    def create(self, validated_data):
        domain = validated_data["domain"]
        sitename = validated_data["sitename"]
        try:
            allowed_domain = AllowedDomain.objects.get(domain=domain)
            allowed_domain.is_active = True
            allowed_domain.save()
            return allowed_domain
        except AllowedDomain.DoesNotExist:
            return AllowedDomain.objects.create(domain = domain , sitename=sitename)


class UpdateDomainSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)
    domain = serializers.CharField(max_length=255 , required=False)
    sitename = serializers.CharField(max_length=255, required=False)
    class Meta:
        model = AllowedDomain
        fields = "__all__"

    def update(self, instance, validated_data):
        instance.domain = validated_data.get("domain", instance.domain)
        instance.sitename = validated_data.get("sitename", instance.sitename)
        instance.save()
        return instance

class BulkUserValidationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField(
        error_messages={
            "blank": "Username should not be empty or null.",
            "required": "Username is required."
        }
    )
    email = serializers.EmailField(
        error_messages={
            "blank": "Email should not be empty or null.",
            "required": "Email is required."
        }
    )
    pwd = serializers.CharField(
        error_messages={
            "blank": "Password should not be empty or null.",
            "required": "Password is required."
        }
    )

    def validate_username(self, value):
        value = value.strip()
        pattern = APIVariable.allowed_username_chars
        conditions = {
            "Username must contain only letters, numbers, and underscores.": not re.match(pattern, value),
            "Username must be at least 5 characters long.": len(value) < 5,
            "Username must be less than 15 characters.": len(value) >= 15,
            "Username already exists.": User.objects.filter(name=value).exists(),
        }
        errors = [msg for msg, condition in conditions.items() if condition]
        if errors:
            raise serializers.ValidationError(errors)
        
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        conditions = {
            "Email must be less than 200 characters.": len(value) >= 200,
            "Email already exists.": User.objects.filter(email=value).exists(),
        }
        errors = [msg for msg, condition in conditions.items() if condition]
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate_pwd(self, value):
        requested_data = self.initial_data 
        email = requested_data.get("email", "").strip().lower()
        email_username = email.split('@')[0] if '@' in email else email
        pwd = value.strip()

        conditions = {
            "Password must be at least 8 characters long.": len(pwd) < 8,
            "Password must be less than 15 characters.": len(pwd) >= 15,
            "Password must not contain spaces.": ' ' in pwd,
            "Password must contain at least one uppercase letter.": not any(c.isupper() for c in pwd),
            "Password must contain at least one lowercase letter.": not any(c.islower() for c in pwd),
            "Password must contain at least one number.": not any(c.isdigit() for c in pwd),
            "Password must contain at least one special character.": not any(c in APIVariable.special_characters for c in pwd),
            "Password is too similar to the email.": email_username and email_username in pwd.lower(),
        }
        errors = [msg for msg, condition in conditions.items() if condition]
        if errors:
            raise serializers.ValidationError(errors)
        return pwd
