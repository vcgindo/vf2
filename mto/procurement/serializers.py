from rest_framework import serializers

class BatchwiseComponentAllocationSerializer(serializers.Serializer):
    on = serializers.CharField()
    lid = serializers.CharField()
    item = serializers.CharField()
    easa = serializers.DecimalField(max_digits=13, decimal_places=3)
    sno = serializers.CharField()
