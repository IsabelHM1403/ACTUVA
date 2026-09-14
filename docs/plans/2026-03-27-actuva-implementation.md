# ACTUVa Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Django web app where medical students chat with 6 AI assistants (OpenAI Assistants API), professors upload clinical cases, and admins view usage stats. All UI in Spanish.

**Architecture:** Django 5.x monolith with 5 apps (accounts, assistants, chat, cases, stats). OpenAI Assistants API for AI conversations with SSE streaming. Tailwind CSS via CDN for frontend (same design as borrador_web.html). SQLite for dev.

**Tech Stack:** Python 3.12, Django 5.1, openai SDK, Tailwind CSS (CDN), HTMX for dynamic UI, SSE for chat streaming.

---

## Task 1: Project Bootstrap & Git Init

**Files:**
- Create: `requirements.txt`
- Create: `actuva/` (Django project)
- Create: `.gitignore`
- Create: `.env.example`

**Step 1: Initialize git repo**

```bash
cd D:/PycharmProjects/anamnesio
git init
```

**Step 2: Create .gitignore**

```
__pycache__/
*.py[cod]
*.sqlite3
.env
media/
staticfiles/
node_modules/
*.pyc
db.sqlite3
.DS_Store
```

**Step 3: Create requirements.txt**

```
Django>=5.1,<6.0
openai>=1.30,<2.0
python-dotenv>=1.0
Pillow>=10.0
```

**Step 4: Install dependencies**

Run: `pip install -r requirements.txt`

**Step 5: Create Django project**

Run: `django-admin startproject actuva .`

This creates `manage.py` and `actuva/` in the project root (D:/PycharmProjects/anamnesio/).

**Step 6: Create .env.example**

```
OPENAI_API_KEY=sk-your-key-here
DJANGO_SECRET_KEY=change-me-in-production
DEBUG=True
```

**Step 7: Configure settings.py for .env loading**

In `actuva/settings.py`, add at the very top after imports:

```python
from dotenv import load_dotenv
import os

load_dotenv()
```

Replace `SECRET_KEY` line with:
```python
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-insecure-key-change-in-prod')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
```

Set language and timezone:
```python
LANGUAGE_CODE = 'es'
TIME_ZONE = 'Europe/Madrid'
```

Add to `TEMPLATES[0]['OPTIONS']['context_processors']`:
```python
'assistants.context_processors.assistant_list',
```

**Step 8: Verify server starts**

Run: `python manage.py runserver`
Expected: Django welcome page at http://127.0.0.1:8000/

**Step 9: Commit**

```bash
git add .gitignore requirements.txt manage.py actuva/ .env.example docs/
git commit -m "feat: bootstrap Django project with settings and dependencies"
```

---

## Task 2: Accounts App — Custom User Model

**Files:**
- Create: `accounts/` app
- Create: `accounts/models.py`
- Create: `accounts/admin.py`
- Create: `accounts/forms.py`
- Create: `accounts/views.py`
- Create: `accounts/urls.py`
- Create: `templates/accounts/login.html`
- Create: `templates/accounts/register.html`
- Test: `accounts/tests.py`

**Step 1: Create app**

Run: `python manage.py startapp accounts`

**Step 2: Write the User model**

`accounts/models.py`:
```python
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
```

**Step 3: Register in settings**

In `actuva/settings.py`:
- Add `'accounts'` to `INSTALLED_APPS`
- Add `AUTH_USER_MODEL = 'accounts.User'`
- Add `LOGIN_URL = '/cuentas/login/'`
- Add `LOGIN_REDIRECT_URL = '/panel/'`
- Add `LOGOUT_REDIRECT_URL = '/'`

**Step 4: Write test**

`accounts/tests.py`:
```python
from django.test import TestCase
from accounts.models import User


class UserModelTest(TestCase):
    def test_create_estudiante(self):
        user = User.objects.create_user(
            username='est1', password='testpass123',
            role='estudiante', curso=3,
        )
        self.assertTrue(user.is_estudiante())
        self.assertEqual(user.curso, 3)

    def test_create_profesor(self):
        user = User.objects.create_user(
            username='prof1', password='testpass123',
            role='profesor',
        )
        self.assertTrue(user.is_profesor())
        self.assertIsNone(user.curso)

    def test_curso_nullable_for_non_students(self):
        user = User.objects.create_user(
            username='admin1', password='testpass123',
            role='admin',
        )
        self.assertIsNone(user.curso)
```

**Step 5: Migrate and test**

```bash
python manage.py makemigrations accounts
python manage.py migrate
python manage.py test accounts
```
Expected: 3 tests pass.

**Step 6: Admin registration**

`accounts/admin.py`:
```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'curso', 'is_active')
    list_filter = ('role', 'curso', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('ACTUVa', {'fields': ('role', 'curso')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('ACTUVa', {'fields': ('role', 'curso')}),
    )
```

**Step 7: Registration and login forms**

`accounts/forms.py`:
```python
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
```

**Step 8: Views**

`accounts/views.py`:
```python
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = form.cleaned_data['role']
            curso = form.cleaned_data.get('curso')
            user.curso = int(curso) if curso else None
            user.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})
```

**Step 9: URLs**

`accounts/urls.py`:
```python
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('registro/', views.register_view, name='register'),
]
```

In `actuva/urls.py`:
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cuentas/', include('accounts.urls')),
]
```

**Step 10: Create templates** (minimal — full styling comes in Task 6)

Create `templates/` directory at project root. Add to `settings.py` TEMPLATES DIRS:
```python
TEMPLATES = [{
    ...
    'DIRS': [BASE_DIR / 'templates'],
    ...
}]
```

`templates/base.html`:
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{% block title %}ACTUVa{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
    tailwind.config = {
        theme: {
            extend: {
                colors: {
                    "primary": "#1A5F7A",
                    "brand-yellow": "#FFCC00",
                },
                fontFamily: {
                    "headline": ["Manrope", "sans-serif"],
                    "body": ["Inter", "sans-serif"],
                },
            },
        },
    }
    </script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Manrope:wght@600;700;800&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
</head>
<body class="bg-gray-50 font-body text-gray-900">
    {% block content %}{% endblock %}
</body>
</html>
```

