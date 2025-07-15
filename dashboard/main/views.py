from typing import List, Tuple
from django.shortcuts import render, reverse, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, HttpResponseForbidden, HttpResponseBadRequest, JsonResponse
from django.core.files.uploadedfile import UploadedFile
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.forms.models import model_to_dict
from django import forms as django_forms
from .models import AppInstanceModel, AppConnectionModel, AppPresetModel, LocationModel, OrganizationEntity, AppStatusEnum, TemplateFileModel
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

def is_proxy_running():
    docker_client = docker.from_env()
    proxy_containers = docker_client.containers.list(filters={
        "name": "amsys-traefik"
    })

    return len(proxy_containers) == 1

def get_instance_statuses(instances=None):
    docker_client = docker.from_env()
    instance_statuses = []

    if instances is None:
        instances = AppInstanceModel.objects.all()

    for inst in instances:
        containers_raw = []

        if inst.using_compose:
            containers_raw = docker_client.containers.list(all=True, filters={
                "label": f"com.docker.compose.project={inst.app_name}"
            })
        else:
            # This will match all containers where their name includes the given string.
            # For example, if app name is "test", this will return "app_test",
            # "test_db", and "testing_container" if they exist.
            containers_raw = docker_client.containers.list(all=True, filters={
                "name": inst.app_name
            })

        containers = []

        for c in containers_raw:
            if c.name != inst.app_name:
                # Skip containers that don't exactly match the app name
                continue
            containers.append(c)

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

    return instance_statuses

@login_required
def index(request):
    instance_statuses = get_instance_statuses()
    organizations = OrganizationEntity.objects.all()
    locations = LocationModel.objects.all()

    context = {
        "organizations": organizations,
        "locations": locations,
        "instance_statuses": instance_statuses,
        "is_proxy_running": is_proxy_running()
    }

    if "preset" in request.session:
        del request.session["preset"]

    return render(request, "index.html", context)

@login_required
def organizations(request):
    orgs = OrganizationEntity.objects.all()

    return render(request, "organizations.html", { "organizations": orgs })

@login_required
def locations(request):
    locations = LocationModel.objects.all()
    organizations = OrganizationEntity.objects.all()

    context = {
        "locations": locations,
        "organizations": organizations,
        "is_proxy_running": is_proxy_running()
    }

    return render(request, "locations.html", context)

@login_required
def presets(request):
    presets = AppPresetModel.objects.all()
    locations = LocationModel.objects.all()

    context = {
        "presets": presets,
        "locations": locations
    }

    return render(request, "presets.html", context)

@login_required
def view_organization(request, org_name):
    organization = get_object_or_404(OrganizationEntity, org_name=org_name)
    locations = LocationModel.objects.filter(owner_org=organization)

    context = {
        "org": organization,
        "locations": locations,
        "is_proxy_running": is_proxy_running()
    }

    if "preset" in request.session:
        del request.session["preset"]

    return render(request, "view_organization.html", context)

@login_required
def view_location(request, location_name):
    location = get_object_or_404(LocationModel, location_name=location_name)
    connected_apps = AppInstanceModel.objects.filter(location=location)
    instance_statuses = get_instance_statuses(connected_apps)

    context = {
        "location": location,
        "instance_statuses": instance_statuses,
        "is_proxy_running": is_proxy_running()
    }

    if "preset" in request.session:
        del request.session["preset"]

    return render(request, "view_location.html", context)

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
            messages.error(request, "Invalid form")
            return render(request, "create_organization.html", { "form": form })

    return HttpResponseRedirect(reverse("index"))

@login_required
@permission_required("main.delete_organizationentity")
def remove_organization(request, organization_pk):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    org = get_object_or_404(OrganizationEntity, pk=organization_pk)
    org.delete()

    return HttpResponse(status=204)

@login_required
@permission_required("main.add_organizationentitymodel")
def create_location(request):
    if request.method == "GET":
        form = forms.LocationForm()

        return render(request, "create_location.html", { "form": form })

    if request.method == "POST":
        form = forms.LocationForm(request.POST)

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(reverse("index"))
        else:
            messages.error(request, "Invalid form")
            return render(request, "create_location.html", { "form": form })

    return HttpResponseRedirect(reverse("index"))

