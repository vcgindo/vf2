from common.response_code import construct_response_code
from api.common.api_varibale import APIVariable

class AuthCode:
    __prefix_code = "3"
    IS_VALIDATE_ERROR = construct_response_code(
        __prefix_code, 403, 1, "Invalid password"
    )
    IS_VALIDATE_SUCCESS = construct_response_code(
        __prefix_code, 200, 2, "Password changed successfully"
    )
    PW_DOES_NOT_MATCH = construct_response_code(
        __prefix_code, 400, 3, "Password does not match"
    )
    NOT_ALLOW = construct_response_code(__prefix_code, 403, 4, "Action is not allowed")
    USER_MUST_CHANGE_PASSWORD = construct_response_code(
        __prefix_code, 400, 5, "User must change password"
    )
    CREATE_USER_SUCCESS = construct_response_code(
         __prefix_code, 200, 6, "User created successfully")
    UPDATE_USER_SUCCESS = construct_response_code(
         __prefix_code, 200, 7, "User updated successfully")
    CAN_NOT_UPDATE = construct_response_code(
         __prefix_code, 403, 8, "You can't update this user")
    CHANGE_PWD_SUCCESS = construct_response_code(
         __prefix_code, 200, 9, "Password changed successfully")
    EMAIL_IS_EXISTS = construct_response_code(
         __prefix_code, 400, 10, "Email already exists")
    SEND_MAIL_ERROR = construct_response_code(
        __prefix_code, 400, 11, "Unable to send the emai"
    )
    USER_DELETE_SUCCESS = construct_response_code(
        __prefix_code, 200, 12, "User Deleted Successfully"
    )
    INVALID_ID = construct_response_code(
        __prefix_code, 400, 13, "Id must be a number"
    )
    PRODUCT_PRERMISSION_REQUIRED = construct_response_code(
        __prefix_code, 400, 14, "Product permission is required"
    )
    LOCATION_PRERMISSION_REQUIRED = construct_response_code(
        __prefix_code, 400, 15, "Location permission is required"
    )
    CHANGE_THEME_SUCCESS = construct_response_code(
        __prefix_code, 200, 16, "Theme updated successfully"
    )
    OLD_PASSWORD_NOT_CORRECT = construct_response_code(
        __prefix_code, 400, 17, "Incorrect old password."
    )
    PASSWORD_NOT_CONTAIN_WHITESPACE = construct_response_code(
        __prefix_code, 400, 18, "Your password mustn't contain whitespace"
    )
    RESET_PASSWORD_SUCCESS = construct_response_code(
        __prefix_code, 200, 19, "Your password has been reset successfully."
    )
    SEND_RESET_PASSWORD_SUCCESS = construct_response_code(
        __prefix_code, 200, 26, "Password Reset link sent. Please check your email"
    )
    USERNAME_IS_EXIST = construct_response_code(
        __prefix_code, 400, 27,'Username already exists'
    )
    USERNAME_NOT_VALID = construct_response_code(
    __prefix_code, 400, 28, f'Username must be contained {APIVariable.allowed_username_chars_error}'
    )
    REPORT_SUCCESS = construct_response_code(
        __prefix_code, 200, 29, "Report successful"
    )
    ERROR_RANGE_IMAGE = construct_response_code(
        __prefix_code, 400, 30, "Length of report image must be less than 5"
    )
    ERROR_SIZE_IMAGE = construct_response_code(
        __prefix_code, 400, 31, "Size of report image must be less than 4MB"
    )
    CREATE_USER_ERROR = construct_response_code(
        __prefix_code, 400, 31, "User not created."
    )
    ADD_DOMAIN_SUCCESS = construct_response_code(
        __prefix_code, 200, 32, "Domain added successfully"
    )
    UPDATE_DOMAIN_SUCCESS = construct_response_code(
        __prefix_code, 200, 33, "Domain updated successfully"
    )
    DELETE_DOMAIN_SUCCESS = construct_response_code(
        __prefix_code, 200, 35, "Domain deleted successfully"
    )
    USER_INACTIVE = construct_response_code(
        __prefix_code, 400, 36, "User is inactive please contact admin"
    )
    SMTP_NOT_ENABLED_PASSWORD_RESET = construct_response_code(
        __prefix_code, 200, 37, "Password reset is currently unavailable because the email service is not active. Please check the server configuration or contact your system administrator for assistance."
    )
    SMTP_NOT_ENABLED_ADD_USER = construct_response_code(
        __prefix_code, 200, 38, {
                    "message": "The user has been created successfully.",
                    "warning": "Activation email was not sent as email service is unavailable. Password reset will remain unavailable until the email service is configured."
                    }
    )
    SMTP_NOT_ENABLED_ADS_EXPIRY = construct_response_code(
        __prefix_code, 200, 38, {
                    "message": "Your Active Directory Credentials Will Expire in ",
                    "warning": "notification email was not sent as email service is unavailable. Please ensure the email service is configured."
                    }
    )

class NotExistCode:
    __prefix_code = "3"

    USER_NOT_EXIST = construct_response_code(
        __prefix_code, 400, 20, "User doesn't exist"
    )
    ROLE_NOT_EXIST = construct_response_code(
        __prefix_code, 400, 21, "Role does not exist"
    )
    TOKEN_NOT_EXIST = construct_response_code(
        __prefix_code, 400, 25, "Your password reset link has expired."
    )
    DOMAIN_NOT_EXIST = construct_response_code(
        __prefix_code, 400, 34, "Domain does not exist"
    )
    @classmethod
    def data_permission_not_exist(cls, string):
        return construct_response_code(
        cls.__prefix_code, 400, 22, f"{string} does not exist for current user."
    )



class NotPermissionCode:
    __prefix_code = "3"

    NO_PERMISSION = construct_response_code(
        __prefix_code, 403, 23, "User doesn't have permission"
    )
    @classmethod
    def data_not_permission(cls, string):
        return construct_response_code(
        cls.__prefix_code, 403, 24, f"{string} doesn't have permission"
    )

