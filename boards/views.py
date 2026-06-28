# Vistas de tableros, columnas y etiquetas.

import calendar as _calendar
import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Board, Column
from .permissions import user_can_access_board


MONTH_NAMES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]
WEEKDAY_NAMES_ES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


@login_required
def home_view(request):
    """Página principal con los tableros de la organización activa."""
    boards = (
        Board.objects
        .filter(Q(owner=request.user) | Q(members=request.user))
        .distinct()
        .annotate(
            column_count=Count('columns', distinct=True),
            card_count=Count('columns__cards', distinct=True),
        )
        .select_related('owner')
        .order_by('-updated_at')
    )

    # Acotar a la organización activa. Si el usuario aún no tiene organización
    # (caso límite, p.ej. superusuario recién creado) se mantiene la vista por
    # propietario/miembro para no dejarle sin tableros.
    if request.organization is not None:
        boards = boards.filter(organization=request.organization)

    boards = list(boards)

    # Resumen tipo dashboard de la organización activa.
    from tasks.models import Card

    today = timezone.localdate()
    week_end = today + timedelta(days=7)
    board_ids = [b.id for b in boards]
    org_cards = Card.objects.filter(column__board_id__in=board_ids)
    summary = {
        'boards': len(boards),
        'tasks': org_cards.count(),
        'due_soon': org_cards.filter(due_date__gte=today, due_date__lte=week_end).count(),
        'overdue': org_cards.filter(due_date__lt=today).count(),
        'mine': org_cards.filter(assignees=request.user).count(),
    }

    return render(request, 'index.html', {'boards': boards, 'summary': summary})


@login_required
@require_POST
def board_create_view(request):
    """Crear un tablero nuevo con columnas por defecto."""
    name = request.POST.get('name', '').strip()
    if not name:
        return redirect('home')

    desc = request.POST.get('description', '').strip()
    board = Board.objects.create(
        owner=request.user,
        organization=request.organization,
        name=name,
        description=desc,
    )

    for i, title in enumerate(['Pendiente', 'En Progreso', 'Completado']):
        Column.objects.create(board=board, title=title, order=i)

    return redirect('board-detail', board_id=board.pk)


@login_required
@require_POST
def board_update_view(request, board_id):
    """Editar nombre y descripción de un tablero."""
    board = get_object_or_404(Board, pk=board_id)
    if board.owner_id != request.user.id:
        return HttpResponseForbidden()

    name = request.POST.get('name', '').strip()
    if name:
        board.name = name
    board.description = request.POST.get('description', '').strip()
    board.save(update_fields=['name', 'description', 'updated_at'])
    return redirect('home')


@login_required
@require_POST
def board_delete_view(request, board_id):
    """Eliminar un tablero (solo el propietario)."""
    board = get_object_or_404(Board, pk=board_id)
    if board.owner_id != request.user.id:
        return HttpResponseForbidden()
    board.delete()
    return redirect('home')


BOARD_VIEWS = {'kanban', 'list', 'table', 'calendar'}

# Ordenaciones permitidas para la vista de tabla (campo de BD).
TABLE_SORTS = {
    'title': 'title', '-title': '-title',
    'priority': 'priority', '-priority': '-priority',
    'due_date': 'due_date', '-due_date': '-due_date',
}


