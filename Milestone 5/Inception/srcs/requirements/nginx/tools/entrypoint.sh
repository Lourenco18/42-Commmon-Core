#!/bin/bash
# ============================================================================
# NGINX entrypoint.
#   1. Render the real nginx.conf from the template (substitute DOMAIN_NAME
#      only — every other "$..." nginx variable is left untouched thanks to
#      envsubst's explicit variable list).
#   2. Generate a self-signed TLS certificate for DOMAIN_NAME if missing.
#   3. exec nginx in the foreground, so it becomes PID 1.
# ============================================================================
set -e

envsubst '${DOMAIN_NAME} ${NGINX_PORT} ${WP_FPM_PORT}' \
    < /etc/nginx/conf.d/nginx.conf.template \
    > /etc/nginx/nginx.conf

mkdir -p /etc/nginx/ssl

if [ ! -f "/etc/nginx/ssl/${DOMAIN_NAME}.crt" ]; then
    echo "[nginx] Generating self-signed TLS certificate for ${DOMAIN_NAME}..."
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout "/etc/nginx/ssl/${DOMAIN_NAME}.key" \
        -out    "/etc/nginx/ssl/${DOMAIN_NAME}.crt" \
        -subj "/C=PT/ST=Porto/L=Porto/O=42/OU=Inception/CN=${DOMAIN_NAME}"
fi

echo "[nginx] Starting nginx as PID 1..."
exec nginx -g "daemon off;"
