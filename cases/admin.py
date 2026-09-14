from django.contrib import admin
from .models import ClinicalCase

@admin.register(ClinicalCase)
class ClinicalCaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'assistant', 'created_by', 'is_active', 'created_at')
    list_filter = ('assistant', 'is_active')