@login_required
def board_detail_view(request, board_id):
    """Vista del tablero. `?view=` alterna kanban (default), lista, tabla y
    calendario; solo el kanban carga board.js (drag&drop)."""
    from tasks.models import Card
    from tasks.views import _board_members

    board = get_object_or_404(Board, pk=board_id)
    if not user_can_access_board(request.user, board):
        return HttpResponseForbidden()

    view = request.GET.get('view', 'kanban')
    if view not in BOARD_VIEWS:
        view = 'kanban'

    base_ctx = {
        'board': board,
        'members': _board_members(board),
        'total_cards': Card.objects.filter(column__board=board).count(),
        'current_view': view,
    }

    # --- Calendario del tablero ---
    if view == 'calendar':
        today = timezone.localdate()
        year, month = _resolve_month(request, today)
        selected_priority = request.GET.get('priority') or ''
        cards = (
            Card.objects
            .filter(column__board=board, due_date__isnull=False)
            .select_related('column')
            .prefetch_related('labels')
        )
        if selected_priority:
            cards = cards.filter(priority=selected_priority)
        ctx = {
            **base_ctx,
            'weeks': build_month_grid(cards, year, month, today),
            'selected_priority': selected_priority,
        }
        ctx.update(month_nav_context(year, month, today))
        return render(request, 'board_calendar.html', ctx)

    # --- Tabla ---
    if view == 'table':
        sort = request.GET.get('sort', '')
        cards = (
            Card.objects
            .filter(column__board=board)
            .select_related('column', 'assignee')
            .prefetch_related('labels', 'assignees', 'subtasks')
        )
        if sort in ('progress', '-progress'):
            cards = sorted(
                cards.order_by('column__order', 'order'),
                key=lambda c: c.progress, reverse=(sort == '-progress'),
            )
        else:
            cards = cards.order_by(TABLE_SORTS.get(sort, 'column__order'), 'order')
        return render(request, 'board_table.html', {**base_ctx, 'cards': cards, 'sort': sort})

    # --- Kanban / Lista (comparten columnas + prefetch) ---
    columns = (
        board.columns
        .prefetch_related(
            'cards__labels', 'cards__assignee',
            'cards__assignees', 'cards__subtasks', 'cards__comments',
        )
        .order_by('order')
    )

    if view == 'list':
        return render(request, 'board_list.html', {**base_ctx, 'columns': columns})

    # Kanban (por defecto)
    from tasks.plantillas_data import PLANTILLAS
    first_column = columns[0] if columns else None
    return render(request, 'board.html', {
        **base_ctx,
        'columns': columns,
        'labels': board.labels.all(),
        'plantillas': PLANTILLAS,
        'first_column': first_column,
    })


# --- Columnas ---

@login_required
@require_POST
def column_create_view(request, board_id):
    """Añadir columna al tablero."""
    board = get_object_or_404(Board, pk=board_id)
    if not user_can_access_board(request.user, board):
        return HttpResponseForbidden()

    title = request.POST.get('title', '').strip()
    if title:
        last = board.columns.order_by('-order').first()
        order = (last.order + 1) if last else 0
        Column.objects.create(board=board, title=title, order=order)

    return redirect('board-detail', board_id=board_id)


@login_required
@require_POST
def column_rename_view(request, board_id, column_id):
    """Renombrar una columna."""
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    if not user_can_access_board(request.user, column.board):
        return HttpResponseForbidden()

    title = request.POST.get('title', '').strip()
    if title:
        column.title = title
        column.save(update_fields=['title'])

    # HTMX: devuelve solo el título actualizado para intercambiarlo en sitio.
    if request.headers.get('HX-Request'):
        return render(request, 'partials/_column_title.html', {'column': column})

    return redirect('board-detail', board_id=board_id)


@login_required
@require_POST
def column_delete_view(request, board_id, column_id):
    """Eliminar columna y todas sus tarjetas."""
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    if not user_can_access_board(request.user, column.board):
        return HttpResponseForbidden()
    column.delete()
    return redirect('board-detail', board_id=board_id)


@login_required
@require_POST
def column_move_view(request, board_id):
    """Reordenar columna (AJAX desde drag & drop)."""
    board = get_object_or_404(Board, pk=board_id)
    if not user_can_access_board(request.user, board):
        return JsonResponse({'error': 'forbidden'}, status=403)

    data = json.loads(request.body)
    column_id = data.get('column_id')
    target_order = int(data.get('order', 0))

    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    siblings = list(board.columns.order_by('order'))
    ordered = [c for c in siblings if c.id != column.id]
    target_order = max(0, min(target_order, len(ordered)))
    ordered.insert(target_order, column)

    with transaction.atomic():
        offset = len(siblings) + 100
        board.columns.update(order=F('order') + offset)
        for i, c in enumerate(ordered):
            Column.objects.filter(pk=c.pk).update(order=i)

    return JsonResponse({'ok': True})


# --- Calendario ---

def _accessible_boards(request):
    """Tableros del usuario en la organización activa."""
    boards = (
        Board.objects
        .filter(Q(owner=request.user) | Q(members=request.user))
        .distinct()
    )
    if request.organization is not None:
        boards = boards.filter(organization=request.organization)
    return boards


def _resolve_month(request, today):
    """Lee year/month de la query (con fallback al mes actual)."""
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (TypeError, ValueError):
        return today.year, today.month
    if not 1 <= month <= 12:
        return today.year, today.month
    return year, month


