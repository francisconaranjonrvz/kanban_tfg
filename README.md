# Kanban TFG

Gestor de tareas tipo Kanban para el TFG de DAW. Backend con Django + DRF, frontend vanilla (HTML/CSS/JS). Autenticación con JWT, tableros compartidos con roles y drag & drop para mover tarjetas entre columnas.

## Stack

- **Backend:** Django 4.2 + Django REST Framework + simplejwt
- **Frontend:** HTML5, CSS3 y JS vanilla (sin frameworks)
- **BD:** SQLite en desarrollo, PostgreSQL en producción
- **Despliegue:** Docker + nginx + Let's Encrypt

## Instalación (desarrollo)

```bash
git clone <repo>
cd kanban_tfg

python -m venv .venv
.venv\Scripts\activate        # en Windows
# source .venv/bin/activate   # en Linux/Mac

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abre `http://127.0.0.1:8000/` y listo.

Si quieres datos de prueba:

```bash
python manage.py seed_demo
# Crea el usuario demo / demo12345 con dos tableros
```

## API

La API está en `/api/v1/`. Todos los endpoints necesitan JWT menos el login y el registro. Por ejemplo:

- `POST /api/v1/auth/token/` → login
- `GET /api/v1/boards/` → tus tableros
- `POST /api/v1/tasks/{id}/move/` → mover tarjeta de columna

## Tests

```bash
python manage.py test
```

Hay 12 tests que cubren CRUD, permisos, reorden de columnas, movimiento de tarjetas y aislamiento entre usuarios.

## Despliegue (producción con Docker)

```bash
cp .env.example .env
# Rellena DOMAIN, DJANGO_SECRET_KEY, POSTGRES_PASSWORD y LETSENCRYPT_EMAIL

docker compose up -d --build
```

Para HTTPS con Let's Encrypt:

```bash
export $(grep -v '^#' .env | xargs)
bash scripts/init-letsencrypt.sh
# Luego descomenta el bloque 443 en nginx/nginx.conf
docker compose restart nginx
```

Renovación automática (crontab):

```
0 3 * * * cd /ruta/al/proyecto && docker compose run --rm certbot renew && docker compose exec nginx nginx -s reload
```

## Licencia

MIT — ver `LICENSE`.
