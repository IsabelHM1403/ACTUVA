from django.test import TestCase
from assistants.models import Assistant


class AssistantModelTest(TestCase):
    def setUp(self):
        self.asst = Assistant.objects.create(
            name='Anamnesio', slug='anamnesio',
            description='Historia clínica', phase='fundacional',
            available_courses=[1, 2], allows_custom_cases=False, order=1,
        )

    def test_available_for_curso(self):
        self.assertTrue(self.asst.is_available_for_curso(1))
        self.assertTrue(self.asst.is_available_for_curso(2))
        self.assertFalse(self.asst.is_available_for_curso(3))

    def test_str(self):
        self.assertEqual(str(self.asst), 'Anamnesio')
