from drf_spectacular.utils import extend_schema
from api.serializer.auth import *
from common.docs import common_docs
from api.serializer.change_pwd_serializer import UserChangePasswordSerializer
from api.serializer.profile import UserChangeThemeSerializer
from api.serializer.rsa_serializer import ResponseRSASerializer, RSASerializer
from api.serializer.issue_report_serializer import IssueReportSerializer

tags = ["user-auth"]


def register_doc():
    return extend_schema(
        operation_id="POST Registration",
        tags=tags,
        description="API create new account for user. Role required Admin",
        request=UserRegistrationSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "msg": {"type": "string"},
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "email": {"type": "array", "items": {"type": "string"}},
                    "name": {"type": "array", "items": {"type": "string"}},
                    "password": {"type": "array", "items": {"type": "string"}},
                    "password2": {"type": "array", "items": {"type": "string"}},
                    "roles": {"type": "array", "items": {"type": "string"}},
                    "product_hierarchy_1": {"type": "array", "items": {"type": "string"}},
                    "product_hierarchy_2": {"type": "array", "items": {"type": "string"}},
                    "product_hierarchy_3": {"type": "array", "items": {"type": "string"}},
                    "wh_region": {"type": "array", "items": {"type": "string"}},
                    "wh_type": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "wh_location_group": {"type": "array", "items": {"type": "string"}},
                },
            },
            401: common_docs[401],
            403: {
                "type": "object",
                "properties": {
                    "details": {"type": "string"},
                    "product_hierarchy_1": {"type": "string"},
                    "product_hierarchy_2": {"type": "string"},
                    "product_hierarchy_3": {"type": "string"},
                    "wh_region": {"type": "string"},
                    "wh_type": {"type": "string"},
                    "wh_location_group": {"type": "string"},
                },
            },
        },
    )

def edit_user_doc():
    return extend_schema(
        operation_id="PUT Edit User",
        tags=tags,
        description="API edit information and permissions of a user. Role required Admin",
        request=EditUserSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    "msg": {"type": "string"},
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'id': {'type': "array", 'items': {'type': "string"}},
                    'email': {'type': "array", 'items': {'type': "string"}},
                    'name': {'type': "array", 'items': {'type': "string"}},
                    'password': {'type': "array", 'items': {'type': "string"}},
                    'password2': {'type': "array", 'items': {'type': "string"}},
                    'roles': {'type': "array", 'items': {'type': "string"}},
                    'product_hierarchy_1': {'type': "array", 'items': {'type': "string"}},
                    'product_hierarchy_2': {'type': "array", 'items': {'type': "string"}},
                    'product_hierarchy_3': {'type': "array", 'items': {'type': "string"}},
                    'wh_region': {'type': "array", 'items': {'type': "string"}},
                    'wh_type': {'type': "array", 'items': {'type': "string"}},
                    'wh_location_group': {'type': "array", 'items': {'type': "string"}},
                }
            },
            401: common_docs[401],
            403:{
                'type': 'object',
                'properties': {
                    'details': {'type': "string"},
                    'product_hierarchy_1': {'type': "string"},
                    'product_hierarchy_2': {'type': "string"},
                    'product_hierarchy_3': {'type': "string"},
                    'wh_region': {'type': "string"},
                    'wh_type': {'type': "string"},
                    'wh_location_group': {'type': "string"},
                }
            }
        }
    )


