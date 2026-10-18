from api.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth import password_validation
from common.errors import ResponseErrorException
from api.error_code import AuthCode, NotExistCode
from api.serializer.profile import *
from common.utils import get_value_of_dict
from rest_framework.response import Response
from rest_framework import status
from api.utils import Util
from api.common.mail_config import smtp_configured

from common.send_mail import mail_update_user
from common.permissions import can_update_user
from api.common.api_varibale import APIVariable
from common.http_status_code import HttpStatusCode
from django.contrib.postgres.aggregates import ArrayAgg
import logging

logger = logging.getLogger(__name__)

class ChangePWService:
    @classmethod
    def change_pw(cls, email, old_password, new_password):
        user = User.objects.get(email=email)
        if user.check_password(old_password):
            if " " in new_password:
                return False, ResponseErrorException(
                    payload=AuthCode.IS_VALIDATE_ERROR,
                    error_msg=AuthCode.PASSWORD_NOT_CONTAIN_WHITESPACE,
                )
            try:
                password_validation.validate_password(new_password, user=user)
            except password_validation.ValidationError as er:
                return False, ResponseErrorException(
                    payload=AuthCode.IS_VALIDATE_ERROR, error_msg=er
                )
            user.password = make_password(new_password)
            user.save()
            return True, AuthCode.IS_VALIDATE_SUCCESS
        return False, ResponseErrorException(payload=AuthCode.PW_DOES_NOT_MATCH)


class ChangePWFirstService:
    @classmethod
    def change_pw(cls, email, old_password, new_password):
        user = User.objects.get(email=email)
        if user.check_password(old_password):
            if not user.is_active:
                if " " in new_password:
                    return False, ResponseErrorException(
                        payload=AuthCode.IS_VALIDATE_ERROR,
                        error_msg=AuthCode.PASSWORD_NOT_CONTAIN_WHITESPACE,
                    )
                try:
                    password_validation.validate_password(new_password, user=user)
                except password_validation.ValidationError as er:
                    return False, ResponseErrorException(
                        payload=AuthCode.IS_VALIDATE_ERROR, error_msg=er
                    )
                user.password = make_password(new_password)
                user.save()
                return True, AuthCode.IS_VALIDATE_SUCCESS
            else:
                return False, ResponseErrorException(payload=AuthCode.NOT_ALLOW)
        return False, ResponseErrorException(payload=AuthCode.PW_DOES_NOT_MATCH)


class GetAllPermissionsService:

    def get_value_of_dict(self, dict_data, keys):
        return get_value_of_dict(dict_data, keys)

    def group_value_to_key(self, list_data, result, key_to_group, keys_remain):
        current_value_of_key = list_data[0].get(key_to_group)
        result[current_value_of_key] = [
            self.get_value_of_dict(list_data[0], keys_remain)
        ]

        for data in list_data[1:]:
            if data.get(key_to_group) == current_value_of_key:
                result[current_value_of_key].append(
                    self.get_value_of_dict(data, keys_remain)
                )
            else:
                current_value_of_key = data.get(key_to_group)
                result[current_value_of_key] = [
                    self.get_value_of_dict(data, keys_remain)
                ]

    def group_data(self, list_data, result, keys, current_index_key, deep_of_key):
        if current_index_key == deep_of_key - 1:
            self.group_value_to_key(
                list_data,
                result,
                keys[current_index_key],
                keys[current_index_key + 1 :],
            )
        else:
            self.group_value_to_key(
                list_data,
                result,
                keys[current_index_key],
                keys[current_index_key + 1 :],
            )
            for key, value in result.items():
                new_list_data = value
                result[key] = {}
                self.group_data(
                    new_list_data, result[key], keys, current_index_key + 1, deep_of_key
                )

    def convert_product_response_filter(self, data_service):
        result = {}
        self.group_data(
            data_service, 
            result, 
            APIVariable.product_columns, 
            0, 
            2
        )
        return result

    def convert_location_response_filter(self, data_service):
        result = {}
        self.group_data(
            data_service,
            result,
            APIVariable.location_columns,
            0,
            2,
        )
        return result
class ResetPasswordService:
    @classmethod
    def reset_password(cls, admin, uid):
        user = User.objects.filter(pk=uid).first()
        if user is None:
            return None, Response(NotExistCode.USER_NOT_EXIST, status=HttpStatusCode.BAD_REQUEST)
        
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
            return None, Response(
                AuthCode.CAN_NOT_UPDATE, status=HttpStatusCode.BAD_REQUEST
            )
        
        if not smtp_configured():
            return None, Response(
                AuthCode.SMTP_NOT_CONFIGURED_PASSWORD_RESET, status=HttpStatusCode.BAD_REQUEST
            )

        new_password = User.all_objects.make_random_password(
                allowed_chars=APIVariable.allowed_chars
            ) 
        try:
            # Send email
            data= mail_update_user(user.email,new_password, user.name)

            if Util.send_html_email(data) != 1:
                raise RuntimeError('Email backend did not accept the reset notification')
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return None, Response(
                AuthCode.SEND_MAIL_ERROR,status=HttpStatusCode.BAD_REQUEST
            )
        user.set_password(new_password)
        user.save(update_fields=['password'])
        return user, Response(
            AuthCode.RESET_PASSWORD_SUCCESS, status=HttpStatusCode.OK
        )



