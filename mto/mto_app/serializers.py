from rest_framework import serializers
from .models import BufferMaster, CCRMaster, DeptMaster, OrderTypeMaster, PlantHolidayList, PlantMaster, UIReportConfigurations,BufferTypeMaster

class UIReportConfigurationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UIReportConfigurations
        fields = '__all__'

class PlantMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantMaster
        fields = '__all__'

class CCRMasterSerializer(serializers.ModelSerializer):
    plant_name = serializers.SerializerMethodField()
    ccr_group_name = serializers.SerializerMethodField()

    class Meta:
        model = CCRMaster
        fields = '__all__'

    def get_plant_name(self, obj):
        return obj.plant.plant_name if obj.plant else None
    
    def get_ccr_group_name(self, obj):
        return obj.ccr_group.ccr_group_name if obj.ccr_group else None

class BufferTypeMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = BufferTypeMaster
        fields = [ 'buffer_type','buffer_type_id']


class BufferMasterSerializer(serializers.ModelSerializer):
    buffer_type = BufferTypeMasterSerializer(read_only=True)
    class Meta:
        model = BufferMaster    
        fields = ['buffer_id', 'buffer_code', 'buffer_desc', 'buffer_size', 'slt', 'mlt', 'is_blue', 'buffer_type', 'is_valid']

class PlantHolidayListSerializer(serializers.ModelSerializer):
    plant_name = serializers.SerializerMethodField()
    ccr_name = serializers.SerializerMethodField()
    ccr_code = serializers.SerializerMethodField()

    class Meta:
        model = PlantHolidayList
        fields = '__all__'

    def get_plant_name(self, obj):
        return obj.plant.plant_name if obj.plant else None
    
    def get_ccr_name(self, obj):
        return obj.ccr.ccr_name if obj.ccr else None

    def get_ccr_code(self, obj):
        return obj.ccr.ccr_code if obj.ccr else None

class DeptMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeptMaster
        fields = '__all__'

class OrderTypeMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTypeMaster
        fields = '__all__'

class UserwiseUIReportConfigurationsSerializer(serializers.Serializer):
    un = serializers.CharField()
    rn_id = serializers.IntegerField()
    cs = serializers.JSONField()