def login_doc():
    return extend_schema(
        operation_id="POST Login",
        tags=tags,
        description="API login to system",
        request=UserLoginSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "token": {
                                "type": "object",
                                "properties": {
                                    "refresh": {"type": "string"},
                                    "access": {"type": "string"},
                                },
                            },
                            "user": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "number"},
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                    "is_admin": {"type": "boolean"},
                                    "theme_ui": {"type": "string"}
                                },
                            },
                            "roles": {
                                "type": "object",
                                "properties": {
                                    "permission": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                           "properties": {
                                                "id": {"type": "number"},
                                                "name": {"type": "string"},
                                                "code": {"type": "string"},
                                                "application_id":{"type":"number"}
                                            }, 
                                        }
                                    },
                                    "product_permission": {
                                        "type": "array",
                                        "items": {
                                            "type":"object",
                                            "properties":{
                                                "application_id":{"type": "number"},
                                                "application_name":{"type":"string"},
                                                "permission":{
                                                    "type":"array",
                                                    "items":{
                                                        "type":"object",
                                                        "properties":{
                                                            "id": {"type": "number"},
                                                            "product_hierarchy_1": {"type": "string"},
                                                            "product_hierarchy_2": {"type": "string"},
                                                            "product_hierarchy_3": {"type": "string"}
                                                        }
                                                    }
                                                }
                                                
                                            }
                                        }
                                    },
                                    "location_permission": {
                                        "type": "array",
                                        "items": {
                                            "type":"object",
                                            "properties":{
                                                "application_id":{"type": "number"},
                                                "application_name":{"type":"string"},
                                                "permission":{
                                                    "type":"array",
                                                    "items":{
                                                        "type":"object",
                                                        "properties":{
                                                            "id": {"type": "number"},
                                                            "wh_region": {"type": "string"},
                                                            "wh_type": {"type": "string"},
                                                            "wh_location_group": {"type":"string"}
                                                        }
                                                    }
                                                }
                                                
                                            }
                                        }
                                    },
                                },
                            },
                            "data":{},
                            "url_permissions": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "language": {"type": "string"},
                            "msg": {"type": "string"},
                        },
                    }
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "email": {"type": "array", "items": {"type": "string"}},
                    "password": {"type": "array", "items": {"type": "string"}},
                },
            },

        },
    )


def reset_pwd_doc():
    return extend_schema(
        operation_id="POST reset-pwd",
        tags=tags,
        description="API reset password user by admin. Role: Admin",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "msg": {},
                },
            },
            400: {
                "type": "object",
                "properties": {
                    "non_field_errors": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "password": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "password2": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },
            },
            401: common_docs[401]
        },
    )


def change_pwd_doc():
    return extend_schema(
        operation_id="POST change-pwd",
        tags=tags,
        description="POST change-pwd",
        request=UserChangePasswordSerializer,
        responses={200: common_docs[200], 
                   400: common_docs[400],
                   401:common_docs[401]},
    )


def change_pwd_first_doc():
    return extend_schema(
        operation_id="POST change-pwd-first",
        tags=tags,
        description="API user change password first login",
        request=UserChangePWFirstSerializer,
        responses={
            200: common_docs[200], 
            400: common_docs[400]
        },
    )


def send_reset_pwd_email_doc():
    return extend_schema(
        operation_id="POST send-reset-pwd-email",
        tags=tags,
        description="API send url reset password for user",
        request=SendPWDResetEmailSerializer,
        responses={
            200: common_docs[200],
            400: common_docs[400]
        },
    )


def profile_doc():
    return extend_schema(
        operation_id="GET Profile",
        tags=tags,
        description="API get profile of user",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "user": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "number"},
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                    "is_admin": {"type": "boolean"},
                                    "theme_ui": {"type": "string"},
                                },
                            },
                            "roles": {
                                "type": "object",
                                "properties": {
                                    "permission": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                           "properties": {
                                                "id": {"type": "number"},
                                                "name": {"type": "string"},
                                                "code": {"type": "string"},
                                            }, 
                                        }
                                    },
                                    "product_permission": {
                            "type": "array",
                            "items": {
                                "type":"object",
                                "properties":{
                                    "application_id":{"type": "number"},
                                    "application_name":{"type":"string"},
                                    "permission":{
                                        "type":"array",
                                        "items":{
                                            "type":"object",
                                            "properties":{
                                                "id": {"type": "number"},
                                                "product_hierarchy_1": {"type": "string"},
                                                "product_hierarchy_2": {"type": "string"},
                                                "product_hierarchy_3": {"type": "string"}
                                            }
                                        }
                                    }
                                    
                                }
                            }
                            },
                                    "location_permission": {
                            "type": "array",
                            "items": {
                                "type":"object",
                                "properties":{
                                    "application_id":{"type": "number"},
                                    "application_name":{"type":"string"},
                                    "permission":{
                                        "type":"array",
                                        "items":{
                                            "type":"object",
                                            "properties":{
                                                "id": {"type": "number"},
                                                "wh_region": {"type": "string"},
                                                "wh_type": {"type": "string"},
                                                "wh_location_group": {"type":"string"}
                                            }
                                        }
                                    }
                                    
                                }
                            }
                            },
                                },
                            },
                            "url_permissions": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "language": {"type": "string"},
                            "msg": {"type": "string"},
                        },
                    }
                },
            },
            401: {
                "type": "object",
                "properties": {
                    "detail": {},
                    "code": {},
                    "message": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "token_class": {},
                                "token_type": {},
                                "message": {},
                            },
                        },
                    },
                },
            },
        },
    )


