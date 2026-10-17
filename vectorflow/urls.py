from django.db import connection
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({'service': 'freshvcf-mta', 'alive': True, 'parity': 'NOT_CERTIFIED'})


def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        from mta.presentation.admission import require_admission
        admission = require_admission()
    except Exception:
        try:
            from mta.presentation.admission import require_application_state
            state = require_application_state()
            if state is not None:
                return JsonResponse({'ready': False, 'application': dict(available=True, **state)}, status=503)
        except Exception:
            pass
        return JsonResponse({'ready': False}, status=503)
    return JsonResponse({'ready': True, 'admission_digest': admission})


urlpatterns = [path('healthz', health), path('readyz', ready),
               path('api/mta/', include('mta.presentation.urls'))]
