from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CustomEmailBackend(EmailBackend):
    def open(self):
        if not self.host:
            raise ValueError('SMTP server is not configured')
        # Django owns connection setup, certificate checks, STARTTLS/SSL and login.
        return super().open()


def smtp_configured():
    return bool(settings.EMAIL_HOST and settings.EMAIL_PORT
                and getattr(settings, 'DEFAULT_FROM_EMAIL', ''))
    

def is_smtp_enabled():
    try:
        if not smtp_configured():
            return False
        from django.core.mail import get_connection
        with get_connection():
            pass
        return True
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return False