@login_required
@permission_required("main.delete_locationmodel")
def remove_location(request, location_pk):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    location = get_object_or_404(LocationModel, pk=location_pk)
    location.delete()

    return HttpResponse(status=204)

class ImageBasedAppAdvancedSettings:
    def __init__(self, env_vars = [], labels = [], volumes = []) -> None:
        self.env_vars: List[Tuple[str, str]] = env_vars
        self.labels: List[Tuple[str, str]] = labels
        self.volumes: List[Tuple[str, str]] = volumes

    @classmethod
    def from_instance(cls, instance: AppInstanceModel) -> 'ImageBasedAppAdvancedSettings':
        env_dict = json.loads(instance.instance_environment_variables)
        labels_dict = json.loads(instance.instance_labels)
        volumes_dict = json.loads(instance.instance_volumes)
        env_vars = [(key, env_dict[key]) for key in env_dict.keys()]
        labels = [(key, labels_dict[key]) for key in labels_dict.keys()]
        volumes = [(key, volumes_dict[key]) for key in volumes_dict.keys()]

        return cls(env_vars=env_vars, labels=labels, volumes=volumes)

    def set_env_vars(self, env_keys: List[str], env_vals: List[str]) -> None:
        self.env_vars = list(zip(env_keys, env_vals))

    def set_labels(self, label_keys: List[str], label_vals: List[str]) -> None:
        self.labels = list(zip(label_keys, label_vals))

    def set_volumes(self, volume_keys: List[str], volume_vals: List[str]) -> None:
        self.volumes = list(zip(volume_keys, volume_vals))

def create_app_from_image(advanced_settings: ImageBasedAppAdvancedSettings, container_image: str, container_user: str, app_name: str, url_path: str, api_token: str, app_instance: AppInstanceModel, instance_path: str, template_files: List[TemplateFileModel], preset_name: str | None = None):
    if container_user == "root" or container_user == "root:root":
        container_user = ""

    # preset_name = request.POST.get("preset_name", None)

    env_entries = advanced_settings.env_vars
    label_entries = advanced_settings.labels
    volume_entries = advanced_settings.volumes

    env = {
        # TODO: Rename this env var to AMSYS_URL_PATH.
        # This is what apps use to determine the path where they are hosted.
        "AMSYS_APP_NAME": url_path,
        "AMSYS_API_TOKEN": api_token,
        "AMSYS_APP_ID": str(app_instance.pk)
    }

    env_json_string = "{"

    for entry in env_entries:
        env[entry[0]] = entry[1]
        env_json_string += f"\"{entry[0]}\": \"{entry[1]}\","

    # Replace last comma with closing curly brace
    if env_json_string[-1:] == ",":
        env_json_string = env_json_string[:-1]

    env_json_string += "}"

    labels = {
        "traefik.enable": "true",
        f"traefik.http.routers.{app_name}-router.rule": f"PathPrefix(\"/{url_path}\")",
        f"traefik.http.services.{app_name}-service.loadbalancer.server.port": "8000",
        f"traefik.http.middlewares.{app_name}-strip.stripprefix.prefixes": f"/{url_path}",
        f"traefik.http.routers.{app_name}-router.middlewares": f"{app_name}-strip@docker"
    }

    labels_json_string = "{"

    for entry in label_entries:
        labels[entry[0]] = entry[1]
        labels_json_string += f"\"{entry[0]}\": \"{entry[1]}\","

    if labels_json_string[-1:] == ",":
        labels_json_string = labels_json_string[:-1]

    labels_json_string += "}"

    amsys_path = get_amsys_path()

    volumes = {
        f"{amsys_path}/ssh/instance_ca.pub": { "bind": "/etc/ssh/instance_ca.pub", "mode": "ro" }
    }

    volumes_json_string = "{"

    for entry in volume_entries:
        volumes[f"{instance_path}/{entry[0]}"] = {
            "bind": entry[1],
            "mode": "rw"
        }
        volumes_json_string += f"\"{entry[0]}\": \"{entry[1]}\","

    if volumes_json_string[-1:] == ",":
        volumes_json_string = volumes_json_string[:-1]

    volumes_json_string += "}"

    app_instance.instance_environment_variables = env_json_string
    app_instance.instance_labels = labels_json_string
    app_instance.instance_volumes = volumes_json_string
    app_instance.save()

    docker_client = docker.from_env()

    try:
        docker_client.containers.run(
            image=container_image,
            environment=env,
            labels=labels,
            volumes=volumes,
            detach=True,
            network="amsys-net",
            user=container_user,
            name=app_name)
    except docker.errors.ImageNotFound:
        print(f"Container image '{container_image}' not found.")
        return False
    except docker.errors.APIError as e:
        print("Docker API error:")
        print(e)

        try:
            app_container = docker_client.containers.get(app_name)
            app_container.remove(force=True)
        except:
            pass

        return False

    if preset_name is not None:
        preset = AppPresetModel(
            preset_name=preset_name,
            container_image=container_image,
            container_user=container_user,
            instance_directories=app_instance.instance_directories,
            instance_labels=app_instance.instance_labels,
            instance_volumes=app_instance.instance_volumes,
            instance_environment_variables=app_instance.instance_environment_variables)

        preset.save()
        preset.template_files.set(template_files)
        preset.save()

    return True

