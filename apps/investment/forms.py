from decimal import Decimal

import account.forms
from django import forms
from django.utils.translation import ugettext_lazy as _
from django_otp import match_token
from django.conf import settings
from passwords.fields import PasswordField

from apps.investment.models import Graduations
from exchange_core.models import Users


class PaymentsForm(forms.Form):
    error_css_class = 'error'

    type = forms.ChoiceField(
        label=_('Payment Type'),
        widget=forms.Select(attrs={'autofocus': True, 'class': 'form-control'}),
        choices=(('plan', _("User plan"),), ('course', _("Course"),))
    )
    code = forms.CharField(
        label=_("Payment Code"),
        max_length=10,
        widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control', 'placeholder': _('Payment Code')}),
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

    def clean_code(self):
        return self.cleaned_data['code']


class Code2FAForm(forms.Form):
    code = forms.CharField(
        label=_('2FA Code'),
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('2FA Code')})
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data['code']

        if not bool(match_token(self.request.user, code)):
            raise forms.ValidationError(_("The 2FA code is invalid"))

        return code


class SignupForm(account.forms.SignupForm):
    advisor = forms.ModelChoiceField(empty_label=_("-- Select your investment advisor --"), queryset=Users.objects.filter(is_active=True, graduations__type=Graduations._advisor), required=False)
    first_name = forms.CharField(label=_("First name"))
    last_name = forms.CharField(label=_("Last name"))
    confirm_email = forms.EmailField(label=_("Confirm e-mail"))
    password = PasswordField(label=_("Password"), strip=settings.ACCOUNT_PASSWORD_STRIP)
    terms = forms.BooleanField(label=_("I have read and agree to the terms of use: <a href=\"https://www.xfactor.cash/terms.html\" target=\"blank\">open terms</a>"))
    
    field_order = ['advisor', 'first_name', 'last_name', 'username', 'email', 'confirm_email', 'password', 'password_confirm', 'term']

    # Valida o campo de confirmar e-mail
    def clean_confirm_email(self):
        email = self.cleaned_data.get('email')
        confirm_email = self.cleaned_data.get('confirm_email')

        if not email == confirm_email:
            raise forms.ValidationError(_("The e-mails aren't equal"))

        return confirm_email


class CourseSubscriptionForm(forms.Form):
    code = forms.CharField(
        label=_('2FA Code'),
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('2FA Code')})
    )
    password = forms.CharField(
        label=_("Password"), 
        widget=forms.PasswordInput
    )
    terms = forms.BooleanField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError(_("Wrong password informed"))
        return password

    def clean_code(self):
        code = self.cleaned_data['code']
        if not bool(match_token(self.user, code)):
            raise forms.ValidationError(_("The 2FA code is invalid"))
        return code
