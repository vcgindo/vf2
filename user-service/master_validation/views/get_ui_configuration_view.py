import pandas as pd
import json
import numpy as np
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.http import JsonResponse
from ..models.master_metadata_models import *
from ..utils.responses import MasterValidationResponses
from ..docs.ui_config import get_uiConfig_docs



class GetUiConfigView(APIView):
    permission_classes = [IsAuthenticated]
    @get_uiConfig_docs()
    def post(self,request):
        """
        This view fetches all the ui configs for all the masters an returns it as  ajson response
        """
        model = MDMUiConfig
        config_data = model.objects.all().values()
        response_obj = MasterValidationResponses()
        response = response_obj.construct_config_response(config_data)
        return JsonResponse(response)
        
        