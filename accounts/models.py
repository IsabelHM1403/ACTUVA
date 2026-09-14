from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ESTUDIANTE = 'estudiante', 'Estudiante'
        PROFESOR = 'profesor', 'Profesor'
        ADMIN = 'admin', 'Administrador'

    CURSO_CHOICES = [(i, f'{i}º') for i in range(1, 7)]

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ESTUDIANTE,
    )
    curso = models.PositiveSmallIntegerField(
        choices=CURSO_CHOICES,
        null=True,
        blank=True,
        help_text='Curso del estudiante (1-6). Solo para estudiantes.',
    )

    def is_estudiante(self):
        return self.role == self.Role.ESTUDIANTE

    def is_profesor(self):
        return self.role == self.Role.PROFESOR

    def is_admin_role(self):
        return self.role == self.Role.ADMIN
