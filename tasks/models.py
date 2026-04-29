# Modelo de tarjeta (Card).

from django.conf import settings
from django.db import models


class Card(models.Model):
    """Tarjeta de tarea dentro de una columna Kanban."""

    class Priority(models.IntegerChoices):
        NONE = 0, 'None'
        LOW = 1, 'Low'
        MEDIUM = 2, 'Medium'
        HIGH = 3, 'High'
        URGENT = 4, 'Urgent'

    title = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    column = models.ForeignKey(
        'boards.Column',
        on_delete=models.CASCADE,
        related_name='cards',
    )
    order = models.PositiveIntegerField()
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=Priority.NONE,
    )
    due_date = models.DateField(null=True, blank=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_cards',
    )
    labels = models.ManyToManyField(
        'boards.Label',
        blank=True,
        related_name='cards',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'card'
        verbose_name_plural = 'cards'

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        """Devuelve True si la fecha límite ya pasó."""
        if not self.due_date:
            return False
        from django.utils import timezone
        return self.due_date < timezone.now().date()

    @property
    def board(self):
        """Atajo para acceder al tablero a través de la columna."""
        return self.column.board
