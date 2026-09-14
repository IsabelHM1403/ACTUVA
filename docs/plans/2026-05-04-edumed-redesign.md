# EduMed Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate ACTUVa Django project to EduMed visual style and replace the
landing/study flow with 12 interactive anamnesis modules, while keeping the
existing OpenAI-chat as a "virtual patient" launched at the end of each module.
All student events are tracked in DB.

**Architecture:** New `anamnesis` Django app holds module CMS models (Module,
Patient, Step, FlipCard, etc.) and tracking models (ModuleProgress, StudentEvent,
QuizAttempt). Content is seeded from the 15 HTML files in
`EduMed_UVa_completo/` via a one-shot management command. Frontend rewritten
from inline Preact to vanilla JS reading initial state from a JSON `<script>`
tag and POSTing events back. Existing `accounts`, `assistants`, `chat`, `cases`,
`stats` apps stay; their templates are restyled with EduMed CSS variables.

**Tech Stack:** Django 5.1 (existing), SQLite (existing), vanilla JS (no build
step), CSS custom properties (no Tailwind in new templates), `demjson3` for
parsing JS literals from EduMed source.

**Reference design:** [docs/plans/2026-05-04-edumed-redesign-design.md](./2026-05-04-edumed-redesign-design.md)

---

## Phase 0 — Preparation

### Task 0.1: Add `demjson3` to requirements

**Files:** Modify `requirements.txt`

**Steps:**
1. Append line `demjson3>=3.0.6` to `requirements.txt`.
2. Run `pip install -r requirements.txt`.
3. Commit: `chore: add demjson3 for parsing EduMed JS literals`.

### Task 0.2: Create the `anamnesis` Django app

**Files:** Create `anamnesis/` directory tree.

**Steps:**
1. Run `python manage.py startapp anamnesis`.
2. Add `'anamnesis'` to `INSTALLED_APPS` in `actuva/settings.py:47-59`.
3. Add `path('anamnesis/', include('anamnesis.urls'))` in `actuva/urls.py:7-15`
   (above admin).
4. Create empty `anamnesis/urls.py` with `urlpatterns = []`.
5. Run `python manage.py check` — expected: no errors.
6. Commit: `feat(anamnesis): scaffold app and route prefix`.

---

## Phase 1 — Content models + migrations

### Task 1.1: Write failing test for `Module` creation

**Files:** Create `anamnesis/tests/__init__.py`, `anamnesis/tests/test_models.py`.

**Test:**
```python
import pytest
from django.test import TestCase
from anamnesis.models import Module

class ModuleModelTest(TestCase):
    def test_create_module_with_required_fields(self):
        m = Module.objects.create(
            slug='cefalea', name='Cefalea', emoji='🧠',
            gradient_from='#3a0860', gradient_to='#5c1490',
            deco_code='DxCf', group=Module.Group.NEUROLOGICAL,
            order=1, description='Dolor de cabeza',
        )
        self.assertEqual(str(m), 'Cefalea')
        self.assertEqual(m.slug, 'cefalea')
```

**Run:** `python manage.py test anamnesis.tests.test_models -v 2`
Expected: ImportError (no `Module`).

### Task 1.2: Implement `Module` model

**Files:** Create `anamnesis/models.py`.

```python
from django.db import models
from django.conf import settings


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
```

**Run:** `python manage.py makemigrations anamnesis` then
`python manage.py migrate` then re-run the test. Expected: PASS.

**Commit:** `feat(anamnesis): add Module model`.

### Task 1.3: Add remaining content models, one model per micro-task

For each of the following, write a small `test_models.py` test that creates the
model with required fields and asserts `__str__` or a basic relation, then
implement, run migrations, run tests, commit.

Models to add (in this order, each in its own commit):

- **Patient** — FK `module`, `name`, `age` (PositiveSmallIntegerField),
  `diagnosis` (CharField), `diagnosis_key` (JSONField default=list,
  list of strings), `order`. Meta: `ordering = ['module', 'order']`.
- **PatientQuote** — FK `patient`, `step_number` (PositiveSmallIntegerField),
  `text` (TextField). Unique together (`patient`, `step_number`).
