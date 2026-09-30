from rest_framework import serializers
import pandas as pd
class GetMasterCountSerializer(serializers.Serializer):
    id = serializers.CharField()
    
    def validate_id(self, value):
        if not (15 <= int(value) <= 27):
            raise serializers.ValidationError("ID must be in the range 15-27.")
        return value
    
