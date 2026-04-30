from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile', verbose_name=_("حساب العميل"))
    phone = models.CharField(max_length=15, verbose_name=_("رقم الموبايل"))

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Driver(models.Model):
    APPROVAL_PENDING = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'
    APPROVAL_CHOICES = [
        (APPROVAL_PENDING, _('قيد المراجعة')),
        (APPROVAL_APPROVED, _('موافق عليه')),
        (APPROVAL_REJECTED, _('مرفوض')),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_("حساب السائق"))
    phone = models.CharField(max_length=15, verbose_name=_("رقم الموبايل"))
    car_model = models.CharField(max_length=100, verbose_name=_("موديل السيارة"), default='')
    car_color = models.CharField(max_length=50, verbose_name=_("لون السيارة"), default='')
    car_year = models.CharField(max_length=4, verbose_name=_("سنة الصنع"), default='')
    is_active = models.BooleanField(default=False, verbose_name=_("متصل حالياً"))

    lat = models.FloatField(default=31.95, verbose_name=_("خط العرض"))
    lon = models.FloatField(default=35.91, verbose_name=_("خط الطول"))

    id_card_front = models.ImageField(upload_to='drivers/ids/', null=True, blank=True, verbose_name=_("صورة الهوية - الوجه"))
    id_card_back = models.ImageField(upload_to='drivers/ids/', null=True, blank=True, verbose_name=_("صورة الهوية - الظهر"))
    license_image = models.ImageField(upload_to='drivers/licenses/', null=True, blank=True, verbose_name=_("رخصة القيادة"))
    face_photo = models.ImageField(upload_to='drivers/faces/', null=True, blank=True, verbose_name=_("صورة الوجه"))
    vehicle_license = models.ImageField(upload_to='drivers/vehicle_licenses/', null=True, blank=True, verbose_name=_("رخصة السيارة"))

    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default=APPROVAL_PENDING, verbose_name=_("حالة الموافقة"))

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def average_rating(self):
        ratings = Rating.objects.filter(order__driver_assigned=self)
        if ratings.exists():
            return round(sum(r.stars for r in ratings) / ratings.count(), 1)
        return 0


class ServiceOrder(models.Model):
    SERVICE_BODY_WASH = 'body_wash'
    SERVICE_FULL_WASH = 'full_wash'
    SERVICE_DRY_CLEAN = 'dry_clean'
    SERVICE_OIL_CHANGE = 'oil_change'
    SERVICE_OIL_FILTER = 'oil_filter'
    SERVICE_CHOICES = [
        (SERVICE_BODY_WASH, _('غسيل خارجي')),
        (SERVICE_FULL_WASH, _('غسيل كامل')),
        (SERVICE_DRY_CLEAN, _('دراي كلين')),
        (SERVICE_OIL_CHANGE, _('غيّار زيت')),
        (SERVICE_OIL_FILTER, _('غيّار زيت وفلتر')),
    ]
    SERVICE_PRICES = {
        SERVICE_BODY_WASH: 5,
        SERVICE_FULL_WASH: 10,
        SERVICE_DRY_CLEAN: 15,
        SERVICE_OIL_CHANGE: 12,
        SERVICE_OIL_FILTER: 18,
    }

    PAYMENT_CASH = 'cash'
    PAYMENT_QLIQ = 'qliq'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, _('نقدي')),
        (PAYMENT_QLIQ, _('QLIQ')),
    ]

    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_ARRIVED = 'arrived'
    STATUS_PICKING_UP = 'picking_up'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, _('قيد الانتظار')),
        (STATUS_ACCEPTED, _('تم القبول - السائق في الطريق')),
        (STATUS_ARRIVED, _('السائق وصل')),
        (STATUS_PICKING_UP, _('جاري استلام السيارة')),
        (STATUS_IN_PROGRESS, _('جاري تنفيذ الخدمة')),
        (STATUS_FINISHED, _('اكتملت الخدمة')),
        (STATUS_CANCELLED, _('ملغي')),
        (STATUS_REJECTED, _('مرفوض')),
    ]

    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name=_("العميل"))
    customer_name = models.CharField(max_length=100, verbose_name=_("اسم العميل"))
    car_model = models.CharField(max_length=100, verbose_name=_("نوع السيارة"))
    phone_number = models.CharField(max_length=20, verbose_name=_("رقم الموبايل"))
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES, default=SERVICE_BODY_WASH, verbose_name=_("نوع الخدمة"))
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default=PAYMENT_CASH, verbose_name=_("طريقة الدفع"))
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name=_("وقت الموعد"))
    area = models.CharField(max_length=100, default='عمان', null=True, blank=True, verbose_name=_("المنطقة"))
    appointment_time = models.DateTimeField(auto_now_add=True, verbose_name=_("وقت الطلب"))
    customer_lat = models.FloatField(default=31.95, verbose_name=_("خط عرض العميل"))
    customer_lon = models.FloatField(default=35.91, verbose_name=_("خط طول العميل"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name=_("حالة الطلب"))
    driver_assigned = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("السائق المسؤول"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"))

    def __str__(self):
        return f"طلب {self.customer_name} - {self.get_service_type_display()}"

    def get_price(self):
        return self.SERVICE_PRICES.get(self.service_type, 0)


class RejectionLog(models.Model):
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='rejections', verbose_name=_("الطلب"))
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, verbose_name=_("السائق"))
    reason = models.TextField(verbose_name=_("سبب الرفض"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("وقت الرفض"))

    def __str__(self):
        return f"رفض - {self.order} - {self.driver}"


class Rating(models.Model):
    order = models.OneToOneField(ServiceOrder, on_delete=models.CASCADE, related_name='rating', verbose_name=_("الطلب"))
    stars = models.IntegerField(verbose_name=_("التقييم (1-5)"))
    comment = models.TextField(blank=True, default='', verbose_name=_("تعليق"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.stars} نجوم - {self.order}"