def role_doc():
    return extend_schema(
        operation_id="GET role",
        tags=tags,
        description="API get all role of system",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "token": {},
                            "roles": {
                                "type": "object",
                                "properties": {
                                    "permission": {},
                                    "product_permission": {},
                                    "location_permission": {},
                                },
                            },
                            "url_permission": {},
                            "language": {"type": "string"},
                            "msg": {"type": "string"},
                        },
                    }
                },
            },
            401: {
                "type": "object",
                "properties": {
                    "detail": {},
                    "code": {},
                    "message": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "token_class": {},
                                "token_type": {},
                                "message": {},
                            },
                        },
                    },
                },
            },
        },
    )


def all_role_doc():
    return extend_schema(
        operation_id="GET All role",
        tags=tags,
        description="API get information of roles",
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "number"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "application_id":{"type":"number"}
                    },
                },
            },
            401: {
                "type": "object",
                "properties": {
                    "detail": {},
                    "code": {},
                    "message": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "token_class": {},
                                "token_type": {},
                                "message": {},
                            },
                        },
                    },
                },
            },
        },
    )

def all_applications_doc():
    return extend_schema(
        operation_id="GET All Applications",
        tags=tags,
        description="API get information of all active Applications",
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "application_id":{"type":"number"},
                        "application_name": {"type": "string"},
                    },
                },
            },
            401: {
                "type": "object",
                "properties": {
                    "detail": {},
                    "code": {},
                    "message": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "token_class": {},
                                "token_type": {},
                                "message": {},
                            },
                        },
                    },
                },
            },
        },
    )

def all_functions_doc():
    return extend_schema(
        operation_id="GET All Functions(URLs)",
        tags=tags,
        description="API get information of all Functions(URLs) available",
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":{"type":"number"},
                        "name": {"type": "string"},
                        "code": {"type": "string"},
                        "description": {"type": "string"},
                        "url": {"type": "string"},
                    },
                },
            },
            401: {
                "type": "object",
                "properties": {
                    "detail": {},
                    "code": {},
                    "message": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "token_class": {},
                                "token_type": {},
                                "message": {},
                            },
                        },
                    },
                },
            },
        },
    )

def add_function_doc():
    from api.serializer.profile import Permission as PermissionSerializer
    return extend_schema(
        operation_id="POST add-function",
        tags=tags,
        description="POST add-function",
        request=PermissionSerializer(many=True),
        responses={200: common_docs[200], 
                   400: common_docs[400],
                   401:common_docs[401]},
    )

def add_role_doc():
    from api.serializer.profile import RolesUrls
    return extend_schema(
        operation_id="POST add-role",
        tags=tags,
        description="POST add-role",
        request=RolesUrls(many=True),
        responses={200: common_docs[200], 
                   400: common_docs[400],
                   401:common_docs[401]},
    )

