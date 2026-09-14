"""ChatGPT integration backend.

We migrated off the OpenAI Assistants API (beta) — its sunset window arrived
in 2026 and the calls (``client.beta.threads.*``) started raising in prod,
producing 500s on "Comenzar Sesión". The new path uses the stable Chat
Completions API and keeps the conversation history in our own DB
(``chat.Message``) instead of OpenAI-side threads.

Public surface used by the chat views:

* ``send_chat_completion_streaming(system_prompt, history, user_message)`` —
  generator yielding text chunks for SSE streaming.
* ``request_feedback(system_prompt, history)`` — one-shot JSON evaluation.

Both honor ``MOCK_MODE`` (active when ``OPENAI_API_KEY`` is empty) so dev/CI
runs without an API key keep working with canned responses.
"""

import json as _json
import time
import uuid

from django.conf import settings


MOCK_MODE = not settings.OPENAI_API_KEY

DEFAULT_MODEL = 'gpt-4o-mini'


def get_client():
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _build_messages(system_prompt, history, user_message=None):
    """Assemble the OpenAI messages list from a system prompt + DB history.

    ``history`` is an iterable of ``(role, content)`` tuples (oldest first).
    ``user_message`` is appended as the latest user turn when provided.
    """
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    for role, content in history:
        messages.append({'role': role, 'content': content})
    if user_message is not None:
        messages.append({'role': 'user', 'content': user_message})
    return messages


