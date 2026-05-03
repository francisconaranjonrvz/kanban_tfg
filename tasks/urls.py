# URLs de la app tasks.

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CardViewSet

app_name = 'tasks'

router = DefaultRouter()
router.register(r'', CardViewSet, basename='card')

urlpatterns = [
    path('', include(router.urls)),
]