`templates/accounts/login.html`:
```html
{% extends "base.html" %}
{% block title %}Iniciar Sesión — ACTUVa{% endblock %}
{% block content %}
<div class="min-h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-2xl shadow-lg w-full max-w-md">
        <h1 class="text-2xl font-headline font-bold text-primary mb-6 text-center">Iniciar Sesión</h1>
        <form method="post">
            {% csrf_token %}
            {% for field in form %}
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ field.label }}</label>
                <input type="{{ field.field.widget.input_type|default:'text' }}"
                       name="{{ field.html_name }}"
                       value="{{ field.value|default:'' }}"
                       class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                       {% if field.field.required %}required{% endif %}/>
                {% for error in field.errors %}
                <p class="text-red-500 text-xs mt-1">{{ error }}</p>
                {% endfor %}
            </div>
            {% endfor %}
            <button type="submit" class="w-full py-3 bg-primary text-white font-bold rounded-lg hover:bg-primary/90">Entrar</button>
        </form>
        <p class="text-center text-sm text-gray-500 mt-4">
            ¿No tienes cuenta? <a href="{% url 'register' %}" class="text-primary font-bold">Regístrate</a>
        </p>
    </div>
</div>
{% endblock %}
```

`templates/accounts/register.html`:
```html
{% extends "base.html" %}
{% block title %}Registro — ACTUVa{% endblock %}
{% block content %}
<div class="min-h-screen flex items-center justify-center py-12">
    <div class="bg-white p-8 rounded-2xl shadow-lg w-full max-w-md">
        <h1 class="text-2xl font-headline font-bold text-primary mb-6 text-center">Crear Cuenta</h1>
        <form method="post">
            {% csrf_token %}
            {% for field in form %}
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ field.label }}</label>
                {% if field.field.widget.input_type == 'select' or field.name == 'role' or field.name == 'curso' %}
                <select name="{{ field.html_name }}"
                        class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary">
                    {% for value, label in field.field.choices %}
                    <option value="{{ value }}" {% if field.value|stringformat:"s" == value|stringformat:"s" %}selected{% endif %}>{{ label }}</option>
                    {% endfor %}
                </select>
                {% else %}
                <input type="{{ field.field.widget.input_type|default:'text' }}"
                       name="{{ field.html_name }}"
                       value="{{ field.value|default:'' }}"
                       class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary"
                       {% if field.field.required %}required{% endif %}/>
                {% endif %}
                {% if field.help_text %}
                <p class="text-gray-400 text-xs mt-1">{{ field.help_text }}</p>
                {% endif %}
                {% for error in field.errors %}
                <p class="text-red-500 text-xs mt-1">{{ error }}</p>
                {% endfor %}
            </div>
            {% endfor %}
            <button type="submit" class="w-full py-3 bg-primary text-white font-bold rounded-lg hover:bg-primary/90">Registrarse</button>
        </form>
        <p class="text-center text-sm text-gray-500 mt-4">
            ¿Ya tienes cuenta? <a href="{% url 'login' %}" class="text-primary font-bold">Inicia sesión</a>
        </p>
    </div>
</div>
{% endblock %}
```

**Step 11: Commit**

```bash
git add accounts/ templates/ actuva/
git commit -m "feat: accounts app with custom User model, registration, login"
```

---

## Task 3: Assistants App — Model & Seed Data

**Files:**
- Create: `assistants/` app
- Create: `assistants/models.py`
- Create: `assistants/admin.py`
- Create: `assistants/management/commands/seed_assistants.py`
- Create: `assistants/context_processors.py`
- Test: `assistants/tests.py`

**Step 1: Create app**

Run: `python manage.py startapp assistants`

Add `'assistants'` to `INSTALLED_APPS` in settings.

**Step 2: Write model**

`assistants/models.py`:
```python
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
    openai_assistant_id = models.CharField(
        max_length=100, blank=True,
        help_text='ID del asistente en OpenAI (asst_xxx). Se rellena con el comando create_assistants.',
    )
    available_courses = models.JSONField(
        default=list,
        help_text='Lista de cursos que pueden acceder: [1,2,3]',
    )
    allows_custom_cases = models.BooleanField(default=False)
    system_prompt = models.TextField(
        blank=True,
        help_text='Instrucciones del sistema para el asistente. Placeholder hasta extraer de Custom GPTs.',
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

    def is_available_for_curso(self, curso):
        return curso in self.available_courses
```

**Step 3: Write test**

`assistants/tests.py`:
```python
from django.test import TestCase
from assistants.models import Assistant


class AssistantModelTest(TestCase):
    def setUp(self):
        self.asst = Assistant.objects.create(
            name='Anamnesio', slug='anamnesio',
            description='Historia clínica',
            phase='fundacional',
            available_courses=[1, 2],
            allows_custom_cases=False,
            order=1,
        )

    def test_available_for_curso(self):
        self.assertTrue(self.asst.is_available_for_curso(1))
        self.assertTrue(self.asst.is_available_for_curso(2))
        self.assertFalse(self.asst.is_available_for_curso(3))

    def test_str(self):
        self.assertEqual(str(self.asst), 'Anamnesio')
```

**Step 4: Migrate and test**

```bash
python manage.py makemigrations assistants
python manage.py migrate
python manage.py test assistants
```

**Step 5: Seed command**

Create `assistants/management/__init__.py` and `assistants/management/commands/__init__.py` (empty files).

