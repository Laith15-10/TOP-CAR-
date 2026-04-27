from django.contrib import admin
from .models import ServiceOrder, Driver

# تسجيل الطلبات لرؤيتها في لوحة الإدارة
@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'service_type', 'area', 'status', 'driver_assigned')
    list_editable = ('status', 'driver_assigned')
    list_filter = ('status', 'area')

# تسجيل السائقين لرؤيتهم في لوحة الإدارة
admin.site.register(Driver)