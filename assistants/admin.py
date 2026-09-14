from django.contrib import admin

from .models import Assistant


@admin.register(Assistant)
class AssistantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'phase', 'available_courses', 'allows_custom_cases', 'order')
    list_editable = ('order',)
    list_filter = ('phase', 'allows_custom_cases')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description', 'icon_image')}),
        ('Disponibilidad', {'fields': ('phase', 'available_courses', 'allows_custom_cases', 'order')}),
        ('IA', {
            'fields': ('system_prompt', 'openai_assistant_id'),
            'description': (
                'system_prompt se envía como mensaje "system" en cada turno '
                'de la conversación (Chat Completions). El openai_assistant_id '
                'es heredado de la antigua Assistants API y ya no se usa.'
            ),
        }),
    )
