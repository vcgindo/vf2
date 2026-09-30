from rest_framework.views import APIView
from rest_framework.response import Response
from .service_config.config import service_map
from rest_framework.permissions import IsAuthenticated
import requests
from django.http import JsonResponse,HttpResponse,StreamingHttpResponse
import logging

logger = logging.getLogger(__name__)

class API_GATEWAY_VIEW(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _passthrough_local_json(response):
        """Keep a local interceptor's Django JSON error intact.

        MTA's demo read-only boundary deliberately returns ``JsonResponse``
        before a network response exists.  The gateway otherwise handles
        ``requests.Response`` objects, whose ``json()`` method is not present
        on Django responses.  Returning it directly preserves the intended
        stable 403 contract instead of converting it to a 500.
        """
        return response if isinstance(response, JsonResponse) else None

    def get(self, request, format=None):
        try:
            application_name = request.path.split('/')[2]
            response = service_map[application_name]['interceptor']().forward(request, service_map)        
            local_response = self._passthrough_local_json(response)
            if local_response is not None:
                return local_response
            if 'Content-Disposition' in response.headers:
                if response.status_code == 404:
                    return HttpResponse(status=404)
                file_response = HttpResponse(response.content, content_type=response.headers.get('Content-Type', 'application/octet-stream'))
                file_response['Content-Disposition'] = response.headers['Content-Disposition']
                return file_response        
            if response.status_code == 200 and response.text:
                return Response(response.json())
            else:
                return Response(response.json(), status=response.status_code)
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=500)

    def post(self, request, format=None):
        application_name = request.path.split('/')[2]
        response = service_map[application_name]['interceptor']().forward(request, service_map)
        local_response = self._passthrough_local_json(response)
        if local_response is not None:
            return local_response
        
        try:
            if 'Content-Disposition' in response.headers:
                proxy_response = StreamingHttpResponse(
                    (chunk for chunk in response.iter_content(chunk_size=8192) if chunk),
                    content_type=response.headers.get("Content-Type", "application/octet-stream")
                )
                proxy_response["Content-Disposition"] = response.headers.get("Content-Disposition")
                return proxy_response
            if response.status_code == 200 and response.text:
                return Response(response.json())
            else:
                return Response(response.json(),status=response.status_code)
        except ValueError:
            return Response({"error": "Invalid JSON response"}, status=500)

    def delete(self, request, format=None):
        application_name = request.path.split('/')[2]
        response = service_map[application_name]['interceptor']().forward(request,service_map)
        local_response = self._passthrough_local_json(response)
        if local_response is not None:
            return local_response
        return Response(response.json())
        
    def put(self, request, format=None):
        try:
            application_name = request.path.split('/')[2]
            response = service_map[application_name]['interceptor']().forward(request, service_map)
            local_response = self._passthrough_local_json(response)
            if local_response is not None:
                return local_response
            if 'Content-Disposition' in response.headers:
                file_response = HttpResponse(response.content, content_type=response.headers.get('Content-Type', 'application/octet-stream'))
                file_response['Content-Disposition'] = response.headers['Content-Disposition']
                return file_response        
            if response.status_code == 200 and response.text:
                return Response(response.json())
            else:
                return Response(response.json(), status=response.status_code)
        except ValueError:
            return Response({"error": "Invalid JSON response"}, status=500)
