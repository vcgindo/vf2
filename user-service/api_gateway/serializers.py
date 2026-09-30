# myapp/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .tokens import SiteScopedAccessToken
from .utils import get_site_key
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken
from .tokens import SiteScopedRefreshToken
from .utils import get_site_key

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        refresh = SiteScopedRefreshToken.for_user(user)
        access = SiteScopedAccessToken()
        access.set_jti()
        access.set_exp()
        access.set_iat()
        access['user_id'] = user.id
        access['site_key'] = get_site_key()

        refresh['site_key'] = get_site_key()
        return {
            'refresh': str(refresh),
            'access': str(access),
        }


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = attrs.get("refresh")
        try:
            token = RefreshToken(refresh)
            if token.get("site_key") != get_site_key():
                raise InvalidToken("Invalid site token.")
        except Exception as e:
            raise InvalidToken(str(e))

        return super().validate(attrs)