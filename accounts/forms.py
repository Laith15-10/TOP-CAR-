from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import Driver, CustomerProfile, ServiceOrder


class CustomerSignupForm(UserCreationForm):
    first_name = forms.CharField(label=_('الاسم الكامل'), max_length=100)
    email = forms.EmailField(label=_('البريد الإلكتروني'))
    phone = forms.CharField(label=_('رقم الموبايل'), max_length=15)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'email', 'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            CustomerProfile.objects.create(user=user, phone=self.cleaned_data['phone'])
        return user


class DriverSignupForm(UserCreationForm):
    first_name = forms.CharField(label=_('الاسم الكامل'), max_length=100)
    email = forms.EmailField(label=_('البريد الإلكتروني'))
    phone = forms.CharField(label=_('رقم الموبايل'), max_length=15)
    car_model = forms.CharField(label=_('موديل السيارة'), max_length=100)
    car_color = forms.CharField(label=_('لون السيارة'), max_length=50)
    car_year = forms.CharField(label=_('سنة الصنع'), max_length=4)
    id_card_front = forms.ImageField(label=_('صورة الهوية - الوجه'))
    id_card_back = forms.ImageField(label=_('صورة الهوية - الظهر'))
    license_image = forms.ImageField(label=_('رخصة القيادة'))
    face_photo = forms.ImageField(label=_('صورة الوجه'))
    vehicle_license = forms.ImageField(label=_('رخصة السيارة'))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'email', 'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Driver.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                car_model=self.cleaned_data['car_model'],
                car_color=self.cleaned_data['car_color'],
                car_year=self.cleaned_data['car_year'],
                id_card_front=self.cleaned_data['id_card_front'],
                id_card_back=self.cleaned_data['id_card_back'],
                license_image=self.cleaned_data['license_image'],
                face_photo=self.cleaned_data['face_photo'],
                vehicle_license=self.cleaned_data['vehicle_license'],
                approval_status='pending',
            )
        return user


class BookingForm(forms.ModelForm):
    class Meta:
        model = ServiceOrder
        fields = ['customer_name', 'car_model', 'phone_number', 'service_type', 'payment_method', 'scheduled_at', 'customer_lat', 'customer_lon']
        widgets = {
            'scheduled_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'customer_lat': forms.HiddenInput(),
            'customer_lon': forms.HiddenInput(),
        }
        labels = {
            'customer_name': _('اسمك الكريم'),
            'car_model': _('نوع السيارة وموديلها'),
            'phone_number': _('رقم الموبايل'),
            'service_type': _('نوع الخدمة'),
            'payment_method': _('طريقة الدفع'),
            'scheduled_at': _('وقت الموعد'),
        }


class RejectionForm(forms.Form):
    reason = forms.CharField(
        label=_('سبب الرفض'),
        widget=forms.Textarea(attrs={'rows': 3, 'required': True}),
    )


class RatingForm(forms.Form):
    stars = forms.IntegerField(
        label=_('التقييم'),
        min_value=1,
        max_value=5,
        widget=forms.HiddenInput(),
    )
    comment = forms.CharField(
        label=_('تعليق (اختياري)'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
