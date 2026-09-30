# myapp/authentication.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .utils import get_site_key

class SiteScopedJWTAuthentication(JWTAuthentication):
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if token.get("site_key") != get_site_key():
            raise AuthenticationFailed("Invalid site token.")
        return token
