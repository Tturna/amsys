from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('create_app_instance/', views.create_app_instance, name="create_app_instance"),
    path('stop_instance/<app_name>', views.stop_instance, name="stop_instance"),
    path('admin/', admin.site.urls),
]