def all_user_doc():
    return extend_schema(
        operation_id="GET All User",
        tags=tags,
        description="API get all users of the system",
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "number"},
                        "email": {"type": "string", "format": "email"},
                        "name": {"type": "string"},
                        "role_id": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "number"},
                                    "name": {"type": "string"},
                                    "code": {"type": "string"},
                                    "description": {"type": "string"},
                                    "permission_id": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "number"},
                                                "name": {"type": "string"},
                                                "code": {"type": "string"},
                                                "description": {"type": "string"},
                                                "url": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                        "product_id": {
                            "type": "array",
                            "items": {
                                "type":"object",
                                "properties":{
                                    "application_id":{"type": "number"},
                                    "application_name":{"type":"string"},
                                    "permission":{
                                        "type":"array",
                                        "items":{
                                            "type":"object",
                                            "properties":{
                                                "id": {"type": "number"},
                                                "product_hierarchy_1": {"type": "string"},
                                                "product_hierarchy_2": {"type": "string"},
                                                "product_hierarchy_3": {"type": "string"}
                                            }
                                        }
                                    }
                                    
                                }
                            }
                            },
                        "location_id": {
                            "type": "array",
                            "items": {
                                "type":"object",
                                "properties":{
                                    "application_id":{"type": "number"},
                                    "application_name":{"type":"string"},
                                    "permission":{
                                        "type":"array",
                                        "items":{
                                            "type":"object",
                                            "properties":{
                                                "id": {"type": "number"},
                                                "wh_region": {"type": "string"},
                                                "wh_type": {"type": "string"},
                                                "wh_location_group": {"type":"string"}
                                            }
                                        }
                                    }
                                    
                                }
                            }
                            },
                        "is_active": {"type": "bool"},
                        "is_admin": {"type": "bool"},
                        "is_deleted": {"type": "bool"},
                        "theme_uid": {"type": "string"},
                    },
                },
            },
            401: {
                "type": "object",
                "properties": {
                    "detail": {},
                    "code": {},
                    "message": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "token_class": {},
                                "token_type": {},
                                "message": {},
                            },
                        },
                    },
                },
            },
            403: common_docs[403]
        },
    )


def soft_delete_doc():
    return extend_schema(
        operation_id="PUT user",
        tags=tags,
        description="API soft delete user by Admin. Role required Admin",
        responses={
            200: common_docs[200], 
            400: common_docs[400], 
            401: common_docs[401],
            403: common_docs[403]
        },
    )

def all_permissions_doc():
    return extend_schema(
        operation_id="get-all-permissions-list",
        tags=tags,
        description="API get all permissions of user",
        responses={
            200: {
                "type": "array",
                "items":{
                    "type":"object",
                    "properties": {
                        "application_id":{"type":"number"},
                        "application_name":{"type":"string"},
                        "product": {
                            "type": "object",
                            "properties": {
                                "product_hierarchy_1": {
                                    "type": "object",
                                    "properties": {
                                        "product_hierarchy_2": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "product_hierarchy_3": {"type": "string"}
                                                },
                                            },
                                        }
                                    },
                                }
                            },
                        },
                        "location": {
                        "type": "object",
                        "properties": {
                            "wh_region": {
                                "type": "object",
                                "properties": {
                                    "wh_type": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "wh_location_group": {"type": "string"}
                                            },
                                        },
                                    }
                                },
                            }
                        },
                    },
                    },
                },
                
            },
            401: common_docs[401],
        },
    )

def refresh_token_doc():
    return extend_schema(
        operation_id="POST get new token",
        tags=tags,
        description="API get new token",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "token": {
                                "type": "object",
                                "properties": {
                                    "refresh": {"type": "string"},
                                    "access": {"type": "string"},
                                },
                            },
                            "user": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "number"},
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                    "is_admin": {"type": "boolean"},
                                    "theme_ui": {"type": "string"},
                                },
                            },
                            "roles": {
                                "type": "object",
                                "properties": {
                                    "permission": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                           "properties": {
                                                "id": {"type": "number"},
                                                "name": {"type": "string"},
                                                "code": {"type": "string"},
                                            }, 
                                        }
                                    },
                                    "product_permission": {
                                        "type": "array",
                                        "properties": {
                                            "id": {"type": "number"},
                                            "product_hierarchy_1": {"type": "string"},
                                            "product_hierarchy_2": {"type": "string"},
                                            "product_hierarchy_3": {"type": "string"}
                                        },
                                    },
                                    "location_permission": {
                                        "type":"array",
                                        "properties": {
                                            "id": {"type": "number"},
                                            "wh_region": {"type": "string"},
                                            "wh_type": {"type": "string"},
                                            "wh_location_group": {"type":"string"}
                                        },
                                    },
                                },
                            },
                            "data":{},
                            "url_permissions": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                }
                            },
                            "language": {"type": "string"},
                            "msg": {"type": "string"},
                        },
                    }
                },
            },
            401: common_docs[401],
        },
    )