`assistants/management/commands/seed_assistants.py`:
```python
from django.core.management.base import BaseCommand
from assistants.models import Assistant


ASSISTANTS_DATA = [
    {
        'name': 'Anamnesio',
        'slug': 'anamnesio',
        'description': 'Entrevista clínica y estructura de historia. Aprende a preguntar lo que importa para orientar el caso.',
        'phase': 'fundacional',
        'available_courses': [1, 2],
        'allows_custom_cases': False,
        'order': 1,
        'system_prompt': 'Eres Anamnesio, un asistente de IA para la práctica de la anamnesis clínica. Tu rol es simular un paciente virtual para que el estudiante de medicina practique la entrevista clínica. Responde como un paciente real respondería. Al final de la sesión, proporciona retroalimentación formativa sobre la estructura y calidad de la anamnesis. Usa el método socrático. No des la respuesta directamente.',
    },
    {
        'name': 'ExplorIA',
        'slug': 'exploria',
        'description': 'Tutor socrático de exploración física. Te guía sobre cómo realizar la maniobra y qué buscar.',
        'phase': 'intermedia',
        'available_courses': [1, 2, 3, 4],
        'allows_custom_cases': False,
        'order': 2,
        'system_prompt': 'Eres ExplorIA, un tutor socrático de exploración física. Guías al estudiante sobre las secuencias de exploración, maniobras y hallazgos sin dar directamente la respuesta. Pregunta al estudiante qué exploraría, en qué orden y qué busca. Proporciona retroalimentación al final.',
    },
    {
        'name': 'Diferencialio',
        'slug': 'diferencialio',
        'description': 'Diagnóstico diferencial y priorización justificada. Conecta hallazgos con probabilidades reales.',
        'phase': 'intermedia',
        'available_courses': [3, 4, 5, 6],
        'allows_custom_cases': True,
        'order': 3,
        'system_prompt': 'Eres Diferencialio, un asistente para la práctica del diagnóstico diferencial. Presentas casos clínicos y guías al estudiante para construir y priorizar diagnósticos diferenciales por niveles de probabilidad y gravedad, justificando cada decisión clínica. Usa el método socrático.',
    },
    {
        'name': 'DecisionIA',
        'slug': 'decisonia',
        'description': 'Toma de decisiones clínicas, diagnóstico, tratamiento y seguimiento en escenarios complejos.',
        'phase': 'avanzada',
        'available_courses': [5, 6],
        'allows_custom_cases': True,
        'order': 4,
        'system_prompt': 'Eres DecisionIA, un asistente para la práctica de toma de decisiones clínicas. Presentas escenarios clínicos complejos donde el estudiante debe elegir conductas clínicas, asumir consecuencias y razonar alternativas en escenarios de incertidumbre real. Usa el método socrático.',
    },
    {
        'name': 'EmpatIA',
        'slug': 'empatia',
        'description': 'Comunicación difícil y vulnerable. Practica la gestión de malas noticias y situaciones de vulnerabilidad.',
        'phase': 'transversal',
        'available_courses': [1, 2, 3, 4, 5, 6],
        'allows_custom_cases': True,
        'order': 5,
        'system_prompt': 'Eres EmpatIA, un asistente para la práctica de comunicación clínica empática. Simulas situaciones de vulnerabilidad, barreras idiomáticas, violencia de género o malas noticias. El estudiante debe practicar comunicación difícil en un entorno seguro. Proporciona retroalimentación sobre empatía y comunicación.',
    },
    {
        'name': 'ReumatIA',
        'slug': 'reumatia',
        'description': 'Asistente socrático para el repaso de Reumatología y enfermedades autoinmunes sistémicas.',
        'phase': 'asignatura',
        'available_courses': [1, 2, 3, 4, 5, 6],
        'allows_custom_cases': True,
        'order': 6,
        'system_prompt': 'Eres ReumatIA, un asistente socrático para el repaso de Reumatología y enfermedades autoinmunes sistémicas. Ayudas al estudiante a repasar contenido teórico, resolver escenarios clínicos y practicar preguntas tipo test. Usa el método socrático para promover el razonamiento activo.',
    },
]


class Command(BaseCommand):
    help = 'Seed the 6 M3RGE-AI assistants into the database'

    def handle(self, *args, **options):
        for data in ASSISTANTS_DATA:
            obj, created = Assistant.objects.update_or_create(
                slug=data['slug'],
                defaults=data,
            )
            status = 'Creado' if created else 'Actualizado'
            self.stdout.write(f'{status}: {obj.name}')
        self.stdout.write(self.style.SUCCESS('Seed completado.'))
```

**Step 6: Context processor**

`assistants/context_processors.py`:
```python
from assistants.models import Assistant


def assistant_list(request):
    return {'all_assistants': Assistant.objects.all()}
```

**Step 7: Admin**

`assistants/admin.py`:
```python
from django.contrib import admin
from .models import Assistant


@admin.register(Assistant)
class AssistantAdmin(admin.ModelAdmin):
    list_display = ('name', 'phase', 'available_courses', 'allows_custom_cases', 'order')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}
```

**Step 8: Run seed and verify**

```bash
python manage.py seed_assistants
```
Expected: 6 lines "Creado: [name]"

**Step 9: Commit**

```bash
git add assistants/
git commit -m "feat: assistants app with model, seed data for 6 M3RGE-AI assistants"
```

---

## Task 4: Chat App — OpenAI Integration & Streaming

**Files:**
- Create: `chat/` app
- Create: `chat/models.py`
- Create: `chat/views.py`
- Create: `chat/urls.py`
- Create: `chat/openai_client.py`
- Create: `templates/chat/session.html`
- Test: `chat/tests.py`

**Step 1: Create app**

Run: `python manage.py startapp chat`

Add `'chat'` to `INSTALLED_APPS`. Add `OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')` to settings.

**Step 2: ChatSession model**

`chat/models.py`:
```python
from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assistant = models.ForeignKey('assistants.Assistant', on_delete=models.CASCADE)
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
```

**Step 3: Migrate**

```bash
python manage.py makemigrations chat
python manage.py migrate
```

**Step 4: OpenAI client wrapper**

`chat/openai_client.py`:
```python
from openai import OpenAI
from django.conf import settings


def get_client():
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def create_assistant(name, instructions, model='gpt-4o-mini'):
    client = get_client()
    assistant = client.beta.assistants.create(
        name=name,
        instructions=instructions,
        model=model,
    )
    return assistant.id


def create_thread():
    client = get_client()
    thread = client.beta.threads.create()
    return thread.id


def send_message_streaming(thread_id, assistant_id, user_message):
    """Generator that yields text chunks from the assistant response."""
    client = get_client()
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role='user',
        content=user_message,
    )
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
    ) as stream:
        for text in stream.text_deltas:
            yield text
```

**Step 5: Views**

