from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from anamnesis.models import Module, Patient, PatientQuote, Step


class ImportCommandTest(TestCase):
    def test_imports_cefalea(self):
        out = StringIO()
        call_command('import_edumed_content', '--only=cefalea', stdout=out)
        m = Module.objects.get(slug='cefalea')
        self.assertEqual(m.name, 'Cefalea')
        self.assertEqual(Patient.objects.filter(module=m).count(), 1)
        self.assertEqual(Step.objects.filter(module=m).count(), 7)
        # PatientQuote: there are 7 quotes for the single patient.
        self.assertEqual(PatientQuote.objects.filter(patient__module=m).count(), 7)

    def test_idempotent(self):
        call_command('import_edumed_content', '--only=cefalea')
        before = Module.objects.count()
        call_command('import_edumed_content', '--only=cefalea')
        self.assertEqual(Module.objects.count(), before)

    def test_imports_all_twelve(self):
        call_command('import_edumed_content')
        self.assertEqual(Module.objects.count(), 12)

    def test_disnea_warns_on_orphan_dx(self):
        out = StringIO()
        call_command('import_edumed_content', '--only=disnea', stdout=out)
        self.assertIn('skipped 2 STEP_DX', out.getvalue())

    def test_import_creates_one_virtual_patient_per_module(self):
        from anamnesis.models import Module, VirtualPatient
        call_command('import_edumed_content', '--only=cefalea')
        cef = Module.objects.get(slug='cefalea')
        self.assertEqual(cef.virtual_patients.count(), 1)
        vp = cef.virtual_patients.first()
        self.assertIn('Ana G.', vp.display_name)
        self.assertEqual(vp.age, 34)
        # Persona must be non-trivial — it carries the LLM's instructions.
        self.assertGreater(len(vp.persona_summary), 100)

    def test_import_virtual_patient_idempotent(self):
        from anamnesis.models import VirtualPatient
        call_command('import_edumed_content', '--only=cefalea')
        before = VirtualPatient.objects.count()
        call_command('import_edumed_content', '--only=cefalea')
        self.assertEqual(VirtualPatient.objects.count(), before)

    def test_imports_quiz_questions(self):
        from anamnesis.models import QuizQuestion
        call_command('import_edumed_content', '--only=cefalea')
        cef_questions = QuizQuestion.objects.filter(module__slug='cefalea')
        self.assertGreaterEqual(cef_questions.count(), 3)
        for q in cef_questions:
            self.assertGreaterEqual(q.choices.count(), 2)
            self.assertGreaterEqual(q.choices.filter(is_correct=True).count(), 1)

    def test_quiz_idempotent(self):
        from anamnesis.models import QuizQuestion
        call_command('import_edumed_content', '--only=cefalea')
        before = QuizQuestion.objects.count()
        call_command('import_edumed_content', '--only=cefalea')
        self.assertEqual(QuizQuestion.objects.count(), before)
