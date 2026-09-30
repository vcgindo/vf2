class ResponseErrorException(Exception):
    def __init__(self, payload, *args, **kwargs):
        super().__init__(*args)
        self.payload = payload

        if isinstance(payload, dict) and isinstance(kwargs, dict):
            self.payload = {**self.payload, **kwargs}

from rest_framework import exceptions
from rest_framework import status


class ResponseError403Exception(exceptions.APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'error'

    def __init__(self, detail, status_code=None):
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
class ResponseError400Exception(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'error'

    def __init__(self, detail, status_code=None):
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
