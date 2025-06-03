from django import forms
from .models import OrganizationEntity, AppInstanceModel

class OrganizationEntityForm(forms.ModelForm):
    class Meta:
        model = OrganizationEntity
        fields = "__all__"

class AppInstanceForm(forms.ModelForm):
    transmit_destinations = forms.ModelMultipleChoiceField(queryset=AppInstanceModel.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = AppInstanceModel
        fields = [ "app_name", "url_path", "owner_org" ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance_arg = kwargs.get("instance", None)
        if (instance_arg):
            self.instance = instance_arg

        self.uneditable_fields = ["app_name", "url_path"]

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
