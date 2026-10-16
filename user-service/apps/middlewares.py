from django.http import HttpResponseForbidden, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
import hmac
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken

from api.models import TokenBlacklistAccessToken
from common.enum import ExcludedApiEndpoints
from common.startup_probe import observed

class BlockHttpMethodOverrideHeadersMiddleware(MiddlewareMixin):
    def process_request(self, request):
        override_headers = [
            'HTTP_X_HTTP_METHOD_OVERRIDE',
            'HTTP_X_HTTP_METHOD',
            'HTTP_X_METHOD_OVERRIDE',
        ]
        for header in override_headers:
            if header in request.META:
                return HttpResponseForbidden("HTTP Method override not allowed.")


class NoCacheHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    



"""
JwtAccessTokenAuthMiddleware that checks if the access token in the request is blacklisted. 
If the token is blacklisted, a 401 Unauthorized response is returned. 
Otherwise, the request proceeds as normal.
"""
class JwtAccessTokenAuthMiddleware(MiddlewareMixin):
    @observed('jwt_blacklist')
    def process_request(self, request):
        #fetching access token
        ignore_paths = tuple(endpoint.value for endpoint in ExcludedApiEndpoints)
        if request.path.startswith(ignore_paths):
            return None
        
        access_token_str=request.COOKIES.get('access_token')
        if not access_token_str:
            return None
        try:
            access_token=AccessToken(access_token_str)
            access_jti=access_token['jti']
        except Exception as e:
            return self._deny("Access token is invalid")
        if TokenBlacklistAccessToken.objects.filter(access_jti=access_jti).exists():
            return self._deny("Access token is blacklisted")
        return None
    def _deny(self,message):
        response = JsonResponse(
            {"detail": message},
            status=401
        )
        return response

    
