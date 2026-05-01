from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from accounts import views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),

    # صفحات الواجهة الرئيسية والدخول
    path('', views.splash, name='splash'),
    path('home/', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # تسجيل الحسابات
    path('signup/customer/', views.customer_signup, name='customer_signup'),
    path('signup/driver/', views.driver_signup, name='driver_signup'),

    # نظام الطلبات للعميل
    path('book/', views.book_service, name='book_service'),
    path('order/<int:order_id>/status/', views.order_status, name='order_status'),
    path('order/<int:order_id>/payment/', views.payment, name='payment'),
    path('order/<int:order_id>/rate/', views.rate_order, name='rate_order'),

    # لوحة تحكم السائق والعمليات المالية
    path('driver/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/order/<int:order_id>/accept/', views.accept_order, name='accept_order'),
    path('driver/order/<int:order_id>/reject/', views.reject_order, name='reject_order'),
    path('driver/order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),

    # ملاحظة: إذا كان لديك APIs لتحديث الموقع، ستبقى هنا
    # path('driver/location/', views.driver_location_api, name='driver_location_api'),

    prefix_default_language=False,
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)