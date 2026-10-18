"""Verify SMTP connection/TLS/login without sending mail or resetting a password.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
import os


def check():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'release.auth_settings')
    import django
    django.setup()
    from django.conf import settings
    from django.core.mail import get_connection
    from api.common.mail_config import smtp_configured
    if not smtp_configured():
        return dict(status='SMTP_NOT_CONFIGURED', message='Configure EMAIL_HOST and EMAIL_FROM; no password was changed.'), 1
    try:
        with get_connection():
            pass
    except Exception as error:
        # Provider errors can contain private identifiers; never dump credentials.
        return dict(status='SMTP_CONNECTION_FAILED', error=type(error).__name__,
                    message='Check provider host/port/TLS, credentials and outbound access.'), 1
    return dict(status='SMTP_CONNECTION_TLS_LOGIN_VERIFIED', port=settings.EMAIL_PORT,
                starttls=settings.EMAIL_USE_TLS, implicit_tls=settings.EMAIL_USE_SSL,
                mail_sent=False, password_changed=False,
                limitation='Connection/login only; recipient delivery is not proved.'), 0


if __name__ == '__main__':
    result, status = check()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(status)
