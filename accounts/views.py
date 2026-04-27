import math
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import ServiceOrder, Driver

# --- 1. المحرك الرياضي (حساب المسافة بين نقطتين) ---
def calculate_distance(lat1, lon1, lat2, lon2):
    # معادلة هافيرسين لحساب المسافة بالكيلومترات
    radius = 6371  
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(float(lat1))) \
        * math.cos(math.radians(float(lat2))) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return radius * c

# --- 2. استقبال طلب العميل والربط التلقائي بالأقرب ---
def create_order(request):
    if request.method == 'POST':
        # سحب بيانات العميل والموقع من الخريطة
        name = request.POST.get('customer_name')
        car = request.POST.get('car_model')
        phone = request.POST.get('phone_number')
        service = request.POST.get('service_type')
        area = request.POST.get('area')
        c_lat = request.POST.get('customer_lat')
        c_lon = request.POST.get('customer_lon')

        # إنشاء الطلب في قاعدة البيانات
        new_order = ServiceOrder.objects.create(
            customer_name=name,
            car_model=car,
            phone_number=phone,
            service_type=service,
            area=area,
            customer_lat=c_lat,
            customer_lon=c_lon
        )

        # البحث التلقائي عن أقرب سائق "نشط"
        active_drivers = Driver.objects.filter(is_active=True)
        closest_driver = None
        min_dist = float('inf')

        for driver in active_drivers:
            # حساب المسافة بين موقع العميل وموقع السائق الحالي
            dist = calculate_distance(c_lat, c_lon, driver.lat, driver.lon)
            if dist < min_dist:
                min_dist = dist
                closest_driver = driver

        # ربط السائق الأقرب بالطلب فوراً
        if closest_driver:
            new_order.driver_assigned = closest_driver
            new_order.status = 'accepted'
            new_order.save()
            messages.success(request, f"تم تعيين السائق {closest_driver.user.username} لطلبك")

        return render(request, 'order_success.html', {'order': new_order})

    return render(request, 'order_service.html')

# --- 3. تسجيل دخول السائقين ---
def driver_login(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('driver_dashboard')
        else:
            messages.error(request, "تأكد من اسم المستخدم أو كلمة السر")
    return render(request, 'driver_login.html')

# --- 4. لوحة تحكم السائق (عرض طلباته فقط) ---
def driver_dashboard(request):
    try:
        # التأكد أن المستخدم هو "سائق"
        driver = request.user.driver
    except:
        return redirect('driver_login')

    # جلب الطلبات المسندة لهذا السائق تلقائياً
    my_orders = ServiceOrder.objects.filter(driver_assigned=driver).order_by('-created_at')
    
    return render(request, 'driver_dashboard.html', {
        'driver': driver,
        'my_orders': my_orders
    })

# --- 5. تسجيل الخروج ---
def user_logout(request):
    logout(request)
    return redirect('driver_login')