def create_app_from_compose(compose_file: UploadedFile, instance_path: str, app_name: str):
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
        init_preset = request.session.get("preset", None)
        form = None
        preset_form = None

        if init_preset:
            if init_preset != "new preset":
                preset = get_object_or_404(AppPresetModel, pk=init_preset)
                form = forms.AppInstanceForm(initial={
                        "container_image": preset.container_image,
                        "container_user": preset.container_user,
                        "template_files": preset.template_files.all(),
                        "instance_directories": preset.instance_directories,
                        "instance_labels": preset.instance_labels,
                        "instance_volumes": preset.instance_volumes,
                        "instance_environment_variables": preset.instance_environment_variables
                    },
                    using_compose=False)
            else:
                form = forms.AppInstanceForm(using_compose=using_compose)
                form.fields["preset_name"] = django_forms.CharField(max_length=20, required=True)
                # Insert preset name into crispy forms layout. See the full layout in forms.py
                form.helper.layout.insert(0, "preset_name")

            preset_form = forms.AppPresetForm({"preset": init_preset})
        elif not using_compose:
            preset_form = forms.AppPresetForm()

        if form is None:
            form = forms.AppInstanceForm(using_compose=using_compose)

        context = {
            "form": form,
            "preset_form": preset_form
        }

        if not using_compose:
            return render(request, "create_instance.html", context)
        else:
            return render(request, "create_compose_instance.html", context)

    if request.method != "POST":
        return HttpResponseRedirect(reverse("index"))

    # Handle POST request
    form = forms.AppInstanceForm(request.POST, request.FILES, using_compose=using_compose)

    if (not form.is_valid()):
        messages.error(request, "Invalid form")
        if not using_compose:
            return render(request, "create_instance.html", { "form": form })
        else:
            return render(request, "create_compose_instance.html", { "form": form })

    app_name = form.cleaned_data["app_name"]

    if len(AppInstanceModel.objects.filter(app_name=app_name)) > 0:
        messages.error(request, f"App with name '{app_name}' already exists.")

        if not using_compose:
            return render(request, "create_instance.html", { "form": form })
        else:
            return render(request, "create_compose_instance.html", { "form": form })

    url_path = form.cleaned_data["url_path"]

    if len(AppInstanceModel.objects.filter(url_path=url_path)) > 0:
        messages.error(request, f"App with URL path '{url_path}' already exists.")

        if not using_compose:
            return render(request, "create_instance.html", { "form": form })
        else:
            return render(request, "create_compose_instance.html", { "form": form })

    location = form.cleaned_data["location"]
    transmit_destinations = form.cleaned_data["transmit_destinations"]
    template_files = form.cleaned_data["template_files"]
    container_image = form.cleaned_data.get("container_image", "")
    container_user = form.cleaned_data.get("container_user", "")

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
                                    location=location, status=AppStatusEnum.RUNNING.value,
                                    created_at=datetime_now, api_token=api_token,
                                    using_compose=using_compose, container_image=container_image,
                                    container_user=container_user)
    app_instance.save()
    app_instance.template_files.set(template_files)

    instance_path = get_instance_path(app_name)

    for template_file in template_files:
        shutil.copy(template_file.filepath, f"{instance_path}/{template_file.filename}")

    dir_vals = request.POST.getlist("dir_entry[]")
    dir_entries = list(dir_vals)

    app_instance.instance_directories = str(dir_entries).replace("'", "\"")
    app_instance.save()

    # TODO: make sure the user doesn't create any weird directories outside the instance dir
    for dir_path in dir_entries:
        path_in_instance = f"{instance_path}/{dir_path}"
        if not os.path.exists(path_in_instance):
            os.makedirs(path_in_instance)

    started_successfully = False

    if using_compose:
        compose_file = request.FILES["compose_file"]
        started_successfully = create_app_from_compose(compose_file, instance_path, app_name)
    else:
        advanced_settings = ImageBasedAppAdvancedSettings()

        env_keys = request.POST.getlist("env_entry_key[]")
        env_vals = request.POST.getlist("env_entry_val[]")
        label_keys = request.POST.getlist("label_entry_key[]")
        label_vals = request.POST.getlist("label_entry_val[]")
        volume_keys = request.POST.getlist("volume_entry_key[]")
        volume_vals = request.POST.getlist("volume_entry_val[]")

        advanced_settings.set_env_vars(env_keys, env_vals)
        advanced_settings.set_labels(label_keys, label_vals)
        advanced_settings.set_volumes(volume_keys, volume_vals)

        preset_name = request.POST.get("preset_name", None)

        started_successfully = create_app_from_image(advanced_settings, container_image, container_user, app_name, url_path, api_token, app_instance, instance_path, template_files, preset_name)

    if not started_successfully:
        messages.error(request, "App didn't start succesfully")
        print("app startup failed")
        app_instance.delete()

        if not using_compose:
            return render(request, "create_instance.html", { "form": form })
        else:
            return render(request, "create_compose_instance.html", { "form": form })

    del request.session["preset"]

    # Dashboard will always know which instances can transmit to which.
    # Instances should always ask what they can do before trying to do things.
    for dest in transmit_destinations:
        connection = AppConnectionModel(instance_from=app_instance, instance_to=dest)
        connection.save()

    messages.success(request, "App started successfully")
    return HttpResponseRedirect(reverse("index"))

