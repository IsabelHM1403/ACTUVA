# ACTUVa Platform Design

**Date:** 2026-03-27
**Status:** Approved

## Overview

Web platform for medical education at Universidad de Valladolid (UVa). Students practice clinical reasoning through 6 AI assistants powered by OpenAI Assistants API. Built with Django, all UI in Spanish.

## Architecture

**Stack:** Django 5.x + SQLite (dev) / PostgreSQL (prod) + Tailwind CSS + OpenAI Assistants API

**Django apps:**

| App | Purpose |
|-----|---------|
| `accounts` | Auth, roles (Estudiante/Profesor/Admin), student course year |
| `assistants` | Configuration of 6 AI assistants, OpenAI assistant_id mapping |
| `chat` | Chat UI, thread management, SSE streaming |
| `cases` | Professor uploads clinical cases (for Diferencialio, DecisionIA, EmpatIA) |
| `stats` | Aggregated usage statistics (hours, unique users) |

## Data Models

### accounts.User
- email, password, role (estudiante/profesor/admin), curso (1-6, nullable for non-students)

### assistants.Assistant
- name, slug, description, phase (fundacional/intermedia/avanzada/transversal)
- icon_image, openai_assistant_id
- available_courses: JSON field [1,2,3...] — which courses can access this assistant
- allows_custom_cases: boolean

### chat.ChatSession
- user (FK), assistant (FK), openai_thread_id
- started_at, ended_at, message_count, is_active
- No message content stored — only metadata for statistics

### cases.ClinicalCase
- title, description, content_file (FileField)
- assistant (FK), created_by (FK to User/Profesor)
- openai_file_id (after upload to OpenAI)
- created_at, is_active

### stats.UsageStat
- date, assistant (FK), total_minutes, unique_users
- Aggregated daily — no personal data

## Assistant Configuration

| Assistant | Phase | Courses | Custom Cases |
|-----------|-------|---------|--------------|
| Anamnesio | Fundacional | 1-2 | No |
| ExplorIA | Fund.-Intermedia | 1-4 | No |
| Diferencialio | Inter.-Avanzada | 3-6 | Yes |
| DecisionIA | Avanzada | 5-6 | Yes |
| EmpatIA | Transversal | 1-6 | Yes |
| ReumatIA | Por asignatura | 1-6 | Yes |

## OpenAI Integration

- **Setup:** Management command `create_assistants` creates 6 Assistants via API with system prompts (placeholder until extracted from Custom GPTs)
- **Session start:** `client.beta.threads.create()` — new thread per session
- **Message:** `client.beta.threads.messages.create()` + `runs.create(stream=True)`
- **Professor cases:** Uploaded via `client.files.create()`, attached to assistant's vector store
- **Session end:** Thread ID discarded, only stats (duration, message_count) saved

## Pages

1. **Landing** — adapted from borrador_web.html (Tailwind, UVa branding)
2. **Login / Register** — email + password, course selection for students
3. **Student Dashboard** — assistant cards filtered by course
4. **Chat** — streaming chat interface (SSE), session timer
5. **Professor Panel** — upload/manage clinical cases per assistant
6. **Admin** — Django admin + statistics dashboard (hours, users)

## Frontend

- Tailwind CSS (same design system as borrador: primary=#1A5F7A, brand-yellow=#FFCC00)
- Material Symbols for icons
- Chat streaming via Server-Sent Events (SSE) with Django StreamingHttpResponse
- Assistant mascot images (anamnesio.png, etc.) on cards

## Language

All UI in Spanish (es). No i18n — hardcoded Spanish strings.

## Security & Privacy

- No PII beyond email — no ethics committee needed
- No message content stored in DB
- Sessions are ephemeral (thread on OpenAI side, stats on our side)
- OpenAI API key stored in environment variable
- CSRF protection on all forms
- Role-based access control via Django permissions

## Statistics (Minimal)

- Total usage hours per assistant per day
- Number of unique users per assistant per day
- Calculated from ChatSession start/end timestamps
- Viewable by Admin role only
