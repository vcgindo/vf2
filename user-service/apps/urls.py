"""apps URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path

from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularRedocView, SpectacularSwaggerView

from rest_framework import permissions
from django.db import connection
from django.http import JsonResponse
import os
import requests
from common.mta_catalogue import enabled as local_catalogue, validate_configured


def healthz(request):
    return JsonResponse({'status': 'ok', 'service': 'user-service'})


def readyz(request):
    checks = {'identity_database': False, 'mta': False}
    try:
        if local_catalogue():
            checks['mta_catalogue'] = False
            validate_configured()
            checks['mta_catalogue'] = True
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            checks['identity_database'] = cursor.fetchone()[0] == 1
        url = os.environ.get('MTA_BACKEND_URL', 'http://localhost:5153').rstrip('/')
        with requests.get(url + '/readyz', timeout=(2, 2)) as response:
            checks['mta'] = response.status_code == 200 and response.json().get('ready') is True
    except Exception:
        pass
    ready = all(checks.values())
    return JsonResponse({'status': 'ready' if ready else 'unavailable',
        'service': 'user-service', 'scope': 'identity-and-mta-dependencies',
        'checks': checks}, status=200 if ready else 503)


urlpatterns = [
    path('healthz', healthz),
    path('readyz', readyz),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/',
         SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/',
         SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('admin/', admin.site.urls),
    path('api/user/', include('api.urls')),
    path('api/validate-master/',include('master_validation.urls')),
    re_path(r'^api/.*',include('api_gateway.urls')),
    
]
