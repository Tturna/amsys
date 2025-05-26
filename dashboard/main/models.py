from django.db import models

class AppInstanceModel(models.Model):
    app_name = models.CharField(max_length=20)
    url_path = models.CharField(max_length=20)
    is_running = models.BooleanField()
    created_at = models.DateTimeField()

    def __str__(self):
        return str(self.app_name)

class AppConnectionModel(models.Model):
    instance_from = models.ForeignKey(AppInstanceModel, on_delete=models.CASCADE, related_name="instance_from")
    instance_to = models.ForeignKey(AppInstanceModel, on_delete=models.CASCADE, related_name="instance_to")
