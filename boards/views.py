# Vistas de tableros, columnas, etiquetas y miembros.

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Board, BoardMembership, Column, Label
from .permissions import IsBoardMember, IsBoardOwner, user_can_access_board
from .serializers import (
    BoardDetailSerializer,
    BoardListSerializer,
    BoardMembershipSerializer,
    ColumnSerializer,
    LabelSerializer,
)

User = get_user_model()


# =============================================
#  Vistas DRF (API REST) — se mantienen tal cual
# =============================================

class BoardViewSet(viewsets.ModelViewSet):
    """CRUD de tableros del usuario autenticado."""

    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return (
            Board.objects
            .filter(Q(owner=user) | Q(members=user))
            .distinct()
            .prefetch_related('columns__cards', 'labels', 'memberships__user')
            .select_related('owner')
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return BoardListSerializer
        return BoardDetailSerializer

    def get_permissions(self):
        if self.action in ('destroy', 'partial_update', 'update'):
            return [permissions.IsAuthenticated(), IsBoardOwner()]
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated(), IsBoardMember()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class _BoardScopedViewSet(viewsets.ModelViewSet):
    """Base para recursos anidados bajo un tablero (columnas, etiquetas)."""

    pagination_class = None
    permission_classes = [permissions.IsAuthenticated, IsBoardMember]
    board_relation_field = 'board'

    def get_board(self):
        board = get_object_or_404(Board, pk=self.kwargs['board_pk'])
        if not user_can_access_board(self.request.user, board):
            self.permission_denied(self.request, message='Not a member of this board.')
        return board

    def get_queryset(self):
        return self.queryset.filter(**{self.board_relation_field: self.get_board()})

    def perform_create(self, serializer):
        serializer.save(**{self.board_relation_field: self.get_board()})


class ColumnViewSet(_BoardScopedViewSet):
    queryset = Column.objects.all().prefetch_related('cards')
    serializer_class = ColumnSerializer

    @action(detail=True, methods=['post'])
    def move(self, request, board_pk=None, pk=None):
        """Mueve una columna a la posición indicada."""
        column = self.get_object()
        try:
            target_order = int(request.data['order'])
        except (KeyError, TypeError, ValueError):
            return Response({'detail': 'order is required.'}, status=status.HTTP_400_BAD_REQUEST)

        board = column.board
        siblings = list(board.columns.order_by('order'))
        ordered = [c for c in siblings if c.id != column.id]
        target_order = max(0, min(target_order, len(ordered)))
        ordered.insert(target_order, column)

        with transaction.atomic():
            offset = len(siblings) + 100
            board.columns.update(order=F('order') + offset)
            for i, c in enumerate(ordered):
                Column.objects.filter(pk=c.pk).update(order=i)

        return Response(ColumnSerializer(column).data)


class LabelViewSet(_BoardScopedViewSet):
    queryset = Label.objects.all()
    serializer_class = LabelSerializer


class BoardMembershipView(viewsets.ModelViewSet):
    """Gestión de miembros de un tablero."""

    serializer_class = BoardMembershipSerializer
    pagination_class = None
    lookup_field = 'user_id'
    lookup_url_kwarg = 'pk'

    def get_board(self):
        board = get_object_or_404(Board, pk=self.kwargs['board_pk'])
        if self.action in ('create', 'destroy'):
            if board.owner_id != self.request.user.id:
                self.permission_denied(self.request, message='Only the owner can manage members.')
        elif not user_can_access_board(self.request.user, board):
            self.permission_denied(self.request, message='Not a member of this board.')
        return board

    def get_queryset(self):
        return BoardMembership.objects.filter(board=self.get_board()).select_related('user')

    def create(self, request, *args, **kwargs):
        board = self.get_board()
        username = (request.data.get('username') or '').strip()
        role = request.data.get('role') or BoardMembership.Role.MEMBER
        if not username:
            return Response({'detail': 'username is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if user.id == board.owner_id:
            return Response({'detail': 'El propietario ya tiene acceso total.'}, status=status.HTTP_400_BAD_REQUEST)
        membership, created = BoardMembership.objects.get_or_create(
            board=board, user=user, defaults={'role': role},
        )
        if not created and membership.role != role:
            membership.role = role
            membership.save(update_fields=['role'])
        return Response(
            BoardMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


# =============================================
#  Vistas con templates (server-side rendering)
# =============================================

@login_required
def home_view(request):
    """Página principal con la lista de tableros."""
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
    from kanban.integrations import fetch_advice

    return render(request, 'index.html', {
        'boards': boards,
        'advice_quote': fetch_advice(),
    })


@login_required
@require_POST
def board_create_view(request):
    """Crear un tablero nuevo con columnas por defecto."""
    name = request.POST.get('name', '').strip()
    if not name:
        return redirect('home')

    desc = request.POST.get('description', '').strip()
    board = Board.objects.create(owner=request.user, name=name, description=desc)

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


@login_required
def board_detail_view(request, board_id):
    """Vista del tablero con columnas y tarjetas."""
    from tasks.models import Card

    board = get_object_or_404(Board, pk=board_id)
    if not user_can_access_board(request.user, board):
        return HttpResponseForbidden()

    columns = (
        board.columns
        .prefetch_related('cards__labels', 'cards__assignee')
        .order_by('order')
    )
    from kanban.integrations import fetch_random_users
    from tasks.plantillas_data import PLANTILLAS

    labels = board.labels.all()
    total_cards = Card.objects.filter(column__board=board).count()
    team_members = fetch_random_users(3)
    first_column = columns[0] if columns else None
    return render(request, 'board.html', {
        'board': board,
        'columns': columns,
        'labels': labels,
        'total_cards': total_cards,
        'team_members': team_members,
        'plantillas': PLANTILLAS,
        'first_column': first_column,
    })


# --- Columnas (template views) ---

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
