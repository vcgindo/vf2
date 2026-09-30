from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
import re

class UppercaseValidator:
    """
    Validate that the password is not contain upper character.
    """
    def validate(self, password, user=None):
        if not bool(re.search(r'[A-Z]', password)):
            raise ValidationError(
                _("Your password must be contain upper character."),
                code="password_not_contain_upper_char",)
            

    def get_help_text(self):
        return _("Your password must be contain upper character.")

class SpecialCharactersValidator:
    """
    Validate that the password is not contain special character.
    """

    def validate(self, password, user=None):
        regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        if not regex.search(password):
            raise ValidationError(
                _("This password is not contain special character."),
                code="password_entirely_numeric",
            )

    def get_help_text(self):
        return _("Your password must be contain special character.")