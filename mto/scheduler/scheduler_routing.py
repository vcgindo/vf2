from django.urls import re_path
from .scheduler_status_consumer import SchedulerStatusConsumer

websocket_urlpatterns = [
    re_path(r'ws/scheduler/(?P<run_id>[\w\-]+)/$', SchedulerStatusConsumer.as_asgi()),
]
