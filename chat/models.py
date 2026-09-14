from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assistant = models.ForeignKey('assistants.Assistant', on_delete=models.CASCADE)
    # Legacy field from the OpenAI Assistants API era — left in place so old
    # rows don't need backfilling. Chat Completions does not use threads;
    # conversation history lives in the ``Message`` table below.
    openai_thread_id = models.CharField(max_length=100, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    message_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def duration_minutes(self):
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at).total_seconds() / 60
        return 0

    def __str__(self):
        return f'{self.user.username} - {self.assistant.name} ({self.started_at:%Y-%m-%d %H:%M})'


class Message(models.Model):
    """A single user prompt or assistant reply persisted for a ChatSession.

    Replaces the prior reliance on OpenAI Assistants threads (which held the
    history server-side at OpenAI). With the Chat Completions backend the
    history is ours: each ``send_message`` call rebuilds the prompt from
    these rows, so the conversation survives page reloads and is queryable
    by teachers / stats dashboards.
    """

    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    session = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name='messages',
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['session', 'created_at'])]

    def __str__(self):
        return f'{self.role} #{self.session_id} @ {self.created_at:%Y-%m-%d %H:%M}'


class SessionFeedback(models.Model):
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='feedback')
    score = models.PositiveSmallIntegerField(help_text='Puntuación general 1-10')
    strengths = models.TextField(help_text='Puntos fuertes del estudiante')
    improvements = models.TextField(help_text='Áreas de mejora')
    summary = models.TextField(help_text='Resumen general de la evaluación')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Feedback {self.session} — {self.score}/10'
