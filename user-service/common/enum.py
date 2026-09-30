from enum import Enum

#this enum contains the api end points which are excluded when JwtAccessTokenAuthMiddleware is called
class ExcludedApiEndpoints(Enum):
    REFRESH='/api/user/token/refresh/'
    LOGIN='/api/user/login/'
