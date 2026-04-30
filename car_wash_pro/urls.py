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
    path('', views.splash, name='splash'),
    path('home/', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/customer/', views.customer_signup, name='customer_signup'),
    path('signup/driver/', views.driver_signup, name='driver_signup'),
    path('book/', views.book_service, name='book_service'),
    path('order/<int:order_id>/status/', views.order_status, name='order_status'),
    path('order/<int:order_id>/payment/', views.payment, name='payment'),
    path('order/<int:order_id>/rate/', views.rate_order, name='rate_order'),
    path('driver/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/order/<int:order_id>/accept/', views.accept_order, name='accept_order'),
    path('driver/order/<int:order_id>/reject/', views.reject_order, name='reject_order'),
    path('driver/order/<int:order_id>/status/', views.update_order_status, name='update_order_status'),
    path('driver/location/', views.driver_location_api, name='driver_location_api'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    prefix_default_language=False,
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