@login_required
def apply_preset(request):
    preset_form = forms.AppPresetForm(request.POST)

    if preset_form.is_valid():
        preset = preset_form.cleaned_data["preset"]

        if isinstance(preset, AppPresetModel):
            request.session["preset"] = preset.pk
        else:
            request.session["preset"] = preset
    else:
        messages.error(request, "Invalid preset")

    return HttpResponseRedirect(reverse("create_app_instance"))

@login_required
@permission_required("main.delete_apppresetmodel")
def remove_preset(request, preset_pk):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    preset = get_object_or_404(AppPresetModel, pk=preset_pk)
    preset.delete()

    return HttpResponse(status=204)

@login_required
@permission_required("main.change_appinstancemodel")
def stop_instance(request, app_name, should_kill=False):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    docker_client = docker.from_env()

    instance_path = get_instance_path(app_name)

    if (instance.using_compose):
        command = None

        if should_kill:
            command = ["docker", "compose", "-p", app_name, "kill"]
        else:
            command = ["docker", "compose", "-p", app_name, "stop"]

        stop_compose_result = run(command, cwd=instance_path, capture_output=True, text=True)

        if stop_compose_result.returncode != 0:
            messages.error(request, f"App failed to stop. Error code {stop_compose_result.returncode}")
            print(stop_compose_result.stdout)
            print(stop_compose_result.stderr)
            return HttpResponseRedirect(reverse("index"))
    else:
        try:
            app_container = docker_client.containers.get(app_name)

            if should_kill:
                app_container.kill()
            else:
                app_container.stop()
        except docker.errors.NotFound:
            messages.error(request, "App container not found! Some data may be lost.")
            instance.status = AppStatusEnum.MISSING.value
            instance.save()

            return HttpResponse(status=204)
        except docker.errors.APIError:
            messages.error(request, "Container API error. Try again later.")
            return HttpResponse(status=500)

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
            messages.error(request, f"Failed to start instance. Error code {start_compose_result.returncode}")
            print(start_compose_result.stdout)
            print(start_compose_result.stderr)
            return HttpResponseRedirect(reverse("index"))
    else:
        try:
            app_container = docker_client.containers.get(app_name)
            app_container.start()
        except docker.errors.NotFound:
            messages.error(request, "App container not found! Some data may be lost.")
            instance.status = AppStatusEnum.MISSING.value
            instance.save()

            return HttpResponse(status=204)
        except docker.errors.APIError:
            messages.error(request, "Container API error. Try again later.")
            return HttpResponse(status=500)

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
            messages.error(request, f"Failed to restart instance. Error code {remove_compose_result.returncode}")
            print(remove_compose_result.stdout)
            print(remove_compose_result.stderr)
            return HttpResponseRedirect(reverse("index"))
    else:
        try:
            app_container = docker_client.containers.get(app_name)
            app_container.remove(v=True, force=True)
        except docker.errors.NotFound:
            messages.error(request, "App container not found! Some data may be lost.")
        except docker.errors.APIError:
            messages.error(request, "Container API error. Try again later or contact an administrator.")
            return HttpResponse(status=500)

    # TODO: Ensure the app name can't change the instance path to something weird
    shutil.rmtree(instance_path)

    instance.status = AppStatusEnum.REMOVED.value
    instance.save()

    os.makedirs(instance_path)

    for template_file in instance.template_files.all():
        shutil.copy(template_file.filepath, f"{instance_path}/{template_file.filename}")

    dir_entries = json.loads(instance.instance_directories)

    for dir_path in dir_entries:
        path_in_instance = f"{instance_path}/{dir_path}"
        if not os.path.exists(path_in_instance):
            os.makedirs(path_in_instance)

    started_successfully = False
    
    if (instance.using_compose):
        compose_file = request.FILES["compose_file"]
        started_successfully = create_app_from_compose(compose_file, instance_path, instance.app_name)
    else:

        advanced_settings = ImageBasedAppAdvancedSettings.from_instance(instance=instance)
        started_successfully = create_app_from_image(advanced_settings, instance.container_image,
                              instance.container_user, instance.app_name, instance.url_path,
                              instance.api_token, instance, instance_path, instance.template_files.all())

    if not started_successfully:
        messages.error(request, "App didn't restart succesfully")
        print("app restart failed")
        instance.status = AppStatusEnum.ERROR.value
        instance.save()

        return HttpResponseRedirect(reverse("index"))

    messages.success(request, "App restarted successfully")
    return HttpResponseRedirect(reverse("index"))

