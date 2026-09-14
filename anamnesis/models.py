from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


COMPAT_CHOICES = [
    ('neutral', 'Neutral'),
    ('positive', 'Positive'),
    ('strong', 'Strong'),
]


class Module(models.Model):
    class Group(models.TextChoices):
        CARDIORESPIRATORY = 'cardio', 'Cardiorrespiratorios'
        DIGESTIVE_URINARY = 'digestive', 'Digestivos y urinarios'
        NEUROLOGICAL = 'neuro', 'Sistema nervioso'
        GENERAL = 'general', 'Síntomas generales'

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    emoji = models.CharField(max_length=8, blank=True)
    gradient_from = models.CharField(max_length=8, default='#003973')
    gradient_to = models.CharField(max_length=8, default='#00509e')
    deco_code = models.CharField(max_length=8, blank=True)
    group = models.CharField(max_length=20, choices=Group.choices)
    order = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['group', 'order']

    def __str__(self):
        return self.name


class Patient(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='patients')
    name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField()
    diagnosis = models.CharField(max_length=200)
    diagnosis_key = models.JSONField(default=list)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return f'{self.name} — {self.module.name}'


class PatientQuote(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='quotes')
    step_number = models.PositiveSmallIntegerField()
    text = models.TextField()

    class Meta:
        unique_together = [('patient', 'step_number')]
        ordering = ['patient', 'step_number']

    def __str__(self):
        return f'{self.patient.name} #{self.step_number}'


class Step(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='steps')
    n = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    example_question = models.TextField(blank=True)
    think_box = models.TextField(blank=True)
    tip_box = models.TextField(blank=True)
    sec_label = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = [('module', 'n')]
        ordering = ['module', 'n']

    def __str__(self):
        return f'{self.module.slug}#{self.n} — {self.title}'


class FlipCard(models.Model):
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='flip_cards')
    label = models.CharField(max_length=200)
    badge = models.CharField(max_length=50, blank=True)
    back_text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['step', 'order']

    def __str__(self):
        return self.label


class IrrelevantItem(models.Model):
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='irrelevant_items')
    name = models.CharField(max_length=200)
    badge = models.CharField(max_length=50, blank=True)
    body_text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['step', 'order']

    def __str__(self):
        return self.name


class StepDxFeedback(models.Model):
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name='dx_feedbacks')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='dx_feedbacks')
    quote_idx = models.PositiveSmallIntegerField()
    compat = models.CharField(max_length=10, choices=COMPAT_CHOICES)
    evidence = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
    )
    interpretation = models.TextField()
    fits_for = models.JSONField(default=list)
    rules_out = models.JSONField(default=list)

    class Meta:
        unique_together = [('step', 'patient', 'quote_idx')]

    def __str__(self):
        return f'{self.step} / {self.patient.name} (#{self.quote_idx})'


class DiagnosisCombo(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='diagnosis_combos')
    dx = models.CharField(max_length=200)
    compat = models.CharField(max_length=10, choices=COMPAT_CHOICES)
    symptoms = models.JSONField(default=list)
    key_text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return f'{self.dx} ({self.module.slug})'


class QuizQuestion(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quiz_questions')
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return f'Q{self.order} ({self.module.slug})'


class QuizChoice(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['question', 'order']

    def __str__(self):
        return self.text


class VirtualPatient(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='virtual_patients')
    assistant = models.ForeignKey(
        'assistants.Assistant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='virtual_patients',
    )
    display_name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField()
    persona_summary = models.TextField()
    card_blurb = models.CharField(
        max_length=300, blank=True,
        help_text='Public-facing short description shown on the patient card. '
                  'Must NOT mention the diagnosis — that is for the LLM persona only.',
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['module', 'order']

    def __str__(self):
        return self.display_name


class ModuleProgress(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='module_progress',
    )
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='progress_entries')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_step = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [('student', 'module')]

    def is_completed(self):
        return bool(self.completed_at)

    def __str__(self):
        return f'{self.student} → {self.module.slug}'


class StudentEvent(models.Model):
    class EventType(models.TextChoices):
        STEP_OPEN = 'step_open', 'Step opened'
        FLIP = 'flip', 'Flip card flipped'
        KNEW = 'knew', 'Marked as known'
        UNKNOWN = 'unknown', 'Marked as unknown'
        QUIZ_ANSWER = 'quiz_answer', 'Quiz answered'
        DX_VIEW = 'dx_view', 'Diagnosis viewed'
        COMPLETE = 'complete', 'Module completed'
        VP_OPEN = 'vp_open', 'Virtual patient opened'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='anamnesis_events',
    )
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    payload = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['module', 'event_type']),
            models.Index(fields=['student', 'module']),
        ]

    def __str__(self):
        return f'{self.student} {self.event_type} {self.module.slug} @ {self.timestamp:%Y-%m-%d %H:%M}'


