import requests


class IST_INTERCEPTOR:
    def __init__(self):
        pass
    def forward(self,request,service_map):
        url = service_map['ist']['base_url'] + ':' + service_map['ist']['port'] + request.path
        headers = {key: value for key, value in request.headers.items() if key != 'Host'}
        response = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            params=request.query_params,
            data=request.data
        )
        return response