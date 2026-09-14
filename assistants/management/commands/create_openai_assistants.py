from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'DEPRECATED. Provisioning OpenAI Assistants is no longer required '
        'after the migration to the Chat Completions API. Each Assistant '
        "row's ``system_prompt`` is sent on every chat turn instead."
    )

    def add_arguments(self, parser):
        # Kept for backwards compatibility with existing operator scripts.
        parser.add_argument('--model', type=str, default='gpt-4o-mini')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'create_openai_assistants is a no-op since the Chat Completions '
            'migration. Edit Assistant.system_prompt directly to change an '
            "assistant's behaviour."
        ))
