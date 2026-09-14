"""
OpenAI assistant provisioning for virtual patients.

For each ``VirtualPatient`` without an assistant, create an OpenAI
``Assistant`` seeded with the patient's persona, then create a
corresponding ``assistants.Assistant`` row and link it. Skips silently
if ``OPENAI_API_KEY`` is not set; in that case an admin can wire the
assistant later through the admin or by re-running the
``seed_virtual_patient_assistants`` management command after providing
the key.

Implementation note
-------------------
Uses ``chat.openai_client.create_assistant`` for parity with the rest of
the codebase. That helper transparently handles MOCK_MODE (returns a
fake id when no API key is set). Tests patch
``anamnesis.openai_seed.create_assistant`` to avoid real API calls.
"""
from django.conf import settings

from chat.openai_client import create_assistant

from .models import VirtualPatient


def ensure_openai_assistant(vp: VirtualPatient) -> str | None:
    """Provision an OpenAI assistant for ``vp`` if needed.

    Returns the OpenAI assistant id (existing or newly created), or
    ``None`` if no work was done because the API key is not configured.
    """
    if vp.assistant and vp.assistant.openai_assistant_id:
        return vp.assistant.openai_assistant_id
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None

    # Local import keeps the Assistant model out of import-time cycles.
    from assistants.models import Assistant

    persona = vp.persona_summary
    asst_id = create_assistant(
        name=f'Paciente virtual: {vp.display_name}',
        instructions=persona,
        model='gpt-4o-mini',
    )
    # Deterministic slug based on vp.id eliminates the slug-collision race.
    slug = f'vp-{vp.module.slug}-{vp.id}'
    try:
        a = Assistant.objects.create(
            name=f'Paciente: {vp.display_name}',
            slug=slug,
            description=persona[:200],
            phase=Assistant.Phase.TRANSVERSAL,
            openai_assistant_id=asst_id,
            available_courses=[1, 2, 3, 4, 5, 6],
            system_prompt=persona,
        )
    except Exception:
        # Local persistence failed — log loudly so the orphan OpenAI
        # assistant can be cleaned up manually. ``chat.openai_client``
        # does not currently expose a delete helper, so direct cleanup
        # via the OpenAI SDK would re-introduce the import we just
        # removed; logging the id is the safer trade-off.
        import logging
        logging.getLogger(__name__).exception(
            'Orphaned OpenAI assistant %s; manual cleanup needed', asst_id,
        )
        raise
    vp.assistant = a
    vp.save(update_fields=['assistant'])
    return asst_id
