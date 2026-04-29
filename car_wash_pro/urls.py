from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView
from accounts import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('order/', TemplateView.as_view(template_name='order.html'), name='order'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('create-order/', views.create_order, name='create_order'),
]
