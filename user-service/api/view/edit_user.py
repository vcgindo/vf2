from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated

from api.serializer.auth import *
from api.serializer.role import *
from api.serializer.profile import *

from api.docs.auth import *
from api.error_code import AuthCode, NotExistCode
from common.permissions import require_roles_permission, can_update_user
from common.send_mail import mail_update_user
from common.user_role import UserRole
from common.http_status_code import HttpStatusCode
import logging

logger = logging.getLogger(__name__)

class EditUserView(APIView):
    permission_classes = [IsAuthenticated]

    @require_roles_permission(roles=[UserRole.ADMIN])
    @edit_user_doc()
    def put(self, request, format=None):
        if request.data.get('password') and ' ' in request.data.get('password'):
            return Response(
                AuthCode.PASSWORD_NOT_CONTAIN_WHITESPACE,
                status=HttpStatusCode.BAD_REQUEST
            )
        try:
            user = User.objects.get(id=request.data.get('id'))
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response(
                NotExistCode.USER_NOT_EXIST, status=HttpStatusCode.BAD_REQUEST
            )
            
        #Array Containing Application Id to Check Permissions For
        application_ids_product = [app['application_id'] for app in request.data['product_permissions']]
        application_ids_location = [app['application_id'] for app in request.data['location_permissions']]

        if not can_update_user(request.user, user,application_ids_product,application_ids_location):
            return Response(
                AuthCode.CAN_NOT_UPDATE, status=HttpStatusCode.BAD_REQUEST
            )
        old_email = user.email
        serializer = EditUserSerializer(
                instance=user,
                data=request.data,
                context=request.user
            )

        
        if serializer.is_valid():
            cache.delete(user.email)
            password = serializer.validated_data.get('password')
            new_email = serializer.validated_data.get('email')
            if password or old_email!=new_email:
                try:
                    # Send email
                    data= mail_update_user(user.email,password, user.name)
                    Util.send_html_email(data)
                except Exception as e:
                    logger.exception("Unexpected error occurred")
                    return Response(
                        AuthCode.SEND_MAIL_ERROR,status=HttpStatusCode.BAD_REQUEST
                    )
            user = serializer.save()
            return Response(
                AuthCode.UPDATE_USER_SUCCESS, status=HttpStatusCode.OK
            )
        return Response(
            serializer.errors, status=HttpStatusCode.BAD_REQUEST
        )
