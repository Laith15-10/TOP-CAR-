from django.db import models
from django.contrib.auth.models import User

# 1. سجل معلومات السائقين (الموظفين عندك)
class Driver(models.Model):
    # ربط السائق بحساب مستخدم (اسم مستخدم وكلمة سر)
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="حساب السائق")
    phone = models.CharField(max_length=15, verbose_name="رقم الموبايل")
    car_info = models.CharField(max_length=100, verbose_name="معلومات سيارة السائق")
    is_active = models.BooleanField(default=True, verbose_name="هل السائق يعمل حالياً؟")
    # في كلاس Driver أضف:
    lat = models.FloatField(default=31.95, verbose_name="خط العرض") # إحداثيات عمان الافتراضية
    lon = models.FloatField(default=35.91, verbose_name="خط الطول")


    def __str__(self):
        return self.user.username


# 2. سجل طلبات الخدمات (الزبائن)
class ServiceOrder(models.Model):
    # معلومات العميل والسيارة
    customer_name = models.CharField(max_length=100, verbose_name="اسم العميل")
    car_model = models.CharField(max_length=100, verbose_name="نوع السيارة")
    phone_number = models.CharField(max_length=20, verbose_name="رقم الموبايل")
    service_type = models.CharField(max_length=100, verbose_name="نوع الخدمة")
    area = models.CharField(max_length=100, default="عمان", null=True, blank=True, verbose_name="المنطقة")
    appointment_time = models.DateTimeField(verbose_name="وقت الاستلام")
# في كلاس ServiceOrder أضف:
    customer_lat = models.FloatField(default=31.95)
    customer_lon = models.FloatField(default=35.91)


    # حالة الطلب (نظام التتبع)
    STATUS_CHOICES = (
        ('pending', 'قيد الانتظار'),
        ('accepted', 'تم القبول - السائق في الطريق'),
        ('in_progress', 'جاري العمل على السيارة'),
        ('completed', 'تم التسليم بنجاح'),
        ('cancelled', 'ملغي'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="حالة الطلب")
    
    # ربط الطلب بسائق معين (من هو الموظف المسؤول عن هذه السيارة؟)
    driver_assigned = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="السائق المسؤول")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الطلب")

    def __str__(self):
        return f"طلب {self.customer_name} - {self.service_type}"