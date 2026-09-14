from django.test import TestCase
from accounts.models import User


class UserModelTest(TestCase):
    def test_create_estudiante(self):
        user = User.objects.create_user(
            username='est1', password='testpass123',
            role='estudiante', curso=3,
        )
        self.assertTrue(user.is_estudiante())
        self.assertEqual(user.curso, 3)

    def test_create_profesor(self):
        user = User.objects.create_user(
            username='prof1', password='testpass123',
            role='profesor',
        )
        self.assertTrue(user.is_profesor())
        self.assertIsNone(user.curso)

    def test_curso_nullable_for_non_students(self):
        user = User.objects.create_user(
            username='admin1', password='testpass123',
            role='admin',
        )
        self.assertIsNone(user.curso)
