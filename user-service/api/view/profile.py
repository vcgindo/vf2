from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q,Count


from api.serializer.auth import *
from api.serializer.role import *
from api.serializer.profile import *
from api.common.api_varibale import APIVariable


from api.core import ResponseProfile
from api.docs.auth import *
from common.utils import get_user_permissions, query_from_tuple
from common.permissions import require_roles_permission
from common.user_role import UserRole
from common.http_status_code import HttpStatusCode
from api_gateway.service_config.config import service_map
from common.api_gateway_utils import ALL_PERMISSIONS,getAllUserDetails,get_user_product_and_location_permissions
import json
from api_gateway.utils import getApproverList
import logging

logger = logging.getLogger(__name__)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @profile_doc()
    def get(self, request, format=None):     
        resutl = ResponseProfile(user=request.user)
        return Response(
            {"data": resutl.response()}, status=HttpStatusCode.OK
        )


class GetAllUsersAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @require_roles_permission(roles=[UserRole.ADMIN])
    @all_user_doc()
    def get(self, request, format=None):
        return Response(getAllUserDetails(request), status=HttpStatusCode.OK)


class GetAllPermissionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_not_none(self, columns):
        filter_condition = Q()
        for column in columns:
            filter_condition |= Q(**{column: ""})
        
        return filter_condition

    @all_permissions_doc()
    def get(self, request, format=None):
        all_permissions = ALL_PERMISSIONS.get_combined_permissions(nested=True,withIds=True)
        return Response(all_permissions, status=HttpStatusCode.OK)

class UserChangeThemeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @change_theme_doc()
    def post(self, request):
        serializer = UserChangeThemeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.theme_ui = serializer.validated_data.get('theme_ui')
        user.save()
        return Response(AuthCode.CHANGE_THEME_SUCCESS, status=HttpStatusCode.OK)

class GetHeaderForAllApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            headers = ALL_PERMISSIONS.getHeadersData()
            return Response(headers, status=HttpStatusCode.OK)
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=HttpStatusCode.INTERNAL_SERVER_ERROR)

class GetUserPermissionsView(APIView):
    permission_classes = [IsAuthenticated]
    @require_roles_permission(roles=[UserRole.ADMIN])
    def get(self, request):
        try:
            # Get user ID from query parameters
            user_id = request.GET.get('id')
            if not user_id:
                return Response({"error": "User ID is required"}, status=HttpStatusCode.BAD_REQUEST)
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response({"error": "User not found"}, status=HttpStatusCode.NOT_FOUND)
            permissions = get_user_product_and_location_permissions(user)
            return Response(permissions, status=HttpStatusCode.OK)
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=HttpStatusCode.INTERNAL_SERVER_ERROR)


class GetApproverNamesView(APIView):
    permission_classes = [IsAuthenticated]
    
    '''
    
    def post(self, request):
        try:
            approver_ids = request.data.get('approver_ids', [])
            approvers = User.objects.filter(id__in = approver_ids).values('id', 'name', 'email')
            return Response(list(approvers), status=HttpStatusCode.OK)
        except Exception as e:
            return Response({"error": str(e)}, status=HttpStatusCode.INTERNAL_SERVER_ERROR)
    '''

    def post(self, request):
        try:
            application_id = ApplicationMaster.objects.filter(application_name= 'Orders').first()
            data = getApproverList(request=request,application_id= application_id.application_id)
            return Response(data, status=HttpStatusCode.OK)
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=HttpStatusCode.INTERNAL_SERVER_ERROR)

