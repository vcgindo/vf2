from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated , IsAdminUser
from rest_framework import generics, status, permissions
from rest_framework.decorators import authentication_classes, permission_classes
import jwt
from rest_framework_simplejwt.tokens import AccessToken
from api.services import ResetPasswordService
from django.core.cache import cache

from api.serializer.auth import *
from api.serializer.role import *
from api.serializer.profile import *
from api.serializer.change_pwd_serializer import *

from api.docs.auth import *
from api.services import ChangePWService
from api.error_code import AuthCode, NotExistCode
from common.permissions import require_roles_permission, can_update_user
from common.utils import get_user_permissions
from common.send_mail import mail_create_user
from common.user_role import UserRole
from common.http_status_code import HttpStatusCode
from django.contrib.auth.hashers import make_password
from api.core import ResponseUser

from Crypto.Cipher import AES
from Crypto.Util import Counter
import base64
from api.utils import Util,ActiveDirectoryUtil
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Q

from api.common.mail_config import is_smtp_enabled
from rest_framework.views import APIView
from django.conf import settings
from api_gateway.utils import get_site_key, get_client_ip
from rest_framework.permissions import AllowAny

from django.contrib.auth import get_user_model

from datetime import datetime
import logging

logger = logging.getLogger(__name__)
# Generate Token Manually
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token
    user_permission = get_user_permissions(user)
    site_key = get_site_key()

    access["roles"] = user_permission["roles"]
    access["site_key"] = site_key

    refresh["site_key"] = site_key  
    refresh["user_id"] = str(user.id)  

    return {
        "refresh": str(refresh),
        "access": str(access),
        "access_expires_at": access.payload["exp"],
        "refresh_expires_at": refresh.payload["exp"],
    }


class UserRegistrationView(APIView):
    permission_classes = [IsAuthenticated]

    @require_roles_permission(roles=[UserRole.ADMIN])
    @register_doc()
    def post(self, request, format=None):
        if request.data.get("password") and " " in request.data.get("password"):
            return Response(
                AuthCode.PASSWORD_NOT_CONTAIN_WHITESPACE,
                status=HttpStatusCode.BAD_REQUEST,
            )
        serializer = UserRegistrationSerializer(data=request.data, context=request.user)
        if serializer.is_valid():
            try:
                user = serializer.save()
            except Exception as e:
                return Response(
                    AuthCode.CREATE_USER_ERROR,
                    status=HttpStatusCode.BAD_REQUEST,
                )
            try:
                data = mail_create_user(
                    user.email,
                    user.name,
                    serializer.validated_data.get('password')
                )
                smtp_available = is_smtp_enabled()
            
                if smtp_available:
                    Util.send_html_email(data)

                elif not smtp_available:
                    return Response(
                        AuthCode.SMTP_NOT_ENABLED_ADD_USER,
                        status=HttpStatusCode.OK
                    )
            except Exception as e:
                logger.exception("Unexpected error occurred")
                return Response(
                    AuthCode.SEND_MAIL_ERROR,
                    status=HttpStatusCode.BAD_REQUEST,
                )
            return Response(
                AuthCode.CREATE_USER_SUCCESS, status=HttpStatusCode.CREATED
            )
        errors = {}
        for field, error in serializer.errors.items():
            errors[field] = [err[0].upper() + err[1:] for err in error if err is not None]
        return Response(errors, status=HttpStatusCode.BAD_REQUEST)