`chat/views.py`:
```python
import json
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_POST
from assistants.models import Assistant
from .models import ChatSession
from . import openai_client


@login_required
def start_session(request, assistant_slug):
    assistant = get_object_or_404(Assistant, slug=assistant_slug)

    # Check course access
    if request.user.is_estudiante() and not assistant.is_available_for_curso(request.user.curso):
        return render(request, 'chat/no_access.html', {'assistant': assistant})

    # Close any existing active session with this assistant
    ChatSession.objects.filter(
        user=request.user, assistant=assistant, is_active=True,
    ).update(is_active=False, ended_at=timezone.now())

    # Create OpenAI thread
    thread_id = openai_client.create_thread()

    session = ChatSession.objects.create(
        user=request.user,
        assistant=assistant,
        openai_thread_id=thread_id,
    )
    return redirect('chat_session', session_id=session.id)


@login_required
def chat_session_view(request, session_id):
    session = get_object_or_404(
        ChatSession, id=session_id, user=request.user, is_active=True,
    )
    return render(request, 'chat/session.html', {
        'session': session,
        'assistant': session.assistant,
    })


@login_required
@require_POST
def send_message(request, session_id):
    session = get_object_or_404(
        ChatSession, id=session_id, user=request.user, is_active=True,
    )
    body = json.loads(request.body)
    user_message = body.get('message', '').strip()
    if not user_message:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    assistant_id = session.assistant.openai_assistant_id
    if not assistant_id:
        return JsonResponse({'error': 'Asistente no configurado en OpenAI'}, status=500)

    def event_stream():
        try:
            for chunk in openai_client.send_message_streaming(
                session.openai_thread_id, assistant_id, user_message,
            ):
                yield f'data: {json.dumps({"text": chunk})}\n\n'
            yield 'data: {"done": true}\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    # Increment message count
    session.message_count += 2  # user + assistant
    session.save(update_fields=['message_count'])

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_POST
def end_session(request, session_id):
    session = get_object_or_404(
        ChatSession, id=session_id, user=request.user, is_active=True,
    )
    session.is_active = False
    session.ended_at = timezone.now()
    session.save(update_fields=['is_active', 'ended_at'])
    return redirect('dashboard')
```

**Step 6: URLs**

`chat/urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path('iniciar/<slug:assistant_slug>/', views.start_session, name='start_session'),
    path('sesion/<int:session_id>/', views.chat_session_view, name='chat_session'),
    path('sesion/<int:session_id>/enviar/', views.send_message, name='send_message'),
    path('sesion/<int:session_id>/terminar/', views.end_session, name='end_session'),
]
```

In `actuva/urls.py`, add:
```python
path('chat/', include('chat.urls')),
```

**Step 7: Chat template**

`templates/chat/session.html`:
```html
{% extends "base.html" %}
{% block title %}{{ assistant.name }} — ACTUVa{% endblock %}
{% block content %}
<div class="flex flex-col h-screen">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-4">
            {% if assistant.icon_image %}
            <img src="{{ assistant.icon_image.url }}" alt="{{ assistant.name }}" class="w-10 h-10 rounded-full"/>
            {% endif %}
            <div>
                <h1 class="font-headline font-bold text-lg text-primary">{{ assistant.name }}</h1>
                <p class="text-xs text-gray-500">{{ assistant.get_phase_display }}</p>
            </div>
        </div>
        <form method="post" action="{% url 'end_session' session.id %}">
            {% csrf_token %}
            <button type="submit" class="px-4 py-2 text-sm bg-red-50 text-red-600 rounded-lg hover:bg-red-100 font-medium">
                Terminar Sesión
            </button>
        </form>
    </header>

    <!-- Messages -->
    <div id="messages" class="flex-1 overflow-y-auto px-6 py-6 space-y-4">
        <div class="flex gap-3 items-start">
            <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary text-sm font-bold shrink-0">AI</div>
            <div class="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3 max-w-[80%]">
                <p class="text-sm">¡Hola! Soy <strong>{{ assistant.name }}</strong>. {{ assistant.description }} ¿Empezamos?</p>
            </div>
        </div>
    </div>

    <!-- Input -->
    <div class="bg-white border-t border-gray-200 px-6 py-4">
        <form id="chat-form" class="flex gap-3">
            <input id="msg-input" type="text" placeholder="Escribe tu mensaje..."
                   class="flex-1 px-4 py-3 border rounded-xl focus:ring-2 focus:ring-primary focus:border-primary"
                   autocomplete="off"/>
            <button type="submit" id="send-btn"
                    class="px-6 py-3 bg-primary text-white font-bold rounded-xl hover:bg-primary/90 disabled:opacity-50"
                    >Enviar</button>
        </form>
    </div>
</div>

<script>
const messagesDiv = document.getElementById('messages');
const form = document.getElementById('chat-form');
const input = document.getElementById('msg-input');
const sendBtn = document.getElementById('send-btn');
const csrfToken = '{{ csrf_token }}';
const sendUrl = '{% url "send_message" session.id %}';

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = input.value.trim();
    if (!msg) return;

    // Add user message
    appendMessage(msg, 'user');
    input.value = '';
    sendBtn.disabled = true;

    // Create assistant bubble
    const assistantBubble = appendMessage('', 'assistant');
    const textEl = assistantBubble.querySelector('.msg-text');

    try {
        const response = await fetch(sendUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken},
            body: JSON.stringify({message: msg}),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    if (data.text) {
                        textEl.textContent += data.text;
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }
                    if (data.error) {
                        textEl.textContent += '\n[Error: ' + data.error + ']';
                    }
                }
            }
        }
    } catch (err) {
        textEl.textContent = 'Error de conexión. Inténtalo de nuevo.';
    }
    sendBtn.disabled = false;
    input.focus();
});

function appendMessage(text, role) {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex gap-3 items-start' + (role === 'user' ? ' flex-row-reverse' : '');

    const avatar = document.createElement('div');
    avatar.className = `w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${
        role === 'user' ? 'bg-brand-yellow text-primary' : 'bg-primary/10 text-primary'
    }`;
    avatar.textContent = role === 'user' ? 'Tú' : 'AI';

    const bubble = document.createElement('div');
    bubble.className = `rounded-2xl px-4 py-3 max-w-[80%] ${
        role === 'user'
            ? 'bg-primary text-white rounded-tr-none'
            : 'bg-gray-100 text-gray-900 rounded-tl-none'
    }`;
    const p = document.createElement('p');
    p.className = 'text-sm msg-text whitespace-pre-wrap';
    p.textContent = text;
    bubble.appendChild(p);

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    messagesDiv.appendChild(wrapper);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return wrapper;
}
</script>
{% endblock %}
```

