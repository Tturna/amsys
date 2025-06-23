from django.shortcuts import render, reverse, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from .models import AppInstanceModel, AppConnectionModel, OrganizationEntity, AppStatusEnum
from . import forms

from subprocess import run
from datetime import datetime
from pathlib import Path
import secrets
import tempfile
import json
import os
import docker
import shutil

def get_amsys_path():
    return Path(__file__).resolve().parent.parent

def get_instance_path(app_name):
    amsys_path = get_amsys_path()
    default_instance_base = str(amsys_path.parent)
    instance_path = os.getenv("AMSYS_INSTANCE_BASE_PATH", default_instance_base) + f"/{app_name}"

    if not os.path.exists(instance_path):
        os.mkdir(instance_path)

    return instance_path

def index(request):
    all_instances = AppInstanceModel.objects.all()
    docker_client = docker.from_env()
    instance_statuses = []

    for inst in all_instances:
        containers = []

        if inst.using_compose:
            containers = docker_client.containers.list(all=True, filters={
                "label": f"com.docker.compose.project={inst.app_name}"
            })
        else:
            containers = docker_client.containers.list(all=True, filters={
                "name": inst.app_name
            })

        if len(containers) == 0:
            if inst.status != AppStatusEnum.REMOVED.value:
                inst.status = AppStatusEnum.MISSING.value
                instance_statuses.append({
                    "instance": inst,
                    "status": AppStatusEnum(inst.status).name,
                    "target_containers": [],
                    "status_message": "Instance corrupted! Containers are missing. Data may be recoverable.",
                    "is_error": True
                })
            else:
                instance_statuses.append({
                    "instance": inst,
                    "status": AppStatusEnum(inst.status).name,
                    "target_containers": [],
                    "status_message": "Containers removed.",
                    "is_error": True
                })
            
            continue

        stopped_containers = []
        running_containers = []

        for c in containers:
            if c.status == "running":
                running_containers.append(c.name)
            else:
                inst.status = AppStatusEnum.STOPPED.value
                stopped_containers.append(c.name)

        if len(stopped_containers) == 0:
            inst.status = AppStatusEnum.RUNNING.value

            instance_statuses.append({
                "instance": inst,
                "status": AppStatusEnum(inst.status).name,
                "target_containers": running_containers,
                "status_message": "All containers running",
                "is_error": False
            })
        elif len(running_containers) == 0:
            instance_statuses.append({
                "instance": inst,
                "status": AppStatusEnum(inst.status).name,
                "target_containers": stopped_containers,
                "status_message": "Containers are stopped",
                "is_error": False
            })
        elif len(stopped_containers) > 0 and len(running_containers) > 0:
            # This should only happen when running with compose and not
            # all containers are working
            inst.status = AppStatusEnum.ERROR.value

            instance_statuses.append({
                "instance": inst,
                "status": AppStatusEnum(inst.status).name,
                "target_containers": stopped_containers,
                "status_message": "Some containers are not running!",
                "is_error": True
            })
        else:
            inst.status = AppStatusEnum.ERROR.value

            instance_statuses.append({
                "instance": inst,
                "status": AppStatusEnum(inst.status).name,
                "target_containers": [],
                "status_message": "AMSYS error. This should never happen.",
                "is_error": True
            })

    organizations = OrganizationEntity.objects.all()

    proxy_containers = docker_client.containers.list(filters={
        "name": "amsys-traefik"
    })

    is_proxy_running = len(proxy_containers) == 1

    context = {
        "organizations": organizations,
        "instance_statuses": instance_statuses,
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

def create_app_from_image(request, form, app_name, url_path, api_token, app_instance, instance_path):
    container_image = form.cleaned_data["container_image"]

    env_keys = request.POST.getlist("env_entry_key[]")
    env_vals = request.POST.getlist("env_entry_val[]")
    label_keys = request.POST.getlist("label_entry_key[]")
    label_vals = request.POST.getlist("label_entry_val[]")
    volume_keys = request.POST.getlist("volume_entry_key[]")
    volume_vals = request.POST.getlist("volume_entry_val[]")

    env_entries = list(zip(env_keys, env_vals))
    label_entries = list(zip(label_keys, label_vals))
    volume_entries = list(zip(volume_keys, volume_vals))

    env = {
        "AMSYS_APP_NAME": app_name,
        "AMSYS_API_TOKEN": api_token,
        "AMSYS_APP_ID": str(app_instance.pk)
    }

    for entry in env_entries:
        env[entry[0]] = entry[1]

    labels = {
        "traefik.enable": "true",
        f"traefik.http.routers.{app_name}-router.rule": f"PathPrefix(\"/{url_path}\")",
        f"traefik.http.services.{app_name}-service.loadbalancer.server.port": "8000",
        f"traefik.http.middlewares.{app_name}-strip.stripprefix.prefixes": f"/{url_path}",
        f"traefik.http.routers.{app_name}-router.middlewares": f"{app_name}-strip@docker"
    }

    for entry in label_entries:
        labels[entry[0]] = entry[1]

    amsys_path = get_amsys_path()

    volumes = {
        f"{amsys_path}/ssh/instance_ca.pub": { "bind": "/etc/ssh/instance_ca.pub", "mode": "ro" }
    }

    for entry in volume_entries:
        volumes[f"{instance_path}/{entry[0]}"] = {
            "bind": entry[1],
            "mode": "rw"
        }

    docker_client = docker.from_env()

    try:
        docker_client.containers.run(
            image=container_image,
            environment=env,
            labels=labels,
            volumes=volumes,
            detach=True,
            network="amsys-net",
            name=app_name)
    except docker.errors.ImageNotFound:
        return False
    except docker.errors.APIError:
        return False

    return True

def create_app_from_compose(request, instance_path, app_name):
    compose_file = request.FILES["compose_file"]

    with open(f"{instance_path}/docker-compose.yaml", "wb+") as destination:
        for chunk in compose_file.chunks():
            destination.write(chunk)

    # Set the compose project name with -p so it can be used to filter container lists.
    # This way the compose file can create containers with any name and still the amsys
    # app can find them.
    start_compose_result = run(["docker", "compose", "-p", app_name, "up", "-d"], cwd=instance_path, capture_output=True, text=True)

    if start_compose_result.returncode != 0:
        print(start_compose_result.stdout)
        print(start_compose_result.stderr)
        return False

    return True

@login_required
@permission_required("main.add_appinstancemodel")
def create_app_instance(request, using_compose=False):
    if request.method == "GET":
        form = forms.AppInstanceForm(using_compose=using_compose)

        if not using_compose:
            return render(request, "create_instance.html", { "form": form })
        else:
            return render(request, "create_compose_instance.html", { "form": form })

    if request.method != "POST":
        return HttpResponseRedirect(reverse("index"))

    # Handle POST request
    form = forms.AppInstanceForm(request.POST, request.FILES, using_compose=using_compose)

    if (not form.is_valid()):
        if not using_compose:
            return render(request, "create_instance.html", { "form": form })
        else:
            return render(request, "create_compose_instance.html", { "form": form })

    app_name = form.cleaned_data["app_name"]

    if len(AppInstanceModel.objects.filter(app_name=app_name)) > 0:
        # TODO: error msg, already exists
        if not using_compose:
            return render(request, "create_instance.html", { "form": form })
        else:
            return render(request, "create_compose_instance.html", { "form": form })

    url_path = form.cleaned_data["url_path"]
    owner_org = form.cleaned_data["owner_org"]
    transmit_destinations = form.cleaned_data["transmit_destinations"]
    template_files = form.cleaned_data["template_files"]

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
                                    owner_org=owner_org, status=AppStatusEnum.RUNNING.value,
                                    created_at=datetime_now, api_token=api_token,
                                    using_compose=using_compose)
    app_instance.save()
    app_instance.template_files.set(template_files)
    app_instance.save()

    amsys_path = get_amsys_path()
    instance_path = get_instance_path(app_name)

    for template_file in template_files:
        shutil.copy(template_file.filepath, f"{instance_path}/{template_file.filename}")

    dir_vals = request.POST.getlist("dir_entry[]")
    dir_entries = list(dir_vals)

    # TODO: make sure the user doesn't create any weird directories outside the instance dir
    for dir_path in dir_entries:
        path_in_instance = f"{instance_path}/{dir_path}"
        if not os.path.exists(path_in_instance):
            os.makedirs(path_in_instance)

    started_successfully = False

    if using_compose:
        started_successfully = create_app_from_compose(request, instance_path, app_name)
    else:
        started_successfully = create_app_from_image(request, form, app_name, url_path, api_token, app_instance, instance_path)

    if not started_successfully:
        # TODO: error msg
        print("app startup failed")
        app_instance.delete()

        if not using_compose:
            return render(request, "create_instance.html", { "form": form })
        else:
            return render(request, "create_compose_instance.html", { "form": form })

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
    docker_client = docker.from_env()

    instance_path = get_instance_path(app_name)

    if (instance.using_compose):
        stop_compose_result = run(["docker", "compose", "-p", app_name, "stop"], cwd=instance_path, capture_output=True, text=True)

        if stop_compose_result.returncode != 0:
            print(stop_compose_result.stdout)
            print(stop_compose_result.stderr)
            return HttpResponseRedirect(reverse("index"))
    else:
        app_container = docker_client.containers.get(app_name)
        app_container.stop()

    instance.status = AppStatusEnum.STOPPED.value
    instance.save()

    return HttpResponse(status=204)

