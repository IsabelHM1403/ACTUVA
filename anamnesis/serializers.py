"""Serializers for shipping module data into the front-end as JSON.

The module page renders almost all of its UI from a single `<script
type="application/json">` tag emitted via `{{ data|json_script:"module-data" }}`.
`serialize_module_for_frontend` is the single source of truth for that payload.
"""


def serialize_module_for_frontend(module):
    """Return a JSON-serializable dict describing a module for the front-end.

    Keys mirror what the vanilla-JS module renderer (`static/anamnesis/js/module.js`)
    expects to find. The shape stays close to the in-browser data structures used
    by the original Preact reference (`Anamnesis_Cefalea_v1.html`) so the JS port
    stays straightforward.
    """
    patient = module.patients.first()
    steps = list(module.steps.order_by('n'))

    patient_block = None
    if patient is not None:
        patient_block = {
            'name': patient.name,
            'age': patient.age,
            'diagnosis': patient.diagnosis,
            'diagnosis_key': patient.diagnosis_key,
            'quotes': [q.text for q in patient.quotes.order_by('step_number')],
        }

    return {
        'slug': module.slug,
        'name': module.name,
        'emoji': module.emoji,
        'gradient_from': module.gradient_from,
        'gradient_to': module.gradient_to,
        'patient': patient_block,
        'steps': [
            {
                'n': s.n,
                'title': s.title,
                'example_question': s.example_question,
                'think_box': s.think_box,
                'tip_box': s.tip_box,
                'sec_label': s.sec_label,
                'flip_cards': [
                    {'label': fc.label, 'badge': fc.badge, 'back': fc.back_text}
                    for fc in s.flip_cards.order_by('order')
                ],
                'irrelevant': [
                    {'name': i.name, 'badge': i.badge, 'body': i.body_text}
                    for i in s.irrelevant_items.order_by('order')
                ],
                'dx_feedback': [
                    {
                        'compat': dx.compat,
                        'evidence': dx.evidence,
                        'interpretation': dx.interpretation,
                        'fits_for': dx.fits_for,
                        'rules_out': dx.rules_out,
                        'quote_idx': dx.quote_idx,
                    }
                    for dx in s.dx_feedbacks.all()
                ],
            }
            for s in steps
        ],
        'combos': [
            {
                'dx': c.dx,
                'compat': c.compat,
                'symptoms': c.symptoms,
                'key': c.key_text,
            }
            for c in module.diagnosis_combos.order_by('order')
        ],
        'virtual_patients': [
            {
                'id': vp.id,
                'display_name': vp.display_name,
                'age': vp.age,
                # ``card_blurb`` is the public-safe short description (was
                # previously ``persona_summary[:280]``, which leaked the
                # diagnosis through View Source — the persona prompt names
                # the diagnosis so the LLM stays in character).
                'card_blurb': vp.card_blurb,
                'available': bool(vp.assistant and vp.assistant.openai_assistant_id),
            }
            for vp in module.virtual_patients.select_related('assistant').order_by('order')
        ],
        # NOTE: ``is_correct`` is intentionally omitted from the choice payload —
        # the answer key must never reach the client. The submit endpoint
        # (``quiz_submit_view``) is the sole authority on which choice is right.
        # ``explanation`` is also intentionally omitted: it often paraphrases
        # the correct answer and would leak it via View Source. The
        # explanation is reintroduced in the per-question feedback returned
        # by ``quiz_submit_view`` after submission, so the user-facing UX
        # (renderQuiz reads ``attempt.perQuestion[q.id].explanation``) is
        # unchanged.
        'quiz': [
            {
                'id': q.id,
                'text': q.text,
                'choices': [
                    {'id': c.id, 'text': c.text}
                    for c in q.choices.order_by('order')
                ],
            }
            for q in module.quiz_questions.order_by('order').prefetch_related('choices')
        ],
    }


def serialize_progress(progress):
    """Return the per-student progress hint exposed to the front-end.

    Returns ``None`` for anonymous users (caller should not include the key).
    The front-end uses ``last_step`` to resume the student mid-module.
    """
    if progress is None:
        return None
    return {
        'last_step': progress.last_step,
        'completed': bool(progress.completed_at),
    }
