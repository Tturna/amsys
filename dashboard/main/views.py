from django.shortcuts import render, reverse, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from .models import AppInstanceModel, AppConnectionModel, OrganizationEntity
from . import forms

from subprocess import run
from datetime import datetime
import secrets
import tempfile
import json
import os

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

    proxy_fetch_result = run(["docker", "container", "ls", "--format='{{json .Names}}'"], capture_output=True, text=True)
    proxy_fetch_string = proxy_fetch_result.stdout
    proxy_fetch_string = proxy_fetch_string.replace("\"", "")
    proxy_fetch_string = proxy_fetch_string.replace("\'", "")
    running_containers = proxy_fetch_string.split("\n")

    is_proxy_running = "amsys-traefik" in running_containers

    context = {
        "organizations": organizations,
        "running_instances": running_instances,
        "stopped_existing_instances": stopped_but_existing,
        "stopped_nonexistent_instances": stopped_nonexistent,
        "is_proxy_running": is_proxy_running
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
    app_title = form.cleaned_data["app_title"]
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
    api_token = secrets.token_urlsafe(16)

    app_instance = AppInstanceModel(app_name=app_name, url_path=url_path,
                                    owner_org=owner_org, is_running=True,
                                    created_at=datetime_now, api_token=api_token)
    app_instance.save()

    create_result = run([
        os.getenv("AMSYS_CREATE_INSTANCE_SCRIPT_PATH", "./scripts/create-instance.sh"),
        app_name,
        url_path,
        app_title,
        api_token,
        str(app_instance.pk)
    ], capture_output=True, text=True)

    print(create_result.stdout)
    if (create_result.returncode != 0):
        print(create_result.stderr)
        app_instance.delete()
        # TODO: error msg
        return HttpResponseRedirect(reverse("index"))

    app_instance.save()

    # Dashboard will always know which instances can transmit to which.
    # Instances should always ask what they can do before trying to do things.
    for dest in transmit_destinations:
        connection = AppConnectionModel(instance_from=app_instance, instance_to=dest)
        connection.save()

    return HttpResponseRedirect(reverse("index"))

@login_required
@permission_required("main.change_appinstancemodel")
def stop_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)

    stop_result = run([
        os.getenv("AMSYS_STOP_INSTANCE_SCRIPT_PATH", "./scripts/stop-instance.sh"),
        app_name
    ],capture_output=True, text=True)

    if (stop_result.returncode != 0):
        # TODO: Add error message with the message framework
        print(stop_result.stdout)
        return HttpResponseRedirect(reverse("index"))

    instance.is_running = False
    instance.save()

    return HttpResponse(status=204)

@login_required
@permission_required("main.change_appinstancemodel")
def start_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)

    start_result = run(["./scripts/start-instance.sh", app_name], capture_output=True, text=True)

    if (start_result.returncode != 0):
        # TODO: Add error message with the message framework
        print(start_result.stdout)
        return HttpResponseRedirect(reverse("index"))

    instance.is_running = True
    instance.save()

    return HttpResponse(status=204)

@login_required
@permission_required("main.delete_appinstancemodel")
def remove_instance(request, app_name):
    remove_result = run(["./scripts/destroy-instance.sh", app_name], capture_output=True, text=True)

    if (remove_result.returncode != 0):
        # TODO: error msg
        print(remove_result.stdout)
        return HttpResponseRedirect(reverse("index"))

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

def map(request):
    orgs = OrganizationEntity.objects.all().values("org_name", "latitude", "longitude")
    orgs_data = json.dumps(list(orgs), default=str)

    context = {
        "orgs": orgs_data
    }

    return render(request, "map.html", context)

@login_required
def proxy(request):
    proxy_fetch_result = run(["docker", "container", "ls", "--format='{{json .Names}}'"], capture_output=True, text=True)
    proxy_fetch_string = proxy_fetch_result.stdout
    proxy_fetch_string = proxy_fetch_string.replace("\"", "")
    proxy_fetch_string = proxy_fetch_string.replace("\'", "")
    running_containers = proxy_fetch_string.split("\n")

    is_proxy_running = "amsys-traefik" in running_containers

    context = {
        "is_proxy_running": is_proxy_running
    }

    return render(request, "proxy.html", context)

@login_required
@permission_required("main.change_appinstancemodel")
def start_proxy(request):
    start_result = run(["./scripts/start-proxy.sh"], capture_output=True, text=True)

    print(start_result.stdout)
    if (start_result.returncode != 0):
        # TODO: Add error message with the message framework
        return HttpResponseRedirect(reverse("index"))

    return HttpResponse(status=204)

@login_required
@permission_required("main.change_appinstancemodel")
def stop_proxy(request):
    stop_result = run(["./scripts/stop-proxy.sh"], capture_output=True, text=True)

    if (stop_result.returncode != 0):
        # TODO: Add error message with the message framework
        print(stop_result.stdout)
        return HttpResponseRedirect(reverse("index"))

    return HttpResponse(status=204)

