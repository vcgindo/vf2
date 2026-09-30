from rest_framework import serializers

class RSASerializer(serializers.Serializer):
    plain_text = serializers.CharField()

class ResponseRSASerializer(serializers.Serializer):
    private_key = serializers.CharField()
    public_key = serializers.CharField()
    encrypted_text = serializers.CharField()