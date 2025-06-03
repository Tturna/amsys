from django.shortcuts import render, reverse, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required, permission_required
from .models import AppInstanceModel, AppConnectionModel, OrganizationEntity
from . import forms

from subprocess import run
from datetime import datetime

def index(request):
    running_instances = AppInstanceModel.objects.filter(is_running=True)
    stopped_instances = AppInstanceModel.objects.filter(is_running=False)

    name_fetch_result = run(["docker", "container", "ls", "-a", "--format='{{json .Names}}'"], capture_output=True, text=True)
    existing_containers_string = name_fetch_result.stdout
    existing_containers_string = existing_containers_string.replace("\"", "")
    existing_containers_string = existing_containers_string.replace("\'", "")
    existing_containers = existing_containers_string.split("\n")

    stopped_but_existing = []
    stopped_nonexistent = []

    for instance in stopped_instances:
        if instance.app_name in existing_containers:
            stopped_but_existing.append(instance)
        else:
            stopped_nonexistent.append(instance)

    organizations = OrganizationEntity.objects.all()

    context = {
        "organizations": organizations,
        "running_instances": running_instances,
        "stopped_existing_instances": stopped_but_existing,
        "stopped_nonexistent_instances": stopped_nonexistent
    }

    return render(request, "index.html", context)

def view_organization(request, org_name):
    organization = get_object_or_404(OrganizationEntity, org_name=org_name)
    connected_apps = AppInstanceModel.objects.filter(owner_org=organization)

    context = {
        "org": organization,
        "connected_apps": connected_apps
    }

    return render(request, "view_organization.html", context)

@login_required
@permission_required("main.add_organizationentitymodel")
def create_organization(request):
    if request.method == "GET":
        form = forms.OrganizationEntityForm()

        return render(request, "create_organization.html", { "form": form })

    if request.method == "POST":
        form = forms.OrganizationEntityForm(request.POST)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "create_organization.html", { "form": form })

    return HttpResponseRedirect(reverse("index"))

@login_required
@permission_required("main.add_appinstancemodel")
def create_app_instance(request):
    if request.method == "GET":
        form = forms.AppInstanceForm()

        context = {
            "form": form
        }

        return render(request, "create_instance.html", context)

    if request.method != "POST":
        return HttpResponseRedirect(reverse("index"))

    # Handle POST request
    form = forms.AppInstanceForm(request.POST)

    if (not form.is_valid()):
        return render(request, "create_instance.html", { "form": form })

    app_name = form.cleaned_data["app_name"]
    url_path = form.cleaned_data["url_path"]
    owner_org = form.cleaned_data["owner_org"]
    transmit_destinations = form.cleaned_data["transmit_destinations"]

    if (len(url_path) == 0):
        url_path = app_name

    # TODO: Create custom form validator that ensures the app name and URL path
    # make sense.
    app_name = app_name.replace("/", "")
    
    if (url_path[0] == "/"):
        url_path = url_path[1:]

    if (url_path[-1] == "/"):
        url_path = url_path[:-1]

    datetime_now = datetime.now()
    app_instance = AppInstanceModel(app_name=app_name, url_path=url_path,
                                    owner_org=owner_org, is_running=True,
                                    created_at=datetime_now)
    app_instance.save()

    # Dashboard will always know which instances can transmit to which.
    # Instances should always ask what they can do before trying to do things.
    for dest in transmit_destinations:
        connection = AppConnectionModel(instance_from=app_instance, instance_to=dest)
        connection.save()

    run(["./start-instance.sh", app_name, url_path])

    return HttpResponseRedirect(reverse("index"))

@login_required
@permission_required("main.change_appinstancemodel")
def stop_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)

    run(["./stop-instance.sh", app_name])
    instance.is_running = False
    instance.save()

    return HttpResponse(status=204)

@login_required
@permission_required("main.delete_appinstancemodel")
def remove_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    instance.delete()

    return HttpResponse(status=204)

def view_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    available_transmit_destinations = AppConnectionModel.objects.filter(instance_from=instance)

    context = {
        "instance": instance,
        "destinations": available_transmit_destinations
    }

    return render(request, "view_instance.html", context)

@login_required
@permission_required("main.change_appinstancemodel")
def edit_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    defined_connections = AppConnectionModel.objects.filter(instance_from=instance)
    defined_destinations = [conn.instance_to for conn in defined_connections]
    form = None

    if request.method == "GET":
        form = forms.AppInstanceForm(instance=instance, initial={ "transmit_destinations": defined_destinations })

        context = {
            "instance": instance,
            "form": form
        }

        return render(request, "edit_instance.html", context)
    elif request.method == "POST":
        form = forms.AppInstanceForm(request.POST, instance=instance)

        if (form.is_valid()):
            form.save()

            transmit_destinations = form.cleaned_data["transmit_destinations"]

            # Remove unticked connections
            for conn in defined_connections:
                if conn.instance_to not in transmit_destinations:
                    conn.delete()

            # Add ticked connections
            for dest in transmit_destinations:
                # Skip already existing ones
                if dest in defined_destinations:
                    continue

                connection = AppConnectionModel(instance_from=instance, instance_to=dest)
                connection.save()

            # Prevent double posting and stuff
            return HttpResponseRedirect(reverse("edit_instance", args=[instance.app_name]))
    else:
        return HttpResponseRedirect(reverse("index"))
