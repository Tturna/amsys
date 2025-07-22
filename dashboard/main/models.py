from django.db import models
from django.conf import settings
from enum import Enum

class OrganizationEntity(models.Model):
    org_name = models.CharField(max_length=20, verbose_name="Organization name")
    nationality = models.CharField(max_length=100)

    def __str__(self):
        return str(self.org_name)

class LocationModel(models.Model):
    location_name = models.CharField(max_length=100, verbose_name="Location name")
    owner_org = models.ForeignKey(OrganizationEntity, on_delete=models.CASCADE, verbose_name="Owner organization")
    code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=16)
    longitude = models.DecimalField(max_digits=20, decimal_places=16)
    info = models.CharField(max_length=500, verbose_name="Additional information", blank=True)

    def __str__(self):
        return str(self.location_name)

def instance_template_files():
    return settings.INSTANCE_TEMPLATE_FILES_DIR

class TemplateFileModel(models.Model):
    filename = models.CharField(max_length=512)
    filepath = models.CharField(max_length=512)

    def __str__(self):
        return str(self.filename)

class AppStatusEnum(Enum):
    RUNNING = 1
    PAUSED  = 2
    STOPPED = 3
    REMOVED = 4
    MISSING = 5
    ERROR   = 6

    @classmethod
    def as_tuple_list(cls):
        return [(x.name, x.value) for x in list(cls)]

class AppInstanceModel(models.Model):
    app_name = models.CharField(max_length=20, verbose_name="App name")
    url_path = models.CharField(max_length=20, verbose_name="URL path", blank=True, help_text="Leave empty to match app name")
    location = models.ForeignKey(LocationModel, on_delete=models.CASCADE)
    template_files = models.ManyToManyField(TemplateFileModel)
    status = models.IntegerField(choices=AppStatusEnum.as_tuple_list())
    created_at = models.DateTimeField()
    api_token = models.CharField(max_length=20)
    using_compose = models.BooleanField()
    container_image = models.CharField(max_length=50, blank=True)
    container_user = models.CharField(max_length=50, blank=True)
    # These should contain JSON formatted data:
    instance_directories = models.CharField(max_length=1024, blank=True)
    instance_labels = models.CharField(max_length=1024, blank=True)
    instance_volumes = models.CharField(max_length=1024, blank=True)
    instance_environment_variables = models.CharField(max_length=1024, blank=True)

    def __str__(self):
        return str(self.app_name)

class AppConnectionModel(models.Model):
    instance_from = models.ForeignKey(AppInstanceModel, on_delete=models.CASCADE, related_name="instance_from")
    instance_to = models.ForeignKey(AppInstanceModel, on_delete=models.CASCADE, related_name="instance_to")

class AppPresetModel(models.Model):
    preset_name = models.CharField(max_length=20, verbose_name="Preset name")
    container_image = models.CharField(max_length=20)
    container_user = models.CharField(max_length=50)
    template_files = models.ManyToManyField(TemplateFileModel)
    # These should contain JSON formatted data:
    instance_directories = models.CharField(max_length=1024, blank=True)
    instance_labels = models.CharField(max_length=1024, blank=True)
    instance_volumes = models.CharField(max_length=1024, blank=True)
    instance_environment_variables = models.CharField(max_length=1024, blank=True)

    def __str__(self):
        return str(self.preset_name)
