from django.db import models

class AppInstanceModel(models.Model):
    app_name = models.CharField(max_length=20)
    url_path = models.CharField(max_length=20)
    is_running = models.BooleanField()
    created_at = models.DateTimeField()
