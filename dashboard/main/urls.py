from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("view_organization/<org_name>/", views.view_organization, name="view_organization"),
    path("create_organization/", views.create_organization, name="create_organization"),
    path("create_app_instance/", views.create_app_instance, name="create_app_instance"),
    path("stop_instance/<app_name>/", views.stop_instance, name="stop_instance"),
    path("remove_instance/<app_name>/", views.remove_instance, name="remove_instance"),
    path("view_instance/<app_name>/", views.view_instance, name="view_instance"),
    path("edit_instance/<app_name>/", views.edit_instance, name="edit_instance"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html", next_page="/"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(template_name="index.html", next_page="/login/"), name="logout"),
    path("api/existing_instances/<id>/", views.existing_instances, name="existing_instances"),
    path("api/instance_info/<id>/", views.instance_info, name="instance_info"),
    path("admin/", admin.site.urls)
]
