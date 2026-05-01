from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages as admin_messages
from django.utils import timezone
from decimal import Decimal
import subprocess, sys

from .models import (
    Driver, ServiceOrder, RejectionLog, Rating, CustomerProfile,
    DailyReport, CashBalance, CashSettlement,
)


# ─── CustomerProfile ───────────────────────────────────────────────────────────

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    search_fields = ('user__username', 'user__first_name', 'phone')


# ─── Driver ────────────────────────────────────────────────────────────────────

@admin.action(description=_('الموافقة على السائقين المحددين'))
def approve_drivers(modeladmin, request, queryset):
    updated = queryset.update(approval_status='approved')
    modeladmin.message_user(request, f'تمت الموافقة على {updated} سائق.')


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'phone', 'car_model', 'car_color', 'car_year',
        'approval_status', 'is_active', 'average_rating_display',
        'cash_owed_display', 'id_front_preview',
    )
    list_filter = ('approval_status', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'phone')
    actions = [approve_drivers, 'reject_with_reason_action', 'mark_cash_settled_action']
    readonly_fields = (
        'id_front_preview', 'id_back_preview', 'license_preview',
        'face_preview', 'vehicle_preview', 'cash_owed_display',
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('reject-with-reason/', self.admin_site.admin_view(self.reject_with_reason_view), name='driver-reject-reason'),
            path('settle-cash/', self.admin_site.admin_view(self.settle_cash_view), name='driver-settle-cash'),
        ]
        return custom + urls

    # ── reject with reason ─────────────────────────────────────────────────────

    @admin.action(description=_('رفض السائقين المحددين مع تسجيل السبب'))
    def reject_with_reason_action(self, request, queryset):
        selected_ids = ','.join(str(d.pk) for d in queryset)
        return redirect(f'reject-with-reason/?ids={selected_ids}')

    def reject_with_reason_view(self, request):
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
                    orders = ServiceOrder.objects.filter(
                        driver_assigned=driver,
                        status__in=['pending', 'accepted', 'arrived', 'picking_up', 'in_progress']
                    )
                    if orders.exists():
                        for order in orders:
                            RejectionLog.objects.create(order=order, driver=driver, reason=f'[Admin Rejection] {reason}')
                            order.status = ServiceOrder.STATUS_CANCELLED
                            order.save(update_fields=['status'])
                    else:
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

    # ── cash settlement ────────────────────────────────────────────────────────

    @admin.action(description=_('تسجيل تسوية نقدية للسائقين المحددين'))
    def mark_cash_settled_action(self, request, queryset):
        selected_ids = ','.join(str(d.pk) for d in queryset)
        return redirect(f'settle-cash/?ids={selected_ids}')

    def settle_cash_view(self, request):
        ids_param = request.GET.get('ids', '') or request.POST.get('ids', '')
        ids = [int(i) for i in ids_param.split(',') if i.strip().isdigit()]
        drivers = list(Driver.objects.filter(pk__in=ids))
        balances_map = {b.driver_id: b for b in CashBalance.objects.filter(driver__in=drivers)}
        driver_balances = [
            (d, balances_map.get(d.pk)) for d in drivers
        ]
        if request.method == 'POST':
            note = request.POST.get('note', '').strip()
            total_settled = 0
            for driver, balance in driver_balances:
                if balance and balance.amount_owed > 0:
                    CashSettlement.objects.create(
                        driver=driver,
                        amount=balance.amount_owed,
                        note=note,
                        settled_by=request.user,
                    )
                    total_settled += 1
                    balance.amount_owed = Decimal('0')
                    balance.save(update_fields=['amount_owed', 'last_updated'])
            admin_messages.success(request, f'تمت تسوية أرصدة {total_settled} سائق.')
            return redirect('../../')
        context = {
            **self.admin_site.each_context(request),
            'driver_balances': driver_balances,
            'ids': ids_param,
            'title': 'تسجيل تسوية نقدية',
        }
        return render(request, 'admin/driver_settle_cash.html', context)

    # ── display helpers ────────────────────────────────────────────────────────

    def average_rating_display(self, obj):
        return f'{obj.average_rating()} ⭐'
    average_rating_display.short_description = _('متوسط التقييم')

    def cash_owed_display(self, obj):
        try:
            owed = obj.cash_balance.amount_owed
            color = '#e74c3c' if owed > 0 else '#27ae60'
            return format_html('<span style="color:{}; font-weight:bold;">{} د.أ</span>', color, owed)
        except CashBalance.DoesNotExist:
            return format_html('<span style="color:#888;">—</span>')
    cash_owed_display.short_description = _('رصيد نقدي مستحق')

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


