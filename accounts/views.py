import json
import math
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils.translation import gettext_lazy as _

from .models import Driver, ServiceOrder, RejectionLog, Rating, CustomerProfile, CashBalance, DailyReport
from .forms import CustomerSignupForm, DriverSignupForm, BookingForm, RejectionForm, RatingForm

# --- دالة حساب المسافة ---
def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)

# --- دالة توزيع الطلبات الذكية ---
def dispatch_to_driver(order, excluded_driver_ids=None):
    excluded = excluded_driver_ids or []
    # البحث عن السائقين المتاحين والموافق عليهم والذين ليس لديهم طلبات نشطة
    active_drivers_with_orders = ServiceOrder.objects.filter(
        status__in=[ServiceOrder.STATUS_ACCEPTED, ServiceOrder.STATUS_ARRIVED, ServiceOrder.STATUS_IN_PROGRESS]
    ).values_list('driver_assigned_id', flat=True)

    drivers = Driver.objects.filter(
        is_active=True, 
        approval_status=Driver.APPROVAL_APPROVED
    ).exclude(pk__in=list(excluded) + list(active_drivers_with_orders))

    closest = None
    min_dist = float('inf')
    for driver in drivers:
        dist = calculate_distance(order.customer_lat, order.customer_lon, driver.lat, driver.lon)
        if dist < min_dist:
            min_dist = dist
            closest = driver

    if closest:
        order.driver_assigned = closest
        order.status = ServiceOrder.STATUS_PENDING
        order.save(update_fields=['driver_assigned', 'status'])

        # إرسال تنبيه للسائق عبر WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'driver_{closest.pk}',
            {
                'type': 'new_order',
                'data': {
                    'type': 'new_order',
                    'order_id': order.pk,
                    'customer_name': order.customer_name,
                    'service': order.get_service_type_display(),
                    'price': order.get_price(),
                    'phone': order.phone_number,
                }
            }
        )
    return closest

# --- العرض الرئيسي ---
def splash(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'splash.html')

@login_required(login_url='login')
def home(request):
    try:
        driver = request.user.driver
        if driver.approval_status == Driver.APPROVAL_PENDING:
            return render(request, 'driver_pending.html')
        return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        pass
    return render(request, 'home.html')

# --- تسجيل الدخول والحسابات ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('home')
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

def customer_signup(request):
    form = CustomerSignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('home')
    return render(request, 'customer_signup.html', {'form': form})

def driver_signup(request):
    form = DriverSignupForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return render(request, 'driver_pending.html')
    return render(request, 'driver_signup.html', {'form': form})

# --- نظام طلب الخدمة ---
@login_required(login_url='login')
def book_service(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.customer = request.user
            order.save()
            if dispatch_to_driver(order):
                return redirect('order_status', order_id=order.pk)
            else:
                order.status = ServiceOrder.STATUS_CANCELLED
                order.save()
                messages.error(request, _('عذراً، لا يوجد سائق متاح حالياً في منطقتك.'))
    else:
        form = BookingForm()
    return render(request, 'book_service.html', {'form': form})

@login_required(login_url='login')
def order_status(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, customer=request.user)
    if order.status == ServiceOrder.STATUS_FINISHED:
        return redirect('payment', order_id=order.pk)
    return render(request, 'order_status.html', {'order': order})

# --- لوحة تحكم السائق ---
@login_required(login_url='login')
def driver_dashboard(request):
    driver = get_object_or_404(Driver, user=request.user)
    active_order = ServiceOrder.objects.filter(driver_assigned=driver, status__in=[
        ServiceOrder.STATUS_ACCEPTED, ServiceOrder.STATUS_ARRIVED, ServiceOrder.STATUS_PICKING_UP, ServiceOrder.STATUS_IN_PROGRESS
    ]).first()
    pending_order = ServiceOrder.objects.filter(driver_assigned=driver, status=ServiceOrder.STATUS_PENDING).first()

    # البيانات المالية للوحة التحكم
    balance, _ = CashBalance.objects.get_or_create(driver=driver)
    reports = DailyReport.objects.filter(driver=driver).order_by('-date')[:5]

    return render(request, 'driver_dashboard.html', {
        'driver': driver, 'active_order': active_order, 'pending_order': pending_order,
        'cash_balance': balance, 'reports': reports, 'rejection_form': RejectionForm()
    })

@login_required(login_url='login')
def accept_order(request, order_id):
    driver = get_object_or_404(Driver, user=request.user)
    order = get_object_or_404(ServiceOrder, pk=order_id, driver_assigned=driver, status=ServiceOrder.STATUS_PENDING)
    order.status = ServiceOrder.STATUS_ACCEPTED
    order.save()
    return redirect('driver_dashboard')

@require_POST
@login_required(login_url='login')
def reject_order(request, order_id):
    driver = get_object_or_404(Driver, user=request.user)
    order = get_object_or_404(ServiceOrder, pk=order_id, driver_assigned=driver)
    form = RejectionForm(request.POST)
    if form.is_valid():
        rejection = form.save(commit=False)
        rejection.order = order
        rejection.driver = driver
        rejection.save()
        # البحث عن سائق بديل
        excluded = RejectionLog.objects.filter(order=order).values_list('driver_id', flat=True)
        if not dispatch_to_driver(order, excluded_driver_ids=excluded):
            order.status = ServiceOrder.STATUS_CANCELLED
            order.save()
    return redirect('driver_dashboard')

@require_POST
@login_required(login_url='login')
def update_order_status(request, order_id):
    driver = get_object_or_404(Driver, user=request.user)
    order = get_object_or_404(ServiceOrder, pk=order_id, driver_assigned=driver)
    new_status = request.POST.get('status')

    # تحديث الحالة (الـ Signal في المودلز سيتولى الحسابات المالية عند الـ finished)
    order.status = new_status
    order.save()

    # تحديث العميل عبر WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'order_{order.pk}',
        {'type': 'order_update', 'data': {'type': 'status_update', 'status': order.status, 'status_display': order.get_status_display()}}
    )
    return redirect('driver_dashboard')

@login_required(login_url='login')
def payment(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, customer=request.user, status=ServiceOrder.STATUS_FINISHED)
    return render(request, 'payment.html', {'order': order})

@require_POST
@login_required(login_url='login')
def rate_order(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, customer=request.user)
    form = RatingForm(request.POST)
    if form.is_valid():
        rating = form.save(commit=False)
        rating.order = order
        rating.save()
    return redirect('home')