@authentication_classes([])
@permission_classes([])
class UserLoginView(APIView):
    def decrypt_password(self,encrypted_password, secret_key):
        encrypted_data = base64.b64decode(encrypted_password)
        iv = encrypted_data[:16]  # Extract the IV
        ciphertext = encrypted_data[16:]  # Extract the ciphertext
        ctr = Counter.new(128, initial_value=int.from_bytes(iv, byteorder='big'))
        cipher = AES.new(secret_key.encode('utf-8'), AES.MODE_CTR, counter=ctr)
        decrypted_password = cipher.decrypt(ciphertext)
        return decrypted_password.decode('utf-8')

    @login_doc()
    def post(self, request, format=None):
        from apps.settings import SECRET_KEY_FOR_PASSWORD

        # Determine if the request is secure
        is_secure = request.scheme == "https"
        environment = os.getenv("ENVIRONMENT", "")

        if " " in request.data.get("password"):
            return Response(
                AuthCode.PASSWORD_NOT_CONTAIN_WHITESPACE,
                status=HttpStatusCode.BAD_REQUEST,
            )
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.data.get("email").lower()
        password = serializer.data.get("password")
        user = User.objects.filter(Q(email__iexact=email) | Q(name__iexact=email)).first()
        if not user:
              return Response(
                {"error": {"non_field_errors": ["User does not exist"]}},
                status=HttpStatusCode.BAD_REQUEST,
                )
        
        logger.info("fetching the ads_active flag or allowed domain value")
        #this will convert the string into boolean value
        ads_active_flag = str(UserserviceConfig.objects.filter(flag='Is_ADS_ACTIVE').values_list('value', flat=True).first()).lower() == "true"
        domain_to_verify=ADS_Config.objects.filter(flag='verify_domain').values_list('value',flat=True).first()
        logger.info("splitting user's email to fetch domain")
        #splitting the user.email to fetch domain
        user_domain=user.email.split('@')[1]
        #condition 1 if ADS is Active but Domain does not exists it will return bad response
        if ads_active_flag and not domain_to_verify:
            logger.info("Domain is absent in ADS_Config")
            return Response(
                    {"error": {"non_field_errors": [f"No domain is configured for ADS verification. Please contact the administrator"]}},
                    status=HttpStatusCode.BAD_REQUEST,
            )
        #condition 2 where ADS is active and verify_domain matches with user's domain
        should_call_ads= ads_active_flag and (user_domain.lower()==domain_to_verify.lower())
        if should_call_ads:
            """ condition falls true
                if 
                1) ads flag is active
                2) the domain is present in Ads_Config
                3) the domain matches with the user's email domain
            """
            logger.info("now checking if user is active or no in azure directory services")
            ads_authorization=ActiveDirectoryUtil.ads_Authentication(user.email)
            if ads_authorization.get('success') and ads_authorization.get("status") == HttpStatusCode.OK:
                logger.info("ads_authorization has successfully executed")
                #safety check to match mail
                if user.email==ads_authorization.get('mail'):
                    accountEnabled=ads_authorization.get('accountEnabled')
                    if accountEnabled is None:
                        logger.error(f"{user.email} cannot be verified as active directory does not have enough permissions.Check configured permissions in Active Directory if User.Read.All exists")
                        return Response(
                            {"error": {"non_field_errors": ["User's account activity status cannot be verified as active directory lacks required permissions.\n Please contact the administrator"]}},
                                status=HttpStatusCode.BAD_REQUEST,
                    )
                    if accountEnabled is False:
                        logger.info(f"{user.email} is inactive in Active Directory")
                        user.is_active=False
                        user.save()
                        logger.info(f"{user.email} is_active changed to inactive")
                else:
                    logger.error(f"{user.email}'s credentials are invalid or they are not present in Active Directory ")
                    return Response(
                    {"error": {"non_field_errors": ["The user credentials are invalid or they are not present in Active Directory"]}},
                    status=HttpStatusCode.BAD_REQUEST,
                    )
            #if the response is false
            else:
                return Response(
                    {"error": {"non_field_errors": [ads_authorization['message']]}},
                    status=HttpStatusCode.BAD_REQUEST,
                )
        if user and not user.is_active:
            return Response(
                AuthCode.USER_INACTIVE,
                status=HttpStatusCode.BAD_REQUEST,
            )
        # implement IP based limiting
        result = Util.rate_limit_validate(self,request)
        if result==True:
            return Response(
                {"error": {"non_field_errors": ["Too many request, Please try after some times"]}},
                status=HttpStatusCode.TOO_MANY_REQUESTS,
                )

        decrypt_passw = self.decrypt_password(password,SECRET_KEY_FOR_PASSWORD)
        user = authenticate(email=user.email, password=decrypt_passw)

        if user is not None and not user.is_deleted:
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            cache.delete(user.email)
            token = get_tokens_for_user(user)
            user_data = UserProfileSerializer(user)
            #splice ads_authentication's response key into this response
            result = ResponseUser(token=token, user=user_data.data, url_permission=True, feature_permission= True)
            if should_call_ads and ads_authorization.get('smtp_error'):
                """ condition falls true 
                if 
                1) ads autentication flag is true 
                2) the response is sending smtp_error key in dic 
                ie: the smtp has failed due to some reason and message should be shown in UI
                """
                #adding wrng parameter which will hold the message of cred expiry
                response = Response(
                    {"data": result.response(msg="Login successful",wrng=ads_authorization["smtp_error"]),},status=HttpStatusCode.OK,)
            else:
                response = Response({"data": result.response(msg="Login successful")},status=HttpStatusCode.OK,)
            ip_address = get_client_ip(request)
            user_name = user.name
            
            UserAuditInfo.objects.create(
                user = user,
                user_name = user_name,
                ip_address = ip_address,
                log_in=timezone.now(),
                log_out = None
            )
    
            # Attach tokens in cookies instead of JSON
            if environment == "dev":
                response.set_cookie(
                    key="access_token",
                    value=token["access"],
                    httponly=True,
                    secure=True,         
                    samesite="None"   
                )
                response.set_cookie(
                    key="refresh_token",
                    value=token["refresh"],
                    httponly=True,
                    secure=True,
                    samesite="None"
                )
            else:
                response.set_cookie(
                    key="access_token",
                    value=token["access"],
                    httponly=True,
                    secure=is_secure,         
                    samesite="Strict"   
                )
                response.set_cookie(
                    key="refresh_token",
                    value=token["refresh"],
                    httponly=True,
                    secure=is_secure,
                    samesite="Strict"
                )

            return response
        else:
            return Response(
                {"error": {"non_field_errors": ["Email or Password is not valid"]}},
                status=HttpStatusCode.BAD_REQUEST,
            )


