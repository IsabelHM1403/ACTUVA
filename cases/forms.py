from django import forms
from .models import ClinicalCase
from assistants.models import Assistant


class ClinicalCaseForm(forms.ModelForm):
    class Meta:
        model = ClinicalCase
        fields = ('title', 'description', 'content_file', 'assistant')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assistant'].queryset = Assistant.objects.filter(allows_custom_cases=True)
        self.fields['title'].widget.attrs.update({'class': 'edu-input'})
        self.fields['description'].widget.attrs.update({'class': 'edu-input', 'rows': 4})
        self.fields['content_file'].widget.attrs.update({'class': 'edu-file'})
        self.fields['assistant'].widget.attrs.update({'class': 'edu-input'})
