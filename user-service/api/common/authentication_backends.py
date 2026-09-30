from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class CustomModelBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        # Check if the provided username is an email
        if '@' in email:
            kwargs = {'email': email}
        else:
            kwargs = {'name': email}

        try:
            user = UserModel.objects.get(**kwargs)
        except UserModel.DoesNotExist:
            return None

        # Verify the password
        if user.check_password(password) and user.is_active:
            return user

        return None
