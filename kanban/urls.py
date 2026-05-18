# URLs principales del proyecto.

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from boards.views import (
    board_create_view,
    board_delete_view,
    board_detail_view,
    board_update_view,
    column_create_view,
    column_delete_view,
    column_move_view,
    column_rename_view,
    home_view,
)
from tasks.views import (
    card_create_view,
    card_delete_view,
    card_edit_view,
    card_move_view,
    plantillas_api_view,
)
from users.views import register_view

from .health import liveness, readiness

urlpatterns = [
    path('admin/', admin.site.urls),

    # Healthchecks para Docker
    path('healthz', liveness, name='healthz'),
    path('readyz', readiness, name='readyz'),

    # API interna (plantillas de tareas)
    path('api/plantillas/', plantillas_api_view, name='api-plantillas'),

    # API v1 (se mantiene para uso futuro / app móvil)
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/boards/', include('boards.urls')),
    path('api/v1/tasks/', include('tasks.urls')),

    # Autenticación con sesiones
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register_view, name='register'),

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
]
