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


def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def dispatch_to_driver(order, excluded_driver_ids=None):
    excluded = excluded_driver_ids or []
    drivers = Driver.objects.filter(is_active=True, approval_status='approved').exclude(pk__in=excluded)
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
                    'lat': order.customer_lat,
                    'lon': order.customer_lon,
                    'phone': order.phone_number,
                    'car': order.car_model,
                    'payment': order.get_payment_method_display(),
                }
            }
        )
    return closest


# ─── Splash / Home ─────────────────────────────────────────────────────────────

def splash(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'splash.html')


@login_required(login_url='login')
def home(request):
    try:
        driver = request.user.driver
        if driver.approval_status == 'pending':
            return render(request, 'driver_pending.html')
        if driver.approval_status == 'rejected':
            return render(request, 'driver_rejected.html')
        return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        pass
    return render(request, 'home.html')


# ─── Auth ───────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        try:
            driver = user.driver
            if driver.approval_status == Driver.APPROVAL_PENDING:
                return render(request, 'driver_pending.html', {
                    'message': _('حسابك قيد المراجعة. يُرجى الانتظار حتى تتم الموافقة عليه.')
                })
            if driver.approval_status == Driver.APPROVAL_REJECTED:
                logout(request)
                messages.error(request, _('تم رفض حسابك. يرجى التواصل مع الدعم.'))
                return render(request, 'login.html', {'form': form})
        except Driver.DoesNotExist:
            pass
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


# ─── Customer Booking ───────────────────────────────────────────────────────────

@login_required(login_url='login')
def book_service(request):
    try:
        driver = request.user.driver
        return redirect('driver_dashboard')
    except Driver.DoesNotExist:
        pass

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.customer = request.user
            order.save()
            nearest = dispatch_to_driver(order)
            if nearest:
                return redirect('order_status', order_id=order.pk)
            else:
                order.status = ServiceOrder.STATUS_CANCELLED
                order.save()
                messages.error(request, _('لا يوجد سائق متاح حالياً. يرجى المحاولة لاحقاً.'))
    else:
        initial = {}
        try:
            profile = request.user.customer_profile
            initial['customer_name'] = request.user.get_full_name()
            initial['phone_number'] = profile.phone
        except CustomerProfile.DoesNotExist:
            pass
        form = BookingForm(initial=initial)
    return render(request, 'book_service.html', {'form': form})


@login_required(login_url='login')
def order_status(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, customer=request.user)
    if order.status == ServiceOrder.STATUS_FINISHED:
        return redirect('payment', order_id=order.pk)
    rejections = order.rejections.order_by('-timestamp')
    return render(request, 'order_status.html', {'order': order, 'rejections': rejections})


# ─── Driver Dashboard ──────────────────────────────────────────────────────────

@login_required(login_url='login')
def driver_dashboard(request):
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return redirect('home')

    if driver.approval_status != 'approved':
        return render(request, 'driver_pending.html')

    active_order = ServiceOrder.objects.filter(
        driver_assigned=driver,
        status__in=[
            ServiceOrder.STATUS_ACCEPTED,
            ServiceOrder.STATUS_ARRIVED,
            ServiceOrder.STATUS_PICKING_UP,
            ServiceOrder.STATUS_IN_PROGRESS,
        ]
    ).first()

    pending_order = ServiceOrder.objects.filter(
        driver_assigned=driver,
        status=ServiceOrder.STATUS_PENDING,
    ).first()

    rejection_form = RejectionForm()

    try:
        cash_balance = driver.cash_balance
    except CashBalance.DoesNotExist:
        cash_balance = None

    recent_reports = DailyReport.objects.filter(driver=driver).order_by('-date')[:7]

    return render(request, 'driver_dashboard.html', {
        'driver': driver,
        'active_order': active_order,
        'pending_order': pending_order,
        'rejection_form': rejection_form,
        'cash_balance': cash_balance,
        'recent_reports': recent_reports,
    })


@require_POST
@login_required(login_url='login')
def accept_order(request, order_id):
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return redirect('home')

    order = get_object_or_404(ServiceOrder, pk=order_id, driver_assigned=driver)
    order.status = ServiceOrder.STATUS_ACCEPTED
    order.save(update_fields=['status'])

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'order_{order.pk}',
        {
            'type': 'order_update',
            'data': {
                'type': 'status_update',
                'status': order.status,
                'status_display': order.get_status_display(),
                'driver_lat': driver.lat,
                'driver_lon': driver.lon,
                'driver_name': str(driver),
            }
        }
    )
    return redirect('driver_dashboard')


