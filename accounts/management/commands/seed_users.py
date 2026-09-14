"""
Generate test users for ACTUVa.

Usage:
  python manage.py seed_users                  # defaults: 30 students, 4 professors
  python manage.py seed_users --students 50    # 50 students, 4 professors
  python manage.py seed_users --professors 6   # 30 students, 6 professors
  python manage.py seed_users --clear          # delete all non-superuser test users first
"""
import random
from django.core.management.base import BaseCommand
from accounts.models import User

NOMBRES = [
    'Ana', 'Pablo', 'Laura', 'Carlos', 'María', 'Javier', 'Elena', 'Diego',
    'Sofía', 'Andrés', 'Lucía', 'Miguel', 'Carmen', 'Alejandro', 'Isabel',
    'Daniel', 'Marta', 'Sergio', 'Paula', 'Raúl', 'Alba', 'Iván', 'Clara',
    'Hugo', 'Nerea', 'Adrián', 'Irene', 'Óscar', 'Julia', 'Marcos',
    'Patricia', 'David', 'Rocío', 'Fernando', 'Alicia', 'Jorge', 'Beatriz',
    'Rubén', 'Sara', 'Guillermo', 'Cristina', 'Álvaro', 'Natalia', 'Tomás',
    'Victoria', 'Nicolás', 'Lola', 'Enrique', 'Teresa', 'Manuel',
]

APELLIDOS = [
    'García', 'Rodríguez', 'Martínez', 'López', 'González', 'Hernández',
    'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Flores', 'Rivera', 'Gómez',
    'Díaz', 'Reyes', 'Morales', 'Jiménez', 'Ruiz', 'Álvarez', 'Romero',
    'Serrano', 'Blanco', 'Molina', 'Suárez', 'Ortega', 'Delgado', 'Castro',
    'Marín', 'Núñez', 'Iglesias', 'Medina', 'Garrido', 'Cortés', 'Herrera',
    'Santos', 'Vega', 'Domínguez', 'Ramos', 'Cabrera', 'Navarro',
]

PASSWORD = 'actuva2026'


def _slug(name):
    """Remove accents for username generation."""
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u', 'Á': 'A', 'É': 'E', 'Í': 'I',
        'Ó': 'O', 'Ú': 'U', 'Ñ': 'N',
    }
    for k, v in replacements.items():
        name = name.replace(k, v)
    return name.lower()


class Command(BaseCommand):
    help = 'Genera usuarios de prueba (estudiantes y profesores)'

    def add_arguments(self, parser):
        parser.add_argument('--students', type=int, default=30, help='Número de estudiantes')
        parser.add_argument('--professors', type=int, default=4, help='Número de profesores')
        parser.add_argument('--clear', action='store_true', help='Borrar usuarios test existentes')

    def handle(self, *args, **options):
        if options['clear']:
            deleted, _ = User.objects.filter(is_superuser=False).delete()
            self.stdout.write(f'Eliminados {deleted} usuarios de prueba.')

        created_students = 0
        created_profs = 0
        used_usernames = set(User.objects.values_list('username', flat=True))

        # --- Students ---
        random.shuffle(NOMBRES)
        random.shuffle(APELLIDOS)
        for i in range(options['students']):
            nombre = NOMBRES[i % len(NOMBRES)]
            apellido = APELLIDOS[i % len(APELLIDOS)]
            # Avoid duplicates
            base = f'{_slug(nombre)}.{_slug(apellido)}'
            username = base
            n = 2
            while username in used_usernames:
                username = f'{base}{n}'
                n += 1
            used_usernames.add(username)

            curso = random.randint(1, 6)
            User.objects.create_user(
                username=username,
                email=f'{username}@alumnos.uva.es',
                password=PASSWORD,
                first_name=nombre,
                last_name=apellido,
                role='estudiante',
                curso=curso,
            )
            created_students += 1

        # --- Professors ---
        prof_nombres = ['Dr. Martín', 'Dra. Vázquez', 'Dr. Cuesta', 'Dra. Prieto',
                        'Dr. Fernández', 'Dra. Calvo', 'Dr. Rojo', 'Dra. Gil']
        for i in range(options['professors']):
            nombre_completo = prof_nombres[i % len(prof_nombres)]
            parts = nombre_completo.split()
            titulo = parts[0].rstrip('.')
            apellido = parts[1]
            username = f'prof.{_slug(apellido)}'
            n = 2
            while username in used_usernames:
                username = f'prof.{_slug(apellido)}{n}'
                n += 1
            used_usernames.add(username)

            User.objects.create_user(
                username=username,
                email=f'{_slug(apellido)}@med.uva.es',
                password=PASSWORD,
                first_name=titulo,
                last_name=apellido,
                role='profesor',
            )
            created_profs += 1

        self.stdout.write(self.style.SUCCESS(
            f'Creados {created_students} estudiantes y {created_profs} profesores.\n'
            f'Password para todos: {PASSWORD}'
        ))