Create `templates/chat/no_access.html`:
```html
{% extends "base.html" %}
{% block content %}
<div class="min-h-screen flex items-center justify-center">
    <div class="bg-white p-8 rounded-2xl shadow-lg text-center max-w-md">
        <h1 class="text-2xl font-headline font-bold text-primary mb-4">Acceso Restringido</h1>
        <p class="text-gray-600 mb-6">{{ assistant.name }} no está disponible para tu curso actual.</p>
        <a href="{% url 'dashboard' %}" class="px-6 py-3 bg-primary text-white font-bold rounded-lg">Volver al Panel</a>
    </div>
</div>
{% endblock %}
```

**Step 8: Write test**

`chat/tests.py`:
```python
from django.test import TestCase, Client
from accounts.models import User
from assistants.models import Assistant
from chat.models import ChatSession


class ChatSessionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='est1', password='testpass123',
            role='estudiante', curso=2,
        )
        self.assistant = Assistant.objects.create(
            name='Anamnesio', slug='anamnesio',
            description='Test', phase='fundacional',
            available_courses=[1, 2], order=1,
        )

    def test_create_session(self):
        session = ChatSession.objects.create(
            user=self.user, assistant=self.assistant,
            openai_thread_id='thread_test123',
        )
        self.assertTrue(session.is_active)
        self.assertEqual(session.message_count, 0)


class ChatAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='est5', password='testpass123',
            role='estudiante', curso=5,
        )
        self.anamnesio = Assistant.objects.create(
            name='Anamnesio', slug='anamnesio',
            description='Test', phase='fundacional',
            available_courses=[1, 2], order=1,
        )

    def test_no_access_wrong_course(self):
        self.client.login(username='est5', password='testpass123')
        response = self.client.get('/chat/iniciar/anamnesio/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acceso Restringido')
```

**Step 9: Run tests**

```bash
python manage.py test chat
```

**Step 10: Commit**

```bash
git add chat/ templates/chat/ actuva/
git commit -m "feat: chat app with OpenAI streaming, session management, course access control"
```

---

## Task 5: Dashboard & Landing Page

**Files:**
- Create: `templates/dashboard.html`
- Create: `templates/landing.html`
- Modify: `actuva/urls.py`
- Create: `actuva/views.py`
- Move: mascot images to `static/img/`

**Step 1: Create static directory and copy mascot images**

```bash
mkdir -p static/img
cp anamnesio.png static/img/
cp exploria.png static/img/
cp diferencialio.png static/img/
cp decisonia.png static/img/
cp empatia.png static/img/
cp reumatia.png static/img/
```

Add to `settings.py`:
```python
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

**Step 2: Create views**

`actuva/views.py`:
```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from assistants.models import Assistant


def landing(request):
    if request.user.is_authenticated:
        return _dashboard(request)
    assistants = Assistant.objects.all()
    return render(request, 'landing.html', {'assistants': assistants})


@login_required
def dashboard(request):
    return _dashboard(request)


def _dashboard(request):
    user = request.user
    if user.is_estudiante():
        assistants = [a for a in Assistant.objects.all() if a.is_available_for_curso(user.curso)]
    else:
        assistants = Assistant.objects.all()
    return render(request, 'dashboard.html', {'assistants': assistants})
