from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework import status
from api.serializer.profile import *
from api.core import ResponseUser
from api.models import User
from api.error_code import NotExistCode
from api.docs.auth import *
from common.utils import get_user_permissions
from api_gateway.utils import get_site_key
from common.http_status_code import HttpStatusCode
from rest_framework_simplejwt.tokens import AccessToken
from django.core.cache import cache
from api_gateway.serializers import CustomTokenRefreshSerializer

class RefreshTokenView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer

    @refresh_token_doc()
    def post(self, request, *args, **kwargs):
        # Determine if the request is secure
        is_secure = request.scheme == "https"
        environment = os.getenv("ENVIRONMENT", "")
        
        # Get refresh token from cookies
        refresh_token_str = request.COOKIES.get("refresh_token")
        if not refresh_token_str:
            return Response({"error": "Refresh token missing"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token_str)
            access_token_str = str(refresh.access_token)   # generate new access token

            new_refresh_token_str = str(refresh)

        except TokenError as e:
            raise InvalidToken(e.args[0])

        # Validate site_key
        try:
            token = AccessToken(access_token_str)
            if token.get("site_key") != get_site_key():
                raise InvalidToken("Invalid site token.")
        except Exception as e:
            logger.exception("Unexpected error occurred")
            raise InvalidToken(str(e))

        user_id = token.get("user_id")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(NotExistCode.USER_NOT_EXIST, status=HttpStatusCode.NOT_FOUND)

        # Clear cache + reload permissions
        cache.delete(user.email)
        get_user_permissions(user)
        user_data = UserProfileSerializer(user)
        result = ResponseUser(
            token=str(token),
            user=user_data.data,
            url_permission=True
        )
        response = Response(
            {"data": result.response(msg="Get new token successful")},
            status=HttpStatusCode.OK,
        )

        # Set new access token and refresh cookie
        if environment == "dev":
            response.set_cookie(
                key="access_token",
                value=access_token_str,
                httponly=True,
                secure=True,  
                samesite="None"
            )
            response.set_cookie(
                    key="refresh_token",
                    value=new_refresh_token_str,
                    httponly=True,
                    secure=True,  
                    samesite="None",
                )
        else:
            response.set_cookie(
                key="access_token",
                value=access_token_str,
                httponly=True,
                secure=is_secure,  
                samesite="Strict"
            )
            response.set_cookie(
                    key="refresh_token",
                    value=new_refresh_token_str,
                    httponly=True,
                    secure=is_secure,  
                    samesite="Strict",
                )

        return response
