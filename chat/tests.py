import json
from unittest.mock import patch

from django.test import TestCase, Client
from accounts.models import User
from assistants.models import Assistant
from chat.models import ChatSession, Message


class ChatSessionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='est1', password='testpass123', role='estudiante', curso=2,
        )
        self.assistant = Assistant.objects.create(
            name='Anamnesio', slug='anamnesio', description='Test',
            phase='fundacional', available_courses=[1, 2], order=1,
        )

    def test_create_session(self):
        session = ChatSession.objects.create(
            user=self.user, assistant=self.assistant,
        )
        self.assertTrue(session.is_active)
        self.assertEqual(session.message_count, 0)


class ChatAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='est5', password='testpass123', role='estudiante', curso=5,
        )
        self.anamnesio = Assistant.objects.create(
            name='Anamnesio', slug='anamnesio', description='Test',
            phase='fundacional', available_courses=[1, 2], order=1,
        )

    def test_no_access_wrong_course(self):
        self.client.login(username='est5', password='testpass123')
        response = self.client.get('/chat/iniciar/anamnesio/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chat/no_access.html')


class ChatStartSessionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='est2', password='testpass123', role='estudiante', curso=2,
        )
        self.assistant = Assistant.objects.create(
            name='Anamnesio', slug='anamnesio', description='Test',
            phase='fundacional', available_courses=[1, 2], order=1,
            system_prompt='Eres Anamnesio.',
        )
        self.client.login(username='est2', password='testpass123')

    def test_start_creates_session_and_redirects(self):
        # No outbound OpenAI call on start anymore — history lives in our DB,
        # so the view should never 500 just from clicking "Comenzar Sesión".
        response = self.client.get('/chat/iniciar/anamnesio/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ChatSession.objects.count(), 1)
        session = ChatSession.objects.first()
        self.assertTrue(response.url.endswith(f'/chat/sesion/{session.id}/'))
        self.assertTrue(session.is_active)


class ChatSendMessagePersistsTest(TestCase):
    """The whole point of the migration: Q&A must land in the DB."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='est3', password='testpass123', role='estudiante', curso=2,
        )
        self.assistant = Assistant.objects.create(
            name='Anamnesio', slug='anamnesio', description='Test',
            phase='fundacional', available_courses=[1, 2], order=1,
            system_prompt='Eres Anamnesio. Responde como un paciente.',
        )
        self.client.login(username='est3', password='testpass123')
        self.session = ChatSession.objects.create(
            user=self.user, assistant=self.assistant,
        )

    def _consume(self, response):
        # StreamingHttpResponse must be drained for the generator to finish
        # and persist the assistant Message row.
        return b''.join(response.streaming_content)

    def test_user_and_assistant_messages_are_persisted(self):
        with patch(
            'chat.views.openai_client.send_chat_completion_streaming',
            return_value=iter(['Hola, ', 'soy paciente.']),
        ):
            response = self.client.post(
                f'/chat/sesion/{self.session.id}/enviar/',
                data=json.dumps({'message': '¿Qué le pasa?'}),
                content_type='application/json',
            )
            self._consume(response)

        msgs = list(self.session.messages.order_by('created_at', 'id'))
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, Message.Role.USER)
        self.assertEqual(msgs[0].content, '¿Qué le pasa?')
        self.assertEqual(msgs[1].role, Message.Role.ASSISTANT)
        self.assertEqual(msgs[1].content, 'Hola, soy paciente.')

    def test_history_passed_to_openai_uses_prior_messages(self):
        Message.objects.create(
            session=self.session, role=Message.Role.USER, content='Hola.',
        )
        Message.objects.create(
            session=self.session, role=Message.Role.ASSISTANT, content='Buenas.',
        )
        captured = {}

        def fake_stream(system_prompt, history, user_message):
            captured['system'] = system_prompt
            captured['history'] = list(history)
            captured['user'] = user_message
            yield 'OK.'

        with patch(
            'chat.views.openai_client.send_chat_completion_streaming',
            side_effect=fake_stream,
        ):
            response = self.client.post(
                f'/chat/sesion/{self.session.id}/enviar/',
                data=json.dumps({'message': '¿Cuándo empezó?'}),
                content_type='application/json',
            )
            self._consume(response)

        self.assertEqual(captured['system'], 'Eres Anamnesio. Responde como un paciente.')
        self.assertEqual(
            captured['history'],
            [('user', 'Hola.'), ('assistant', 'Buenas.')],
        )
        self.assertEqual(captured['user'], '¿Cuándo empezó?')

    def test_partial_reply_persisted_on_streaming_failure(self):
        def fake_stream(system_prompt, history, user_message):
            yield 'Comienzo de '
            raise RuntimeError('OpenAI flake')

        with patch(
            'chat.views.openai_client.send_chat_completion_streaming',
            side_effect=fake_stream,
        ):
            response = self.client.post(
                f'/chat/sesion/{self.session.id}/enviar/',
                data=json.dumps({'message': 'Hola'}),
                content_type='application/json',
            )
            chunks = self._consume(response).decode('utf-8')

        self.assertIn('"error"', chunks)
        msgs = list(self.session.messages.order_by('created_at', 'id'))
        self.assertEqual(msgs[-1].role, Message.Role.ASSISTANT)
        self.assertEqual(msgs[-1].content, 'Comienzo de')
