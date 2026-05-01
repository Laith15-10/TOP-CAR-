from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=15, verbose_name=_("رقم الهاتف"))

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

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default=APPROVAL_PENDING)
    is_active = models.BooleanField(default=False)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Driver: {self.user.username} ({self.get_approval_status_display()})"

# --- النظام المالي (رصيد الكاش) ---
class CashBalance(models.Model):
    driver = models.OneToOneField(Driver, on_delete=models.CASCADE, related_name='cash_balance')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Balance: {self.driver.user.username} - {self.balance} JOD"

# --- التقارير اليومية ---
class DailyReport(models.Model):
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='daily_reports')
    date = models.DateField(default=timezone.now)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    orders_completed = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('driver', 'date')

# --- Signals لإنشاء البروفايل والرصيد تلقائياً ---
@receiver(post_save, sender=Driver)
def create_driver_financials(sender, instance, created, **kwargs):
    if created:
        CashBalance.objects.get_or_create(driver=instance)