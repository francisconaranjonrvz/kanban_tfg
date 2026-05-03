# Vistas de autenticación y perfil.

from django.contrib.auth import login
from django.shortcuts import redirect, render
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import RegisterForm
from .serializers import RegisterSerializer, UserSerializer


# --- Vistas DRF (API REST) ---

class RegisterView(generics.CreateAPIView):
    """Registro de nuevo usuario (API)."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    """Devuelve el perfil del usuario autenticado (API)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# --- Vista de registro con formulario Django ---

def register_view(request):
    """Registro clásico con formulario y sesión."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})
