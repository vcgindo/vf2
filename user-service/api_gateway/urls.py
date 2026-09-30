from django.urls import path,include
from api.view import *
from api_gateway.views import *

app_name = "api_gateway"

urlpatterns = [
    path('', API_GATEWAY_VIEW.as_view(), name="api_gateway"),
]
