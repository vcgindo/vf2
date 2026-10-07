"""Temporary, explicit policy for the owned3006 client-only CAPTCHA gate.

This never authenticates a user. The unchanged login endpoint still owns every
credential, account, rate-limit and session check.
"""
import os

from django.db import connection
from rest_framework.response import Response
from rest_framework.views import APIView
from api.models import User

ORIGIN = 'http://localhost:3006'
INSTANCE = 'freshvcf-daily3006'
FIXTURES = {'stage2.broad@vectorflow.local': 2,
            'stage2.restricted@vectorflow.local': 3}


def exempt(request):
    try:
        if (os.environ.get('VF_LOCAL_FIXTURE_CAPTCHA_EXEMPTION') != '1'
                or os.environ.get('VF_LOCAL_INSTANCE') != INSTANCE
                or os.environ.get('BASE_CLIENT_URL') != ORIGIN
                or request.headers.get('Origin') != ORIGIN
                or request.get_host() != 'localhost'):
            return False
        email = request.data.get('email')
        if not isinstance(email, str) or email not in FIXTURES:
            return False
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database(), current_schema()')
            if cursor.fetchone() != ('daily_3006', 'identity'):
                return False
        return User.all_objects.filter(pk=FIXTURES[email], email=email,
            is_active=True, is_admin=False, is_deleted=False).exists()
    except Exception:
        # Missing/malformed input and unavailable dependencies never grant it.
        return False


class FixtureCaptchaPolicyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        response = Response({'exempt': bool(exempt(request))})
        response['Cache-Control'] = 'no-store, private'
        return response