def send_chat_completion_streaming(system_prompt, history, user_message, model=DEFAULT_MODEL):
    """Yield assistant text chunks for the next turn of a chat conversation.

    Mirrors the streaming contract the SSE view expects (a generator of
    plain strings). Errors in the underlying API call propagate; the view
    wraps the iterator in try/except and surfaces a ``data: {"error": ...}``
    line on failure so the UI degrades gracefully.
    """
    if MOCK_MODE:
        yield from _mock_streaming_response(system_prompt, user_message)
        return
    client = get_client()
    stream = client.chat.completions.create(
        model=model,
        messages=_build_messages(system_prompt, history, user_message),
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        text = getattr(delta, 'content', None)
        if text:
            yield text


FEEDBACK_PROMPT = (
    'EVALUACION FINAL: Genera una evaluacion estructurada del estudiante en formato JSON. '
    'Campos obligatorios: "score" (entero 1-10), "strengths" (texto en español), '
    '"improvements" (texto en español), "summary" (texto en español). '
    'Responde SOLO con JSON valido, sin markdown ni explicaciones adicionales.'
)


def request_feedback(system_prompt, history, model=DEFAULT_MODEL):
    """One-shot evaluation request that returns a parsed feedback dict."""
    if MOCK_MODE:
        return _mock_feedback(system_prompt)
    client = get_client()
    messages = _build_messages(system_prompt, history, FEEDBACK_PROMPT)
    completion = client.chat.completions.create(
        model=model, messages=messages,
    )
    raw = completion.choices[0].message.content or ''
    raw = raw.strip()
    # Strip possible markdown code fences the model may emit despite instructions.
    if raw.startswith('```'):
        raw = raw.split('\n', 1)[1] if '\n' in raw else raw[3:]
        if raw.endswith('```'):
            raw = raw[:-3]
        raw = raw.strip()
    return _json.loads(raw)


# --------------- Mock responses per assistant ---------------

MOCK_RESPONSES = {
    'anamnesio': [
        "Entendido. Soy tu paciente virtual. ",
        "Tengo 45 años y vengo porque llevo ",
        "unos días con un dolor en el pecho ",
        "que me preocupa bastante. ",
        "¿Qué te gustaría preguntarme?",
    ],
    'exploria': [
        "Muy bien, vamos a repasar la exploración. ",
        "¿Por qué sistema empezarías la exploración ",
        "física de este paciente? ",
        "Piensa en lo que ya sabes del caso ",
        "y decide el orden lógico.",
    ],
    'diferencialio': [
        "Analicemos este caso juntos. Paciente varón de 60 años ",
        "con disnea progresiva y edemas en miembros inferiores. ",
        "¿Cuáles serían tus tres primeras hipótesis diagnósticas? ",
        "Ordénalas por probabilidad y justifica brevemente.",
    ],
    'decisonia': [
        "Estás de guardia. Llega un paciente de 72 años ",
        "con dolor torácico agudo, diaforesis y hipotensión. ",
        "El ECG muestra elevación del ST en derivaciones inferiores. ",
        "¿Cuál es tu primera decisión y por qué?",
    ],
    'empatia': [
        "Eres el médico residente que debe comunicar ",
        "a una madre joven que los resultados de la biopsia ",
        "confirman un diagnóstico de cáncer de mama. ",
        "¿Cómo iniciarías la conversación? ",
        "Recuerda: empatía antes que información.",
    ],
    'reumatia': [
        "Vamos a repasar lupus eritematoso sistémico. ",
        "¿Cuáles son los criterios de clasificación ACR/EULAR 2019? ",
        "Intenta nombrar al menos 5 dominios clínicos ",
        "antes de que te dé pistas.",
    ],
}

DEFAULT_MOCK = [
    "Gracias por tu mensaje. ",
    "Soy un asistente en modo de demostración. ",
    "Cuando se configure la API de OpenAI, ",
    "recibirás respuestas reales del modelo de IA.",
]


def _mock_streaming_response(system_prompt, user_message):
    """Pick a canned response by sniffing the system prompt for an assistant slug."""
    chunks = DEFAULT_MOCK
    needle = (system_prompt or '').lower()
    for slug, response_chunks in MOCK_RESPONSES.items():
        if slug in needle:
            chunks = response_chunks
            break
    for chunk in chunks:
        time.sleep(0.15)
        yield chunk


# --------------- Mock feedback per assistant ---------------

MOCK_FEEDBACK = {
    'anamnesio': {
        'score': 7,
        'strengths': 'Buena estructura de la entrevista. Preguntas abiertas al inicio. Explora antecedentes personales.',
        'improvements': 'Faltó explorar antecedentes familiares y hábitos tóxicos. Podría profundizar en la cronología del dolor.',
        'summary': 'El estudiante demuestra una base sólida en anamnesis. Necesita sistematizar la recogida de información para no olvidar apartados clave.',
    },
    'exploria': {
        'score': 6,
        'strengths': 'Orden lógico en la exploración por aparatos. Buena técnica de auscultación cardiopulmonar.',
        'improvements': 'No realizó inspección general antes de la exploración dirigida. Olvidó la palpación abdominal.',
        'summary': 'Competencia intermedia en exploración física. Debe incorporar la inspección general como primer paso sistemático.',
    },
    'diferencialio': {
        'score': 8,
        'strengths': 'Excelente priorización de hipótesis. Justificación basada en hallazgos clínicos. Considera diagnósticos poco frecuentes.',
        'improvements': 'Podría mejorar la integración de datos analíticos con la clínica.',
        'summary': 'Muy buen razonamiento diferencial. El estudiante conecta bien los hallazgos con las probabilidades diagnósticas.',
    },
    'empatia': {
        'score': 7,
        'strengths': 'Tono empático y respetuoso. Da espacio al paciente para expresarse. Uso adecuado de silencios.',
        'improvements': 'Podría usar más frases de legitimación emocional. Evitar tecnicismos al comunicar malas noticias.',
        'summary': 'Buenas habilidades comunicativas con margen de mejora en la gestión emocional de situaciones difíciles.',
    },
}

DEFAULT_FEEDBACK = {
    'score': 6,
    'strengths': 'Participación activa en la sesión. Muestra interés por aprender.',
    'improvements': 'Necesita mayor profundidad en las respuestas y sistematización del abordaje clínico.',
    'summary': 'Sesión de entrenamiento completada. El estudiante muestra una base sobre la que seguir construyendo.',
}


def _mock_feedback(system_prompt):
    """Return mock feedback dict based on assistant slug sniffed from the prompt."""
    needle = (system_prompt or '').lower()
    for slug, fb in MOCK_FEEDBACK.items():
        if slug in needle:
            return dict(fb)
    return dict(DEFAULT_FEEDBACK)


# --------------- One-time provisioning helper used by management commands ---------------

def create_assistant(name, instructions, model=DEFAULT_MODEL):
    """Legacy provisioning hook kept for the seed_virtual_patient_assistants
    management command. With the Chat Completions backend we no longer need
    server-side OpenAI assistants — the assistant identity lives in the
    DB ``Assistant.system_prompt``. We return a placeholder identifier so
    callers that store ``openai_assistant_id`` keep working without DB
    migrations, but it is not used at request time anymore.
    """
    if MOCK_MODE:
        return f'mock_asst_{uuid.uuid4().hex[:8]}'
    # Synthesize a stable-looking id without calling the deprecated API.
    return f'local_asst_{uuid.uuid4().hex[:8]}'
