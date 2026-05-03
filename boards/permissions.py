# Permisos personalizados para tableros.

from rest_framework import permissions

from .models import Board, BoardMembership


def user_can_access_board(user, board):
    """Comprueba si el usuario es dueño o miembro del tablero."""
    if not user or not user.is_authenticated:
        return False
    if board.owner_id == user.id:
        return True
    return BoardMembership.objects.filter(board=board, user=user).exists()


class IsBoardMember(permissions.BasePermission):
    """El usuario debe ser dueño o miembro del tablero."""

    def has_object_permission(self, request, view, obj):
        board = obj if isinstance(obj, Board) else getattr(obj, 'board', None)
        return user_can_access_board(request.user, board) if board else False


class IsBoardOwner(permissions.BasePermission):
    """Solo el propietario del tablero puede realizar esta acción."""

    def has_object_permission(self, request, view, obj):
        board = obj if isinstance(obj, Board) else getattr(obj, 'board', None)
        return bool(board and board.owner_id == request.user.id)
