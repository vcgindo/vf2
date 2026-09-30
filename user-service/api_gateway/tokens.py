# myapp/tokens.py
from rest_framework_simplejwt.tokens import AccessToken , RefreshToken
from .utils import get_site_key

class SiteScopedAccessToken(AccessToken):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['site_key'] = get_site_key()

class SiteScopedRefreshToken(RefreshToken):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['site_key'] = get_site_key()