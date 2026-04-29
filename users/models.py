# Modelo de usuario personalizado.

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario con campos extra para el perfil."""

    bio = models.TextField(blank=True)
    avatar = models.URLField(blank=True)

    class Meta:
        ordering = ['username']
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.username

    def get_full_name_or_username(self):
        """Devuelve el nombre completo o el username si no tiene."""
        full = super().get_full_name()
        return full if full.strip() else self.username
