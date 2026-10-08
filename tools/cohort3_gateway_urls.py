"""Outer URL boundary for the Cohort3 proof: the unchanged real API gateway."""
from django.urls import include, re_path


urlpatterns = [re_path(r'^api/.*', include('api_gateway.urls'))]