@login_required
@permission_required("main.delete_appinstancemodel")
def remove_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    docker_client = docker.from_env()

    instance_path = get_instance_path(app_name)

    if (instance.using_compose):
        remove_compose_result = run(["docker", "compose", "-p", app_name, "down"], cwd=instance_path, capture_output=True, text=True)

        if remove_compose_result.returncode != 0:
            messages.error(request, f"Failed to remove instance. Error code {remove_compose_result.returncode}")
            print(remove_compose_result.stdout)
            print(remove_compose_result.stderr)
            return HttpResponseRedirect(reverse("index"))
    else:
        try:
            app_container = docker_client.containers.get(app_name)
            app_container.remove(v=True, force=True)
        except docker.errors.NotFound:
            messages.error(request, "App container not found! Removing data.")
        except docker.errors.APIError:
            messages.error(request, "Container API error. Try again later.")
            return HttpResponse(status=500)

    # TODO: Ensure the app name can't change the instance path to something weird
    shutil.rmtree(instance_path)

    instance.status = AppStatusEnum.REMOVED.value
    instance.save()

    return HttpResponse(status=204)

@login_required
def view_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    available_transmit_destinations = AppConnectionModel.objects.filter(instance_from=instance)

    context = {
        "instance": instance,
        "destinations": available_transmit_destinations
    }

    if "preset" in request.session:
        del request.session["preset"]

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
            messages.error(request, "Invalid form")

            context = {
                "instance": instance,
                "form": form
            }

            return render(request, "edit_instance.html", context)
    else:
        return HttpResponseRedirect(reverse("index"))

