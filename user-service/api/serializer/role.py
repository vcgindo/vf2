from rest_framework import serializers
from api.models import *


class RolesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ["id", "name", "description","application_id","code"]
