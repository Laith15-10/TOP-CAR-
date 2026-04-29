from django.shortcuts import render
from .models import ServiceOrder, Driver
import math

# دالة حساب المسافة (تأكد أنها موجودة لتجنب الأخطاء)
def calculate_distance(lat1, lon1, lat2, lon2):
    return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

def create_order(request):
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        car_model = request.POST.get('car_model')
        phone_number = request.POST.get('phone_number')
        area = request.POST.get('area')
        service_type = request.POST.get('service_type', 'Car Wash')
        
        # إحداثيات الموقع
        try:
            c_lat = float(request.POST.get('customer_lat', 0.0))
            c_lon = float(request.POST.get('customer_lon', 0.0))
        except ValueError:
            c_lat, c_lon = 0.0, 0.0

        if customer_name and car_model and phone_number:
            # 1. إنشاء الطلب
            new_order = ServiceOrder.objects.create(
                customer_name=customer_name,
                car_model=car_model,
                phone_number=phone_number,
                area=area,
                service_type=service_type,
                customer_lat=c_lat,
                customer_lon=c_lon
            )
            
            # 2. البحث عن أقرب سائق (هذا الجزء الذي كان يسبب Indentation Error)
            active_drivers = Driver.objects.filter(is_active=True)
            closest_driver = None
            min_dist = float('inf')

            for driver in active_drivers:
                dist = calculate_distance(c_lat, c_lon, driver.lat, driver.lon)
                if dist < min_dist:
                    min_dist = dist
                    closest_driver = driver

            # 3. ربط السائق بالطلب إذا وُجد
            if closest_driver:
                new_order.driver_assigned = closest_driver
                new_order.status = 'accepted'
                new_order.save()

            return render(request, 'home.html')
            
    return render(request, 'order.html')
    
from django.shortcuts import redirect

def signup_view(request):
    # إذا كان المستخدم مسجل دخوله مسبقاً، انقله فوراً للرئيسية ولا تره صفحة التسجيل
    if request.user.is_authenticated:
        return redirect('home')
    
    # باقي كود إنشاء الحساب هنا...
    return render(request, 'signup.html')
