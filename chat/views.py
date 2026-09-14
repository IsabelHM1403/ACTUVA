import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from assistants.models import Assistant

from . import openai_client
from .models import ChatSession, Message, SessionFeedback


logger = logging.getLogger(__name__)


def _history_tuples(session):
    """Pull the persisted (role, content) pairs for ``session`` in order."""
    return list(
        session.messages.order_by('created_at', 'id').values_list('role', 'content')
    )


@login_required
def start_session(request, assistant_slug):
    """Open a fresh chat session backed by Chat Completions + DB history.

    No outbound OpenAI call happens here — the conversation history lives in
    the ``Message`` table now, so the only work is closing any prior active
    session and creating a new one. The OpenAI call is deferred to
    ``send_message`` (per turn).
    """
    assistant = get_object_or_404(Assistant, slug=assistant_slug)
    if request.user.is_estudiante() and not assistant.is_available_for_curso(request.user.curso):
        return render(request, 'chat/no_access.html', {'assistant': assistant})
    ChatSession.objects.filter(
        user=request.user, assistant=assistant, is_active=True,
    ).update(is_active=False, ended_at=timezone.now())
    session = ChatSession.objects.create(
        user=request.user, assistant=assistant,
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
        'messages': session.messages.order_by('created_at', 'id'),
    })


@login_required
@require_POST
def send_message(request, session_id):
    """Persist the user turn, stream the assistant reply, persist that too."""
    session = get_object_or_404(
        ChatSession, id=session_id, user=request.user, is_active=True,
    )
    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Cuerpo JSON inválido'}, status=400)
    user_message = (body.get('message') or '').strip()
    if not user_message:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    # Snapshot history BEFORE saving the new user turn so the OpenAI request
    # passes prior context once and the new prompt arrives via user_message.
    history = _history_tuples(session)
    Message.objects.create(
        session=session, role=Message.Role.USER, content=user_message,
    )
    system_prompt = session.assistant.system_prompt or ''

    def event_stream():
        collected = []
        try:
            for chunk in openai_client.send_chat_completion_streaming(
                system_prompt, history, user_message,
            ):
                collected.append(chunk)
                yield f'data: {json.dumps({"text": chunk})}\n\n'
            full = ''.join(collected).strip()
            if full:
                Message.objects.create(
                    session=session, role=Message.Role.ASSISTANT, content=full,
                )
            yield 'data: {"done": true}\n\n'
        except Exception as e:
            # Persist whatever partial reply we got so it's not lost on retry,
            # then surface the failure to the UI.
            partial = ''.join(collected).strip()
            if partial:
                Message.objects.create(
                    session=session, role=Message.Role.ASSISTANT, content=partial,
                )
            logger.exception('Chat completion failed for session %s', session.id)
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    session.message_count += 2
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
    # Generate feedback before closing.
    system_prompt = session.assistant.system_prompt or ''
    history = _history_tuples(session)
    try:
        fb = openai_client.request_feedback(system_prompt, history)
        SessionFeedback.objects.create(
            session=session,
            score=max(1, min(10, int(fb.get('score', 5)))),
            strengths=fb.get('strengths', ''),
            improvements=fb.get('improvements', ''),
            summary=fb.get('summary', ''),
        )
    except Exception:
        # Don't block session end if feedback generation fails.
        logger.exception('Feedback generation failed for session %s', session.id)

    session.is_active = False
    session.ended_at = timezone.now()
    session.save(update_fields=['is_active', 'ended_at'])
    return redirect('session_feedback', session_id=session.id)


@login_required
def session_feedback_view(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    feedback = getattr(session, 'feedback', None)
    return render(request, 'chat/feedback.html', {
        'session': session,
        'assistant': session.assistant,
        'feedback': feedback,
    })
