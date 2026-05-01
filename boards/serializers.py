# Serializadores de la app boards.

from rest_framework import serializers

from tasks.serializers import CardSerializer
from users.serializers import UserSerializer

from .models import Board, BoardMembership, Column, Label


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'name', 'color', 'board']
        read_only_fields = ['id', 'board']


class ColumnSerializer(serializers.ModelSerializer):
    """Columna con sus tarjetas anidadas."""

    cards = CardSerializer(many=True, read_only=True)

    class Meta:
        model = Column
        fields = ['id', 'title', 'board', 'order', 'cards', 'created_at']
        read_only_fields = ['id', 'board', 'order', 'created_at']

    def create(self, validated_data):
        board = validated_data['board']
        last = board.columns.order_by('-order').first()
        validated_data['order'] = (last.order + 1) if last else 0
        return Column.objects.create(**validated_data)


class BoardMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = BoardMembership
        fields = ['id', 'user', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class BoardListSerializer(serializers.ModelSerializer):
    """Resumen del tablero para la vista de lista."""

    owner = UserSerializer(read_only=True)
    column_count = serializers.IntegerField(source='columns.count', read_only=True)

    class Meta:
        model = Board
        fields = [
            'id', 'name', 'description', 'owner',
            'column_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']


class BoardDetailSerializer(serializers.ModelSerializer):
    """Tablero completo con columnas, tarjetas, etiquetas y miembros."""

    owner = UserSerializer(read_only=True)
    columns = ColumnSerializer(many=True, read_only=True)
    labels = LabelSerializer(many=True, read_only=True)
    memberships = BoardMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = [
            'id', 'name', 'description', 'owner',
            'columns', 'labels', 'memberships',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
