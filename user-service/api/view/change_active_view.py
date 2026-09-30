from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from api.serializer.change_active_serializer import ChangeActiveSerializer
from api.error_code import AuthCode
from common.permissions import require_roles_permission
from common.user_role import UserRole
from api.docs.auth import *
from common.http_status_code import HttpStatusCode

class ChangeActiveView(APIView):
    permission_classes = [IsAuthenticated]

    @require_roles_permission(roles=[UserRole.ADMIN])
    @change_active_doc()
    def post(self, request):
        request.data['admin_id'] = request.user.id
        serializer = ChangeActiveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "msg": [str(serializer.errors)]
                },
                status=HttpStatusCode.BAD_REQUEST
            )

        return Response(
                    AuthCode.UPDATE_USER_SUCCESS,
                    status=HttpStatusCode.OK
                )
