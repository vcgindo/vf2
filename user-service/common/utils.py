from django.core.cache import cache
from django.db.models import Q
from typing import List
import os
from api.models import Roles


def compare_two_iterable(iter1, iter2):
    for item1 in iter1:
        for item2 in iter2:
            if item1 != item2:
                return False
    return True

def get_value_of_dict(dict_data, keys):
        result = {}
        for key in keys:
            result[key] = dict_data.get(key)
        return result



def get_user_permissions(user):
    user_permission = cache.get(user.email)
    if not user_permission:
        user_roles = list(Roles.objects.filter(user_id=user.id).values_list("code",flat=True))
        product_permissions = []
        location_permissions = []
        # if user.is_admin:
        #     product = {}
        #     location = {}
        # else:
        #     product = user.product_id.all()
        #     location = user.location_id.all()
        # if product.exists():
        #     product_permissions = list(
        #             product.values_list('product_hierarchy_1','product_hierarchy_2','product_hierarchy_3')
        #     )

        # if location.exists():
        #     location_permissions = list(
        #             location.values_list('wh_region','wh_type','wh_location_group')
        #     )
        # print(ALL_PERMISSIONS.get_combined_permissions())
        user_permission = {
            'roles': user_roles,
            'product_permissions': product_permissions,
            'location_permissions': location_permissions
        }
        # cache.set(user.email,user_permission,timeout=int(os.environ.get('TIME_CACHE')))
    return user_permission

def is_subset(iter1, iter2 = None):
    if not iter1:
        return False
    if not iter2:
        return True
    return set(iter2)&set(iter1)

def query_from_tuple(keys: List[str], tuples: List[tuple]):
    result = Q()
    for value in tuples:
        temp = Q()
        for index, key in enumerate(keys):
            temp &= Q(**{key : value[index]})
        result |= temp
    return result
    
def max_power_of_ten_divisor(n):
    if n == 0:
        return 0  # Edge case: if the number is 0, return 0
    power_of_ten = 1
    while power_of_ten * 10 <= n:
        power_of_ten *= 10
    return power_of_ten