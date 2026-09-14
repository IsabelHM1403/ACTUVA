from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[('estudiante', 'Estudiante'), ('profesor', 'Profesor')],
        label='Rol',
    )
    curso = forms.ChoiceField(
        choices=[('', '---')] + [(i, f'{i}º') for i in range(1, 7)],
        required=False,
        label='Curso',
        help_text='Solo para estudiantes',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'curso', 'password1', 'password2')

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('role') == 'estudiante' and not cleaned.get('curso'):
            self.add_error('curso', 'Los estudiantes deben seleccionar su curso.')
        if cleaned.get('role') == 'profesor':
            cleaned['curso'] = None
        return cleaned
