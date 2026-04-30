from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages as admin_messages
from .models import Driver, ServiceOrder, RejectionLog, Rating, CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    search_fields = ('user__username', 'user__first_name', 'phone')


@admin.action(description=_('الموافقة على السائقين المحددين'))
def approve_drivers(modeladmin, request, queryset):
    updated = queryset.update(approval_status='approved')
    modeladmin.message_user(request, f'تمت الموافقة على {updated} سائق.')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'car_model', 'car_color', 'car_year', 'approval_status', 'is_active', 'average_rating_display', 'id_front_preview')
    list_filter = ('approval_status', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'phone')
    actions = [approve_drivers, 'reject_with_reason_action']
    readonly_fields = ('id_front_preview', 'id_back_preview', 'license_preview', 'face_preview', 'vehicle_preview')

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('reject-with-reason/', self.admin_site.admin_view(self.reject_with_reason_view), name='driver-reject-reason'),
        ]
        return custom + urls

    @admin.action(description=_('رفض السائقين المحددين مع تسجيل السبب'))
    def reject_with_reason_action(self, request, queryset):
        selected_ids = ','.join(str(d.pk) for d in queryset)
        return redirect(f'reject-with-reason/?ids={selected_ids}')

    def reject_with_reason_view(self, request):
        from django.contrib.admin.sites import site
        ids_param = request.GET.get('ids', '') or request.POST.get('ids', '')
        ids = [int(i) for i in ids_param.split(',') if i.strip().isdigit()]
        drivers = Driver.objects.filter(pk__in=ids)

        if request.method == 'POST':
            reason = request.POST.get('reason', '').strip()
            if not reason:
                admin_messages.error(request, 'يرجى إدخال سبب الرفض.')
            else:
                for driver in drivers:
                    driver.approval_status = 'rejected'
                    driver.save(update_fields=['approval_status'])
                    # Log rejection for each pending/active order if any, else create a standalone log
                    orders = ServiceOrder.objects.filter(driver_assigned=driver, status__in=['pending', 'accepted', 'arrived', 'picking_up', 'in_progress'])
                    if orders.exists():
                        for order in orders:
                            RejectionLog.objects.create(order=order, driver=driver, reason=f'[Admin Rejection] {reason}')
                            order.status = ServiceOrder.STATUS_CANCELLED
                            order.save(update_fields=['status'])
                    else:
                        # Create a synthetic rejection log entry linked to the most recent order if exists
                        last_order = ServiceOrder.objects.filter(driver_assigned=driver).order_by('-created_at').first()
                        if last_order:
                            RejectionLog.objects.create(order=last_order, driver=driver, reason=f'[Admin Rejection] {reason}')
                admin_messages.success(request, f'تم رفض {drivers.count()} سائق مع تسجيل السبب.')
                return redirect('../../')

        context = {
            **self.admin_site.each_context(request),
            'drivers': drivers,
            'ids': ids_param,
            'title': 'رفض السائقين مع تسجيل السبب',
        }
        return render(request, 'admin/driver_reject_reason.html', context)

    def average_rating_display(self, obj):
        return f'{obj.average_rating()} ⭐'
    average_rating_display.short_description = _('متوسط التقييم')

    def id_front_preview(self, obj):
        if obj.id_card_front:
            return format_html('<img src="{}" style="max-height:80px;">', obj.id_card_front.url)
        return '-'
    id_front_preview.short_description = _('الهوية - الوجه')

    def id_back_preview(self, obj):
        if obj.id_card_back:
            return format_html('<img src="{}" style="max-height:80px;">', obj.id_card_back.url)
        return '-'
    id_back_preview.short_description = _('الهوية - الظهر')

    def license_preview(self, obj):
        if obj.license_image:
            return format_html('<img src="{}" style="max-height:80px;">', obj.license_image.url)
        return '-'
    license_preview.short_description = _('رخصة القيادة')

    def face_preview(self, obj):
        if obj.face_photo:
            return format_html('<img src="{}" style="max-height:80px;">', obj.face_photo.url)
        return '-'
    face_preview.short_description = _('صورة الوجه')

    def vehicle_preview(self, obj):
        if obj.vehicle_license:
            return format_html('<img src="{}" style="max-height:80px;">', obj.vehicle_license.url)
        return '-'
    vehicle_preview.short_description = _('رخصة السيارة')


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'service_type', 'payment_method', 'status', 'driver_assigned', 'created_at')
    list_filter = ('status', 'service_type', 'payment_method')
    search_fields = ('customer_name', 'phone_number')
    readonly_fields = ('created_at',)


@admin.register(RejectionLog)
class RejectionLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'driver', 'reason', 'timestamp')
    list_filter = ('timestamp',)
    readonly_fields = ('timestamp',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('order', 'stars', 'comment', 'created_at')
    list_filter = ('stars',)
    readonly_fields = ('created_at',)
