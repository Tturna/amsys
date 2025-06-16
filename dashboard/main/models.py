from django.db import models

class OrganizationEntity(models.Model):
    org_name = models.CharField(max_length=20, verbose_name="Organization name")

    def __str__(self):
        return str(self.org_name)

class AppInstanceModel(models.Model):
    app_name = models.CharField(max_length=20, verbose_name="App name")
    url_path = models.CharField(max_length=20, verbose_name="URL path", blank=True, help_text="Leave empty to match app name")
    app_title = models.CharField(max_length=20, verbose_name="App title", help_text="e.g. \"ADDMAN EXT\" or \"ADDMAN OEM B\"")
    owner_org = models.ForeignKey(OrganizationEntity, on_delete=models.CASCADE, verbose_name="Owner organization")
    is_running = models.BooleanField()
    created_at = models.DateTimeField()
    api_token = models.CharField(max_length=20)

    def __str__(self):
        return str(self.app_name)

class AppConnectionModel(models.Model):
    instance_from = models.ForeignKey(AppInstanceModel, on_delete=models.CASCADE, related_name="instance_from")
    instance_to = models.ForeignKey(AppInstanceModel, on_delete=models.CASCADE, related_name="instance_to")
