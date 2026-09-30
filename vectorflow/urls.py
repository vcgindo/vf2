from django.db import connection
from django.http import JsonResponse
from django.urls import path


def health(request):
    return JsonResponse({'service': 'freshvcf-mta', 'alive': True, 'parity': 'NOT_CERTIFIED'})


def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'ready': False}, status=503)
    return JsonResponse({'ready': True})


urlpatterns = [path('healthz', health), path('readyz', ready)]