- **Step** — FK `module`, `n` (PositiveSmallIntegerField), `title`,
  `example_question` (TextField), `think_box` (TextField, blank), `tip_box`
  (TextField, blank), `sec_label` (CharField, blank). Unique together
  (`module`, `n`).
- **FlipCard** — FK `step`, `label`, `badge` (CharField, blank),
  `back_text` (TextField), `order`.
- **IrrelevantItem** — FK `step`, `name`, `badge` (CharField, blank),
  `body_text` (TextField), `order`.
- **StepDxFeedback** — FK `step`, FK `patient`, `quote_idx`
  (PositiveSmallIntegerField), `compat` (CharField, choices
  neutral/positive/strong), `evidence` (PositiveSmallIntegerField 1–3),
  `interpretation` (TextField), `fits_for` (JSONField default=list),
  `rules_out` (JSONField default=list).
- **DiagnosisCombo** — FK `module`, `dx`, `compat` (same choices),
  `symptoms` (JSONField default=list), `key_text` (TextField), `order`.
- **QuizQuestion** — FK `module`, `text` (TextField), `order`,
  `explanation` (TextField, blank).
- **QuizChoice** — FK `question`, `text`, `is_correct` (BooleanField), `order`.
- **VirtualPatient** — FK `module`, FK `assistant` (assistants.Assistant,
  null=True, blank=True), `display_name`, `age` (PositiveSmallIntegerField),
  `persona_summary` (TextField), `order`.

After all models are added, commit a single `makemigrations` migration:
```bash
python manage.py makemigrations anamnesis
python manage.py migrate
git add anamnesis/migrations/
git commit -m "feat(anamnesis): add migrations for content models"
```

### Task 1.4: Add tracking models

Three tracking models, one commit each:

- **ModuleProgress** — FK `student` (settings.AUTH_USER_MODEL), FK `module`,
  `started_at` (auto_now_add), `completed_at` (DateTimeField null), `last_step`
  (PositiveSmallIntegerField default=0). Unique together (`student`, `module`).
  Method `is_completed(self)` returns `bool(self.completed_at)`.
- **StudentEvent** — FK `student`, FK `module`, `event_type` (CharField with
  TextChoices STEP_OPEN, FLIP, KNEW, UNKNOWN, QUIZ_ANSWER, DX_VIEW, COMPLETE,
  VP_OPEN), `payload` (JSONField default=dict), `timestamp` (auto_now_add).
- **QuizAttempt** — FK `student`, FK `module`, `score` (PositiveSmallIntegerField),
  `total` (PositiveSmallIntegerField), `answers` (JSONField default=list),
  `submitted_at` (auto_now_add).

Each gets a model test before implementation. After all three:
```bash
python manage.py makemigrations anamnesis
python manage.py migrate
git add anamnesis/migrations/
git commit -m "feat(anamnesis): add tracking models"
```

### Task 1.5: Register all models in admin

**Files:** Create `anamnesis/admin.py`.

For each content model use `admin.site.register(Model)`. For models with
inlines (Module → Patient, Step; Patient → PatientQuote; Step → FlipCard,
IrrelevantItem, StepDxFeedback; QuizQuestion → QuizChoice), use
`TabularInline` to make CMS editing convenient.

**Verify manually:** `python manage.py runserver`, open `/admin/`, confirm every
new model appears under "Anamnesis".

**Commit:** `feat(anamnesis): register content and tracking models in admin`.

---

## Phase 2 — Parser + import command (one reference module)

### Task 2.1: Failing test for the parser on Cefalea

**Files:** Create `anamnesis/tests/test_parser.py`.

```python
from pathlib import Path
from django.test import TestCase
from anamnesis.parser import parse_module_html

FIXTURE = Path(__file__).parent.parent.parent / 'EduMed_UVa_completo' / 'Anamnesis_Cefalea_v1.html'

class ParserTest(TestCase):
    def test_parses_patient_block(self):
        data = parse_module_html(FIXTURE.read_text(encoding='utf-8'))
        self.assertEqual(data['patient']['name'], 'Ana G.')
        self.assertEqual(data['patient']['age'], 34)
        self.assertIn('Migraña', data['patient']['diagnosis'])

    def test_parses_quotes(self):
        data = parse_module_html(FIXTURE.read_text(encoding='utf-8'))
        self.assertEqual(len(data['patient']['quotes']), 7)

    def test_parses_steps(self):
        data = parse_module_html(FIXTURE.read_text(encoding='utf-8'))
        self.assertEqual(len(data['steps']), 7)
        self.assertEqual(data['steps'][0]['n'], 1)

    def test_parses_combos(self):
        data = parse_module_html(FIXTURE.read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(data['combos']), 5)
```

