# Modelo de usuario personalizado.

from django.contrib.auth.models import AbstractUser
from django.db import models

from .validators import validate_avatar_extension, validate_avatar_size


class User(AbstractUser):
    """Usuario con campos extra para el perfil."""

    class ThemeBrand(models.TextChoices):
        FLOWLY = 'flowly', 'Flowly'
        NSW = 'nsw', 'NoSoloWebs'

    class ThemeMode(models.TextChoices):
        LIGHT = 'light', 'Claro'
        DARK = 'dark', 'Oscuro'

    bio = models.TextField(blank=True)
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        validators=[validate_avatar_extension, validate_avatar_size],
        help_text='Imagen de perfil (PNG, JPG o WEBP, máx. 2 MB).',
    )
    # Preferencias de aspecto (vacío = heredar de la organización / automático).
    theme_brand = models.CharField(
        max_length=20, choices=ThemeBrand.choices, blank=True, default='',
        help_text='Tema visual preferido. Vacío = heredar de la organización.',
    )
    theme_mode = models.CharField(
        max_length=10, choices=ThemeMode.choices, blank=True, default='',
        help_text='Claro u oscuro. Vacío = automático (según sistema/organización).',
    )

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
