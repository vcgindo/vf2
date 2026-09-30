from typing import List
from functools import wraps
from django.core.cache import cache
from django.db.models import Q
from django.db.models.functions import Upper
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from common.utils import get_user_permissions, is_subset, query_from_tuple
from common.user_role import UserRole
from common.api_gateway_utils import ALL_PERMISSIONS
import pandas as pd

class BaseUserPermission:
    @classmethod
    def check_user_permission(cls, user, *args, **kwargs):
        if not user.is_authenticated:
            raise PermissionDenied()
        if not user.is_active:
            raise PermissionDenied()
        if user.is_deleted:
            raise PermissionDenied()

    @classmethod
    def require_permission(cls, *args, **kwargs):
        def decorator(func):
            @wraps(func)
            def wrapper(*input_args, **input_kwargs):
                request: Request = input_args[1]
                user = request.user
                cls.check_user_permission(user, *args, **kwargs)
                return func(*input_args, **input_kwargs)
            return wrapper
        return decorator


class UserRolePermission(BaseUserPermission):
    @classmethod
    def check_user_permission(cls, user, roles):
        super().check_user_permission(user)
        user_permission = get_user_permissions(user)
        if not (set(user_permission['roles'])&set(roles)) and not user.is_admin:
            raise PermissionDenied()


class UserFunctionPermission(BaseUserPermission):
    @classmethod
    def check_user_permission(cls, user, functions):
        super().check_user_permission(user)
        if not user.has_functions_permission(functions):
            raise PermissionDenied()

class UserDataPermission: 
    @classmethod
    def query_filter_location(
        cls, 
        user, 
        filter_columns: List[str], 
    ):
        if user.is_admin:
            return Q()
        user_permission = get_user_permissions(user)
        filter_query = query_from_tuple(filter_columns, user_permission['location_permissions'])
        return filter_query

    @classmethod
    def query_filter_product(cls, user, filter_columns: List[str]):
        if user.is_admin:
            return Q()
        user_permission = get_user_permissions(user)
        filter_query = query_from_tuple(filter_columns, user_permission['product_permissions'])
        return filter_query

def require_roles_permission(*, roles: List[str]):
    return UserRolePermission.require_permission(roles)


def require_functions_permission(*, functions: List[str]):
    return UserFunctionPermission.require_permission(functions)

def can_update_user(admin, user,application_ids_product,application_ids_location):
    if admin.is_admin:
        return True
    admin_permission = get_user_permissions(admin)
    cache.delete(user.email)
    user_permission = get_user_permissions(user)

    if UserRole.ADMIN in user_permission['roles'] or user.is_admin and not user.is_deleted:
        return True
    all_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
    requester_product_permissions = ALL_PERMISSIONS.generateProductAndLocationPermissions(admin.id,all_permissions,permission_type="product")
    requester_location_permissions = ALL_PERMISSIONS.generateProductAndLocationPermissions(admin.id,all_permissions,permission_type="location")

    requested_product_permissions = ALL_PERMISSIONS.generateProductAndLocationPermissions(user.id,all_permissions,permission_type="product")
    requested_location_permissions = ALL_PERMISSIONS.generateProductAndLocationPermissions(user.id,all_permissions,permission_type="location")

    product_permission = {}
    location_permission = {}  
    #Plz feel free to optimize below code in future
    for application in requested_product_permissions:
        if application['application_id'] in application_ids_product:
            requester_obj = [x for x in requester_product_permissions if hasattr(x,"application_id") and x["application_id"] == application['application_id']]
            if requester_obj:
                requester_obj = requester_obj[0]
            else:
                continue
            requester_ids = [obj['id'] for obj in requester_obj['permissions']]
            requested_ids = [obj['id'] for obj in application['permissions']]
            if requester_obj:
                product_permission[application['application_id']] = not any(x not in requester_ids for x in requested_ids)
    
    for application in requested_location_permissions:
        if application['application_id'] in application_ids_location:
            requester_obj = [x for x in requester_location_permissions if hasattr(x,"application_id") and x["application_id"] == application['application_id']]
            if requester_obj:
                requester_obj = requester_obj[0]
            else:
                continue
            requester_ids = [obj['id'] for obj in requester_obj['permissions']]
            requested_ids = [obj['id'] for obj in application['permissions']]
            if requester_obj:
                location_permission[application['application_id']] = not any(x not in requester_ids for x in requested_ids)
                    
    #check if Falsy value exists in product_permission and location_permission
    if (not any(not value for value in product_permission.values())) and (not any(not value for value in location_permission.values())):
        return True
    return False

# class UserLocationCode:
#     @classmethod
#     def is_access_location_code(cls, location_code, user):
#         if user.is_admin:
#             return True
#         list_location_code = cls.get_list_location_code(user)
#         if location_code in list_location_code:
#             return True
#         return False

#     @classmethod
#     def get_list_location_code(cls, user):
#         if user.is_admin:
#            list_location_code = LocationMaster.objects.all().values_list(
#                'wh_code', 
#                flat=True
#             ).distinct()
#         else:
#             user_permission = get_user_permissions(user)
#             query_filter = query_from_tuple(['wh_region', 'wh_type', 'wh_state'], user_permission['location_permissions'])
#             product_hierarchy_1 = [t[0] for t in user_permission['product_permissions']]
#             query_filter &= Q(**{'wh_attr6__in' : product_hierarchy_1})

#             list_location_code = LocationMaster.objects.filter(
#                 query_filter
#             ).values_list('wh_code', flat=True).distinct()
#         return list_location_code
    