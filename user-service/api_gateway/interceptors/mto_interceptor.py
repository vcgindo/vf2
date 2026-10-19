import requests
from rest_framework.response import Response
from api_gateway.utils import getApproverList
from api.models import User_Application_Location_Permission,User_Application_Product_Permission, User
from common.data_scopes import effective_data_scopes


class MTO_INTERCEPTOR:
    def __init__(self):
        pass
    def forward(self,request,service_map):
        # Get token from cookies
        access_token = request.COOKIES.get("access_token")
        if not access_token:
            return Response({"error": "Access token is missing in cookies"}, status=401)
        path_url = request.path.split('/')[-2]
        url = service_map['mto']['base_url'].rstrip('/') + '/' + path_url + '/'
        application_id = service_map['mto']['application_id']
        # headers = {key: value for key, value in request.headers.items() if key != 'Host'}
        
        # Recovered gateway identity source: browser headers, even though the
        # outer gateway has already authenticated the cookie. LEG-015 records
        # the resulting impersonation risk; do not substitute request.user.
        user_id = int(request.headers.get('User-Id'))
        user_details  = User.objects.filter(id = user_id).values('is_admin')
        user_dict = {
            "id":request.headers.get('User-Id'),
            "name":request.headers.get('User-Name'),
            "is_admin":user_details[0]['is_admin']
        }
        
        files = request.FILES if request.FILES else None
        if not user_id:
            return Response({"error": "User-Id header is missing"}, status=400)
        content_type = 'multipart/form-data' if files else 'application/json'
        headers = {
            "Authorization": f"Bearer {access_token}",  
            'Content-Type': content_type,
        }
        # data = {k: v for k, v in request.data.items() if k != 'file'} #request.data
        data = request.data
        if isinstance(data, list):
            # Wrap the list in a dictionary
            data = {'data': data}
        forwardUsers = request.GET.get('forwardUsers') if request.GET.get('forwardUsers') else None
        # Preserve the retained MTO header identity contract (LEG-015), but never
        # expand a header-selected subject using someone else's admin session.
        product_permissions, location_permissions = effective_data_scopes(user_id, application_id,
            administrator=(getattr(request.user, 'is_admin', False) is True
                           and request.user.id == user_id), services=service_map)
        data['product_permissions'] = product_permissions
        data['location_permissions'] = location_permissions
        data['user'] = user_dict
        if(forwardUsers): data['all_users'] = getApproverList(request=request,application_id=application_id)
        if files:
            response = requests.request(
                method=request.method,
                url=url,
                headers={'Authorization': headers['Authorization']},  # Let requests set Content-Type
                params=request.query_params,
                data=data,  # form fields
                files=files
            )
        else:
            response = requests.request(
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                json=data  # JSON payload
            )
        return response
