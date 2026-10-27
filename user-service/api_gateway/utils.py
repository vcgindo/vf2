from api.models import *
from api.serializer.profile import *
import pandas as pd
from .site_keys import get_site_key
from ipaddress import ip_address
import logging

logger = logging.getLogger(__name__)

def getAllUserDetails(request, application_id, *, typed_empty_permissions=False):
    from common.api_gateway_utils import ALL_PERMISSIONS
    data = []
    all_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
    def permission_frame(rows, fields):
        # MTA's typed empty permission relations retain their queried schema.
        # Other callers keep the existing behavior and eligibility algorithm.
        return pd.DataFrame(rows, columns=fields) if typed_empty_permissions else pd.DataFrame(rows)
    # Get current user's product permissions
    current_user_permissions_product_df = permission_frame(
        User_Application_Product_Permission.objects.filter(user_id=request.user.id).values('application_id', 'productfilter_id'),
        ['application_id', 'productfilter_id']
    )
    # Get all users' product permissions
    all_user_permissions_product_df = permission_frame(
        User_Application_Product_Permission.objects.all().values('user_id', 'application_id', 'productfilter_id'),
        ['user_id', 'application_id', 'productfilter_id']
    )
    # Get unique user ids
    all_user_ids = all_user_permissions_product_df['user_id'].unique()

    # Gather users with any overlapping product permissions
    user_ids_product = []
    for id in all_user_ids:
        if all_user_permissions_product_df.empty:
            continue
        user_perm = all_user_permissions_product_df.loc[all_user_permissions_product_df['user_id'] == id]
        if current_user_permissions_product_df.empty:
            current_user_permissions_product_df = pd.DataFrame(columns=all_user_permissions_product_df.columns)
        # Merge the dataframes to find common permissions
        merged_df = pd.merge(current_user_permissions_product_df, user_perm, on=['application_id', 'productfilter_id'], how='inner')
        # Check if there are common permissions
        if not merged_df.empty:
            user_ids_product.append(id)

    # Repeat the process for location permissions
    current_user_permissions_location_df = permission_frame(
        User_Application_Location_Permission.objects.filter(user_id=request.user.id).values('application_id', 'locationfilter_id'),
        ['application_id', 'locationfilter_id']
    )
    all_user_permissions_location_df = permission_frame(
        User_Application_Location_Permission.objects.all().values('user_id', 'application_id', 'locationfilter_id'),
        ['user_id', 'application_id', 'locationfilter_id']
    ) 
    all_user_ids = all_user_permissions_location_df['user_id'].unique()

    user_ids_location = []
    for id in all_user_ids:
        if all_user_permissions_location_df.empty:
            continue
        user_perm = all_user_permissions_location_df.loc[all_user_permissions_location_df['user_id'] == id]
        if current_user_permissions_location_df.empty:
            current_user_permissions_location_df = pd.DataFrame(columns=all_user_permissions_location_df.columns)
        merged_df = pd.merge(current_user_permissions_location_df, user_perm, on=['application_id', 'locationfilter_id'], how='inner')
        if not merged_df.empty:
            user_ids_location.append(id)


    # Find Users with any common products or locations 
    matching_user_ids = list(set(user_ids_product).union(set(user_ids_location)))
    approver = "approver"
    approvers = Roles.objects.filter(name__icontains = approver).values('id','application_id','user_id')
    application_approver = approvers.filter(application_id = application_id)
    user_list = [data['user_id'] for data in application_approver]
    # Filter active users who have common permissions with current user
    users = User.objects.filter(
        pk__in=[user_id for user_id in matching_user_ids],
        is_active=True
    ).exclude(
        pk=request.user.id
    ).distinct().order_by('name')
    users = users.filter(pk__in=user_list)
    for user in users:
        serializer = UserProfileSerializer(user)
        result = {
            "id": serializer.data['id'],
            "email": serializer.data['email'],
            "name": serializer.data['name'],
            "product_id": [],
            "location_id": []
        }
        
        # Gather product permissions for the user
        for application in ALL_PERMISSIONS.generateProductAndLocationPermissions(user.id, all_permissions, 'product'):
            if application['application_id'] == application_id:
                result['product_id'] = [item['id'] for item in application['permissions']]
        for application in ALL_PERMISSIONS.generateProductAndLocationPermissions(user.id, all_permissions, 'location'):
            if application['application_id'] == application_id:
                result['location_id'] = [item['id'] for item in application['permissions']]
        data.append(result)

    return data




def getApproverList(request,application_id):
    try:
        data = []
        approver = "approver"
        approvers = Roles.objects.filter(name__icontains = approver).values('id','application_id','user_id')
        application_approver = approvers.filter(application_id = application_id)
        user_list = [data['user_id'] for data in application_approver]
        users  = User.objects.filter(pk__in = [user_id for user_id in user_list], is_active = True)
        for user in users:
            serializer = UserProfileSerializer(user)
            result = {
                "id":serializer.data['id'],
                "email":serializer.data['email'],
                "name":serializer.data['name']
            }
            data.append(result)
        return data
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return None


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    remote_addr = request.META.get('REMOTE_ADDR')
    if x_forwarded_for:
        raw_ip = x_forwarded_for.split(',')[0].strip()
    else:
        raw_ip = remote_addr

    if not raw_ip:
        return None

    # Handle IPv4:PORT
    if raw_ip.count('.') == 3 and ':' in raw_ip:
        raw_ip = raw_ip.split(':')[0]

    # Validate & normalize IPv4 / IPv6
    try:
        return str(ip_address(raw_ip))
    except ValueError:
        return None