class UserChangePWView(APIView):
    permission_classes = [IsAuthenticated]

    @change_pwd_doc()
    def post(self, request, format=None):
        serializer = UserChangePWSerializer(
            data=request.data, context={"user": request.user}
        )
        if serializer.is_valid(raise_exception=True):
            return Response(AuthCode.CHANGE_PWD_SUCCESS, status=HttpStatusCode.OK)
        return Response(serializer.errors, status=HttpStatusCode.BAD_REQUEST)


class UserChangePWViewNew(APIView):
    permission_classes = [IsAuthenticated]

    @change_pwd_doc()
    def post(self, request, format=None):
        serializers = UserChangePasswordSerializer(data=request.data, context = request.user)
        if serializers.is_valid():
            return Response(AuthCode.CHANGE_PWD_SUCCESS, status=HttpStatusCode.OK)
        else:
            errors = serializers.errors
            first_field = next(iter(errors))
            prefix = 'Current Password: ' if first_field == 'old_password' else ''
            response_msg = prefix + str(errors[first_field][0])
            return Response({"msg": response_msg}, status=HttpStatusCode.BAD_REQUEST)

class UserChangePWFirstView(APIView):
    @change_pwd_first_doc()
    def post(self, request, format=None):
        password = request.data.get("new_password")
        password2 = request.data.get("new_password2")
        if password != password2:
            return Response(
                AuthCode.PW_DOES_NOT_MATCH, status=HttpStatusCode.BAD_REQUEST
            )
        result, error_or_succes = ChangePWService.change_pw(
            request.data.get("email"), request.data.get("old_password"), password
        )
        if result:
            return Response(error_or_succes, status=HttpStatusCode.OK)
        return Response(error_or_succes.payload, status=HttpStatusCode.BAD_REQUEST)

@authentication_classes([])
@permission_classes([])
class SendPWDResetEmailView(APIView):
    @send_reset_pwd_email_doc()
    def post(self, request, format=None):
        # implement IP based limiting
        result = Util.rate_limit_validate(self,request)
        if result==True:
            return Response(
                {"error": {"non_field_errors": ["Too nmany request, Please try after some times"]}},
                status=HttpStatusCode.TOO_MANY_REQUESTS,
                )
        
        smtp_available = is_smtp_enabled()
        
        if smtp_available:
            serializer = SendPWDResetEmailSerializer(data=request.data, context={'request': request})
            if serializer.is_valid(raise_exception=True):
                return Response(
                    AuthCode.SEND_RESET_PASSWORD_SUCCESS,
                    status=HttpStatusCode.OK,
                )
            return Response(serializer.errors, status=HttpStatusCode.BAD_REQUEST)
        
        elif not smtp_available:
            return Response(
                AuthCode.SMTP_NOT_ENABLED_PASSWORD_RESET,
                status=HttpStatusCode.OK
            )


