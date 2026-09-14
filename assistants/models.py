from django.db import models


class Assistant(models.Model):
    class Phase(models.TextChoices):
        FUNDACIONAL = 'fundacional', 'Fase Fundacional'
        INTERMEDIA = 'intermedia', 'Fase Intermedia'
        AVANZADA = 'avanzada', 'Fase Avanzada'
        TRANSVERSAL = 'transversal', 'Transversal'
        ASIGNATURA = 'asignatura', 'Por Asignatura'

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    phase = models.CharField(max_length=20, choices=Phase.choices)
    icon_image = models.ImageField(upload_to='assistants/icons/', blank=True)
    openai_assistant_id = models.CharField(max_length=100, blank=True, help_text='ID del asistente en OpenAI (asst_xxx).')
    available_courses = models.JSONField(default=list, help_text='Lista de cursos que pueden acceder: [1,2,3]')
    allows_custom_cases = models.BooleanField(default=False)
    system_prompt = models.TextField(blank=True, help_text='Instrucciones del sistema para el asistente.')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

    def is_available_for_curso(self, curso):
        return curso in self.available_courses
