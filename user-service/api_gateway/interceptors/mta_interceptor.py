import json
import os
import requests
from api.models import Permission, User_Application_Location_Permission
from api.models import User_Application_Product_Permission
from api_gateway.utils import getAllUserDetails
from django.http import JsonResponse
from rest_framework.response import Response
from api_gateway.mta_stream import (PICK_DOWNLOAD_PATHS, streams_mta_read,
    bounded_mta_read, UPSTREAM_TIMEOUT)
from api_gateway.inprocess_mta import request as mta_request

class MTA_INTERCEPTOR:
    def __init__(self):
        pass
    def forward(self,request,service_map):
        access_token = request.COOKIES.get("access_token")
        if not access_token:
            return Response({"error": "Access token is missing in cookies"}, status=401)
        url = service_map['mta']['base_url'].rstrip('/') + request.path
        application_id = service_map['mta']['application_id']
        identity = {
            'id': request.user.id,
            'name': request.user.name,
            'email': request.user.email,
        }
        if request.path in PICK_DOWNLOAD_PATHS:
            granted = (request.user.is_admin or Permission.objects.filter(
                url='mta-report-urls', role_id__user_id=request.user.id,
                role_id__application_id=application_id).exists())
            if not granted:
                return JsonResponse({'error': 'mta_report_download_forbidden'}, status=403)
            identity['entitlements'] = ['mta-report-urls']
        # headers = {key: value for key, value in request.headers.items() if key != 'Host'}
        headers = {
            'Authorization':  f"Bearer {access_token}",
            'Content-Type': 'application/json',
            os.environ.get('MTA_TRUSTED_GATEWAY_HEADER', 'X-VectorFLOW-Identity'): json.dumps(identity),
        }

        # Migrated MTA requests have an exact schema. Identity is derived from
        # the authenticated gateway session, never from browser-supplied data.
        if request.path.startswith('/api/mta/v1/'):
            return mta_request(base_url=service_map['mta']['base_url'],
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                json=request.data if request.method not in ('GET', 'DELETE') else None,
            )

        # print("REQUEST DATA",request.data)
        data = request.data.copy() if hasattr(request.data, 'copy') else request.data

        #Inject Current Application Permissions
        user_dict = {
            "id":request.user.id,
            "name":request.user.name
        }
        forwardUsers = data.get('forwardUsers') if data.get('forwardUsers') else None
        product_permissions = list(User_Application_Product_Permission.objects.filter(application_id=application_id,user_id=request.user.id).values_list('productfilter_id',flat=True))
        location_permissions = list(User_Application_Location_Permission.objects.filter(application_id=application_id,user_id=request.user.id).values_list('locationfilter_id',flat=True))
        data['product_permissions'] = product_permissions
        data['location_permissions'] = location_permissions
        data['user'] = user_dict
        # Task assignees must come from the existing authenticated eligibility
        # owner even if the browser omits forwardUsers or supplies all_users.
        mdm_submit = request.path.rstrip('/').rsplit('/', 1)[-1] in (
            'AddMasterData', 'ModifyMasterData', 'RemoveMasterData')
        if mdm_submit:
            data.pop('all_users', None)
        if forwardUsers or mdm_submit:
            data['all_users'] = getAllUserDetails(request=request,application_id=application_id)
        
        bounded_read = bounded_mta_read(request)
        stream = streams_mta_read(request) or bool(int(data.get("stream", 0)))
        transport = {'timeout': UPSTREAM_TIMEOUT} if bounded_read else {}
        
        if hasattr(request, "FILES") and request.FILES:
            # multipart/form-data
            uploaded_file = list(request.FILES.values())[0]
            files = {
                "file": (uploaded_file.name, uploaded_file, uploaded_file.content_type)
            }
            form_data = {
                "permissionType": request.data.get("permissionType"),
                "headers": request.data.get("headers"),
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                os.environ.get('MTA_TRUSTED_GATEWAY_HEADER', 'X-VectorFLOW-Identity'): json.dumps({
                    'id': request.user.id,
                    'name': request.user.name,
                    'email': request.user.email,
                }),
            }  # do not force Content-Type
            response = mta_request(base_url=service_map['mta']['base_url'],
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                data=form_data,
                files=files,
                stream=stream,
                **transport,
            )
        else:
           
            response = mta_request(base_url=service_map['mta']['base_url'],
                method=request.method,
                url=url,
                headers=headers,
                params=request.query_params,
                json=data,
                stream=stream,
                **transport,
            )

        if response.status_code >= 400:
            # The isolated demo deliberately disables business writes. Preserve
            # its public error code across the gateway rather than burying it
            # in the generic legacy-forwarding error wrapper.
            if response.status_code == 403:
                try:
                    if response.json().get("error") == "demo_read_only":
                        response.close()
                        return JsonResponse({"error": "demo_read_only"}, status=403)
                except (ValueError, AttributeError):
                    pass
            if response.status_code ==404:
                return response
            else:
                error = JsonResponse(
                    {
                        'error': 'Failed to forward request',
                        'status_code': response.status_code,
                        'message': response.text
                    },
                    status=response.status_code
                )
                response.close()
                return error
        # Separately approved SKU and Location compatibility boundaries: the
        # retained history screen consumes two lists; native masters 1/2 emit arrays.
        if (request.path.rstrip('/').endswith('/GetSkuLoc')
                and str(data.get('masterId')) in ('1', '2') and response.status_code == 200):
            body = response.json()
            if isinstance(body.get('data'), list):
                rows = body['data']
                body['data'] = ({'sku': rows, 'loc': []} if str(data.get('masterId')) == '1'
                                else {'sku': [], 'loc': rows})
                response.close()
                return JsonResponse(body)
        return response
