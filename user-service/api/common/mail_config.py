from django.core.mail.backends.smtp import EmailBackend
import smtplib
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CustomEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False
        try:
            self.connection = self.connection_class(self.host, self.port)
            self.connection.ehlo()
            if self.use_tls:
                self.connection.starttls()  # Ensure no `keyfile` or `certfile` is passed
                self.connection.ehlo()
            if self.username and self.password and self.username.strip() and self.password.strip():
                self.connection.login(self.username, self.password)
        except Exception as e:
            logger.exception("Unexpected error occurred")
            self.close()
            raise
        return True
    

def is_smtp_enabled():
    try:
        host = getattr(settings, 'EMAIL_HOST', None)
        port = getattr(settings, 'EMAIL_PORT', None)
        user = getattr(settings, 'EMAIL_HOST_USER', None)
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
        use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
        use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)

        if not all([host, port]):
            return False  # Incomplete SMTP config

        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)

        server.ehlo()

        if use_tls:
            server.starttls()
            server.ehlo()

        if user and password and user.strip() and password.strip():
            server.login(user, password)

        server.quit()
        return True
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return False
