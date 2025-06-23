from django import forms
from django.conf import settings
from .models import OrganizationEntity, AppInstanceModel, TemplateFileModel
import os

class OrganizationEntityForm(forms.ModelForm):
    class Meta:
        model = OrganizationEntity
        fields = "__all__"

def update_instance_template_file_selection():
    files = os.listdir(settings.INSTANCE_TEMPLATE_FILES_DIR)

    template_files = TemplateFileModel.objects.all()

    for tf in template_files:
        if tf.filename not in files:
            tf.delete()

    for file in files:
        filepath = f"{settings.INSTANCE_TEMPLATE_FILES_DIR}/{file}"

        if not TemplateFileModel.objects.filter(filepath=filepath).exists():
            template_file = TemplateFileModel(filename=file, filepath=filepath)
            template_file.save()

class AppInstanceForm(forms.ModelForm):
    transmit_destinations = forms.ModelMultipleChoiceField(
            queryset=AppInstanceModel.objects.all(),
            widget=forms.CheckboxSelectMultiple,
            required=False)

    template_files = forms.ModelMultipleChoiceField(
            queryset=TemplateFileModel.objects.all(),
            widget=forms.CheckboxSelectMultiple,
            required=False)

    # This form has dynamic input fields defined in the instance creation template

    class Meta:
        model = AppInstanceModel
        fields = [ "app_name", "url_path", "owner_org", "template_files" ]

    def __init__(self, *args, **kwargs):
        self.using_compose = kwargs.get("using_compose", False)
        kwargs.pop("using_compose", None)

        super().__init__(*args, **kwargs)

        update_instance_template_file_selection()

        instance_arg = kwargs.get("instance", None)
        if (instance_arg):
            self.instance = instance_arg

        self.uneditable_fields = ["app_name", "url_path", "template_files"]

        if self.using_compose:
            self.fields["compose_file"] = forms.FileField(label="Docker compose YAML file", widget=forms.FileInput(attrs={"accept": ".yaml, .yml"}))
            self.order_fields([ "app_name", "url_path", "owner_org", "compose_file", "template_files" ])
        else:
            self.fields["container_image"] = forms.CharField(label="Docker container image name", max_length=50, strip=True, help_text="e.g. addman, nginx:1.27, debian:bookworm")
            self.order_fields([ "app_name", "url_path", "owner_org", "container_image", "template_files" ])

        # If form is created from an existing model (editing form)
        if self.instance and self.instance.pk:
            self.fields["transmit_destinations"].queryset = AppInstanceModel.objects.exclude(app_name=self.instance.app_name)

            for field in self.uneditable_fields:
                self.fields[field].widget.attrs["disabled"] = True
                # Make uneditable fields get past validation
                # as their POST values will be empty at that point
                self.fields[field].required = False

    def clean(self):
        cleaned_data = super().clean()

        # If form is created from an existing model (editing form)
        if self.instance and self.instance.pk:
            for field in self.uneditable_fields:
                old_value = getattr(self.instance, field)
                new_value = self.data.get(field)

                if new_value is not None and old_value != new_value:
                    self.add_error(field, f"Can't edit field '{field}'")
                else:
                    # Get uneditable field values from the existing
                    # instance instead of POST values
                    cleaned_data[field] = old_value

        return cleaned_data
