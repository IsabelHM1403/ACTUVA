# CLAUDE.md — actuva / EduMed UVa

Project guide for Claude Code sessions on this repository.

## What this project is

Django 5.1 application that combines two layers:
1. **EduMed (anamnesis app)** — interactive learning modules covering the 12 most
   frequent presenting symptoms (chest pain, dyspnea, headache, fever, etc.).
   Content is seeded from `EduMed_UVa_completo/` HTML files into Django models
   and rendered as a vanilla-JS frontend driven by JSON.
2. **OpenAI virtual-patient chat (chat + assistants apps)** — at the end of each
   module the student can chat with an OpenAI-backed simulated patient who
   embodies the module's case. Existing legacy app for student/professor flow.

## Routes

- `/` — landing (two CTAs: "Comenzar Entrenamiento" → /panel/, "Estudiar Anamnesis" → /anamnesis/)
- `/panel/` — student dashboard (existing chat-based assistants)
- `/anamnesis/` — EduMed modules dashboard (12 cards, 4 groups + video collections)
- `/anamnesis/<slug>/` — interactive module page
- `/anamnesis/<slug>/event/` — student event tracking POST endpoint
- `/anamnesis/<slug>/quiz/` — quiz submission POST endpoint
- `/anamnesis/vp/<id>/start/` — launch chat with a virtual patient
- `/cuentas/`, `/chat/`, `/casos/`, `/estadisticas/` — existing apps
- `/admin/` — Django admin (CMS for module content + tracking data)

## Common workflows

### Re-import EduMed content from source HTMLs
```
python manage.py import_edumed_content              # all 12
python manage.py import_edumed_content --only=cefalea
```
Idempotent at the module level — child rows (Patient, Step, etc.) are wiped and
recreated on re-run; VirtualPatient rows survive (so existing OpenAI assistant
links are preserved).

**VP rename caveat:** Re-importing a module after the source HTML changes a
patient's display_name will create a SECOND VirtualPatient and orphan the
original assistant link. To rename safely, edit the existing VP through
`/admin/` instead of changing the source HTML.

### Provision OpenAI assistants for virtual patients
Requires `OPENAI_API_KEY` in `.env`. Without it, the seed command logs and skips.
```
python manage.py seed_virtual_patient_assistants
```
Re-runnable; only provisions VPs that don't already have an `Assistant` link.

### Run the test suite
```
python manage.py test
```
Should report 101 tests passing as of the EduMed redesign merge; the count grows
as new features land. The `EduMed_UVa_completo/` directory at the repo root is
**required** to run the test suite — many `setUpTestData` blocks call
`import_edumed_content`, which reads source HTMLs from that directory. Subset:
```
python manage.py test anamnesis.tests
python manage.py test stats.tests
python manage.py test chat.tests
```

### Local dev
```
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Then open http://127.0.0.1:8000/ to see the landing.

## Architecture notes

- **anamnesis content models** (Module, Patient, PatientQuote, Step, FlipCard,
  IrrelevantItem, StepDxFeedback, DiagnosisCombo, QuizQuestion, QuizChoice,
  VirtualPatient) — CMS layer, editable in `/admin/`.
- **anamnesis tracking models** (ModuleProgress, StudentEvent, QuizAttempt) —
  every student action is recorded; teacher dashboard surfaces aggregates.
- **Frontend** — no build step. Vanilla ES2020 JS in `static/anamnesis/js/module.js`
  reads initial state from a `<script id="module-data" type="application/json">`
  tag and renders all sections. Events POST to `/anamnesis/<slug>/event/` with
  CSRF token from cookie.
- **Visual style** — CSS custom properties in `static/anamnesis/css/edumed.css`
  (--blue-deep, --yellow, --uva-blue, --surface, --bg, --ink-*, --line, --shadow-card,
  --font-serif=Playfair Display, --font-sans=Source Sans 3). Per-page CSS in
  `landing.css`, `dashboard.css`, `module.css`, `auth.css`.
- **Admin** — Module page hosts inline editors for Patient + Step. DiagnosisCombo,
  QuizQuestion, VirtualPatient have their own ModelAdmin with `module` filter to
  keep the Module change page fast.
- **OpenAI integration** — `chat/openai_client.py` is the single helper used by
  both the chat session flow and the virtual-patient provisioning command. Has a
  MOCK_MODE that activates when `OPENAI_API_KEY` is empty.
- Virtual-patient assistants are intentionally available to all cursos (1-6)
  regardless of the student's enrollment year; access is gated only by being
  logged in and the module being importable.

## Plan & design history

The migration from the prior ACTUVa Tailwind app to EduMed is documented in:
- `docs/plans/2026-05-04-edumed-redesign-design.md` — design decisions
- `docs/plans/2026-05-04-edumed-redesign.md` — phased implementation plan

Implementation followed those docs phase by phase on the `edumed-redesign` branch.
