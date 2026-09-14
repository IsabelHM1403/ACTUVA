"""Create or update an admin (superuser) idempotently.

Useful on deploy when you don't want to ssh into the box and run
``createsuperuser`` interactively. Reads credentials from CLI flags or
environment variables; both forms are safe to re-run.

Usage examples::

    # From .env / shell env (safest for prod)
    DJANGO_ADMIN_USERNAME=admin \\
    DJANGO_ADMIN_PASSWORD='secret' \\
    DJANGO_ADMIN_EMAIL='admin@example.com' \\
    python manage.py ensure_admin

    # From flags (good for quick one-offs)
    python manage.py ensure_admin --username admin --password secret --email admin@example.com
"""

import os

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = (
        'Create or update a Django superuser non-interactively. '
        'Reads DJANGO_ADMIN_USERNAME / DJANGO_ADMIN_PASSWORD / DJANGO_ADMIN_EMAIL '
        'from the environment if flags are not provided.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--username', help='Admin username (or DJANGO_ADMIN_USERNAME).')
        parser.add_argument('--password', help='Admin password (or DJANGO_ADMIN_PASSWORD).')
        parser.add_argument('--email', default='', help='Admin email (or DJANGO_ADMIN_EMAIL).')

    def handle(self, *args, **options):
        username = options['username'] or os.environ.get('DJANGO_ADMIN_USERNAME')
        password = options['password'] or os.environ.get('DJANGO_ADMIN_PASSWORD')
        email = options['email'] or os.environ.get('DJANGO_ADMIN_EMAIL', '')

        if not username:
            raise CommandError(
                'Username is required. Pass --username or set DJANGO_ADMIN_USERNAME.'
            )
        if not password:
            raise CommandError(
                'Password is required. Pass --password or set DJANGO_ADMIN_PASSWORD.'
            )

        user, created = User.objects.get_or_create(username=username, defaults={
            'email': email,
            'role': User.Role.ADMIN,
        })
        user.email = email or user.email
        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{verb} superuser "{username}".'))
