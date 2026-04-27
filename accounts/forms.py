from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django.utils.translation import gettext_lazy as _

class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'phone_number', 'user_type')
        labels = {
            'username': _('اسم المستخدم'),
            'phone_number': _('رقم الهاتف'),
            'user_type': _('نوع الحساب'),
        }