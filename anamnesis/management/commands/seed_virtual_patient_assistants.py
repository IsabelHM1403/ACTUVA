"""Provision OpenAI assistants for VirtualPatients that don't have one."""
from django.core.management.base import BaseCommand

from anamnesis.models import VirtualPatient
from anamnesis.openai_seed import ensure_openai_assistant


class Command(BaseCommand):
    help = (
        "Create OpenAI assistants for VirtualPatients without one. "
        "Requires OPENAI_API_KEY in the environment."
    )

    def handle(self, *args, **options):
        without_assistant = VirtualPatient.objects.filter(assistant__isnull=True)
        if not without_assistant.exists():
            self.stdout.write(self.style.SUCCESS(
                'All virtual patients already have assistants. Nothing to do.'
            ))
            return
        provisioned = 0
        skipped = 0
        failed = 0
        for vp in without_assistant.select_related('module'):
            try:
                asst_id = ensure_openai_assistant(vp)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(
                    f'  [{vp.module.slug}] FAILED for {vp.display_name}: {exc}'
                ))
                failed += 1
                continue
            if asst_id:
                self.stdout.write(self.style.SUCCESS(
                    f'  [{vp.module.slug}] provisioned {vp.display_name} -> {asst_id}'
                ))
                provisioned += 1
            else:
                self.stdout.write(self.style.WARNING(
                    f'  [{vp.module.slug}] skipped {vp.display_name} (no OPENAI_API_KEY)'
                ))
                skipped += 1
        self.stdout.write(self.style.SUCCESS(
            f'Done: provisioned {provisioned}, skipped {skipped}, failed {failed}.'
        ))