**Run:** `python manage.py test anamnesis.tests.test_parser -v 2`
Expected: ImportError (no `parser`).

### Task 2.2: Implement minimal parser

**Files:** Create `anamnesis/parser.py`.

Approach: regex-extract each named JS block (`const PATIENT = {...};`,
`const ALL_QS = [...];`, `const STEP_DX = [...];`, `const COMBOS = [...];`),
then parse with `demjson3.decode` (lenient — tolerates unquoted keys, single
quotes, trailing commas, comments).

```python
import re
import demjson3


def _extract_block(html: str, name: str) -> str | None:
    """Find `const NAME = ...;` and return the literal as a string."""
    pattern = re.compile(
        rf'const\s+{re.escape(name)}\s*=\s*(?P<body>[\[\{{].*?)\n;\s*\n',
        re.DOTALL,
    )
    m = pattern.search(html)
    if not m:
        # Fallback: search until line ending with `};` or `];`
        pattern2 = re.compile(
            rf'const\s+{re.escape(name)}\s*=\s*(?P<body>[\[\{{].*?)\];?\s*\n',
            re.DOTALL,
        )
        m = pattern2.search(html)
    return m.group('body') if m else None


def _decode(literal: str):
    return demjson3.decode(literal, strict=False)


def parse_module_html(html: str) -> dict:
    patient_raw = _extract_block(html, 'PATIENT')
    qs_raw = _extract_block(html, 'ALL_QS')
    dx_raw = _extract_block(html, 'STEP_DX')
    combos_raw = _extract_block(html, 'COMBOS')
    return {
        'patient': _decode(patient_raw) if patient_raw else {},
        'steps': _decode(qs_raw) if qs_raw else [],
        'step_dx': _decode(dx_raw) if dx_raw else [],
        'combos': _decode(combos_raw) if combos_raw else [],
    }
```

Iterate the regex until all four assertions pass. Acceptable to refine the
regex over 2-3 commits — re-run tests after each.

**Commit:** `feat(anamnesis): add HTML parser for EduMed module data`.

### Task 2.3: Failing test for the import command

**Files:** Create `anamnesis/tests/test_import_command.py`.

```python
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from anamnesis.models import Module, Patient, Step

class ImportCommandTest(TestCase):
    def test_imports_cefalea(self):
        out = StringIO()
        call_command('import_edumed_content', '--only=cefalea', stdout=out)
        m = Module.objects.get(slug='cefalea')
        self.assertEqual(m.name, 'Cefalea')
        self.assertEqual(Patient.objects.filter(module=m).count(), 1)
        self.assertEqual(Step.objects.filter(module=m).count(), 7)

    def test_idempotent(self):
        call_command('import_edumed_content', '--only=cefalea')
        before = Module.objects.count()
        call_command('import_edumed_content', '--only=cefalea')
        self.assertEqual(Module.objects.count(), before)
```

**Run:** Expected: CommandError (no command).

### Task 2.4: Implement import command for Cefalea only

**Files:** Create `anamnesis/management/__init__.py`,
`anamnesis/management/commands/__init__.py`,
`anamnesis/management/commands/import_edumed_content.py`.

The command holds a hardcoded mapping of all 12 module slugs to their
`(filename, group, emoji, gradient_from, gradient_to, deco_code, order)`
metadata (taken from `EduMed_UVa_completo/index.html`). Loop over the mapping,
optionally filtered by `--only=<slug>`. For each:

1. `update_or_create` `Module` by `slug`.
2. Parse the HTML via `parse_module_html`.
3. Wipe child rows for this module (`Patient.objects.filter(module=m).delete()`,
   etc.) — re-import is destructive for the module's children, idempotent at
   the module level.
