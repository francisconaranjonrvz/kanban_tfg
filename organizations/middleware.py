# Middleware que resuelve la organización activa de cada petición.

from .models import OrganizationMembership

SESSION_KEY = 'active_org_id'


class OrganizationMiddleware:
    """Fija ``request.organization`` y ``request.user_organizations``.

    Debe ir DESPUÉS de AuthenticationMiddleware. Hace UNA sola consulta de
    membresías (con el tema precargado) que reutiliza el context processor,
    evitando consultas duplicadas por petición. Para usuarios anónimos o sin
    membresías deja ``request.organization = None``.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._attach(request)
        return self.get_response(request)

    def _attach(self, request):
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            request.organization = None
            request.user_organizations = []
            return

        memberships = list(
            OrganizationMembership.objects
            .filter(user=user)
            .select_related('organization', 'organization__theme')
        )
        orgs = [m.organization for m in memberships]
        request.user_organizations = orgs

        if not orgs:
            request.organization = None
            return

        orgs_by_id = {org.id: org for org in orgs}
        active_id = request.session.get(SESSION_KEY)
        if active_id in orgs_by_id:
            request.organization = orgs_by_id[active_id]
            return

        # Por defecto: la organización personal, o la primera por nombre.
        default = sorted(orgs, key=lambda o: (not o.is_personal, o.name.lower()))[0]
        request.session[SESSION_KEY] = default.id
        request.organization = default
