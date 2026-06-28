"""
Demo seeder.

Creates a demo user, two boards with realistic columns/labels/cards, and
hands you ready-to-use credentials to log in. Idempotent: re-running
deletes the demo user's data and starts over.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --user demo --password demo12345 --reset
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from boards.models import Board, BoardMembership, Column, Label
from organizations.models import OrganizationMembership
from organizations.services import get_or_create_personal_organization
from tasks.models import Card, Comment, Subtask

User = get_user_model()


# Compañeros de equipo demo: (username, nombre, apellido).
DEMO_TEAMMATES = [
    ('ana', 'Ana', 'Ruiz'),
    ('luis', 'Luis', 'Gómez'),
]
# Asignación de tarjetas a compañeros (por título de tarjeta -> username).
DEMO_TEAMMATE_ASSIGN = {
    'Tokens del sistema de diseño': 'ana',
    'Diagrama ER de la BD': 'luis',
    'Modal edición de tarjeta': 'ana',
    'Permisos por board': 'luis',
    'Cobertura de tests al 80%': 'luis',
}


# Subtareas (checklist) y comentarios de ejemplo, por título de tarjeta.
DEMO_SUBTASKS = {
    'Tokens del sistema de diseño': [
        ('Definir paleta de color', True),
        ('Elegir tipografías', True),
        ('Escala de espaciado', False),
        ('Documentar tokens', False),
    ],
    'Reorden de columnas drag&drop': [
        ('Endpoint card-move', True),
        ('Listeners de drop', True),
        ('Animación de reorden', False),
    ],
    'Modal edición de tarjeta': [
        ('Maquetar formulario', True),
        ('Guardar etiquetas', False),
    ],
}

DEMO_COMMENTS = {
    'Reorden de columnas drag&drop': '¿Reutilizamos el endpoint de mover columnas?',
    'Modal edición de tarjeta': 'Falta el selector de asignados múltiples.',
}

# Tarjetas en las que el usuario demo aparece como asignado.
DEMO_ASSIGNED_TITLES = {
    'Reorden de columnas drag&drop',
    'Refresh automático JWT',
    'Modal edición de tarjeta',
}


DEMO_BOARDS = [
    {
        'name': 'Hoja de Ruta TFG',
        'description': 'Sprint final del proyecto Kanban TFG.',
        'columns': ['Pendiente', 'En Progreso', 'Revisión', 'Completado'],
        'labels': [
            ('Frontend', '#60a5fa'),
            ('Backend', '#f97316'),
            ('Diseño', '#a78bfa'),
            ('Bug', '#ef4444'),
            ('Docs', '#fbbf24'),
        ],
        'cards': [
            ('Tokens del sistema de diseño', 'Definir paleta, tipografía y espaciado en :root.', 3, ['Diseño', 'Frontend'], 'Pendiente', 5),
            ('Diagrama ER de la BD', 'Modelo entidad-relación para la memoria.', 1, ['Docs'], 'Pendiente', 10),
            ('Reorden de columnas drag&drop', 'Endpoint de move + frontend.', 2, ['Frontend', 'Backend'], 'En Progreso', 2),
            ('Refresh automático JWT', 'Renovar access token al recibir 401.', 4, ['Backend'], 'En Progreso', None),
            ('Modal edición de tarjeta', 'Prioridad, fecha, etiquetas, asignado.', 2, ['Frontend'], 'Revisión', 3),
            ('Permisos por board', 'Aislamiento entre usuarios y miembros.', 3, ['Backend'], 'Completado', -2),
        ],
    },
    {
        'name': 'Backlog Técnico',
        'description': 'Deuda técnica y mejoras de infraestructura.',
        'columns': ['Pendiente', 'Activo', 'Hecho'],
        'labels': [
            ('Tests', '#34d399'),
            ('Infra', '#06b6d4'),
            ('Refactor', '#ec4899'),
        ],
        'cards': [
            ('Cobertura de tests al 80%', 'Añadir APITestCase para cards y labels.', 2, ['Tests'], 'Pendiente', None),
            ('Migrar a PostgreSQL en producción', 'SQLite solo para dev local.', 1, ['Infra'], 'Pendiente', None),
            ('Extraer lógica de drag&drop a módulo', '', 1, ['Refactor'], 'Activo', None),
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed the database with a demo user and two example boards.'

    def add_arguments(self, parser):
        parser.add_argument('--user', default='demo', help='Demo username (default: demo).')
        parser.add_argument('--password', default='demo12345', help='Demo password (default: demo12345).')
        parser.add_argument('--reset', action='store_true', help='Wipe the demo user\'s boards before seeding.')

    @transaction.atomic
    def handle(self, *args, **opts):
        username = opts['user']
        password = opts['password']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': f'{username}@example.com'},
        )
        if created or opts['reset']:
            user.set_password(password)
            user.save()

        if opts['reset']:
            user.owned_boards.all().delete()
            self.stdout.write(self.style.WARNING(f'Wiped existing boards owned by {username}.'))

        organization = get_or_create_personal_organization(user)

        # Compañeros de equipo (miembros de la organización demo).
        teammates = {}
        for t_username, first, last in DEMO_TEAMMATES:
            mate, _ = User.objects.get_or_create(
                username=t_username,
                defaults={'email': f'{t_username}@example.com', 'first_name': first, 'last_name': last},
            )
            OrganizationMembership.objects.get_or_create(
                organization=organization, user=mate,
                defaults={'role': OrganizationMembership.Role.MEMBER},
            )
            teammates[t_username] = mate

        for spec in DEMO_BOARDS:
            board = Board.objects.create(
                owner=user, organization=organization,
                name=spec['name'], description=spec['description'],
            )
            # Compañeros como miembros del tablero (asignables y visibles).
            for mate in teammates.values():
                BoardMembership.objects.get_or_create(
                    board=board, user=mate,
                    defaults={'role': BoardMembership.Role.MEMBER},
                )
            cols = {}
            for i, title in enumerate(spec['columns']):
                cols[title] = Column.objects.create(board=board, title=title, order=i)

            labels = {}
            for name, color in spec['labels']:
                labels[name] = Label.objects.create(board=board, name=name, color=color)

            order_per_col = {}
            today = date.today()
            for title, desc, prio, label_names, col_name, due_offset in spec['cards']:
                col = cols[col_name]
                idx = order_per_col.get(col.id, 0)
                order_per_col[col.id] = idx + 1
                card = Card.objects.create(
                    column=col, title=title, description=desc,
                    priority=prio, order=idx,
                    due_date=(today + timedelta(days=due_offset)) if due_offset is not None else None,
                )
                if label_names:
                    card.labels.set([labels[n] for n in label_names])

                # Subtareas, comentarios y asignados de ejemplo (Fase 2).
                for s_idx, (s_title, s_done) in enumerate(DEMO_SUBTASKS.get(title, [])):
                    Subtask.objects.create(card=card, title=s_title, is_done=s_done, order=s_idx)
                if title in DEMO_COMMENTS:
                    Comment.objects.create(card=card, author=user, body=DEMO_COMMENTS[title])
                if title in DEMO_ASSIGNED_TITLES:
                    card.assignees.add(user)
                    card.assignee = user
                    card.save(update_fields=['assignee'])
                mate_username = DEMO_TEAMMATE_ASSIGN.get(title)
                if mate_username and mate_username in teammates:
                    mate = teammates[mate_username]
                    card.assignees.add(mate)
                    if card.assignee_id is None:
                        card.assignee = mate
                        card.save(update_fields=['assignee'])

        self.stdout.write(self.style.SUCCESS('\nDemo seeded.'))
        self.stdout.write(f'  user:     {username}')
        self.stdout.write(f'  password: {password}')
        self.stdout.write(f'  boards:   {len(DEMO_BOARDS)}\n')
