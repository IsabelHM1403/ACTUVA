"""
Management command: ``import_edumed_content``.

Purpose
-------
Imports the 12 EduMed anamnesis modules into the ``anamnesis`` content
tables (Module, Patient, PatientQuote, Step, StepDxFeedback,
DiagnosisCombo, QuizQuestion, QuizChoice). The module metadata (name,
group, gradient colors, deco code, emoji, description, order) is
hardcoded in the ``MODULES`` list below and was extracted from
``EduMed_UVa_completo/index.html`` (group cards, lines 411-597). The
dynamic content (patient, quotes, steps, feedback, combos, quiz) is
parsed from each module HTML using ``anamnesis.parser.parse_module_html``.

Quiz synthesis
--------------
The shipped EduMed HTMLs only contain ``QUIZ_CARDS`` (study flashcards),
not native multiple-choice items. We synthesise an MCQ per flashcard:
the question text is built from the card's clinical-vignette / clue
fields, the choices are every distinct ``dx`` in the module's
``QUIZ_CARDS`` array, and the correct choice is the card's own ``dx``.
If a card already exposes ``options``/``choices`` with explicit
``correct`` flags (a future-proofing path) we honour that shape instead.

Idempotency
-----------
Idempotent at the module level: ``Module`` rows are upserted by ``slug``,
and the child rows (``Patient`` and its quotes/feedback, ``Step`` and its
flip cards/irrelevant items/feedback, ``DiagnosisCombo``,
``QuizQuestion`` + ``QuizChoice``) are wiped and recreated on every run.
Running the command repeatedly leaves the DB in a consistent state
without ever creating duplicate ``Module`` rows.

Usage
-----
    python manage.py import_edumed_content              # all 12 modules
    python manage.py import_edumed_content --only=cefalea

Source files
------------
``<BASE_DIR>/EduMed_UVa_completo/Anamnesis_*.html``

Not yet imported (Phase 8 work)
-------------------------------
- ``FlipCard`` (per-step flip cards) — needs a separate HTML/DOM parser.
- ``IrrelevantItem`` (per-step distractor items) — same.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from anamnesis.models import (
    DiagnosisCombo,
    Module,
    Patient,
    PatientQuote,
    QuizChoice,
    QuizQuestion,
    Step,
    StepDxFeedback,
    VirtualPatient,
)
from anamnesis.parser import parse_module_html


# slug, filename, group, emoji, gradient_from, gradient_to, deco_code, name, description, order
MODULES = [
    ('dolor-toracico', 'Anamnesis_Dolor_Toracico_v2.html', 'cardio', '🫀', '#5c0a1a', '#8b1a2e', 'DxTc', 'Dolor torácico',
     '¿Cómo interpretar el dolor torácico? Diferenciando infarto, pericarditis, embolia pulmonar, disección aórtica o causas benignas.', 1),
    ('disnea', 'Anamnesis_Disnea_v1.html', 'cardio', '🫁', '#003060', '#004d8f', 'DxDs', 'Disnea',
     '¿Cómo orientar la falta de aire? Navegando entre insuficiencia cardiaca, EPOC, asma, neumonía o embolia pulmonar.', 2),
    ('edema-mmii', 'Anamnesis_Edema_MMII_v1.html', 'cardio', '🦵', '#003820', '#005c34', 'DxEd', 'Edema de MMII',
     '¿Cómo interpretar unas piernas hinchadas? Buscando claves de insuficiencia cardiaca, renal, hepática, venosa o fármacos.', 3),
    ('dolor-abdominal', 'Anamnesis_Dolor_Abdominal_v2.html', 'digestive', '🫃', '#5c2800', '#8b4000', 'DxAb', 'Dolor abdominal',
     '¿Cómo orientar el dolor abdominal? Navegando entre cólicos, pancreatitis, úlceras, abdomen agudo o embarazo ectópico.', 1),
    ('disuria', 'Anamnesis_Disuria_v1.html', 'digestive', '💧', '#280a50', '#401070', 'DxDu', 'Disuria',
     '¿Cómo orientar el escozor al orinar? Diferenciando cistitis, pielonefritis, uretritis, litiasis o síntomas ginecológicos.', 2),
    ('diarrea', 'Anamnesis_Diarrea_v1.html', 'digestive', '💩', '#003a20', '#005c34', 'DxDi', 'Diarrea',
     '¿Cómo abordar la diarrea? Distinguiendo infección, inflamación, malabsorción, fármacos o signos de deshidratación y alarma.', 3),
    ('cefalea', 'Anamnesis_Cefalea_v1.html', 'neuro', '🧠', '#3a0860', '#5c1490', 'DxCf', 'Cefalea',
     '¿Cómo orientar el dolor de cabeza? Navegando entre migrañas, cefalea tensional, meningitis, hemorragia subaracnoidea o neuralgias.', 1),
    ('mareo-vertigo', 'Anamnesis_Mareo_Vertigo_v1.html', 'neuro', '🌀', '#0a2a50', '#103d70', 'DxMv', 'Mareo / Vértigo',
     '¿Cómo abordar el mareo? Diferenciando vértigo periférico, causas neurológicas centrales, hipotensión ortostática o ansiedad.', 2),
    ('sincope', 'Anamnesis_Sincope_v1.html', 'neuro', '😵', '#4a2800', '#704000', 'DxSn', 'Síncope',
     '¿Cómo estudiar un desmayo? Distinguiendo síncope vasovagal, cardiogénico, ortostático, crisis epilépticas o causas graves.', 3),
    ('fiebre', 'Anamnesis_Fiebre_v1.html', 'general', '🌡️', '#5c1800', '#8a2800', 'DxFb', 'Fiebre',
     '¿Cómo estudiar la fiebre? Aprendiendo a buscar foco, patrón temporal, contexto epidemiológico y signos de gravedad.', 1),
    ('dolor-articular', 'Anamnesis_Dolor_Articular_v1.html', 'general', '🦴', '#2a1060', '#3d1a8a', 'DxAr', 'Dolor articular',
     '¿Cómo explorar el dolor articular? Separando artritis inflamatoria, artrosis, gota, artritis séptica o enfermedades autoinmunes.', 2),
    ('tos', 'Anamnesis_Tos_v1.html', 'general', '😮‍💨', '#3a0a60', '#5a1890', 'DxTo', 'Tos',
     '¿Cómo preguntar por la tos? Separando infección respiratoria, asma, EPOC, reflujo gastroesofágico, fármacos o señales de alarma.', 3),
]


# Field names used in QUIZ_CARDS across modules. We probe these in order to
# build the question stem; the first non-empty hit wins. Modules use a mix of
# `caso` (clinical vignette), `loc`/`tipo`/`mod`/`asoc` (descriptive snippets),
# `claves` (key clues), `patron`/`mecan`/`peli`, etc.
_CASE_FIELDS = ('caso', 'case', 'vignette')
_CLUE_FIELDS = (
    'claves', 'clues', 'pistas', 'loc', 'tipo', 'mod', 'asoc', 'patron',
    'mecan', 'peli', 'orienta',
)
_EXPLANATION_FIELDS = (
    'orienta', 'explanation', 'exp', 'patofisio', 'pat', 'prueba',
)


def _build_question_stem(card: dict) -> str:
    """Compose a human-readable MCQ stem from a flashcard dict.

    Prefers the clinical vignette (``caso``). Falls back to any combination
    of the descriptive fields available on the card. Always ends with the
    standard prompt asking for the most likely diagnosis.
    """
    case = ''
    for f in _CASE_FIELDS:
        v = card.get(f)
        if isinstance(v, str) and v.strip():
            case = v.strip()
            break

    if not case:
        # Fall back to a concatenation of clue fields.
        bits = []
        for f in _CLUE_FIELDS:
            v = card.get(f)
            if isinstance(v, str) and v.strip():
                bits.append(v.strip())
        case = ' · '.join(bits)

    case = case.strip()
    suffix = '¿Cuál es el diagnóstico más probable?'
    if not case:
        return suffix
    return f'{case}\n\n{suffix}'


def _build_explanation(card: dict) -> str:
    """Pick the best explanation snippet from a flashcard dict."""
    for f in _EXPLANATION_FIELDS:
        v = card.get(f)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ''


def _is_native_mcq(card: dict) -> bool:
    """Future-proofing: detect cards already shaped as multiple-choice items."""
    opts = card.get('options') or card.get('choices')
    return isinstance(opts, list) and bool(opts)


def _import_quiz_for_module(module, quiz_data):
    """Wipe and re-create QuizQuestion/QuizChoice rows for ``module``.

    Returns the number of questions created.
    """
    QuizQuestion.objects.filter(module=module).delete()  # cascades to choices
    if not quiz_data:
        return 0

    # Native MCQ shape (q + options[{text,correct}]) — use as-is.
    if all(_is_native_mcq(c) for c in quiz_data if isinstance(c, dict)):
        n = 0
        for i, item in enumerate(quiz_data):
            if not isinstance(item, dict):
                continue
            text = item.get('q') or item.get('text') or item.get('pregunta', '')
            q = QuizQuestion.objects.create(
                module=module,
                text=text,
                order=i,
                explanation=item.get('explanation') or item.get('exp', ''),
            )
            options = item.get('options') or item.get('choices') or []
            for j, opt in enumerate(options):
                if isinstance(opt, dict):
                    QuizChoice.objects.create(
                        question=q,
                        text=opt.get('text', ''),
                        is_correct=bool(opt.get('correct')),
                        order=j,
                    )
                else:
                    QuizChoice.objects.create(
                        question=q, text=str(opt), is_correct=False, order=j,
                    )
            n += 1
        return n

    # Synthesise MCQs from QUIZ_CARDS flashcards: choices are the distinct
    # diagnoses in this module, the correct one is the card's own `dx`.
    cards = [c for c in quiz_data if isinstance(c, dict) and c.get('dx')]
    if not cards:
        return 0

    # Preserve order of first appearance, drop duplicates.
    seen = set()
    diagnoses: list[str] = []
    for c in cards:
        dx = c['dx'].strip()
        if dx and dx not in seen:
            seen.add(dx)
            diagnoses.append(dx)

    n = 0
    for i, card in enumerate(cards):
        correct_dx = card['dx'].strip()
        q = QuizQuestion.objects.create(
            module=module,
            text=_build_question_stem(card),
            order=i,
            explanation=_build_explanation(card),
        )
        for j, dx in enumerate(diagnoses):
            QuizChoice.objects.create(
                question=q,
                text=dx,
                is_correct=(dx == correct_dx),
                order=j,
            )
        n += 1
    return n


class Command(BaseCommand):
    help = 'Imports EduMed module data from EduMed_UVa_completo/*.html into anamnesis tables.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--only',
            type=str,
            default=None,
            help='Slug of a single module to import (e.g. --only=cefalea).',
        )

    def handle(self, *args, only=None, **options):
        base = Path(settings.BASE_DIR) / 'EduMed_UVa_completo'
        for entry in MODULES:
            (slug, filename, group, emoji, gfrom, gto, deco, name, desc, order) = entry
            if only and slug != only:
                continue
            html_path = base / filename
            if not html_path.exists():
                self.stderr.write(self.style.ERROR(f'Missing file: {html_path}'))
                continue
            html = html_path.read_text(encoding='utf-8')
            data = parse_module_html(html)
            for warning in data.get('warnings', []):
                self.stdout.write(self.style.WARNING(f'  [{slug}] {warning}'))
            with transaction.atomic():
                module, _ = Module.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'name': name,
                        'group': group,
                        'emoji': emoji,
                        'gradient_from': gfrom,
                        'gradient_to': gto,
                        'deco_code': deco,
                        'description': desc,
                        'order': order,
                    },
                )
                # Wipe child rows for this module — cascades clean up the rest.
                Patient.objects.filter(module=module).delete()
                Step.objects.filter(module=module).delete()
                DiagnosisCombo.objects.filter(module=module).delete()

                patient_data = data.get('patient') or {}
                if not patient_data:
                    self.stdout.write(self.style.WARNING(
                        f'No patient block in {filename}; skipping {slug}.'
                    ))
                    continue

                patient = Patient.objects.create(
                    module=module,
                    name=patient_data['name'],
                    age=int(patient_data['age']),
                    diagnosis=patient_data.get('diagnosis', ''),
                    diagnosis_key=patient_data.get('diagnosisKey', []),
                    order=0,
                )
                quotes = patient_data.get('quotes', []) or []
                for i, quote_text in enumerate(quotes):
                    PatientQuote.objects.create(
                        patient=patient,
                        step_number=i + 1,
                        text=quote_text,
                    )

                # Seed a base VirtualPatient for this module (idempotent on
                # (module, display_name)). The persona is the LLM's instruction
                # set — it names the diagnosis so the LLM stays in character,
                # but the prompt explicitly tells the model not to reveal it.
                quotes_text = '\n'.join(
                    f'  - "{q}"' for q in (quotes[:2] or [])
                )
                persona = (
                    f'Eres {patient.name}, paciente de {patient.age} años, hispanohablante.\n'
                    f'Tu cuadro clínico real (no lo reveles directamente): {patient.diagnosis}.\n'
                    f'\nFragmentos representativos de cómo te expresas:\n{quotes_text}\n'
                    f'\nResponde en primera persona, en español natural y breve. '
                    f"NO reveles el diagnóstico bajo ninguna circunstancia. "
                    f"Si el estudiante te pregunta directamente '¿qué tienes?' o "
                    f"'¿qué enfermedad es?', responde algo como 'no lo sé, por eso "
                    f"vengo a consulta'. Solo describe tus síntomas y cómo te sientes."
                )

                # Public-facing card blurb — must NOT reveal the diagnosis.
                # The first patient quote is the chief complaint, which is
                # informative without naming the underlying disease.
                age_str = f'{patient.age} años'
                first_quote = (quotes or [''])[0]
                blurb = f'Paciente de {age_str} que acude por: "{first_quote[:140]}"'
                if len(blurb) > 290:
                    blurb = blurb[:287] + '…'

                VirtualPatient.objects.update_or_create(
                    module=module,
                    display_name=patient.name,
                    defaults={
                        'age': patient.age,
                        'persona_summary': persona,
                        'card_blurb': blurb,
                        'order': 0,
                    },
                )

                steps_by_n: dict[int, Step] = {}
                for item in data.get('steps', []):
                    step = Step.objects.create(
                        module=module,
                        n=item['n'],
                        title=item['title'],
                        example_question=item.get('eq', ''),
                    )
                    steps_by_n[step.n] = step

                n_dx = 0
                n_skipped_dx = 0
                for item in data.get('step_dx', []):
                    quote_idx = item['quoteIdx']
                    step = steps_by_n.get(quote_idx + 1)
                    if step is None:
                        # The dx entry references a step that does not exist
                        # (or the module uses a non-step-aligned dx structure).
                        n_skipped_dx += 1
                        continue
                    StepDxFeedback.objects.create(
                        step=step,
                        patient=patient,
                        quote_idx=quote_idx,
                        compat=item['compat'],
                        evidence=int(item.get('evidence', 1)),
                        interpretation=item.get('interpretation', ''),
                        fits_for=item.get('fitsFor', []),
                        rules_out=item.get('rulesOut', []),
                    )
                    n_dx += 1

                n_combos = 0
                for i, item in enumerate(data.get('combos', [])):
                    DiagnosisCombo.objects.create(
                        module=module,
                        dx=item['dx'],
                        compat=item['compat'],
                        symptoms=item.get('symptoms', []),
                        key_text=item.get('key', ''),
                        order=i,
                    )
                    n_combos += 1

                if n_skipped_dx > 0:
                    self.stdout.write(self.style.WARNING(
                        f'  [{slug}] skipped {n_skipped_dx} STEP_DX entries with no matching step (quoteIdx out of range)'
                    ))

                n_quiz = _import_quiz_for_module(module, data.get('quiz', []))

                self.stdout.write(self.style.SUCCESS(
                    f'Imported {slug}: {len(steps_by_n)} steps, {n_dx} feedbacks, {n_combos} combos, '
                    f'{n_quiz} quiz questions, '
                    f'{module.virtual_patients.count()} virtual patient(s)'
                ))
