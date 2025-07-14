from django import forms
from django.conf import settings
from .models import OrganizationEntity, AppInstanceModel, TemplateFileModel, AppPresetModel, LocationModel
import os

class OrganizationEntityForm(forms.ModelForm):
    class Meta:
        model = OrganizationEntity
        fields = "__all__"

class LocationForm(forms.ModelForm):
    class Meta:
        model = LocationModel
        fields = "__all__"
        widgets = {
            "info": forms.Textarea()
        }

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
        fields = ["app_name", "url_path", "location", "instance_directories",
                  "instance_labels", "instance_volumes", "instance_environment_variables"]
        widgets = {
            "instance_directories": forms.HiddenInput(),
            "instance_labels": forms.HiddenInput(),
            "instance_volumes": forms.HiddenInput(),
            "instance_environment_variables": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.using_compose = kwargs.get("using_compose", False)
        self.create_new_preset = kwargs.get("create_new_preset", False)
        kwargs.pop("using_compose", None)
        kwargs.pop("create_new_preset", None)

        super().__init__(*args, **kwargs)

        update_instance_template_file_selection()

        instance_arg = kwargs.get("instance", None)
        if (instance_arg):
            self.instance = instance_arg

        self.uneditable_fields = ["app_name", "url_path", "template_files"]

        # If form is created from an existing model (editing form)
        if self.instance and self.instance.pk:
            self.fields["transmit_destinations"].queryset = AppInstanceModel.objects.exclude(app_name=self.instance.app_name)

            for field in self.uneditable_fields:
                self.fields[field].widget.attrs["disabled"] = True
                # Make uneditable fields get past validation
                # as their POST values will be empty at that point
                self.fields[field].required = False
        else:
            # Don't show compose file or container image fields when editing. They can't be changed anyway.
            if self.using_compose:
                self.fields["compose_file"] = forms.FileField(label="Docker compose YAML file", widget=forms.FileInput(attrs={"accept": ".yaml, .yml"}))
                self.order_fields(["app_name", "url_path", "location", "compose_file", "template_files"])
            else:
                self.fields["container_image"] = \
                        forms.CharField(label="Docker container image name", max_length=50,
                                        strip=True, help_text="e.g. addman, nginx:1.27, debian:bookworm")
                self.fields["container_user"] = \
                        forms.CharField(label="Container user", max_length=20, strip=True,
                                        required=False,
                                        help_text="The user must exist in the container. \"root\" or an empty user will run the container as the root user.",
                                        widget=forms.TextInput(attrs={"placeholder": "username"}))
                self.order_fields(["app_name", "url_path", "location", "container_image", "template_files"])

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

class AppPresetForm(forms.Form):
    preset = forms.ModelChoiceField(queryset=AppPresetModel.objects.all(), empty_label="No preset", required=False)

    # The "preset" field should have the preset objects as available choices as well as
    # an always available default choice, "New preset", which is not an object. Choosing this
    # will break the default validation. Django automatically calls "clean_<fieldname>" for all
    # fields, but only after calling the default validators for the field, which are the part
    # that cause the validation error in our use case. For this reason, we have to override
    # the field's "clean" method. There may be a more sensible way, but this is my understanding.
    # Source (literally): https://github.com/django/django/blob/main/django/forms/forms.py
    @staticmethod
    def generate_preset_cleaner(default_clean_method):
        def clean_preset(raw_value):
            if raw_value == "new preset":
                return raw_value
            else:
                return default_clean_method(raw_value)
        return clean_preset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preset"].clean = AppPresetForm.generate_preset_cleaner(self.fields["preset"].clean)

        choices = list(self.fields["preset"].choices)
        insert_index = len(choices)
        # TODO: Consider using a "stickier" value like some constant defined in settings.py
        # or something instead of "new preset".
        choices.insert(insert_index, ("new preset", "New preset"))
        self.fields["preset"].choices = choices