```

**Step 3: URLs**

`actuva/urls.py` (full):
```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('panel/', views.dashboard, name='dashboard'),
    path('admin/', admin.site.urls),
    path('cuentas/', include('accounts.urls')),
    path('chat/', include('chat.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

**Step 4: Dashboard template**

`templates/dashboard.html`:
```html
{% extends "base.html" %}
{% load static %}
{% block title %}Panel — ACTUVa{% endblock %}
{% block content %}
<div class="min-h-screen">
    <!-- Nav -->
    <header class="bg-white border-b-4 border-brand-yellow px-6 py-3">
        <div class="max-w-7xl mx-auto flex justify-between items-center">
            <div class="font-headline font-bold text-xl text-primary flex items-center gap-2">
                <span class="w-2 h-6 bg-brand-yellow rounded-full"></span> ACTUVa
            </div>
            <div class="flex items-center gap-4">
                <span class="text-sm text-gray-600">{{ request.user.username }}
                    {% if request.user.is_estudiante %} · {{ request.user.curso }}º curso{% endif %}
                </span>
                {% if request.user.is_profesor %}
                <a href="{% url 'case_list' %}" class="text-sm text-primary font-bold hover:underline">Mis Casos</a>
                {% endif %}
                <a href="{% url 'logout' %}" class="px-4 py-2 text-sm bg-gray-100 rounded-lg hover:bg-gray-200">Cerrar sesión</a>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-12">
        <h1 class="font-headline font-bold text-3xl text-primary mb-2">Tus Asistentes</h1>
        <p class="text-gray-500 mb-10">Selecciona un asistente para comenzar tu práctica clínica.</p>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {% for a in assistants %}
            <div class="bg-white rounded-2xl shadow-sm hover:shadow-md transition-shadow border border-gray-100 overflow-hidden group">
                <div class="p-6">
                    <div class="flex items-center gap-4 mb-4">
                        <img src="{% static 'img/'|add:a.slug|add:'.png' %}"
                             alt="{{ a.name }}"
                             class="w-16 h-16 rounded-xl object-cover"
                             onerror="this.style.display='none'"/>
                        <div>
                            <h3 class="font-headline font-bold text-xl text-primary">{{ a.name }}</h3>
                            <span class="text-xs font-bold text-primary/60 bg-primary/5 px-2 py-0.5 rounded">{{ a.get_phase_display }}</span>
                        </div>
                    </div>
                    <p class="text-sm text-gray-600 mb-6 leading-relaxed">{{ a.description }}</p>
                    <a href="{% url 'start_session' a.slug %}"
                       class="block text-center px-4 py-3 bg-primary text-white font-bold rounded-xl hover:bg-primary/90 transition-colors">
                        Comenzar Sesión
                    </a>
                </div>
            </div>
            {% endfor %}
        </div>
    </main>
</div>
{% endblock %}
```

**Step 5: Landing template** (simplified version of borrador)

`templates/landing.html`:
```html
{% extends "base.html" %}
{% load static %}
{% block title %}ACTUVa — Aprendizaje Clínico Temprano UVa{% endblock %}
{% block content %}
<!-- Hero -->
<header class="bg-white border-b-4 border-brand-yellow px-6 py-3">
    <div class="max-w-7xl mx-auto flex justify-between items-center">
        <div class="font-headline font-bold text-xl text-primary flex items-center gap-2">
            <span class="w-2 h-6 bg-brand-yellow rounded-full"></span> ACTUVa
        </div>
        <div class="flex items-center gap-4">
            <a href="{% url 'login' %}" class="text-sm text-primary font-bold">Iniciar Sesión</a>
            <a href="{% url 'register' %}" class="px-5 py-2 bg-primary text-white font-bold text-sm rounded-lg hover:bg-primary/90">Registrarse</a>
        </div>
    </div>
</header>

<section class="px-6 py-20 md:py-32 max-w-7xl mx-auto">
    <div class="max-w-3xl">
        <span class="inline-block py-1 px-3 rounded-md bg-brand-yellow text-primary text-xs font-black tracking-widest uppercase mb-6">
            Innovación Educativa UVa
        </span>
        <h1 class="font-headline font-extrabold text-4xl md:text-6xl text-primary leading-tight mb-6">
            Domina el razonamiento clínico con IA antes del paciente real.
        </h1>
        <p class="text-lg text-gray-600 mb-10 leading-relaxed border-l-4 border-brand-yellow pl-6">
            Practica sin límite en un entorno seguro con feedback inmediato. Diseñado por y para estudiantes de Medicina de la UVa.
        </p>
        <div class="flex gap-4">
            <a href="{% url 'register' %}" class="px-8 py-4 rounded-lg bg-primary text-white font-bold text-lg shadow-xl">Comenzar Entrenamiento</a>
        </div>
    </div>
</section>

<!-- Assistants preview -->
<section class="bg-gray-50 py-20 px-6">
    <div class="max-w-7xl mx-auto">
        <h2 class="font-headline font-bold text-3xl text-primary mb-12 text-center">Los Asistentes M3RGE-AI</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            {% for a in assistants %}
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <div class="flex items-center gap-3 mb-3">
                    <img src="{% static 'img/'|add:a.slug|add:'.png' %}"
                         alt="{{ a.name }}" class="w-12 h-12 rounded-xl object-cover"
                         onerror="this.style.display='none'"/>
                    <h3 class="font-headline font-bold text-lg text-primary">{{ a.name }}</h3>
                </div>
                <p class="text-sm text-gray-600">{{ a.description }}</p>
            </div>
            {% endfor %}
        </div>
    </div>
</section>

<footer class="py-8 border-t text-center text-xs text-gray-400">
    © 2026 ACTUVa — Facultad de Medicina, Universidad de Valladolid.
</footer>
{% endblock %}
```

**Step 6: Fix static image paths**

The `{% static 'img/'|add:a.slug|add:'.png' %}` pattern requires slug-matching filenames. Rename files to match slugs:

```bash
cd D:/PycharmProjects/anamnesio/static/img
mv decisonia.png decisonia.png  # slug is 'decisonia'
mv empatia.png empatia.png      # slug is 'empatia'
```

Note: The slugs in seed_assistants are `anamnesio`, `exploria`, `diferencialio`, `decisonia`, `empatia`, `reumatia`. The png files match except no rename needed — they already align.

**Step 7: Commit**

```bash
git add templates/ actuva/views.py actuva/urls.py static/
git commit -m "feat: dashboard with filtered assistants and landing page"
```

---

## Task 6: Cases App — Professor Clinical Cases

**Files:**
- Create: `cases/` app
- Create: `cases/models.py`
- Create: `cases/views.py`
- Create: `cases/urls.py`
- Create: `cases/forms.py`
- Create: `templates/cases/list.html`
- Create: `templates/cases/create.html`
- Test: `cases/tests.py`

**Step 1: Create app**

Run: `python manage.py startapp cases`

Add `'cases'` to `INSTALLED_APPS`.

**Step 2: Model**

`cases/models.py`:
```python
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
```

**Step 3: Form**

`cases/forms.py`:
```python
from django import forms
from .models import ClinicalCase
from assistants.models import Assistant


class ClinicalCaseForm(forms.ModelForm):
    class Meta:
        model = ClinicalCase
        fields = ('title', 'description', 'content_file', 'assistant')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assistant'].queryset = Assistant.objects.filter(allows_custom_cases=True)
        self.fields['title'].widget.attrs.update({'class': 'w-full px-4 py-2 border rounded-lg'})
        self.fields['description'].widget.attrs.update({'class': 'w-full px-4 py-2 border rounded-lg', 'rows': 4})
        self.fields['content_file'].widget.attrs.update({'class': 'w-full'})
        self.fields['assistant'].widget.attrs.update({'class': 'w-full px-4 py-2 border rounded-lg'})
```

**Step 4: Views**

`cases/views.py`:
```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ClinicalCase
from .forms import ClinicalCaseForm


def profesor_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_profesor() and not request.user.is_staff:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


@profesor_required
def case_list(request):
    cases = ClinicalCase.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'cases/list.html', {'cases': cases})


@profesor_required
def case_create(request):
    if request.method == 'POST':
        form = ClinicalCaseForm(request.POST, request.FILES)
        if form.is_valid():
            case = form.save(commit=False)
            case.created_by = request.user
            case.save()
            # TODO: Upload to OpenAI when API key is configured
            return redirect('case_list')
    else:
        form = ClinicalCaseForm()
    return render(request, 'cases/create.html', {'form': form})


@profesor_required
def case_toggle(request, case_id):
    case = get_object_or_404(ClinicalCase, id=case_id, created_by=request.user)
    case.is_active = not case.is_active
    case.save(update_fields=['is_active'])
    return redirect('case_list')
```

**Step 5: URLs**

`cases/urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.case_list, name='case_list'),
    path('nuevo/', views.case_create, name='case_create'),
    path('<int:case_id>/toggle/', views.case_toggle, name='case_toggle'),
]
```

In `actuva/urls.py` add:
```python
path('casos/', include('cases.urls')),
```

**Step 6: Templates**

`templates/cases/list.html`:
```html
{% extends "base.html" %}
{% block title %}Mis Casos — ACTUVa{% endblock %}
{% block content %}
<div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b-4 border-brand-yellow px-6 py-3">
        <div class="max-w-7xl mx-auto flex justify-between items-center">
            <div class="font-headline font-bold text-xl text-primary flex items-center gap-2">
                <span class="w-2 h-6 bg-brand-yellow rounded-full"></span> ACTUVa
            </div>
            <div class="flex items-center gap-4">
                <a href="{% url 'dashboard' %}" class="text-sm text-primary font-bold">Panel</a>
                <a href="{% url 'logout' %}" class="px-4 py-2 text-sm bg-gray-100 rounded-lg">Cerrar sesión</a>
            </div>
        </div>
    </header>
    <main class="max-w-4xl mx-auto px-6 py-12">
        <div class="flex justify-between items-center mb-8">
            <h1 class="font-headline font-bold text-3xl text-primary">Mis Casos Clínicos</h1>
            <a href="{% url 'case_create' %}" class="px-6 py-3 bg-primary text-white font-bold rounded-lg">Nuevo Caso</a>
        </div>
        {% if cases %}
        <div class="space-y-4">
            {% for case in cases %}
            <div class="bg-white p-6 rounded-xl shadow-sm border flex justify-between items-center">
                <div>
                    <h3 class="font-bold text-primary">{{ case.title }}</h3>
                    <p class="text-sm text-gray-500">{{ case.assistant.name }} · {{ case.created_at|date:"d M Y" }}</p>
                </div>
                <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded {{ case.is_active|yesno:'bg-green-100 text-green-700,bg-gray-100 text-gray-500' }}">
                        {{ case.is_active|yesno:'Activo,Inactivo' }}
                    </span>
                    <form method="post" action="{% url 'case_toggle' case.id %}">
                        {% csrf_token %}
                        <button class="text-xs text-primary underline">{{ case.is_active|yesno:'Desactivar,Activar' }}</button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p class="text-gray-500 text-center py-12">No has creado ningún caso todavía.</p>
        {% endif %}
    </main>
</div>
{% endblock %}
```

`templates/cases/create.html`:
```html
{% extends "base.html" %}
{% block title %}Nuevo Caso — ACTUVa{% endblock %}
{% block content %}
<div class="min-h-screen flex items-center justify-center py-12">
    <div class="bg-white p-8 rounded-2xl shadow-lg w-full max-w-lg">
        <h1 class="text-2xl font-headline font-bold text-primary mb-6">Nuevo Caso Clínico</h1>
        <form method="post" enctype="multipart/form-data">
            {% csrf_token %}
            {% for field in form %}
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-1">{{ field.label }}</label>
                {{ field }}
                {% for error in field.errors %}
                <p class="text-red-500 text-xs mt-1">{{ error }}</p>
                {% endfor %}
            </div>
            {% endfor %}
            <div class="flex gap-3">
                <button type="submit" class="flex-1 py-3 bg-primary text-white font-bold rounded-lg">Guardar</button>
                <a href="{% url 'case_list' %}" class="flex-1 py-3 text-center bg-gray-100 rounded-lg font-bold">Cancelar</a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

**Step 7: Migrate and test**

```bash
python manage.py makemigrations cases
python manage.py migrate
python manage.py test cases
```

**Step 8: Commit**

```bash
git add cases/ templates/cases/ actuva/urls.py
git commit -m "feat: cases app — professor uploads clinical cases per assistant"
```

---

## Task 7: Stats App — Usage Statistics

**Files:**
- Create: `stats/` app
- Create: `stats/models.py`
- Create: `stats/views.py`
- Create: `stats/urls.py`
- Create: `stats/management/commands/aggregate_stats.py`
- Create: `templates/stats/dashboard.html`

**Step 1: Create app**

Run: `python manage.py startapp stats`

Add `'stats'` to `INSTALLED_APPS`.

**Step 2: Model**

`stats/models.py`:
```python
from django.db import models


class UsageStat(models.Model):
    date = models.DateField()
    assistant = models.ForeignKey('assistants.Assistant', on_delete=models.CASCADE)
    total_minutes = models.FloatField(default=0)
    unique_users = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('date', 'assistant')
        ordering = ['-date']

    def __str__(self):
        return f'{self.date} - {self.assistant.name}: {self.total_minutes:.0f}min, {self.unique_users} users'
```

**Step 3: Aggregation command**

`stats/management/commands/aggregate_stats.py`:
```python
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Count, Sum, F
from django.db.models.functions import Coalesce
from chat.models import ChatSession
from assistants.models import Assistant
from stats.models import UsageStat


class Command(BaseCommand):
    help = 'Aggregate daily usage stats from chat sessions'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Date YYYY-MM-DD (default: yesterday)')

    def handle(self, *args, **options):
        target = date.fromisoformat(options['date']) if options.get('date') else date.today() - timedelta(days=1)

        for assistant in Assistant.objects.all():
            sessions = ChatSession.objects.filter(
                assistant=assistant,
                started_at__date=target,
                ended_at__isnull=False,
            )
            total_minutes = sum(s.duration_minutes() for s in sessions)
            unique_users = sessions.values('user').distinct().count()

            UsageStat.objects.update_or_create(
                date=target, assistant=assistant,
                defaults={'total_minutes': total_minutes, 'unique_users': unique_users},
            )
            self.stdout.write(f'{assistant.name}: {total_minutes:.0f}min, {unique_users} usuarios')

        self.stdout.write(self.style.SUCCESS(f'Estadísticas agregadas para {target}'))
```

**Step 4: View (admin only)**

`stats/views.py`:
```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import UsageStat


@login_required
def stats_dashboard(request):
    if not (request.user.is_admin_role() or request.user.is_staff):
        from django.shortcuts import redirect
        return redirect('dashboard')

    stats = UsageStat.objects.select_related('assistant').order_by('-date', 'assistant__order')[:60]
    return render(request, 'stats/dashboard.html', {'stats': stats})
```

**Step 5: URLs**

`stats/urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.stats_dashboard, name='stats_dashboard'),
]
```

Add to `actuva/urls.py`:
```python
path('estadisticas/', include('stats.urls')),
```

**Step 6: Template**

`templates/stats/dashboard.html`:
```html
{% extends "base.html" %}
{% block title %}Estadísticas — ACTUVa{% endblock %}
{% block content %}
<div class="min-h-screen bg-gray-50">
    <header class="bg-white border-b-4 border-brand-yellow px-6 py-3">
        <div class="max-w-7xl mx-auto flex justify-between items-center">
            <div class="font-headline font-bold text-xl text-primary flex items-center gap-2">
                <span class="w-2 h-6 bg-brand-yellow rounded-full"></span> ACTUVa — Estadísticas
            </div>
            <a href="{% url 'dashboard' %}" class="text-sm text-primary font-bold">Volver</a>
        </div>
    </header>
    <main class="max-w-5xl mx-auto px-6 py-12">
        <h1 class="font-headline font-bold text-3xl text-primary mb-8">Uso de la Plataforma</h1>
        <div class="bg-white rounded-xl shadow-sm overflow-hidden">
            <table class="w-full text-sm">
                <thead class="bg-primary text-white">
                    <tr>
                        <th class="px-6 py-3 text-left">Fecha</th>
                        <th class="px-6 py-3 text-left">Asistente</th>
                        <th class="px-6 py-3 text-right">Minutos Totales</th>
                        <th class="px-6 py-3 text-right">Usuarios Únicos</th>
                    </tr>
                </thead>
                <tbody>
                    {% for s in stats %}
                    <tr class="border-t hover:bg-gray-50">
                        <td class="px-6 py-3">{{ s.date|date:"d M Y" }}</td>
                        <td class="px-6 py-3 font-medium">{{ s.assistant.name }}</td>
                        <td class="px-6 py-3 text-right">{{ s.total_minutes|floatformat:0 }}</td>
                        <td class="px-6 py-3 text-right">{{ s.unique_users }}</td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="4" class="px-6 py-8 text-center text-gray-400">Sin datos todavía.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </main>