@require_POST
@login_required(login_url='login')
def reject_order(request, order_id):
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return redirect('home')

    order = get_object_or_404(ServiceOrder, pk=order_id, driver_assigned=driver)
    form = RejectionForm(request.POST)
    if form.is_valid():
        reason = form.cleaned_data['reason']
        RejectionLog.objects.create(order=order, driver=driver, reason=reason)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'order_{order.pk}',
            {
                'type': 'order_update',
                'data': {
                    'type': 'rejected',
                    'reason': reason,
                    'driver_name': str(driver),
                }
            }
        )

        excluded = list(RejectionLog.objects.filter(order=order).values_list('driver_id', flat=True))
        order.status = ServiceOrder.STATUS_PENDING
        order.driver_assigned = None
        order.save()
        nearest = dispatch_to_driver(order, excluded_driver_ids=excluded)
        if not nearest:
            order.status = ServiceOrder.STATUS_REJECTED
            order.save()
            async_to_sync(channel_layer.group_send)(
                f'order_{order.pk}',
                {
                    'type': 'order_update',
                    'data': {'type': 'no_driver', 'message': 'لا يوجد سائق آخر متاح'}
                }
            )

    return redirect('driver_dashboard')


@require_POST
@login_required(login_url='login')
def update_order_status(request, order_id):
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return redirect('home')

    order = get_object_or_404(ServiceOrder, pk=order_id, driver_assigned=driver)
    new_status = request.POST.get('status')

    valid_transitions = {
        ServiceOrder.STATUS_ACCEPTED: ServiceOrder.STATUS_ARRIVED,
        ServiceOrder.STATUS_ARRIVED: ServiceOrder.STATUS_PICKING_UP,
        ServiceOrder.STATUS_PICKING_UP: ServiceOrder.STATUS_IN_PROGRESS,
        ServiceOrder.STATUS_IN_PROGRESS: ServiceOrder.STATUS_FINISHED,
    }

    if new_status == valid_transitions.get(order.status):
        order.status = new_status
        order.save(update_fields=['status'])

        if new_status == ServiceOrder.STATUS_FINISHED and order.payment_method == ServiceOrder.PAYMENT_CASH:
            from decimal import Decimal
            balance, _ = CashBalance.objects.get_or_create(
                driver=driver,
                defaults={'amount_owed': Decimal('0')}
            )
            balance.amount_owed += Decimal(str(order.get_price()))
            balance.save(update_fields=['amount_owed', 'last_updated'])

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'order_{order.pk}',
            {
                'type': 'order_update',
                'data': {
                    'type': 'status_update',
                    'status': order.status,
                    'status_display': order.get_status_display(),
                }
            }
        )

    return redirect('driver_dashboard')


# ─── Payment & Rating ──────────────────────────────────────────────────────────

@login_required(login_url='login')
def payment(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, customer=request.user)
    if order.status != ServiceOrder.STATUS_FINISHED:
        messages.error(request, _('الدفع متاح فقط بعد اكتمال الخدمة.'))
        return redirect('order_status', order_id=order.pk)
    return render(request, 'payment.html', {'order': order})


@login_required(login_url='login')
def rate_order(request, order_id):
    order = get_object_or_404(ServiceOrder, pk=order_id, customer=request.user)
    if order.status != ServiceOrder.STATUS_FINISHED:
        messages.error(request, _('التقييم متاح فقط بعد اكتمال الخدمة.'))
        return redirect('order_status', order_id=order.pk)
    if hasattr(order, 'rating'):
        return redirect('home')

    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            Rating.objects.create(
                order=order,
                stars=form.cleaned_data['stars'],
                comment=form.cleaned_data.get('comment', ''),
            )
            return redirect('home')
    else:
        form = RatingForm()
    return render(request, 'rate_order.html', {'order': order, 'form': form})


# ─── Driver Location API ────────────────────────────────────────────────────────

@require_POST
@login_required(login_url='login')
def driver_location_api(request):
    try:
        driver = request.user.driver
    except Driver.DoesNotExist:
        return JsonResponse({'error': 'Not a driver'}, status=403)

    try:
        data = json.loads(request.body)
        driver.lat = float(data['lat'])
        driver.lon = float(data['lon'])
        driver.save(update_fields=['lat', 'lon'])
        order_id = data.get('order_id')
        if order_id:
            order_id = int(order_id)
            # Only broadcast if this order is actually assigned to this driver
            if ServiceOrder.objects.filter(pk=order_id, driver_assigned=driver).exists():
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'order_{order_id}',
                    {
                        'type': 'driver_location',
                        'data': {'type': 'driver_location', 'lat': driver.lat, 'lon': driver.lon}
                    }
                )
        return JsonResponse({'ok': True})
    except (KeyError, ValueError, TypeError) as e:
        return JsonResponse({'error': str(e)}, status=400)


# ─── Profile ────────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def profile(request):
    try:
        driver = request.user.driver
        avg_rating = driver.average_rating()
        return render(request, 'profile.html', {'driver': driver, 'avg_rating': avg_rating})
    except Driver.DoesNotExist:
        return render(request, 'profile.html', {})


# ─── Settings ───────────────────────────────────────────────────────────────────

@login_required(login_url='login')
def settings_view(request):
    return render(request, 'settings.html')
