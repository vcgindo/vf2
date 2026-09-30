from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from kombu import Queue
from asyncio.log import logger

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.settings')

app = Celery('apps')

# Load settings from Django's settings.py with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.task_queues = (
    Queue("default", routing_key="default"),
    Queue("db_cleanup_queue", routing_key="db_cleanup_queue"),
)

# Set default queue (optional but good practice)
app.conf.task_default_queue = "default"
app.conf.task_default_routing_key = "default"

# Auto-discover tasks in all apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    logger.info(f'Request: {self.request!r}')