class QuizAttempt(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts',
    )
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.PositiveSmallIntegerField()
    total = models.PositiveSmallIntegerField()
    answers = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['student', 'module']),
            models.Index(fields=['module']),  # for teacher metrics aggregation
        ]

    def __str__(self):
        return f'{self.student} {self.module.slug} {self.score}/{self.total}'


# ----------------------------------------------------------------------------
# Video collections — small CMS so admins can curate YouTube playlists
# (e.g. "Anamnesis y Exploración Física en vídeo", "Ponerse en la piel del
# paciente") through /admin/ instead of hard-coding cards in the template.
# ----------------------------------------------------------------------------

class VideoCollection(models.Model):
    """A curated set of YouTube videos shown as its own internal page.

    Two of these ship out of the box (data-migrated): the structure/symptoms
    video collection and the "10 errores" patient-perspective set. Admins can
    add more without code changes — sections + videos are inlined editable.
    """

    slug = models.SlugField(unique=True, help_text='URL part: /anamnesis/coleccion/<slug>/')
    name = models.CharField(max_length=120, help_text='Short label used in dashboard cards.')
    blurb = models.CharField(
        max_length=300,
        help_text='Short description for the dashboard card.',
    )
    thumb_video_id = models.CharField(
        max_length=20, blank=True,
        help_text='YouTube ID used for the dashboard card thumbnail.',
    )

    # Hero on the collection page itself
    hero_title = models.CharField(max_length=200)
    hero_title_emphasis = models.CharField(
        max_length=120, blank=True,
        help_text='Optional italic/colored fragment of the hero title.',
    )
    hero_subtitle = models.TextField(blank=True)
    hero_stat_count = models.CharField(
        max_length=40, blank=True,
        help_text='e.g. "11 vídeos"',
    )
    hero_stat_count_caption = models.CharField(max_length=80, blank=True)
    hero_stat_origin = models.CharField(
        max_length=40, blank=True, default='UVa Online',
    )
    hero_stat_origin_caption = models.CharField(
        max_length=120, blank=True, default='Dir. Luis Corral Gudino',
    )

    # Introductory ("presentación") video, rendered as a wide hero card
    intro_video_id = models.CharField(max_length=20, blank=True)
    intro_eyebrow = models.CharField(max_length=80, blank=True)
    intro_title = models.CharField(max_length=200, blank=True)
    intro_description = models.TextField(blank=True)
    intro_badge_number = models.CharField(max_length=8, blank=True, default='00')

    notice = models.CharField(
        max_length=400, blank=True,
        help_text='Optional yellow notice line shown under the hero.',
    )
    accent_color = models.CharField(
        max_length=8, default='#003973',
        help_text='Brand color used for section pips and play-buttons.',
    )

    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class VideoSection(models.Model):
    """A subgroup of videos inside a collection (e.g. "Estructura", "Los 10 errores")."""

    collection = models.ForeignKey(
        VideoCollection, on_delete=models.CASCADE, related_name='sections',
    )
    title = models.CharField(max_length=200)
    pip_color = models.CharField(
        max_length=8, default='#003973',
        help_text='Color of the small pip next to the section title.',
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['collection', 'order']

    def __str__(self):
        return f'{self.collection.slug} / {self.title}'


class Video(models.Model):
    """A single YouTube video card inside a VideoSection."""

    section = models.ForeignKey(
        VideoSection, on_delete=models.CASCADE, related_name='videos',
    )
    youtube_id = models.CharField(max_length=20, help_text='The "v=" parameter from the YouTube URL.')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    badge_number = models.CharField(
        max_length=10, blank=True,
        help_text='Small overlay on the thumbnail, e.g. "01" / "Error 03".',
    )
    duration_label = models.CharField(
        max_length=20, blank=True,
        help_text='Optional duration hint shown above the title (e.g. "<1 min").',
    )
    chip_label = models.CharField(
        max_length=30, blank=True,
        help_text='Optional red chip above the title (e.g. "Error 01").',
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['section', 'order']

    def __str__(self):
        return self.title

    @property
    def youtube_url(self):
        return f'https://www.youtube.com/watch?v={self.youtube_id}'

    @property
    def thumbnail_url(self):
        return f'https://img.youtube.com/vi/{self.youtube_id}/mqdefault.jpg'
