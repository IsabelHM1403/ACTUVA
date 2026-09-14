from django.contrib import admin

from .models import (
    DiagnosisCombo,
    FlipCard,
    IrrelevantItem,
    Module,
    ModuleProgress,
    Patient,
    PatientQuote,
    QuizAttempt,
    QuizChoice,
    QuizQuestion,
    Step,
    StepDxFeedback,
    StudentEvent,
    Video,
    VideoCollection,
    VideoSection,
    VirtualPatient,
)


# --- Inlines ---

class PatientInline(admin.TabularInline):
    model = Patient
    extra = 0


class StepInline(admin.TabularInline):
    model = Step
    extra = 0


class DiagnosisComboInline(admin.TabularInline):
    model = DiagnosisCombo
    extra = 0


class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0


class VirtualPatientInline(admin.TabularInline):
    model = VirtualPatient
    extra = 0


class PatientQuoteInline(admin.TabularInline):
    model = PatientQuote
    extra = 0


class FlipCardInline(admin.TabularInline):
    model = FlipCard
    extra = 0


class IrrelevantItemInline(admin.TabularInline):
    model = IrrelevantItem
    extra = 0


class StepDxFeedbackInline(admin.TabularInline):
    model = StepDxFeedback
    extra = 0


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 0


# --- ModelAdmins ---

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'group', 'order')
    list_filter = ('group',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [
        PatientInline,
        StepInline,
    ]


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'age', 'diagnosis')
    list_filter = ('module',)
    search_fields = ('name', 'diagnosis')
    inlines = [PatientQuoteInline]


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ('module', 'n', 'title')
    list_filter = ('module',)
    search_fields = ('title',)
    inlines = [FlipCardInline, IrrelevantItemInline, StepDxFeedbackInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('module', 'order', 'text')
    list_filter = ('module',)
    inlines = [QuizChoiceInline]


@admin.register(VirtualPatient)
class VirtualPatientAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'module', 'age', 'assistant')
    list_filter = ('module',)
    search_fields = ('display_name',)


@admin.register(DiagnosisCombo)
class DiagnosisComboAdmin(admin.ModelAdmin):
    list_display = ('module', 'dx', 'compat', 'order')
    list_filter = ('module', 'compat')


# --- Tracking admins ---

@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'started_at', 'completed_at', 'last_step')
    list_filter = ('module',)


@admin.register(StudentEvent)
class StudentEventAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'event_type', 'timestamp')
    list_filter = ('event_type', 'module')
    readonly_fields = ('timestamp',)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'module', 'score', 'total', 'submitted_at')
    list_filter = ('module',)


# --- Video collections (small CMS for YouTube playlist landing pages) ---

class VideoInline(admin.TabularInline):
    model = Video
    extra = 0
    fields = ('order', 'badge_number', 'youtube_id', 'title', 'chip_label', 'duration_label')


class VideoSectionInline(admin.StackedInline):
    model = VideoSection
    extra = 0
    show_change_link = True


@admin.register(VideoCollection)
class VideoCollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')
    inlines = [VideoSectionInline]
    fieldsets = (
        (None, {'fields': ('slug', 'name', 'blurb', 'thumb_video_id', 'order', 'accent_color')}),
        ('Hero', {'fields': (
            'hero_title', 'hero_title_emphasis', 'hero_subtitle',
            'hero_stat_count', 'hero_stat_count_caption',
            'hero_stat_origin', 'hero_stat_origin_caption',
            'notice',
        )}),
        ('Vídeo introductorio', {'fields': (
            'intro_video_id', 'intro_eyebrow', 'intro_title',
            'intro_description', 'intro_badge_number',
        )}),
    )


@admin.register(VideoSection)
class VideoSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'collection', 'order')
    list_filter = ('collection',)
    inlines = [VideoInline]


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'youtube_id', 'order')
    list_filter = ('section__collection', 'section')
    search_fields = ('title', 'youtube_id')
