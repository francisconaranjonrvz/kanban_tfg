# Serializador de tarjetas (Card).

from rest_framework import serializers

from boards.models import Label
from users.serializers import UserSerializer

from .models import Card


class CardSerializer(serializers.ModelSerializer):
    """Serializador completo de Card. Lectura anidada, escritura por IDs."""

    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        source='assignee',
        queryset=UserSerializer.Meta.model.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    label_ids = serializers.PrimaryKeyRelatedField(
        source='labels',
        many=True,
        queryset=Label.objects.all(),
        required=False,
        write_only=True,
    )
    labels = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Card
        fields = [
            'id', 'title', 'description', 'column', 'order',
            'priority', 'due_date',
            'assignee', 'assignee_id',
            'labels', 'label_ids',
            'is_overdue', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'order', 'created_at', 'updated_at']

    def get_labels(self, obj):
        from boards.serializers import LabelSerializer
        return LabelSerializer(obj.labels.all(), many=True).data

    def create(self, validated_data):
        column = validated_data['column']
        last = column.cards.order_by('-order').first()
        validated_data['order'] = (last.order + 1) if last else 0
        labels = validated_data.pop('labels', [])
        card = Card.objects.create(**validated_data)
        if labels:
            card.labels.set(labels)
        return card

    def update(self, instance, validated_data):
        labels = validated_data.pop('labels', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if labels is not None:
            instance.labels.set(labels)
        return instance
