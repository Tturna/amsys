from django.contrib import admin
from .models import AppInstanceModel, OrganizationEntity, AppPresetModel, TemplateFileModel, AppConnectionModel

admin.site.register(AppInstanceModel)
admin.site.register(OrganizationEntity)
admin.site.register(AppPresetModel)
admin.site.register(TemplateFileModel)
admin.site.register(AppConnectionModel)
