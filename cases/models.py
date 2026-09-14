from django.db import models
from django.conf import settings


class ClinicalCase(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    content_file = models.FileField(upload_to='cases/')
    assistant = models.ForeignKey('assistants.Assistant', on_delete=models.CASCADE,
                                  limit_choices_to={'allows_custom_cases': True})
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    openai_file_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.title} ({self.assistant.name})'