# ─── ServiceOrder ──────────────────────────────────────────────────────────────

@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'service_type', 'price_display', 'payment_method', 'status', 'driver_assigned', 'created_at')
    list_filter = ('status', 'service_type', 'payment_method', 'created_at')
    search_fields = ('customer_name', 'phone_number')
    readonly_fields = ('created_at',)

    def price_display(self, obj):
        return f'{obj.get_price()} د.أ'
    price_display.short_description = _('السعر')


# ─── DailyReport ──────────────────────────────────────────────────────────────

@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('date', 'driver', 'orders_count', 'cash_total_display', 'qliq_total_display', 'grand_total_display', 'generated_at')
    list_filter = ('date', 'driver')
    search_fields = ('driver__user__username', 'driver__user__first_name')
    readonly_fields = ('generated_at',)
    ordering = ('-date', 'driver')
    date_hierarchy = 'date'
    change_list_template = 'admin/daily_report_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('generate/', self.admin_site.admin_view(self.generate_report_view), name='dailyreport-generate'),
        ]
        return custom + urls

    def generate_report_view(self, request):
        if request.method == 'POST':
            report_date = request.POST.get('report_date', '').strip()
            cmd = [sys.executable, 'manage.py', 'generate_daily_reports']
            if report_date:
                cmd += ['--date', report_date]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    admin_messages.success(request, result.stdout.strip() or 'تم إنشاء التقارير بنجاح.')
                else:
                    admin_messages.error(request, result.stderr.strip() or 'حدث خطأ أثناء إنشاء التقارير.')
            except Exception as e:
                admin_messages.error(request, f'خطأ: {e}')
            return redirect('../')
        context = {
            **self.admin_site.each_context(request),
            'title': 'إنشاء تقارير يومية',
        }
        return render(request, 'admin/generate_report.html', context)

    def cash_total_display(self, obj):
        return format_html('<span style="color:#e74c3c; font-weight:bold;">{} د.أ</span>', obj.cash_total)
    cash_total_display.short_description = _('نقدي')

    def qliq_total_display(self, obj):
        return format_html('<span style="color:#3498db; font-weight:bold;">{} د.أ</span>', obj.qliq_total)
    qliq_total_display.short_description = _('QLIQ')

    def grand_total_display(self, obj):
        return format_html('<span style="color:#27ae60; font-weight:bold;">{} د.أ</span>', obj.grand_total)
    grand_total_display.short_description = _('الإجمالي')


# ─── CashBalance ──────────────────────────────────────────────────────────────

@admin.register(CashBalance)
class CashBalanceAdmin(admin.ModelAdmin):
    list_display = ('driver', 'amount_owed_display', 'last_updated', 'bank_account')
    search_fields = ('driver__user__username', 'driver__user__first_name')
    readonly_fields = ('last_updated',)
    ordering = ('-amount_owed',)

    def amount_owed_display(self, obj):
        color = '#e74c3c' if obj.amount_owed > 0 else '#27ae60'
        return format_html('<span style="color:{}; font-weight:bold; font-size:15px;">{} د.أ</span>', color, obj.amount_owed)
    amount_owed_display.short_description = _('المبلغ المستحق')


# ─── CashSettlement ───────────────────────────────────────────────────────────

@admin.register(CashSettlement)
class CashSettlementAdmin(admin.ModelAdmin):
    list_display = ('driver', 'amount', 'settled_by', 'settled_at', 'note')
    list_filter = ('settled_at', 'driver')
    search_fields = ('driver__user__username',)
    readonly_fields = ('settled_at',)
    ordering = ('-settled_at',)


# ─── RejectionLog / Rating ────────────────────────────────────────────────────

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
