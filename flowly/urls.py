# URLs principales del proyecto.

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, re_path
from django.views.static import serve as static_serve

from boards.views import (
    board_create_view,
    board_delete_view,
    board_detail_view,
    board_update_view,
    calendario_view,
    column_create_view,
    column_delete_view,
    column_move_view,
    column_rename_view,
    equipo_view,
    home_view,
)
from tasks.views import (
    card_create_view,
    card_delete_view,
    card_edit_view,
    card_move_view,
    comment_create_view,
    comment_delete_view,
    plantillas_api_view,
    subtask_create_view,
    subtask_delete_view,
    subtask_toggle_view,
)
from organizations.views import org_switch_view
from users.views import appearance_update_view, perfil_view, register_view

from .health import liveness, readiness

urlpatterns = [
    path('admin/', admin.site.urls),

    # Healthchecks para Docker
    path('healthz', liveness, name='healthz'),
    path('readyz', readiness, name='readyz'),

    # API interna (plantillas de tareas)
    path('api/plantillas/', plantillas_api_view, name='api-plantillas'),

    # Autenticación con sesiones
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register_view, name='register'),

    # Organizaciones
    path('org/switch/', org_switch_view, name='org-switch'),

    # Secciones de la app
    path('calendario/', calendario_view, name='calendario'),
    path('equipo/', equipo_view, name='equipo'),
    path('perfil/', perfil_view, name='perfil'),
    path('perfil/apariencia/', appearance_update_view, name='perfil-apariencia'),

    # Home
    path('', home_view, name='home'),

    # Tableros
    path('board/create/', board_create_view, name='board-create'),
    path('board/<int:board_id>/', board_detail_view, name='board-detail'),
    path('board/<int:board_id>/edit/', board_update_view, name='board-update'),
    path('board/<int:board_id>/delete/', board_delete_view, name='board-delete'),

    # Columnas
    path('board/<int:board_id>/column/create/', column_create_view, name='column-create'),
    path('board/<int:board_id>/column/<int:column_id>/rename/', column_rename_view, name='column-rename'),
    path('board/<int:board_id>/column/<int:column_id>/delete/', column_delete_view, name='column-delete'),
    path('board/<int:board_id>/column/move/', column_move_view, name='column-move'),

    # Tarjetas
    path('board/<int:board_id>/card/create/', card_create_view, name='card-create'),
    path('board/<int:board_id>/card/<int:card_id>/edit/', card_edit_view, name='card-edit'),
    path('board/<int:board_id>/card/<int:card_id>/delete/', card_delete_view, name='card-delete'),
    path('board/<int:board_id>/card/move/', card_move_view, name='card-move'),

    # Subtareas (checklist) — HTMX
    path('board/<int:board_id>/card/<int:card_id>/subtask/create/', subtask_create_view, name='subtask-create'),
    path('board/<int:board_id>/card/<int:card_id>/subtask/<int:subtask_id>/toggle/', subtask_toggle_view, name='subtask-toggle'),
    path('board/<int:board_id>/card/<int:card_id>/subtask/<int:subtask_id>/delete/', subtask_delete_view, name='subtask-delete'),

    # Comentarios — HTMX
    path('board/<int:board_id>/card/<int:card_id>/comment/create/', comment_create_view, name='comment-create'),
    path('board/<int:board_id>/card/<int:card_id>/comment/<int:comment_id>/delete/', comment_delete_view, name='comment-delete'),
]

# Servir /media/ (subidas, p.ej. avatares) en desarrollo y despliegue local.
# django.views.static.serve funciona aunque DEBUG=False (a diferencia de
# static()); en producción SERVE_MEDIA=False (FS efímero de Railway).
if getattr(settings, 'SERVE_MEDIA', False):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
    ]