@authentication_classes([])
@permission_classes([])
class ForgotPasswordView(APIView):

    @forgot_password_doc()
    def post(self, request, uid, token, format=None):
        serializer = ForgotPasswordSerializer(data=request.data, context={'uid': uid, 'token': token})
        if serializer.is_valid():
            return Response(AuthCode.CHANGE_PWD_SUCCESS, status=HttpStatusCode.OK)
        return Response(serializer.errors, status=HttpStatusCode.BAD_REQUEST)


class UserResetPWDView(APIView):
    permission_classes = [IsAuthenticated]

    @require_roles_permission(roles=[UserRole.ADMIN])
    @reset_pwd_doc()
    def post(self, request, uid, format=None):
        _, respone = ResetPasswordService.reset_password(request.user, uid)
        return respone


class LogoutAPIView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @logout_doc()
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        #fetching access token
        access_token_str=request.COOKIES.get('access_token')
        if not refresh_token:
            return Response({"detail": "Refresh token missing"}, status=HttpStatusCode.BAD_REQUEST)

        try:
            # Decode the refresh token to extract user info
            token = RefreshToken(refresh_token)
            user_id = token["user_id"]
        except Exception as e:
            user_id = None  # invalid token or tampered

        serializer = self.serializer_class(data= {"refresh" : refresh_token})
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()
        except Exception as e:
            # Token is already expired or invalid — just clear cookies anyway and blacklist the access token
            logger.exception("the session has expired already so just clear cookies anyway and blacklist the access token")
            response = Response({"detail": "Session already expired"}, status=200)
            if access_token_str:
                access_token=AccessToken(access_token_str)
                access_jti=access_token['jti']
                expired_at=timezone.now()
                logger.info("Blacklisting access token")

                TokenBlacklistAccessToken.objects.create(
                    access_jti=access_jti,
                    refresh_jti=token['jti'],
                    access_token=access_token_str,
                    expired_at=expired_at
                )

                logger.info("Access token blacklisted")
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            return response

        # Clear cache for this user
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            cache.delete(user.email)

        if user_id:
            try:
                user = User.objects.get(id=user_id)
                ip_address = get_client_ip(request)

                last_login_record = (
                    UserAuditInfo.objects.filter(user=user, ip_address=ip_address, log_out__isnull=True)
                    .order_by("-log_in")
                    .first()
                )

                if last_login_record:
                    last_login_record.log_out = timezone.now()
                    last_login_record.save(update_fields=["log_out"])
            except User.DoesNotExist:
                pass  # user might have been deleted


        response = Response(status=HttpStatusCode.NO_CONTENT)
        #black listing access token
        if access_token_str:
            try:
                access_token=AccessToken(access_token_str)
                access_jti=access_token['jti']
                expired_at=timezone.now()

                logger.info("Blacklisting access token")
                
                TokenBlacklistAccessToken.objects.create(
                    access_jti=access_jti,
                    refresh_jti=token['jti'],
                    access_token=access_token_str,
                    expired_at=expired_at
                )

                logger.info("Access token blacklisted")
                

            except Exception as e:
                response.data = {"detail": "Access token could not be blacklisted. Cookies cleared."}
                response.status_code = HttpStatusCode.OK
                logger.exception(f"Access token could not be blacklisted: {e}",exc_info=True)
        # Delete cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")


        return response


class SoftDeleteUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @require_roles_permission(roles=[UserRole.ADMIN])
    @soft_delete_doc()
    def put(self, request, uid, format=None):
        try:
            user = User.objects.get(id=uid)
            user_product_permission = User_Application_Product_Permission.objects.filter(user_id=user.id)
            user_location_permission = User_Application_Location_Permission.objects.filter(user_id=user.id)
            if user.is_deleted:
                raise User.DoesNotExist
            
            #avaiable application permissions for request user
            # The updation the code is due to change in the version of the library as it does not allow to take the first queryset if the queryset is not order by 
            application_ids_product = user_product_permission.values('user_id').distinct().annotate(application_ids=ArrayAgg('application_id', distinct=True)).order_by('user_id').first()
            if application_ids_product:
                application_ids_product = application_ids_product['application_ids']
            else:
                application_ids_product = []

            application_ids_location = user_location_permission.values('user_id').distinct().annotate(application_ids=ArrayAgg('application_id', distinct=True)).order_by('user_id').first()
            if application_ids_location:
                application_ids_location = application_ids_location['application_ids']
            else:
                application_ids_location = []
            
            if not can_update_user(request.user, user,application_ids_product,application_ids_location):
                return Response(NotPermissionCode.NO_PERMISSION, status=HttpStatusCode.BAD_REQUEST)
            
            cache.delete(user.email)
            
            user.is_deleted = True
            prefix = "*"
            suffix = f"*{datetime.now().strftime('%d%m%Y_%H%M%S')}"  
            user.email = f"{prefix}{user.email}{suffix}"
            user.name = f"{prefix}{user.name}{suffix}"
            user.save()

            return Response(AuthCode.USER_DELETE_SUCCESS, status=HttpStatusCode.OK)
        except ValueError as e:
            return Response(AuthCode.INVALID_ID, status=HttpStatusCode.BAD_REQUEST)
        except User.DoesNotExist:
            return Response(
                NotExistCode.USER_NOT_EXIST, status=HttpStatusCode.BAD_REQUEST
            )

class GetAllowedDomain(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            domains = AllowedDomain.objects.values('id','domain')
            return Response({"data": domains}, status=HttpStatusCode.OK)
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=HttpStatusCode.BAD_REQUEST)

class AddDomain(APIView):
    permission_classes = [IsAuthenticated]
    @add_domain_doc()
    def post(self, request):
        try:
            serializer = AddDomainSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(AuthCode.ADD_DOMAIN_SUCCESS, status=HttpStatusCode.CREATED)
            return Response(serializer.errors, status=HttpStatusCode.BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=HttpStatusCode.BAD_REQUEST)


