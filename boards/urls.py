# URLs de la app boards (rutas anidadas para columnas, etiquetas y miembros).

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BoardMembershipView, BoardViewSet, ColumnViewSet, LabelViewSet

app_name = 'boards'

router = DefaultRouter()
router.register(r'', BoardViewSet, basename='board')

column_list = ColumnViewSet.as_view({'get': 'list', 'post': 'create'})
column_detail = ColumnViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
    'put': 'update',
    'delete': 'destroy',
})
column_move = ColumnViewSet.as_view({'post': 'move'})
label_list = LabelViewSet.as_view({'get': 'list', 'post': 'create'})
label_detail = LabelViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
    'put': 'update',
    'delete': 'destroy',
})
member_list = BoardMembershipView.as_view({'get': 'list', 'post': 'create'})
member_detail = BoardMembershipView.as_view({'delete': 'destroy'})

urlpatterns = [
    path('<int:board_pk>/columns/', column_list, name='column-list'),
    path('<int:board_pk>/columns/<int:pk>/', column_detail, name='column-detail'),
    path('<int:board_pk>/columns/<int:pk>/move/', column_move, name='column-move'),
    path('<int:board_pk>/labels/', label_list, name='label-list'),
    path('<int:board_pk>/labels/<int:pk>/', label_detail, name='label-detail'),
    path('<int:board_pk>/members/', member_list, name='member-list'),
    path('<int:board_pk>/members/<int:pk>/', member_detail, name='member-detail'),
    path('', include(router.urls)),
]