@login_required
@permission_required("main.change_appinstancemodel")
def start_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    docker_client = docker.from_env()

    instance_path = get_instance_path(app_name)

    if (instance.using_compose):
        start_compose_result = run(["docker", "compose", "-p", app_name, "start"], cwd=instance_path, capture_output=True, text=True)

        if start_compose_result.returncode != 0:
            print(start_compose_result.stdout)
            print(start_compose_result.stderr)
            return HttpResponseRedirect(reverse("index"))
    else:
        app_container = docker_client.containers.get(app_name)
        app_container.start()

    instance.status = AppStatusEnum.RUNNING.value
    instance.save()

    return HttpResponse(status=204)

@login_required
@permission_required("main.change_appinstancemodel")
def restart_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    docker_client = docker.from_env()

    instance_path = get_instance_path(app_name)

    if (instance.using_compose):
        remove_compose_result = run(["docker", "compose", "-p", app_name, "kill"], cwd=instance_path, capture_output=True, text=True)

        if remove_compose_result.returncode != 0:
            print(remove_compose_result.stdout)
            print(remove_compose_result.stderr)
            return HttpResponseRedirect(reverse("index"))
    else:
        app_container = docker_client.containers.get(app_name)
        app_container.remove(v=True, force=True)

    # TODO: Ensure the app name can't change the instance path to something weird
    shutil.rmtree(instance_path)

    instance.status = AppStatusEnum.REMOVED.value
    instance.save()
    
    # TODO: Recreate instance from saved parameters

@login_required
@permission_required("main.delete_appinstancemodel")
def remove_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    docker_client = docker.from_env()

    instance_path = get_instance_path(app_name)

    if (instance.using_compose):
        remove_compose_result = run(["docker", "compose", "-p", app_name, "down"], cwd=instance_path, capture_output=True, text=True)

        if remove_compose_result.returncode != 0:
            print(remove_compose_result.stdout)
            print(remove_compose_result.stderr)
            return HttpResponseRedirect(reverse("index"))
    else:
        app_container = docker_client.containers.get(app_name)
        app_container.remove(v=True, force=True)

    # TODO: Ensure the app name can't change the instance path to something weird
    shutil.rmtree(instance_path)

    instance.status = AppStatusEnum.REMOVED.value
    instance.save()

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

@login_required
@permission_required("main.change_appinstancemodel")
def forget_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    instance.delete()

    return HttpResponse(status=204)

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
    destinations_available = destinations_raw.filter(instance_to__status=AppStatusEnum.RUNNING.value)
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