class UpdateDomain(APIView):
    permission_classes = [IsAuthenticated]
    @update_domain_doc()
    def put(self, request):
        try:
            domain_id = request.data.get('id')
            domain = AllowedDomain.objects.filter(id=domain_id).first()
            if not domain.exists():
                return Response(
                    NotExistCode.DOMAIN_NOT_EXIST, status=HttpStatusCode.BAD_REQUEST
                )
            serializer = UpdateDomainSerializer(domain, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(AuthCode.UPDATE_DOMAIN_SUCCESS, status=HttpStatusCode.OK)
            return Response(serializer.errors, status=HttpStatusCode.BAD_REQUEST)
        except AllowedDomain.DoesNotExist:
            return Response(
                NotExistCode.DOMAIN_NOT_EXIST, status=HttpStatusCode.BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=HttpStatusCode.BAD_REQUEST)

class DeleteDomain(APIView):
    permission_classes = [IsAuthenticated]
    @delete_domain_doc()
    def delete(self, request):
        try:
            domain_id = request.data.get('id')
            domain = AllowedDomain.objects.filter(id=domain_id).first()
            if not domain.exists():
                return Response(
                    NotExistCode.DOMAIN_NOT_EXIST, status=HttpStatusCode.BAD_REQUEST
                )
            domain.delete()
            return Response(AuthCode.DELETE_DOMAIN_SUCCESS, status=HttpStatusCode.OK)
        except AllowedDomain.DoesNotExist:
            return Response(
                NotExistCode.DOMAIN_NOT_EXIST, status=HttpStatusCode.BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Unexpected error occurred")
            return Response({"error": str(e)}, status=HttpStatusCode.BAD_REQUEST)

class BulkUploadUsersView(APIView):
    permission_classes = [IsAuthenticated , IsAdminUser]
    def post(self, request, format=None):
        users = request.data.get("userData", [])
        seen_usernames = set()
        seen_emails = set()
        error_info = []
        success_count = 0  
        error_count = 0  
        for user in users:
            user_id = user.get("id")
            serializer = BulkUserValidationSerializer(data=user)
            errors = []
            username = user.get("username")
            email = user.get("email")
            if username in seen_usernames:
                errors.append("Duplicate username in input.")
            else:
                seen_usernames.add(username)

            if email in seen_emails:
                errors.append("Duplicate email in input.")
            else:
                seen_emails.add(email)

            if not errors and not serializer.is_valid():
                errors.extend(serializer.errors.get("__all__", []))
                for key in ['username', 'email', 'pwd']:
                    if key in serializer.errors:
                        errors.extend(serializer.errors[key])

            if errors:
                error_count += 1
                error_info.append({
                    "id": user_id,
                    "err": errors
                })
            else:
                success_count += 1

        return Response({
            "sc": success_count,
            "ec": error_count,
            "inv_ent": error_info
        }, status=status.HTTP_200_OK)

class BulkUsersRegisterView(APIView):
    permission_classes = [IsAuthenticated , IsAdminUser]

    def get_product_permission(self,product_permissions , all_product_permissions):
        product_permission_map = []
        for app in product_permissions:
                app_id = app["application_id"]
                all_app_perms = next((x["permission"] for x in all_product_permissions if x["application_id"] == app_id), [])
                if not all_app_perms:
                    continue
                all_permissions_df = pd.DataFrame(all_app_perms)
                product_permission_df = pd.DataFrame(app["permissions"])
                if product_permission_df.empty:
                    product_permission_df = pd.DataFrame(columns=all_permissions_df.columns)
                merged_df = pd.merge(product_permission_df, all_permissions_df, how="left", on=product_permission_df.columns.tolist(), indicator=True)
                permission_ids = merged_df[merged_df["_merge"] == "both"]["id"].tolist()
                df_nan = merged_df[merged_df.isnull().any(axis=1)].drop(["id", "_merge"], axis=1)
                for _, row in df_nan.iterrows():
                    columns_with_nan = row[~row.isna()].index.tolist()
                    fuzzy_merge = pd.merge(pd.DataFrame(row).T, all_permissions_df, on=columns_with_nan, how='left', indicator=True)
                    permission_ids += fuzzy_merge[fuzzy_merge['_merge'] == 'both']['id'].tolist()
                permission_ids = list(set([int(id) for id in permission_ids]))
                permission_json = {
                    "application_id" : app_id,
                    "permissions" : permission_ids
                }
                product_permission_map.append(permission_json)
        return product_permission_map
        
    def get_location_permission(self , location_permissions ,all_location_permissions):
        location_permission_map = []
        for app in location_permissions:
                app_id = app["application_id"]
                all_app_perms = next((x["permission"] for x in all_location_permissions if x["application_id"] == app_id), [])
                if not all_app_perms:
                    continue
                all_permissions_df = pd.DataFrame(all_app_perms)
                location_permission_df = pd.DataFrame(app["permissions"])
                if location_permission_df.empty:
                    location_permission_df = pd.DataFrame(columns=all_permissions_df.columns)
                merged_df = pd.merge(location_permission_df, all_permissions_df, how="left", on=location_permission_df.columns.tolist(), indicator=True)
                permission_ids = merged_df[merged_df["_merge"] == "both"]["id"].tolist()
                df_nan = merged_df[merged_df.isnull().any(axis=1)].drop(["id", "_merge"], axis=1)
                for _, row in df_nan.iterrows():
                    cols = row[~row.isna()].index.tolist()
                    fuzzy_merge = pd.merge(pd.DataFrame(row).T, all_permissions_df, on=cols, how='left', indicator=True)
                    permission_ids += fuzzy_merge[fuzzy_merge['_merge'] == 'both']['id'].tolist()
                permission_ids = list(set([int(id) for id in permission_ids]))
                permission_json = {
                    "application_id" : app_id,
                    "permissions" : permission_ids
                }
                location_permission_map.append(permission_json)
        return location_permission_map

    def post(self, request, format=None):
        logger.info("Started bulk user registration process")

        users = request.data.get("users", [])
        permissions = request.data.get("permissions", {})
        roles = request.data.get("roles", {})

        # Check SMTP
        is_smtp = is_smtp_enabled()
        warning_msg = ""
        if not is_smtp:
            warning_msg = (
                "Activation email was not sent as email service is unavailable. "
                "Password reset will remain unavailable until the email service is configured."
            )
            logger.warning(warning_msg)

        try:
            combined_permissions = ALL_PERMISSIONS.get_combined_permissions(permission_type="both")
            logger.info("Fetched combined permissions")

            all_product_permissions = [
            {"application_id": permission["application_id"], "permission": permission.get("product_permission", [])}
            for permission in combined_permissions
            ]
            all_location_permissions = [
                {"application_id": permission["application_id"], "permission": permission.get("location_permission", [])}
                for permission in combined_permissions
            ]

            # Build Permission Maps
            product_permission_id_list_map = {}
            location_permission_id_list_map = {}

            for perm_id, perm in permissions.items():
                product_permission_id_list_map[perm_id] = self.get_product_permission(
                    perm.get("product_permissions", []), all_product_permissions
                )
                location_permission_id_list_map[perm_id] = self.get_location_permission(
                    perm.get("location_permissions", []), all_location_permissions
                )

            all_roles = Roles.objects.in_bulk(field_name="id")
            bulk_email_data = []

            with transaction.atomic():
                # Create Users
                user_objs = []
                user_payload_map = {}
                for user in users:
                    role_ids = roles.get(str(user["rid"]), {}).get("roles", [])
                    role_objs = [all_roles[rid] for rid in role_ids if rid in all_roles]
                    
                    admin_roles = {UserRole.ADMIN, UserRole.MTOADMIN, UserRole.SUPERADMIN}
                    is_admin = any(role.code in admin_roles for role in role_objs)

                    user_obj = User(
                        email=user["email"],
                        name=user["name"],
                        password=make_password(user["pwd"]),
                        tc=user["tc"],
                        is_admin=is_admin,
                    )
                    user_objs.append(user_obj)
                    user_payload_map[user["email"]] = user

                created_users = User.objects.bulk_create(user_objs, batch_size=500)
                logger.info("bulk users saved in db")

                # Bulk Assign Permissions
                prod_perms, loc_perms, role_map = [], [], []
                
                for user in created_users:
                    udata = user_payload_map[user.email]
                    perm_id = str(udata["perm_id"])
                    rid = str(udata["rid"])

                    if is_smtp:
                        email_data = mail_create_user(user.email, user.name, udata.get("pwd"))
                        bulk_email_data.append((email_data, udata.get("id")))

                    for app in product_permission_id_list_map.get(perm_id, []):
                        for pid in app["permissions"]:
                            prod_perms.append(
                                User_Application_Product_Permission(
                                    user_id=user.id,
                                    application_id=app["application_id"],
                                    productfilter_id=pid,
                                )
                            )

                    for app in location_permission_id_list_map.get(perm_id, []):
                        for lid in app["permissions"]:
                            loc_perms.append(
                                User_Application_Location_Permission(
                                    user_id=user.id,
                                    application_id=app["application_id"],
                                    locationfilter_id=lid,
                                )
                            )

                    for role_id in roles.get(rid, {}).get("roles", []):
                        if role_id in all_roles:
                            role_map.append(
                                User.role_id.through(user_id=user.id, roles_id=role_id)
                            )

                # --- Bulk Insert ---
                if prod_perms:
                    User_Application_Product_Permission.objects.bulk_create(prod_perms, batch_size=1000)
                if loc_perms:
                    User_Application_Location_Permission.objects.bulk_create(loc_perms, batch_size=1000)   
                if role_map:
                    User.role_id.through.objects.bulk_create(role_map, batch_size=1000)
                    

        except Exception as e:
            logger.exception("Bulk user registration failed")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        if is_smtp and bulk_email_data:
            try:
                email_data_list = [item[0] for item in bulk_email_data]
                Util.send_html_email_bulk(email_data_list)
            except Exception as mail_err:
                logger.info(mail_err)

        response_data = {"status": "success", "message": "Bulk users registered successfully"}
        if warning_msg:
            response_data["warning"] = warning_msg

        logger.info("Bulk user registration process completed")
        return Response(response_data, status=status.HTTP_200_OK)


class LoginAuditView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        users = User.objects.filter(last_login__isnull = False).values("name", "last_login", "is_active")
        result = []
        current_date = timezone.now()

        for user in users:
            last_login = user["last_login"]
            if last_login:
                delta_days = (current_date.date() - last_login.date()).days
                last_login_str = last_login.strftime("%m-%d-%Y")
            else:
                delta_days = None
                last_login_str = None  

            result.append({
                "username": user["name"],
                "last_login": last_login_str,
                "days_since_last_login": delta_days,
                "status": "Active" if user["is_active"] else "Inactive"
            })

        return Response({"data": result})

