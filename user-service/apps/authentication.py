from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from common.startup_probe import observed

class CookieJWTAuthentication(JWTAuthentication):
    @observed('jwt_user')
    def authenticate(self, request):
        # Try to get token from cookies
        access_token = request.COOKIES.get("access_token")
        if access_token is None:
            return None  # fallback to default if no cookie

        validated_token = self.get_validated_token(access_token)
        return self.get_user(validated_token), validated_token
