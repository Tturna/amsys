from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("organizations/", views.organizations, name="organizations"),
    path("locations/", views.locations, name="locations"),
    path("view_organization/<org_name>/", views.view_organization, name="view_organization"),
    path("view_location/<location_name>/", views.view_location, name="view_location"),
    path("create_organization/", views.create_organization, name="create_organization"),
    path("create_location/", views.create_location, name="create_location"),
    path("create_app_instance/", views.create_app_instance, name="create_app_instance"),
    path("create_app_instance/<using_compose>", views.create_app_instance, name="create_app_instance"),
    path("apply_preset/", views.apply_preset, name="apply_preset"),
    path("stop_instance/<app_name>/", views.stop_instance, name="stop_instance"),
    path("stop_instance/<app_name>/<should_kill>", views.stop_instance, name="stop_instance"),
    path("start_instance/<app_name>/", views.start_instance, name="start_instance"),
    path("restart_instance/<app_name>/", views.restart_instance, name="restart_instance"),
    path("remove_instance/<app_name>/", views.remove_instance, name="remove_instance"),
    path("remove_location/<location_pk>/", views.remove_location, name="remove_location"),
    path("forget_instance/<app_name>/", views.forget_instance, name="forget_instance"),
    path("view_instance/<app_name>/", views.view_instance, name="view_instance"),
    path("edit_instance/<app_name>/", views.edit_instance, name="edit_instance"),
    path("map/", views.map, name="map"),
    path("proxy/", views.proxy, name="proxy"),
    path("start_proxy/", views.start_proxy, name="start_proxy"),
    path("stop_proxy/", views.stop_proxy, name="stop_proxy"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html", next_page="/"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(template_name="index.html", next_page="/login/"), name="logout"),
    path("api/existing_instances/<id>/", views.existing_instances, name="existing_instances"),
    path("api/instance_info/<id>/", views.instance_info, name="instance_info"),
    path("api/get_ssh_certificate/<id>/", views.get_ssh_certificate, name="get_ssh_certificate"),
    path("api/available_destinations/<id>/", views.available_destinations, name="available_destinations"),
    path("admin/", admin.site.urls)
]
