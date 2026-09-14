# Session Feedback Design

## Problem
Student diagnostic quality feedback from AI assistants is not persisted. Professors cannot see how students perform.

## Decision
Store AI-generated feedback per chat session in a dedicated `SessionFeedback` model. Generate feedback automatically when the student ends the session.

## Model: `SessionFeedback` (chat app)

| Field | Type | Notes |
|-------|------|-------|
| session | OneToOneField → ChatSession | Primary link |
| score | PositiveSmallIntegerField | 1-10 overall rating |
| strengths | TextField | What the student did well |
| improvements | TextField | Areas to improve |
| summary | TextField | General assessment |
| created_at | DateTimeField(auto_now_add) | |

## Flow

1. Student clicks "Terminar Sesion"
2. `end_session` view sends hidden evaluation prompt to OpenAI thread
3. AI returns JSON: `{"score": N, "strengths": "...", "improvements": "...", "summary": "..."}`
4. Parse response → save `SessionFeedback`
5. Redirect to `chat/feedback.html` showing the results
6. Session is marked inactive

## Mock Mode
When `MOCK_MODE` is active, generate a static mock feedback response per assistant type.

## Evaluation Prompt
Sent as a user message in the existing thread so the AI has full dialogue context:

```
EVALUACION FINAL: Genera una evaluacion estructurada del estudiante en formato JSON.
Campos: score (1-10), strengths (texto), improvements (texto), summary (texto).
Responde SOLO con JSON valido, sin markdown.
```

## Professor Dashboard

New view at `/evaluaciones/` accessible to `profesor` and `admin` roles.

Features:
- Table of all sessions with feedback (student, assistant, score, date)
- Filters: by assistant, by course, by date range
- Average score per student
- Click to expand full feedback detail

## Files to Create/Modify

- `chat/models.py` — add SessionFeedback
- `chat/openai_client.py` — add `request_feedback()` + mock variant
- `chat/views.py` — modify `end_session`, add `feedback_view`
- `chat/urls.py` — add feedback URL
- `templates/chat/feedback.html` — feedback results page
- `stats/views.py` — add professor evaluations view
- `stats/urls.py` — add evaluaciones URL
- `templates/stats/evaluaciones.html` — professor dashboard
- `templates/dashboard.html` — add link to evaluaciones for profesor
