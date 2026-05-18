# Vistas de tarjetas (Card).

import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from boards.models import Board, Column
from boards.permissions import IsBoardMember, user_can_access_board

from .models import Card
from .serializers import CardSerializer


# =============================================
#  Vista DRF (API REST) — se mantiene
# =============================================

class CardViewSet(viewsets.ModelViewSet):
    """CRUD y reordenación de tarjetas."""

    serializer_class = CardSerializer
    permission_classes = [permissions.IsAuthenticated, IsBoardMember]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        return (
            Card.objects
            .filter(Q(column__board__owner=user) | Q(column__board__members=user))
            .distinct()
            .select_related('column', 'assignee')
            .prefetch_related('labels')
        )

    def perform_create(self, serializer):
        column = serializer.validated_data['column']
        if not user_can_access_board(self.request.user, column.board):
            self.permission_denied(self.request, message='Cannot add card to this board.')
        serializer.save()

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """Mueve la tarjeta a otra columna/posición (drag & drop)."""
        card = self.get_object()
        try:
            target_column_id = int(request.data['column_id'])
            target_order = int(request.data['order'])
        except (KeyError, TypeError, ValueError):
            return Response(
                {'detail': 'column_id and order are required integers.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_column = get_object_or_404(Column, pk=target_column_id)
        if not user_can_access_board(request.user, target_column.board):
            return Response(
                {'detail': 'Cannot move card to a board you do not belong to.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            source_column = card.column
            source_order = card.order

            card.column = target_column
            card.save(update_fields=['column'])

            if source_column.id != target_column.id:
                Card.objects.filter(
                    column=source_column,
                    order__gt=source_order,
                ).update(order=F('order') - 1)

            Card.objects.filter(
                column=target_column,
                order__gte=target_order,
            ).exclude(pk=card.pk).update(order=F('order') + 1)

            card.order = target_order
            card.save(update_fields=['order'])

        return Response(CardSerializer(card).data)


# =============================================
#  Vistas con templates (server-side rendering)
# =============================================

@login_required
@require_POST
def card_create_view(request, board_id):
    """Crear tarjeta en una columna."""
    column_id = request.POST.get('column')
    column = get_object_or_404(Column, pk=column_id, board_id=board_id)
    if not user_can_access_board(request.user, column.board):
        return HttpResponseForbidden()

    title = request.POST.get('title', '').strip()
    if not title:
        return redirect('board-detail', board_id=board_id)

    last = column.cards.order_by('-order').first()
    order = (last.order + 1) if last else 0

    due = request.POST.get('due_date', '').strip() or None

    Card.objects.create(
        column=column,
        title=title,
        description=request.POST.get('description', '').strip(),
        priority=int(request.POST.get('priority', 0) or 0),
        due_date=due,
        order=order,
    )
    return redirect('board-detail', board_id=board_id)


@login_required
def card_edit_view(request, board_id, card_id):
    """Página de edición de una tarjeta."""
    card = get_object_or_404(Card, pk=card_id, column__board_id=board_id)
    board = card.column.board
    if not user_can_access_board(request.user, board):
        return HttpResponseForbidden()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            title = card.title

        card.title = title
        card.description = request.POST.get('description', '').strip()
        card.priority = int(request.POST.get('priority', 0) or 0)
        card.due_date = request.POST.get('due_date', '').strip() or None

        new_col_id = request.POST.get('column')
        if new_col_id:
            new_col = get_object_or_404(Column, pk=new_col_id, board=board)
            card.column = new_col

        card.save()

        label_ids = request.POST.getlist('labels')
        card.labels.set(label_ids)

        return redirect('board-detail', board_id=board_id)

    labels = board.labels.all()
    columns = board.columns.order_by('order')
    card_label_ids = set(card.labels.values_list('id', flat=True))

    return render(request, 'card_edit.html', {
        'board': board,
        'card': card,
        'labels': labels,
        'columns': columns,
        'card_label_ids': card_label_ids,
    })


@login_required
@require_POST
def card_delete_view(request, board_id, card_id):
    """Eliminar una tarjeta."""
    card = get_object_or_404(Card, pk=card_id, column__board_id=board_id)
    if not user_can_access_board(request.user, card.column.board):
        return HttpResponseForbidden()
    card.delete()
    return redirect('board-detail', board_id=board_id)


@login_required
@require_POST
def card_move_view(request, board_id):
    """Mover tarjeta entre columnas (AJAX, para drag & drop)."""
    board = get_object_or_404(Board, pk=board_id)
    if not user_can_access_board(request.user, board):
        return JsonResponse({'error': 'forbidden'}, status=403)

    data = json.loads(request.body)
    card_id = data.get('card_id')
    column_id = data.get('column_id')
    target_order = int(data.get('order', 0))

    card = get_object_or_404(Card, pk=card_id, column__board_id=board_id)
    target_column = get_object_or_404(Column, pk=column_id, board_id=board_id)

    with transaction.atomic():
        source_column = card.column
        source_order = card.order

        card.column = target_column
        card.save(update_fields=['column'])

        if source_column.id != target_column.id:
            Card.objects.filter(
                column=source_column, order__gt=source_order,
            ).update(order=F('order') - 1)

        Card.objects.filter(
            column=target_column, order__gte=target_order,
        ).exclude(pk=card.pk).update(order=F('order') + 1)

        card.order = target_order
        card.save(update_fields=['order'])

    return JsonResponse({'ok': True})


@login_required
def plantillas_api_view(request):
    """API interna: plantillas de tareas sugeridas."""
    from .plantillas_data import PLANTILLAS
    return JsonResponse(PLANTILLAS, safe=False)
