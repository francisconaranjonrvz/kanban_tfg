#!/bin/sh
# Genera el primer certificado Let's Encrypt para $DOMAIN usando el reto HTTP-01.
#
# Pre-requisitos:
#   - El puerto 80 del router redirige al host donde corre docker.
#   - $DOMAIN ya apunta a la IP pública (DNS propagado).
#   - El stack está arriba con `docker compose up -d` y nginx sirve HTTP.
#
# Después de ejecutarlo:
#   1) Edita nginx/nginx.conf y reemplaza DOMAIN_PLACEHOLDER por $DOMAIN.
#   2) Reinicia nginx: docker compose restart nginx
#
# Renovación: añade a crontab del host (sustituyendo /ruta/proyecto):
#   0 3 * * * cd /ruta/proyecto && docker compose run --rm certbot renew \
#     && docker compose exec nginx nginx -s reload

set -e

if [ -z "$DOMAIN" ] || [ -z "$LETSENCRYPT_EMAIL" ]; then
    echo "Falta DOMAIN o LETSENCRYPT_EMAIL en el entorno (carga .env primero)."
    exit 1
fi

mkdir -p ./certbot/www ./certbot/conf

docker compose run --rm certbot certonly \
    --webroot \
    -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$LETSENCRYPT_EMAIL" \
    --agree-tos \
    --no-eff-email

echo
echo "Certificado obtenido. Edita nginx/nginx.conf:"
echo "  sed -i 's/DOMAIN_PLACEHOLDER/$DOMAIN/g' nginx/nginx.conf"
echo "Y reinicia nginx:"
echo "  docker compose restart nginx"
