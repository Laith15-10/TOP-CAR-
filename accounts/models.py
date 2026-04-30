from django.db import models
from django.contrib.auth.models import User

# 1. سجل معلومات السائقين (الموظفين)
class Driver(models.Model):
    # ربط السائق بحساب مستخدم
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="حساب السائق")
    phone = models.CharField(max_length=15, verbose_name="رقم الموبايل")
    car_info = models.CharField(max_length=100, verbose_name="معلومات سيارة السائق")
    is_active = models.BooleanField(default=True, verbose_name="هل السائق يعمل حالياً؟")
    
    # الإحداثيات (للتتبع على الخريطة)
    lat = models.FloatField(default=31.95, verbose_name="خط العرض") 
    lon = models.FloatField(default=35.91, verbose_name="خط الطول")
    
    # حقول التوثيق (الصور)
    id_card_front = models.ImageField(upload_to='drivers/ids/', null=True, blank=True, verbose_name="صورة الهوية - الوجه")
    id_card_back = models.ImageField(upload_to='drivers/ids/', null=True, blank=True, verbose_name="صورة الهوية - الظهر")
    license_image = models.ImageField(upload_to='drivers/licenses/', null=True, blank=True, verbose_name="رخة القيادة")
    is_verified = models.BooleanField(default=False, verbose_name="تم التحقق من الحساب")

    def __str__(self):
        return self.user.username


# 2. سجل طلبات الخدمات (الزبائن)
class ServiceOrder(models.Model):
    customer_name = models.CharField(max_length=100, verbose_name="اسم العميل")
    car_model = models.CharField(max_length=100, verbose_name="نوع السيارة")
    phone_number = models.CharField(max_length=20, verbose_name="رقم الموبايل")
    service_type = models.CharField(max_length=100, verbose_name="نوع الخدمة")
    area = models.CharField(max_length=100, default="عمان", null=True, blank=True, verbose_name="المنطقة")
    
    # تعديل جوهري: جعل الوقت يسجل تلقائياً لمنع خطأ IntegrityError
    appointment_time = models.DateTimeField(auto_now_add=True, verbose_name="وقت الطلب")
    
    # إحداثيات العميل
    customer_lat = models.FloatField(default=31.95)
    customer_lon = models.FloatField(default=35.91)

    # حالة الطلب
    STATUS_CHOICES = (
        ('pending', 'قيد الانتظار'),
        ('accepted', 'تم القبول - السائق في الطريق'),
        ('in_progress', 'جاري العمل على السيارة'),
        ('completed', 'تم التسليم بنجاح'),
        ('cancelled', 'ملغي'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="حالة الطلب")
    
    # ربط الطلب بسائق
    driver_assigned = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="السائق المسؤول")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    def __str__(self):
        return f"طلب {self.customer_name} - {self.service_type}"
