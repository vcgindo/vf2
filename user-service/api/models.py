from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.db.models.indexes import Index
import os
from django.utils import timezone


# Custom User manager
class UserManager(BaseUserManager):
    def create_user(self, email, name, tc, password=None, password2=None, is_admin=False):
        """
        Creates and saves a User with the given email, name, tc, password, password2
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(email=self.normalize_email(email), name=name, tc=tc, is_admin=is_admin)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, tc, password=None):
        """
        Creates and saves a superuser with the email, name, tc, password.
        """
        user = self.create_user(email, password=password, name=name, tc=tc)
        user.is_admin = True
        user.save(using=self._db)
        return user
    
    #created custom make random password as the original one is deprecated
    @classmethod
    def make_random_password(
        cls, length=12, allowed_chars="abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789@_!#$%^&*()<>?/|}{~:"
    ):
        """
        Generates a random password of given length using allowed characters.
        using secrets module cause it uses os entropy and is non predictible
        """
        import secrets as secret_key
        return ''.join(secret_key.choice(allowed_chars) for _ in range(length))
        
class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    objects = SoftDeleteManager()
    # all_objects = models.Manager()

    def soft_delete(self):
        self.is_deleted = True
        self.save()

    def restore(self):
        self.is_deleted = False
        self.save()

    class Meta:
        abstract = True

class UserTheme:
    NOIRFUSION = 'NOIRFUSION'
    PUREELEGANCE = 'PUREELEGANCE'
    CHARCOALCHIC = 'CHARCOALCHIC'
    REGALBLAZE = 'REGALBLAZE'

    @classmethod
    def choices_for_model(cls):
        return [
            (cls.NOIRFUSION, 'NoirFusion'),
            (cls.PUREELEGANCE, 'PureElegance'),
            (cls.CHARCOALCHIC, 'CharcoalChic'),
            (cls.REGALBLAZE, 'RegalBlaze')
        ]
    
    @classmethod
    def get_choices(cls):
        return [
            cls.NOIRFUSION,
            cls.PUREELEGANCE,
            cls.CHARCOALCHIC,
            cls.REGALBLAZE
        ]
# Custom User
class User(AbstractBaseUser, SoftDeleteModel):
    email = models.EmailField(
        verbose_name="Email",
        max_length=255,
        unique=True,
    )
    name = models.CharField(max_length=200, unique=True)
    tc = models.BooleanField()
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_changed = models.BooleanField(default=False)
    theme_ui = models.CharField(
        max_length=255, choices=UserTheme.choices_for_model(),db_column='theme_ui', default=UserTheme.NOIRFUSION
    )
    all_objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "tc"]

    class Meta:
        db_table = "USER"

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return self.is_admin

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin

    def has_role(self, roles):
        """
        Returns True if the user has one role in the given roles.
        """
        if self.is_admin:
            return True
        return False

    def has_functions_permission(self, functions):
        """
        Returns True if the user has one function in the given functions.
        """
        if self.is_admin:
            return True
        user_functions = Permission.objects.filter(
            role_id__user_id=self.pk
        ).values_list("code")
        for function in user_functions:
            if function.code in functions:
                return True
        return False

    def has_locations_permission(self, locations):
        """
        Returns True if the user has one location in the given locations.
        """
        if self.is_admin:
            return True
        user_locations = LocationsFilter.objects.filter(
            user__user_id=self.pk
        ).values_list("location_type", "location_region", "location_cluster")
        for location in user_locations:
            if location[0] in locations:
                return True


class Roles(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    application_id = models.IntegerField(default=1)
    is_visible = models.BooleanField(default=True)
    user_id = models.ManyToManyField(
        "api.User", related_name="role_id", blank=True, db_table="USER_ROLE"
    )

    class Meta:
        db_table = "ROLE"


class Permission(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    url = models.CharField(max_length=255,unique=True)

    role_id = models.ManyToManyField(
        "api.Roles", related_name="permission_id", blank=True, db_table="ROLE_FUNCTION"
    )

    class Meta:
        db_table = "FUNCTION"
    
class ApplicationMaster(models.Model):
    application_id = models.IntegerField()
    application_name = models.CharField(max_length=50)

    class Meta:
        db_table = "APPLICATION_MASTER"

class User_Application_Product_Permission(models.Model):
    user_id = models.IntegerField()
    application_id = models.IntegerField()
    productfilter_id = models.IntegerField()
    
    class Meta:
        db_table = "USER_APPLICATION_PRODUCT_PERMISSION"
        unique_together = ["productfilter_id", "user_id", "application_id"]

class User_Application_Location_Permission(models.Model):
    user_id = models.IntegerField()
    application_id = models.IntegerField()
    locationfilter_id = models.IntegerField()
    
    class Meta:
        db_table = "USER_APPLICATION_LOCATION_PERMISSION"
        unique_together = ["locationfilter_id", "user_id", "application_id"]


class User_Application_Data_Permission(models.Model):
    user_id = models.IntegerField()
    application_id = models.IntegerField()
    datafilter_id = models.IntegerField()
    
    class Meta:
        db_table = "USER_APPLICATION_DATA_PERMISSION"
        unique_together = ["datafilter_id", "user_id", "application_id"]


class RateLimitTable(models.Model):
    ipaddress = models.CharField(max_length=50)
    token_used = models.IntegerField(default=0)
    last_req = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "RATE_LIMIT_TABLE"
        

class SystemConfig(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.CharField(max_length=255)


    class Meta:
        db_table = "SYSTEM_CONFIGURATION"
        indexes = [
            Index(fields=["key"])
        ]

class ForgotPasswordToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id")
    token = models.CharField(max_length=255)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "FORGOT_PASSWORD_TOKEN"
        indexes = [
            Index(fields=["user", "token"])
        ]

class IssueReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_report")
    component = models.CharField(max_length=255)
    _type = models.CharField(max_length=255, db_column='type')
    description = models.TextField(blank=True, null=True)
    attachment = models.TextField(blank=True, null=True)
    report_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ISSUE_REPORT"

class AllowedDomain(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sitename = models.CharField(max_length=255, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ALLOWED_DOMAIN"

class FeatureMaster(models.Model):
    feature = models.CharField(max_length=255, unique=True)
    page = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    
    role_id = models.ManyToManyField(
        "api.Roles", related_name="feature_id", blank=True, db_table="ROLE_FEATURE"
    )

    class Meta:
        db_table = "FEATURE_MASTER"
    

class UserserviceConfig(models.Model):
    flag = models.CharField(max_length=50, primary_key=True)
    value = models.CharField(max_length=500, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    isvisible = models.BooleanField(default=False)

    class Meta:
        db_table = 'USERSERVICE_CONFIG'  
 
    def __str__(self):
        return f'{self.flag}'
    

class ADS_Config(models.Model):
    flag = models.CharField(max_length=50, primary_key=True)
    value = models.CharField(max_length=2100, null=True, blank=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    class Meta:
        db_table='ADS_CONFIG'
    def __str__(self):
        return f'{self.flag}'



class AlertEmailCCDetails(models.Model):
    event_key=models.CharField(max_length=255, unique=True)
    email_to=models.CharField(max_length=255,null=True,blank=True)
    cc= models.TextField(null=True, blank=True)
    event_type=models.CharField(max_length=255)
    subject=models.CharField(max_length=350)
    is_active=models.BooleanField(default=True)
    class Meta:
        db_table='AlertEmailCCDetails'

    def __str__(self):
        return f'{self.email_to}'

class UserAuditInfo(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    user_name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    log_in = models.DateTimeField(null=True, blank=True)
    log_out = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'USER_AUDIT_INFO'




class TokenBlacklistAccessToken(models.Model):
    access_jti=models.CharField(max_length=255, unique=True)
    refresh_jti=models.CharField(max_length=255)
    access_token=models.TextField(null=True,blank=True)
    expired_at=models.DateTimeField(null=True,blank=True)

    class Meta:
        db_table='token_blacklist_accesstoken'