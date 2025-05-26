from django import forms
from .models import AppInstanceModel

class AppInstanceForm(forms.Form):
    app_name = forms.CharField(max_length=20, min_length=3, strip=True, label="App name")
    url_path = forms.CharField(max_length=20, min_length=0, strip=True, label="URL path", help_text="Leave empty to match app name", empty_value="", required=False)
    transmit_destinations = forms.ModelMultipleChoiceField(queryset=AppInstanceModel.objects.all(), widget=forms.CheckboxSelectMultiple)
