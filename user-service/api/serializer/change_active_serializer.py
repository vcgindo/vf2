from rest_framework import serializers
from api.models import User
from api.error_code import NotExistCode, NotPermissionCode
from common.exceptions import ValidationError
from common.http_status_code import HttpStatusCode
from common.permissions import can_update_user
from django.contrib.postgres.aggregates import ArrayAgg
from api.models import User_Application_Product_Permission,User_Application_Location_Permission
import logging

logger = logging.getLogger(__name__)
class ChangeActiveSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(allow_null=False)
    user_id = serializers.IntegerField(allow_null=False)
    admin_id = serializers.IntegerField()

    def validate(self, attrs):
        try:
            if not User.objects.filter(id=attrs['user_id']).exists():
                raise ValidationError(
                    NotExistCode.USER_NOT_EXIST,
                    code=HttpStatusCode.BAD_REQUEST
                )
            
            user = User.objects.filter(id=attrs['user_id']).first()
            admin = User.objects.filter(id=attrs['admin_id']).first()
            #avaiable application permissions for request user
            # The updation the code is due to change in the version of the library as it does not allow to take the first queryset if the queryset is not order by 
            application_ids_product = User_Application_Product_Permission.objects.filter(user_id=user.id).values('user_id').distinct().annotate(application_ids=ArrayAgg('application_id', distinct=True)).order_by('user_id').first()
            application_ids_location = User_Application_Location_Permission.objects.filter(user_id=user.id).values('user_id').distinct().annotate(application_ids=ArrayAgg('application_id', distinct=True)).order_by('user_id').first()
            if application_ids_product:
                product_permission_application_ids = application_ids_product.get('application_ids')
            else:
                product_permission_application_ids = []
            if application_ids_location:
                location_permission_application_ids = application_ids_location.get('application_ids')
            else:
                location_permission_application_ids = []
            if not can_update_user(admin, user, product_permission_application_ids, location_permission_application_ids):
                raise ValidationError(
                        NotPermissionCode.NO_PERMISSION,
                        code=HttpStatusCode.FORBIDDEN
                    )
            
            user.is_active = attrs['is_active']
            user.save()

            return super().validate(attrs)
        except Exception as e:
            logger.exception("Unexpected error occurred")
            raise ValidationError(f'Exception has occurred in validating the active user due to {e}',code=HttpStatusCode.INTERNAL_SERVER_ERROR)
