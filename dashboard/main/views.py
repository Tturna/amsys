from django.shortcuts import render, reverse, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from . import forms
from .models import AppInstanceModel, AppConnectionModel

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

    context = {
        "running_instances": running_instances,
        "stopped_existing_instances": stopped_but_existing,
        "stopped_nonexistent_instances": stopped_nonexistent
    }

    return render(request, "index.html", context)

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
                                           is_running=True, created_at=datetime_now)
    app_instance.save()

    # Dashboard will always know which instances can transmit to which.
    # Instances should always ask what they can do before trying to do things.
    for dest in transmit_destinations:
        connection = AppConnectionModel(instance_from=app_instance, instance_to=dest)
        connection.save()

    run(["./start-instance.sh", app_name, url_path])

    return HttpResponseRedirect(reverse("index"))

def stop_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)

    run(["./stop-instance.sh", app_name])
    instance.is_running = False
    instance.save()

    return HttpResponse(status=204)

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