4. Create `Patient` from `data['patient']`. For each item in
   `data['patient']['quotes']` create a `PatientQuote` with `step_number=i+1`.
5. Create `Step` rows from `data['steps']`.
6. Create `StepDxFeedback` from `data['step_dx']` linking by `quote_idx → step`.
7. Create `DiagnosisCombo` rows from `data['combos']`.

Implement minimally to make the two tests pass. Don't bother with quiz parsing
yet (separate task in Phase 8).

**Commit:** `feat(anamnesis): import_edumed_content command for Cefalea module`.

### Task 2.5: Add the other 11 modules to the metadata mapping

**Files:** Modify
`anamnesis/management/commands/import_edumed_content.py` — extend the mapping
dict with the remaining 11 entries (Disnea, Edema_MMII, Dolor_Abdominal,
Disuria, Diarrea, Mareo_Vertigo, Sincope, Fiebre, Dolor_Articular, Tos,
Dolor_Toracico). Get gradients/codes/emojis from
`EduMed_UVa_completo/index.html` lines 411-597.

Add a loop test that imports all 12 and asserts `Module.objects.count() == 12`.

Run `python manage.py import_edumed_content` (no flag, all). Inspect via
admin that all 12 modules and their children appeared.

**Commit:** `feat(anamnesis): metadata for all 12 EduMed modules`.

---

## Phase 3 — Frontend rendering (one module template)

### Task 3.1: Extract EduMed CSS to a static file

**Files:** Create `static/anamnesis/css/edumed.css`,
`static/anamnesis/css/module.css`.

Take the inline `<style>` block from `Anamnesis_Cefalea_v1.html` (lines 6-204).
Split:
- shared CSS variables, body, header, footer → `edumed.css`
- module-specific (.card, .fc, .step-pill, .quiz-*, .dx-*) → `module.css`

Run `python manage.py collectstatic --noinput --dry-run` to confirm Django
sees the files.

**Commit:** `feat(anamnesis): extract EduMed module CSS to static files`.

### Task 3.2: Write the module Django template

**Files:** Create `templates/anamnesis/module.html`.

The template:
1. Extends `anamnesis/_module_base.html` (a dedicated base because the module
   page has its own header/topbar instead of the global nav).
2. Renders module data into a `<script id="module-data" type="application/json">`
   tag using `{{ data|json_script }}`.
3. Renders the static page chrome (header with module name and progress bar)
   using Django template tags from the `module` and `student_progress` context.
4. Loads `/static/anamnesis/css/edumed.css`,
   `/static/anamnesis/css/module.css`,
   `/static/anamnesis/js/module.js` (defer).

**Files:** Create `anamnesis/views.py`:

```python
from django.shortcuts import render, get_object_or_404
from .models import Module, ModuleProgress
from .serializers import serialize_module_for_frontend


def module_view(request, slug):
    module = get_object_or_404(Module, slug=slug)
    progress = None
    if request.user.is_authenticated:
        progress, _ = ModuleProgress.objects.get_or_create(
            student=request.user, module=module,
        )
    return render(request, 'anamnesis/module.html', {
        'module': module,
        'progress': progress,
        'data': serialize_module_for_frontend(module),
    })
```

**Files:** Create `anamnesis/serializers.py`:

```python
def serialize_module_for_frontend(module):
    """Return a JSON-serializable dict the JS frontend renders from."""
    patient = module.patient_set.first()
    steps = list(module.step_set.order_by('n'))
    return {
        'slug': module.slug,
        'name': module.name,
        'patient': {
            'name': patient.name,
            'age': patient.age,
            'diagnosis': patient.diagnosis,
            'diagnosis_key': patient.diagnosis_key,
            'quotes': [q.text for q in patient.patientquote_set.order_by('step_number')],
        } if patient else None,
        'steps': [
            {
                'n': s.n,
                'title': s.title,
                'example_question': s.example_question,
                'think_box': s.think_box,
                'tip_box': s.tip_box,
                'flip_cards': [
                    {'label': fc.label, 'badge': fc.badge, 'back': fc.back_text}
                    for fc in s.flipcard_set.order_by('order')
                ],
                'irrelevant': [
                    {'name': i.name, 'badge': i.badge, 'body': i.body_text}
                    for i in s.irrelevantitem_set.order_by('order')
                ],
                'dx_feedback': [
                    {
                        'compat': dx.compat, 'evidence': dx.evidence,
                        'interpretation': dx.interpretation,
                        'fits_for': dx.fits_for, 'rules_out': dx.rules_out,
                    }
                    for dx in s.stepdxfeedback_set.all()
                ],
            } for s in steps
        ],
        'combos': [
            {'dx': c.dx, 'compat': c.compat, 'symptoms': c.symptoms, 'key': c.key_text}
            for c in module.diagnosiscombo_set.order_by('order')
        ],
    }
```

