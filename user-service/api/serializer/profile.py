from rest_framework import serializers
from api.models import *


class Permission(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "code", "description", "url"]

class Features(serializers.ModelSerializer):
    class Meta:
        model = FeatureMaster
        fields = ["id" ,"feature" , "page", "is_active"]

class RolesUser(serializers.ModelSerializer):
    permission_id = Permission(many=True)
    feature_id = Features(many = True)
    class Meta:
        model = Roles
        fields = ["id", "name", "code", "description", "permission_id","application_id" ,'feature_id']


# class LocationsUser(serializers.ModelSerializer):
#     class Meta:
#         model = LocationsFilter
#         fields = ["id", "wh_region", "wh_type", "wh_location_group"]

class RolesUrls(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=255)
    application_id = serializers.IntegerField()
    urls = Permission(many=True)


class ProductUser(serializers.Serializer):
    id = serializers.IntegerField()
    product_hierarchy_1 = serializers.CharField()
    product_hierarchy_2 = serializers.CharField()
    product_hierarchy_3 = serializers.CharField()

class UserProfileSerializer(serializers.ModelSerializer):
    role_id = RolesUser(many=True)
    # location_id = LocationsUser(many=True)
    # product_id = ProductUser(many=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role_id",
            # "product_id",
            # "location_id",
            "is_admin",
            "is_active",
            "is_deleted",
            "theme_ui",
        ]

class UserChangeThemeSerializer(serializers.Serializer):
    theme_ui = serializers.ChoiceField(
        choices=UserTheme.get_choices(), required=True
    )
class UserRoles(serializers.ModelSerializer):
    class Meta:
        model = Roles
        fields = ["id", "name", "code", "description", "application_id"]

class UserDetailsSerializer(serializers.ModelSerializer):
    role_id = UserRoles(many=True)


    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "role_id",
            "is_admin",
            "is_active",
            "is_deleted",
            "theme_ui",
        ]