@login_required
@permission_required("main.change_appinstancemodel")
def forget_instance(request, app_name):
    instance = get_object_or_404(AppInstanceModel, app_name=app_name)
    instance.delete()

    return HttpResponse(status=204)

@login_required
def map(request):
    instances = AppInstanceModel.objects.all()
    location_entries = list(LocationModel.objects.values())

    for index in range(len(location_entries)):
        location_entries[index].update({ "apps": [] })

    for inst in instances:
        location_dict = model_to_dict(inst.location)
        inst_dict = model_to_dict(inst, fields=["app_name", "url_path"])

        for entry in location_entries:
            if location_dict["id"] == entry["id"]:
                apps = entry["apps"]
                apps.append(inst_dict)
                entry["apps"] = apps
                break

    locations_data = json.dumps(location_entries, default=str)

    connections = AppConnectionModel.objects.all()
    connection_pair_coordinates = []

    for connection in connections:
        instance_from = connection.instance_from
        instance_to = connection.instance_to
        location_from = instance_from.location
        location_to = instance_to.location

        if location_from is location_to:
            continue

        from_coordinates = [location_from.latitude, location_from.longitude]
        to_coordinates = [location_to.latitude, location_to.longitude]
        pair = [from_coordinates, to_coordinates]
        connection_pair_coordinates.append(pair)

    connections_data = json.dumps(connection_pair_coordinates, default=str)

    context = {
        "locations": locations_data,
        "connections": connections_data
    }

    if "preset" in request.session:
        del request.session["preset"]

    return render(request, "map.html", context)

@login_required
def proxy(request):
    proxy_fetch_result = run(["docker", "container", "ls", "--format='{{json .Names}}'"], capture_output=True, text=True)

    if (proxy_fetch_result.returncode != 0):
        messages.error(request, "Failed to fetch proxy status.")

        context = {
            "is_proxy_running": False
        }

        return render(request, "proxy.html", context)

    proxy_fetch_string = proxy_fetch_result.stdout
    proxy_fetch_string = proxy_fetch_string.replace("\"", "")
    proxy_fetch_string = proxy_fetch_string.replace("\'", "")
    running_containers = proxy_fetch_string.split("\n")

    is_proxy_running = "amsys-traefik" in running_containers

    context = {
        "is_proxy_running": is_proxy_running
    }

    if "preset" in request.session:
        del request.session["preset"]

    return render(request, "proxy.html", context)

@login_required
@permission_required("main.change_appinstancemodel")
def start_proxy(request):
    start_result = run(["./scripts/start-proxy.sh"], capture_output=True, text=True)

    print(start_result.stdout)
    if (start_result.returncode != 0):
        messages.error(request, f"Proxy failed to start. Error code {start_result.returncode}")
        return HttpResponseRedirect(reverse("index"))

    return HttpResponse(status=204)

@login_required
@permission_required("main.change_appinstancemodel")
def stop_proxy(request):
    stop_result = run(["./scripts/stop-proxy.sh"], capture_output=True, text=True)

    if (stop_result.returncode != 0):
        messages.error(request, f"Proxy failed to stop. Error code {stop_result.returncode}")
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

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Malformatted JSON data. Make sure the data is encapsulated with {} or [].")
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