</div>
{% endblock %}
```

**Step 7: Migrate and commit**

```bash
python manage.py makemigrations stats
python manage.py migrate
git add stats/ templates/stats/ actuva/urls.py
git commit -m "feat: stats app with daily usage aggregation and admin dashboard"
```

---

## Task 8: OpenAI Assistant Provisioning Command

**Files:**
- Create: `assistants/management/commands/create_openai_assistants.py`

**Step 1: Write the command**

`assistants/management/commands/create_openai_assistants.py`:
```python
from django.core.management.base import BaseCommand
from assistants.models import Assistant
from chat.openai_client import get_client


class Command(BaseCommand):
    help = 'Create or update OpenAI Assistants for each local Assistant record'

    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, default='gpt-4o-mini',
                            help='OpenAI model to use (default: gpt-4o-mini)')

    def handle(self, *args, **options):
        client = get_client()
        model = options['model']

        for assistant in Assistant.objects.all():
            if not assistant.system_prompt:
                self.stdout.write(self.style.WARNING(f'SKIP {assistant.name}: sin system_prompt'))
                continue

            if assistant.openai_assistant_id:
                # Update existing
                client.beta.assistants.update(
                    assistant.openai_assistant_id,
                    name=assistant.name,
                    instructions=assistant.system_prompt,
                    model=model,
                )
                self.stdout.write(f'Actualizado: {assistant.name} ({assistant.openai_assistant_id})')
            else:
                # Create new
                oai_assistant = client.beta.assistants.create(
                    name=assistant.name,
                    instructions=assistant.system_prompt,
                    model=model,
                )
                assistant.openai_assistant_id = oai_assistant.id
                assistant.save(update_fields=['openai_assistant_id'])
                self.stdout.write(f'Creado: {assistant.name} → {oai_assistant.id}')

        self.stdout.write(self.style.SUCCESS('Provisionamiento completado.'))
