from django.shortcuts import render, reverse, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from . import forms
from .models import AppInstanceModel

from subprocess import run
from datetime import datetime

def index(request):
    running_instances = AppInstanceModel.objects.filter(is_running=True)
    stopped_instances = AppInstanceModel.objects.filter(is_running=False)

    context = {
        "running_instances": running_instances,
        "stopped_instances": stopped_instances
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
        return render(request, "index.html", { "form": form })

    app_name = form.cleaned_data["app_name"]
    url_path = form.cleaned_data["url_path"]

    if (len(url_path) == 0):
        url_path = app_name

    # TODO: Create custom form validator that ensures the app name and URL path
    # make sense.
    app_name = app_name.replace("/", "")
    
    if (url_path[0] == "/"):
        url_path = url_path[1:]

    if (url_path[-1] == "/"):
        url_path = url_path[:-1]

    run(["./start-instance.sh", app_name, url_path])

    datetime_now = datetime.now()
    app_instance = AppInstanceModel(app_name=app_name, url_path=url_path,
                                           is_running=True, created_at=datetime_now)

    app_instance.save()

    return HttpResponseRedirect(reverse("index"))

def stop_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)

    run(["./stop-instance.sh", app_name])
    instance.is_running = False
    instance.save()

    return HttpResponse(status=204)