def build_month_grid(cards, year, month, today):
    """Rejilla mensual (semanas lun-dom, con días de meses vecinos) con las
    tarjetas agrupadas por fecha límite. `cards` es un queryset con due_date."""
    cal = _calendar.Calendar(firstweekday=0)
    grid = cal.monthdatescalendar(year, month)
    grid_start, grid_end = grid[0][0], grid[-1][-1]

    by_day = {}
    for card in cards.filter(due_date__gte=grid_start, due_date__lte=grid_end):
        by_day.setdefault(card.due_date, []).append(card)

    return [
        [{
            'date': day,
            'day': day.day,
            'in_month': day.month == month,
            'is_today': day == today,
            'cards': by_day.get(day, []),
        } for day in week]
        for week in grid
    ]


def month_nav_context(year, month, today):
    """Etiqueta del mes y enlaces de navegación (anterior/siguiente/hoy)."""
    prev_month = date(year, month, 1) - timedelta(days=1)
    next_month = date(year, month, 28) + timedelta(days=10)
    return {
        'weekday_names': WEEKDAY_NAMES_ES,
        'month_label': f'{MONTH_NAMES_ES[month]} {year}',
        'year': year,
        'month': month,
        'prev_year': prev_month.year,
        'prev_month': prev_month.month,
        'next_year': next_month.year,
        'next_month': next_month.month,
        'today_year': today.year,
        'today_month': today.month,
    }


@login_required
def calendario_view(request):
    """Vista mensual global: tareas de todos los tableros por fecha límite."""
    from tasks.models import Card

    today = timezone.localdate()
    year, month = _resolve_month(request, today)
    boards = _accessible_boards(request).order_by('name')

    # Filtros opcionales.
    selected_board = request.GET.get('board') or ''
    selected_priority = request.GET.get('priority') or ''

    cards = (
        Card.objects
        .filter(column__board__in=boards, due_date__isnull=False)
        .select_related('column__board')
        .prefetch_related('labels')
    )
    if selected_board:
        cards = cards.filter(column__board_id=selected_board)
    if selected_priority:
        cards = cards.filter(priority=selected_priority)

    context = {
        'weeks': build_month_grid(cards, year, month, today),
        'boards': boards,
        'selected_board': selected_board,
        'selected_priority': selected_priority,
    }
    context.update(month_nav_context(year, month, today))
    return render(request, 'calendario.html', context)


# --- Equipo ---

# Columnas consideradas "terminadas" (sus tareas no cuentan como carga activa).
DONE_COLUMN_TITLES = {
    'completado', 'hecho', 'done', 'terminado', 'finalizado', 'cerrado',
}
# Capacidad de tareas activas por persona antes de saturarse.
MEMBER_CAPACITY = 8


@login_required
def equipo_view(request):
    """Vista de equipo: miembros de la organización y su carga de trabajo."""
    from collections import Counter

    from tasks.models import Card

    org = request.organization
    board_ids = list(_accessible_boards(request).values_list('id', flat=True))

    if org is not None:
        memberships = list(
            org.memberships.select_related('user').order_by('role', 'user__username')
        )
    else:
        memberships = []

    members = []
    total_active = 0
    overloaded_count = 0

    for m in memberships:
        user = m.user
        assigned = (
            Card.objects
            .filter(assignees=user, column__board_id__in=board_ids)
            .select_related('column')
            .prefetch_related('labels')
        )
        active = [c for c in assigned if c.column.title.strip().lower() not in DONE_COLUMN_TITLES]
        active_count = len(active)
        overdue_count = sum(1 for c in active if c.is_overdue)

        # Áreas de trabajo = etiquetas más frecuentes entre sus tareas activas.
        label_counter = Counter()
        for c in active:
            for lbl in c.labels.all():
                label_counter[(lbl.name, lbl.color)] += 1
        areas = [
            {'name': name, 'color': color}
            for (name, color), _ in label_counter.most_common(3)
        ]

        percent_raw = round(active_count / MEMBER_CAPACITY * 100) if MEMBER_CAPACITY else 0
        overloaded = percent_raw > 85
        total_active += active_count
        if overloaded:
            overloaded_count += 1

        members.append({
            'user': user,
            'role': m.get_role_display(),
            'role_key': m.role,
            'active_count': active_count,
            'overdue_count': overdue_count,
            'capacity': MEMBER_CAPACITY,
            'percent': min(100, percent_raw),
            'percent_raw': percent_raw,
            'overloaded': overloaded,
            'areas': areas,
        })

    return render(request, 'equipo.html', {
        'members': members,
        'member_count': len(members),
        'total_active': total_active,
        'overloaded_count': overloaded_count,
        'capacity': MEMBER_CAPACITY,
    })
