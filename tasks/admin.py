from django.contrib import admin
from django.utils.html import format_html

from .models import Card


PRIORITY_DOTS = {
    0: ('#444444', 'Sin prioridad'),
    1: ('#34d399', 'Baja'),
    2: ('#fbbf24', 'Media'),
    3: ('#f97316', 'Alta'),
    4: ('#ef4444', 'Urgente'),
}


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('title', 'column', 'priority_badge', 'due_date', 'assignee', 'order')
    list_filter = ('priority', 'column__board', 'labels')
    list_editable = ('order',)
    search_fields = ('title', 'description', 'column__board__name')
    autocomplete_fields = ['column', 'assignee', 'labels']
    ordering = ('column', 'order')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Prioridad', ordering='priority')
    def priority_badge(self, obj):
        color, label = PRIORITY_DOTS.get(obj.priority, ('#888', '?'))
        return format_html(
            '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            'background:{};margin-right:6px;"></span>{}',
            color, label,
        )
