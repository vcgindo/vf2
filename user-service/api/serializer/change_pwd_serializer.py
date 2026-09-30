from rest_framework import serializers
from api.models import User
from api.error_code import  NotPermissionCode
from common.exceptions import ValidationError
from django.contrib.auth import password_validation
from common.http_status_code import HttpStatusCode
from api.error_code import AuthCode



class UserChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(min_length=8, max_length=15)
    new_password = serializers.CharField(min_length=8, max_length=15)
    confirm_password = serializers.CharField(min_length=8, max_length=15)

    def validate(self, attrs):
        user = User.objects.get(email=self.context.email)
        if not user.check_password(attrs.get("old_password")):
            raise ValidationError(
                    AuthCode.OLD_PASSWORD_NOT_CORRECT,
                    code=HttpStatusCode.BAD_REQUEST
                )
        if " " in attrs.get("new_password"):
            raise ValidationError(
                    AuthCode.PASSWORD_NOT_CONTAIN_WHITESPACE,
                    code=HttpStatusCode.BAD_REQUEST
                )
        if attrs.get("new_password") != attrs.get("confirm_password"):
            raise ValidationError(
                    AuthCode.PW_DOES_NOT_MATCH
                )
        try:  
            password_validation.validate_password(password=attrs.get("new_password"), user=self.context)
        except ValidationError as e:
            serializer_errors = serializers.as_serializer_error(e)
            raise ValidationError(
                {"password": serializer_errors["non_field_errors"]}
            )
        
        user.set_password(attrs.get("new_password"))
        user.save()

        return user