# Web API for instances to use
def existing_instances(request, id):
    if (request.method != "GET"):
        return HttpResponseNotAllowed(["GET"])

    request_api_token = request.headers.get("X-API-Token")

    if not request_api_token:
        return HttpResponseForbidden()

    request_instance_queryset = AppInstanceModel.objects.filter(pk=id)

    if len(request_instance_queryset) != 1:
        return HttpResponseForbidden()

    request_instance = request_instance_queryset[0]

    if not request_instance:
        return HttpResponseForbidden()

    if request_instance.api_token != request_api_token:
        return HttpResponseForbidden()

    running_instances = AppInstanceModel.objects.filter(is_running=True)
    stopped_instances = AppInstanceModel.objects.filter(is_running=False)

    name_fetch_result = run(["docker", "container", "ls", "-a", "--format='{{json .Names}}'"], capture_output=True, text=True)
    existing_containers_string = name_fetch_result.stdout
    existing_containers_string = existing_containers_string.replace("\"", "")
    existing_containers_string = existing_containers_string.replace("\'", "")
    existing_containers = existing_containers_string.split("\n")

    stopped_but_existing = []

    for instance in stopped_instances:
        if instance.app_name in existing_containers:
            stopped_but_existing.append({ "id": instance.pk, "name": instance.app_name })
        else:
            pass

    instances = [{ "id": x.pk, "name": x.app_name } for x in running_instances]
    instances.extend(stopped_but_existing)

    data = {
        "instances": instances
    }

    return JsonResponse(data=data)

def available_destinations(request, id):
    if (request.method != "GET"):
        return HttpResponseNotAllowed(["GET"])

    request_api_token = request.headers.get("X-API-Token")

    if not request_api_token:
        return HttpResponseForbidden()

    request_instance_queryset = AppInstanceModel.objects.filter(pk=id)

    if len(request_instance_queryset) != 1:
        return HttpResponseForbidden()

    request_instance = request_instance_queryset[0]

    if not request_instance:
        return HttpResponseForbidden()

    if request_instance.api_token != request_api_token:
        return HttpResponseForbidden()

    destinations_raw = AppConnectionModel.objects.filter(instance_from=request_instance)
    destinations_available = destinations_raw.filter(instance_to__is_running=True)
    destinations = [{ "id": x.instance_to.pk, "app_name": x.instance_to.app_name } for x in destinations_available]

    data = {
        "available_destinations": destinations
    }

    return JsonResponse(data=data)

def instance_info(request, id):
    if (request.method != "GET"):
        return HttpResponseNotAllowed(["GET"])

    request_api_token = request.headers.get("X-API-Token")

    if not request_api_token:
        return HttpResponseForbidden()

    request_instance_queryset = AppInstanceModel.objects.filter(pk=id)

    if len(request_instance_queryset) != 1:
        return HttpResponseForbidden()

    request_instance = request_instance_queryset[0]

    if not request_instance:
        return HttpResponseForbidden()

    if request_instance.api_token != request_api_token:
        return HttpResponseForbidden()

    destinations_raw = AppConnectionModel.objects.filter(instance_from=request_instance)
    destinations = [{ "id": x.instance_to.pk, "app_name": x.instance_to.app_name } for x in destinations_raw]

    data = {
        "id": request_instance.pk,
        "app_name": request_instance.app_name,
        "url_path": request_instance.url_path,
        "app_title": request_instance.app_title,
        "owner_org": {
            "id": request_instance.owner_org.pk,
            "org_name": request_instance.owner_org.org_name
        },
        "transmit_destinations": destinations
    }

    return JsonResponse(data=data)

@csrf_exempt
def get_ssh_certificate(request, id):
    if (request.method != "POST"):
        return HttpResponseNotAllowed(["POST"])

    request_api_token = request.headers.get("X-API-Token")

    if not request_api_token:
        return HttpResponseForbidden()

    request_instance_queryset = AppInstanceModel.objects.filter(pk=id)

    if len(request_instance_queryset) != 1:
        return HttpResponseForbidden()

    request_instance = request_instance_queryset[0]

    if not request_instance:
        return HttpResponseForbidden()

    if request_instance.api_token != request_api_token:
        return HttpResponseForbidden()

    data = json.loads(request.body)
    public_key = data.get("public_key")

    if not public_key or len(public_key) == 0:
        return HttpResponseForbidden()

    with tempfile.NamedTemporaryFile(mode='w+', delete=True) as pk_file:
        pk_file.write(public_key)
        pk_file.flush()

        instance_ca_path = "./ssh/instance_ca"

        run([
            "ssh-keygen",
            "-s", instance_ca_path,
            "-I", id,
            "-n", "remote",
            "-V", "+5m",
            pk_file.name
        ], check=True)

        cert_name = pk_file.name + "-cert.pub"
        cert = ""

        with open(cert_name, "r") as cert_file:
            cert = cert_file.read()

        if os.path.exists(cert_name):
            os.remove(cert_name)

    data = { "certificate": cert }

    return JsonResponse(data=data)