**Files:** Modify `anamnesis/urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path('<slug:slug>/', views.module_view, name='anamnesis_module'),
]
```

**Test:** Add `anamnesis/tests/test_views.py`:
```python
from django.test import TestCase, Client
from django.core.management import call_command

class ModuleViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('import_edumed_content', '--only=cefalea')

    def test_module_view_renders(self):
        r = Client().get('/anamnesis/cefalea/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ana G.')
        self.assertContains(r, 'module-data')
```

**Run:** `python manage.py test anamnesis.tests.test_views -v 2`. Iterate
until PASS.

**Commit:** `feat(anamnesis): module view with JSON data injection`.

### Task 3.3: Implement vanilla JS frontend for the module

**Files:** Create `static/anamnesis/js/module.js`.

This is the largest single piece of JS work. Structure (one function per
bullet, no framework):

1. On `DOMContentLoaded`, read JSON from `#module-data`, store in `state`.
2. Render the patient card (top), the step nav pills, and the active step
   container.
3. For the active step, render the example question, think-box, tip-box,
   the flip-cards grid (each card flips on click; back face has "Ya lo
   sabía" / "Repasar" buttons).
4. Render the irrelevant-items accordion below.
5. Render the dx-feedback panel (per-step diagnostic clues).
6. After last step → render the quiz, then the diagnostic reveal, then the
   "Hablar con paciente virtual" CTA list.
7. Every user action calls `postEvent(type, payload)` which does
   `fetch('/anamnesis/<slug>/event/', { method: 'POST', credentials: 'same-origin',
   headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
   body: JSON.stringify({ event_type: type, payload }) })`.

Use a simple `render(state)` function that re-renders the active section into a
container `<main id="module-root"></main>`. No virtual DOM — just `innerHTML =
template(state)` with template-string functions.

**Verify visually:** `python manage.py runserver`, open
`/anamnesis/cefalea/` and click through one whole module. Compare side-by-side
to `EduMed_UVa_completo/Anamnesis_Cefalea_v1.html`. Fix layout/JS bugs as you
go.

**Commit:** `feat(anamnesis): vanilla JS module frontend`.

> Note: this task is intentionally chunky — split further by section
> (header & nav → flip cards → dx feedback → quiz → final reveal), one
> commit per section, if it gets unwieldy.

---

## Phase 4 — Event tracking endpoint

### Task 4.1: Failing test for `event_view`

**Files:** Add to `anamnesis/tests/test_views.py`:

```python
import json
from django.contrib.auth import get_user_model
from anamnesis.models import StudentEvent

class EventViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('import_edumed_content', '--only=cefalea')
        cls.user = get_user_model().objects.create_user(
            username='alice', password='pw', role='estudiante', curso=3,
        )

    def test_anonymous_rejected(self):
        r = Client().post('/anamnesis/cefalea/event/',
                          data='{}', content_type='application/json')
        self.assertEqual(r.status_code, 302)  # redirect to login

    def test_logged_in_creates_event(self):
        c = Client()
        c.login(username='alice', password='pw')
        r = c.post('/anamnesis/cefalea/event/',
                   data=json.dumps({'event_type': 'flip', 'payload': {'card': 1}}),
                   content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(StudentEvent.objects.count(), 1)
```

### Task 4.2: Implement the endpoint

**Files:** Modify `anamnesis/views.py` and `anamnesis/urls.py`.

```python
# views.py
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Module, StudentEvent, ModuleProgress

VALID_EVENTS = {e.value for e in StudentEvent.EventType}

@login_required
@require_POST
def event_view(request, slug):
    module = get_object_or_404(Module, slug=slug)
    body = json.loads(request.body or '{}')
    event_type = body.get('event_type')
    if event_type not in VALID_EVENTS:
        return JsonResponse({'error': 'invalid event_type'}, status=400)
    StudentEvent.objects.create(
        student=request.user, module=module,
        event_type=event_type, payload=body.get('payload') or {},
    )
    progress, _ = ModuleProgress.objects.get_or_create(
        student=request.user, module=module,
    )
    if event_type == StudentEvent.EventType.STEP_OPEN:
        step_n = (body.get('payload') or {}).get('step', 0)
        if step_n > progress.last_step:
            progress.last_step = step_n
            progress.save(update_fields=['last_step'])
    elif event_type == StudentEvent.EventType.COMPLETE and not progress.completed_at:
        progress.completed_at = timezone.now()
        progress.save(update_fields=['completed_at'])
    return JsonResponse({'ok': True})
```

```python
# urls.py — add:
path('<slug:slug>/event/', views.event_view, name='anamnesis_event'),
```

Run the tests until both pass.

**Commit:** `feat(anamnesis): student event tracking endpoint`.

### Task 4.3: Wire `postEvent` into the JS frontend

**Files:** Modify `static/anamnesis/js/module.js`.

For each user action (step pill click → STEP_OPEN; flip card → FLIP;
"Ya lo sabía" → KNEW; "Repasar" → UNKNOWN; quiz answer → QUIZ_ANSWER;
view diagnosis → DX_VIEW; complete (last step done) → COMPLETE; click
"Hablar con paciente virtual" → VP_OPEN), call `postEvent(type, payload)`.
Already-defined helper from Task 3.3.

**Verify manually:** click around in browser, check `/admin/anamnesis/studentevent/`
that events appear with the right payload.

**Commit:** `feat(anamnesis): emit tracking events from frontend`.

---

## Phase 5 — Anamnesis dashboard + new landing + base template restyle

### Task 5.1: New base template in EduMed style

**Files:** Modify `templates/base.html`. Replace Tailwind references with the
EduMed CSS variables and load `/static/anamnesis/css/edumed.css` globally.
Provide blocks: `title`, `extra_css`, `topbar`, `content`, `extra_js`.

**Commit:** `feat(ui): EduMed base template (CSS variables, global styles)`.

### Task 5.2: New landing page (two CTAs)

**Files:** Modify `templates/landing.html`. Lay out the hero from the screenshot:
"INNOVACIÓN EDUCATIVA UVA" badge → big title "Domina el razonamiento clínico
con IA antes del paciente real." → subhead → primary CTA "Comenzar
Entrenamiento" linking to `{% url 'dashboard' %}` (existing chat dashboard) →
secondary CTA "Estudiar Anamnesis" linking to `{% url 'anamnesis_dashboard' %}`.

Below the hero keep the assistant grid section restyled with EduMed cards (same
visual language as `EduMed_UVa_completo/index.html` group cards but for
ACTUVa assistants).

**Commit:** `feat(ui): redesign landing in EduMed style with two CTAs`.

### Task 5.3: Anamnesis dashboard view

**Files:** Add `anamnesis/views.py::dashboard_view` and template
`templates/anamnesis/dashboard.html`. Port HTML/CSS from
`EduMed_UVa_completo/index.html`. Group modules by `Module.Group` choices,
render each card from the model. If user is authenticated, show a small
status pill on each card: "✓ Completado" / "En curso" / nothing, computed
from `ModuleProgress`.

Add URL `path('', views.dashboard_view, name='anamnesis_dashboard')` to
`anamnesis/urls.py`.

Test:
```python
def test_dashboard_lists_modules(self):
    call_command('import_edumed_content')
    r = Client().get('/anamnesis/')
    self.assertEqual(r.status_code, 200)
    for slug in ['cefalea', 'disnea', 'diarrea']:
        self.assertContains(r, slug)
```

**Commit:** `feat(anamnesis): dashboard with 12 modules grouped`.

---

## Phase 6 — Restyle existing templates

For each of the listed templates: open the existing template, port the layout
to EduMed CSS variables (`--blue-deep`, `--yellow`, `--surface`, `--bg`,
`--ink`...), drop Tailwind classes, use shared classes from `edumed.css`.
One commit per template:

- `templates/dashboard.html` (existing student dashboard)
- `templates/accounts/login.html`
- `templates/accounts/register.html`
- `templates/chat/session.html`
- `templates/chat/feedback.html`
- `templates/chat/no_access.html`
- `templates/cases/list.html`
- `templates/cases/create.html`
- `templates/stats/dashboard.html`
- `templates/stats/evaluaciones.html`

For each: `python manage.py runserver`, navigate to the page, screenshot or
side-by-side compare with `EduMed_UVa_completo/Anamnesis_Cefalea_v1.html`
header/footer for the visual baseline.

**Commit pattern:** `style(<area>): restyle <page> in EduMed visual language`.

---

## Phase 7 — Virtual patients + chat integration

### Task 7.1: Seed one base virtual patient per module

Extend `import_edumed_content`: after creating each `Module` and `Patient`,
create a `VirtualPatient` row with `display_name=patient.name`, `age=patient.age`,
`persona_summary` built from `patient.diagnosis` + first 2 quotes. Set
`assistant=None` initially (assistant_id filled by next task).

Test that `VirtualPatient.objects.filter(module__slug='cefalea').count() >= 1`.

**Commit:** `feat(anamnesis): seed one virtual patient per module from import`.

### Task 7.2: OpenAI assistant creation helper

**Files:** Add `anamnesis/openai_seed.py`:

```python
import os
from openai import OpenAI
from assistants.models import Assistant
from .models import VirtualPatient

PERSONA_SYSTEM = (
    "Eres {name}, paciente de {age} años. Tienes el cuadro clínico que se te describe.\n"
    "{summary}\n"
    "Responde SOLO como el paciente, en primera persona, en español, breve y natural.\n"
    "No reveles directamente el diagnóstico — el estudiante debe deducirlo."
)

def ensure_openai_assistant(vp: VirtualPatient) -> str | None:
    if vp.assistant and vp.assistant.openai_assistant_id:
        return vp.assistant.openai_assistant_id
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    client = OpenAI(api_key=api_key)
    persona = PERSONA_SYSTEM.format(
        name=vp.display_name, age=vp.age, summary=vp.persona_summary,
    )
    resp = client.beta.assistants.create(
        name=f'Paciente virtual: {vp.display_name}',
        instructions=persona,
        model='gpt-4o-mini',
    )
    a = Assistant.objects.create(
        name=f'Paciente: {vp.display_name}',
        slug=f'vp-{vp.module.slug}-{vp.id}',
        description=vp.persona_summary[:200],
        phase=Assistant.Phase.TRANSVERSAL,
        openai_assistant_id=resp.id,
        available_courses=[1, 2, 3, 4, 5, 6],
        system_prompt=persona,
    )
    vp.assistant = a
    vp.save(update_fields=['assistant'])
    return resp.id
```

Add management command `python manage.py seed_virtual_patient_assistants` that
loops `VirtualPatient.objects.filter(assistant__isnull=True)` and calls the
helper.

**Commit:** `feat(anamnesis): OpenAI assistant provisioning for virtual patients`.

### Task 7.3: "Hablar con paciente virtual" UI in module

**Files:** Modify `templates/anamnesis/module.html` and `static/anamnesis/js/module.js`.

After the final reveal section, render a list of `module.virtualpatient_set`
cards. Each card has the patient's display name, age, persona summary preview,
and a button "Hablar" that does:

```js
window.location.href = `/anamnesis/vp/${vpId}/start/`;
```

**Files:** Add `anamnesis/views.py::start_virtual_patient_view`:

```python
@login_required
def start_virtual_patient_view(request, vp_id):
    vp = get_object_or_404(VirtualPatient.objects.select_related('assistant'), id=vp_id)
    if not vp.assistant:
        return render(request, 'anamnesis/vp_not_ready.html', {'vp': vp})
    # Reuse existing chat start
    return redirect('start_chat', assistant_slug=vp.assistant.slug)
```

Add URL `path('vp/<int:vp_id>/start/', views.start_virtual_patient_view,
name='anamnesis_vp_start')`.

Test:
```python
def test_vp_redirects_to_chat_when_ready(self):
    call_command('import_edumed_content', '--only=cefalea')
    vp = VirtualPatient.objects.first()
    a = Assistant.objects.create(slug='test-vp', name='X', description='',
        phase=Assistant.Phase.TRANSVERSAL, available_courses=[3],
        openai_assistant_id='asst_test')
    vp.assistant = a; vp.save()
    c = Client(); c.login(username='alice', password='pw')
    r = c.get(f'/anamnesis/vp/{vp.id}/start/', follow=False)
    self.assertEqual(r.status_code, 302)
    self.assertIn('/chat/', r.url)
```

**Commit:** `feat(anamnesis): launch virtual patient chat from module`.

---

## Phase 8 — Quiz + extended teacher stats

### Task 8.1: Parse and import quiz questions

Extend `parse_module_html` to extract a `QUIZ` array (look at one of the EduMed
files for the actual structure name; if absent, design a minimal in-template
quiz). Extend the import command to populate `QuizQuestion`/`QuizChoice`.

Tests: `assertEqual(QuizQuestion.objects.filter(module__slug='cefalea').count(), >=3)`.

**Commit:** `feat(anamnesis): import quiz questions from EduMed`.

### Task 8.2: Quiz UI + submission

**Files:** Modify `module.js` quiz section. On submit, POST to
`/anamnesis/<slug>/quiz/` with the answer payload. Server creates `QuizAttempt`,
returns score and per-question correctness for inline feedback rendering.

Add `quiz_submit_view` in `anamnesis/views.py` and corresponding URL.

Tests for the endpoint (rejects anonymous, computes score, persists
QuizAttempt).

**Commit:** `feat(anamnesis): quiz submission endpoint and UI`.

### Task 8.3: Teacher metrics in `stats/`

**Files:** Modify `stats/views.py` and `templates/stats/dashboard.html`,
`templates/stats/evaluaciones.html`.

Add a new section "Anamnesis EduMed" for `is_profesor()` users, listing per
student: modules completed (count and percent), average quiz score,
total events. Reuse styling from EduMed dashboard cards.

Add aggregation queries in `stats/views.py` using
`anamnesis.models.ModuleProgress`, `QuizAttempt`, `StudentEvent`.

Test:
```python
def test_teacher_sees_anamnesis_metrics(self):
    # Create teacher, students, progress rows, quiz attempts.
    # Login as teacher.
    # GET stats dashboard, assert metrics rendered.
```

**Commit:** `feat(stats): teacher dashboard with EduMed metrics`.

---

## Phase 9 — Final import + smoke test

### Task 9.1: Import all 12 modules and verify each renders

```bash
python manage.py import_edumed_content
python manage.py runserver
```

For each of the 12 slugs (cefalea, disnea, edema, dolor-abdominal, disuria,
diarrea, mareo, sincope, fiebre, dolor-articular, tos, dolor-toracico):

- Open `/anamnesis/<slug>/` in the browser.
- Click through all steps.
- Submit the quiz.
- Click "Hablar con paciente virtual".
- Confirm `/admin/anamnesis/studentevent/` shows events.

Capture any module that fails to render and create follow-up issues.

**Commit:** none unless bugs are fixed.

### Task 9.2: README / CLAUDE.md update

**Files:** Update top-level `CLAUDE.md` (create if missing) and/or `README` with:
- Two main routes: `/` (landing) and `/anamnesis/` (modules).
- How to re-import content: `python manage.py import_edumed_content`.
- How to (re)provision virtual patients: `python manage.py seed_virtual_patient_assistants`.
- Where the design lives: `docs/plans/2026-05-04-edumed-redesign-design.md`.

**Commit:** `docs: document EduMed redesign workflow`.

---

## Cross-cutting reminders

- Run `python manage.py test` after every commit batch — keep all tests green.
- For visual changes, restart `runserver` and reload the browser; do not claim
  a template is restyled without seeing the rendered result.
- Use `python manage.py shell` to spot-check seeded data when writing the parser.
- Each frontend section in `module.js` is the riskiest piece — commit after
  every working subsection (nav, flip cards, dx panel, quiz, final reveal).
- Keep all UI text in Spanish to match existing project.