```

**Step 2: Commit**

```bash
git add assistants/management/commands/create_openai_assistants.py
git commit -m "feat: management command to provision OpenAI assistants from local config"
```

---

## Task 9: Create Superuser & Final Wiring

**Step 1: Create .env from example**

```bash
cp .env.example .env
```
Edit `.env` and add real `OPENAI_API_KEY` when available.

**Step 2: Run full migration**

```bash
python manage.py migrate
python manage.py seed_assistants
python manage.py createsuperuser
```

**Step 3: Verify full flow**

```bash
python manage.py runserver
```

Test:
1. Visit `/` — landing page
2. Register as student (curso 2) → redirected to dashboard → see Anamnesio, ExplorIA
3. Register as profesor → see all assistants + "Mis Casos" link
4. Create a clinical case as profesor
5. Visit `/admin/` as superuser
6. Visit `/estadisticas/` as admin

**Step 4: Final commit**

```bash
git add .
git commit -m "feat: final wiring — seed data, static files, complete flow"
```

---

## Summary of File Structure

```
D:/PycharmProjects/anamnesio/
├── .env.example
├── .gitignore
├── requirements.txt
├── manage.py
├── actuva/
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   └── wsgi.py
├── accounts/
│   ├── models.py      (Custom User with role + curso)
│   ├── forms.py       (RegisterForm)
│   ├── views.py       (register)
│   ├── urls.py
│   ├── admin.py
│   └── tests.py
├── assistants/
│   ├── models.py      (Assistant)
│   ├── admin.py
│   ├── context_processors.py
│   ├── management/commands/
│   │   ├── seed_assistants.py
│   │   └── create_openai_assistants.py
│   └── tests.py
├── chat/
│   ├── models.py      (ChatSession)
│   ├── views.py       (start, chat, send SSE, end)
│   ├── openai_client.py
│   ├── urls.py
│   └── tests.py
├── cases/
│   ├── models.py      (ClinicalCase)
│   ├── forms.py
│   ├── views.py
│   └── urls.py
├── stats/
│   ├── models.py      (UsageStat)
│   ├── views.py
│   ├── urls.py
│   └── management/commands/aggregate_stats.py
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── dashboard.html
│   ├── accounts/login.html
│   ├── accounts/register.html
│   ├── chat/session.html
│   ├── chat/no_access.html
│   ├── cases/list.html
│   ├── cases/create.html
│   └── stats/dashboard.html
├── static/img/
│   ├── anamnesio.png
│   ├── exploria.png
│   ├── diferencialio.png
│   ├── decisonia.png
│   ├── empatia.png
│   └── reumatia.png
└── docs/plans/
    ├── 2026-03-27-actuva-platform-design.md
    └── 2026-03-27-actuva-implementation.md
```
