from django.contrib import admin

from .models import ChatSession, Message, SessionFeedback


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('role', 'content', 'created_at')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Messages are written by the chat backend during a session — adding
        # them by hand from the admin would just confuse the chat history.
        return False


class SessionFeedbackInline(admin.StackedInline):
    model = SessionFeedback
    extra = 0
    readonly_fields = ('created_at',)
    can_delete = True


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'assistant', 'started_at', 'ended_at', 'message_count', 'is_active')
    list_filter = ('assistant', 'is_active')
    search_fields = ('user__username', 'assistant__name')
    readonly_fields = ('openai_thread_id', 'started_at', 'ended_at', 'message_count')
    inlines = [MessageInline, SessionFeedbackInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'short_content', 'created_at')
    list_filter = ('role', 'session__assistant')
    search_fields = ('content',)
    readonly_fields = ('session', 'role', 'content', 'created_at')

    def short_content(self, obj):
        return (obj.content or '')[:80] + ('…' if obj.content and len(obj.content) > 80 else '')
    short_content.short_description = 'Content'


@admin.register(SessionFeedback)
class SessionFeedbackAdmin(admin.ModelAdmin):
    list_display = ('session', 'score', 'created_at')
    list_filter = ('score',)
    search_fields = ('session__user__username',)
    readonly_fields = ('created_at',)
