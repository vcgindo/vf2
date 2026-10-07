from django.urls import path
from api.view import *
from api.view.captcha_policy import FixtureCaptchaPolicyView
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

app_name = "api_user"

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("captcha-policy/", FixtureCaptchaPolicyView.as_view(), name="captcha-policy"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("role/", RolesView.as_view(), name="roles"),
    path("all-role/", GetAllRolesView.as_view(), name="all roles"),
    path("change-pwd/", UserChangePWViewNew.as_view(), name="change-pwd"),
    path("change-pwd-first/", UserChangePWFirstView.as_view(), name="change-pwd-first"),
    path("send-email-reset-pwd/", SendPWDResetEmailView.as_view(), name="send-email-reset-pwd"),
    path("forgot-password/<str:uid>/<str:token>", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-pwd/<int:uid>", UserResetPWDView.as_view(), name="reset-pwd"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token_refresh"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("all-users/", GetAllUsersAPIView.as_view(), name="all-users"),
    path("soft-delete/<int:uid>", SoftDeleteUserAPIView.as_view(), name="soft-delete"),
    path("all-permissions/", GetAllPermissionsAPIView.as_view(), name="all-permissions"),
    path('edit-user', EditUserView.as_view(), name='edit-user'),
    path('change-active', ChangeActiveView.as_view(), name='change-active'),
    path('change-theme', UserChangeThemeAPIView.as_view(), name='change-theme'),
    path('get-rsa', RSAGenerateView.as_view(), name='get-rsa'),
    path('issue-report/', IssueReportView.as_view(), name='issue-report'),
    path('get-all-applications/',GetAllApplications.as_view(), name='get-all-applications'),
    path('get-all-functions/',GetAllFunctions.as_view(), name='get-all-functions'),
    path('add-function/',AddFunction.as_view(), name='add-function'),
    path('delete-function/<int:id>/', DeleteFunction.as_view(), name='delete-function'),
    path('add-role/',AddRole.as_view(), name='add-role'),
    path('delete-role/<int:id>/',DeleteRole.as_view(), name='delete-role'),
    path('edit-role/',EditRole.as_view(), name='edit-role'),
    path('get-headers-data/',GetHeaderForAllApplicationView.as_view(), name='get-headers-data'),
    path('add-domain/',AddDomain.as_view(), name='add-domain'),
    path('get-all-domain/',GetAllowedDomain.as_view(), name='get-all-domain'),
    path('update-domain/',UpdateDomain.as_view(), name='update-domain'),
    path('delete-domain/',DeleteDomain.as_view(), name='delete-domain'),
    path('bulkUploadUsers/', BulkUploadUsersView.as_view(), name='bulkUploadUser'),
    path('get-user-permissions/', GetUserPermissionsView.as_view(), name='get-user-product-location-permissions'),
    path('get-approver-names/',GetApproverNamesView.as_view(), name='get-approver-names'),
    path('bulkUsersRegister/', BulkUsersRegisterView.as_view(), name='bulkUploadUser'),
    path('login-audit-report/', LoginAuditView.as_view(), name='login-audit-report')
]