class FakeChangeActiveSerializer(serializers.Serializer):
    is_active = serializers.BooleanField(allow_null=False)
    user_id = serializers.IntegerField(allow_null=False)

def change_active_doc():
    return extend_schema(
        operation_id="POST change active user. Role required Admin",
        tags=tags,
        description="API change active/deactive user by admin. Role required Admin",
        request=FakeChangeActiveSerializer,
        responses={
            200:common_docs[200],
            400:common_docs[400],
            403: common_docs[403]
        }
    )

def change_theme_doc():
    return extend_schema(
        operation_id="POST change theme ui user",
        tags=tags,
        description="POST change theme ui user",
        request=UserChangeThemeSerializer,
        responses={
            200:common_docs[200],
            400:common_docs[400],
            401: common_docs[401]
        }
    )

def rsa_doc():
    return extend_schema(
        operation_id="POST get ras",
        tags=tags,
        description="API encrypted password database",
        request=RSASerializer,
        responses={200: ResponseRSASerializer, 
                   400: common_docs[400],
                   401:common_docs[401]},
    )

def forgot_password_doc():
    return extend_schema(
        operation_id="POST change password",
        tags=tags,
        description="API user change password by url forgot password",
        request=ForgotPasswordSerializer,
        responses={
            200: common_docs[200], 
            400: common_docs[400],
        },
    )

def issue_report_doc():
    return extend_schema(
        operation_id="POST issue report",
        tags=tags,
        description="API for user to issue report",
        request=IssueReportSerializer,
        responses={
            200: common_docs[200], 
            400: common_docs[400],
            401: common_docs[401],
        },
    )

def get_issue_report_doc():
    return extend_schema(
        operation_id="GET issue report",
        tags=tags,
        description="API get choices issue report for user",
        responses={
            200: {
                "type": "object",
                "properties":{
                    "issue_component":{
                        "type":"object",
                        "properties":{
                            "Inter Store Transfer":{
                                "type":"array",
                                "items":{"type":"string"}
                            }
                        }
                    },
                    "issue_type":{
                        "type":"array",
                        "items":{"type":"string"}
                    }
                }
            }, 
            400: common_docs[400],
            401: common_docs[401],
        },
    )

def logout_doc():
    return extend_schema(
        operation_id="POST user logout",
        tags=tags,
        description="API for user to logout",
        request=LogoutSerializer,
        responses={
            200: common_docs[200], 
            400: common_docs[400],
            401: common_docs[401],
        },
    )

def add_domain_doc():
    return extend_schema(
        operation_id="POST add domain",
        tags=tags,
        description="API for user to add domain",
        request=AddDomainSerializer,
        responses={
            200: common_docs[200], 
            400: common_docs[400],
            401: common_docs[401],
        },
    )

def update_domain_doc():
    return extend_schema(
        operation_id="PUT update domain",
        tags=tags,
        description="API for user to update domain",
        request=UpdateDomainSerializer,
        responses={
            200: common_docs[200], 
            400: common_docs[400],
            401: common_docs[401],
        },
    )

def delete_domain_doc():
    return extend_schema(
        operation_id="DELETE delete domain",
        tags=tags,
        description="API for user to delete domain",
        responses={
            200: common_docs[200], 
            400: common_docs[400],
            401: common_docs[401],
        },
    )