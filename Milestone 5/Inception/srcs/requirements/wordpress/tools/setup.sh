#!/bin/bash
# ============================================================================
# WordPress / php-fpm entrypoint.
#   1. Wait for MariaDB to accept connections.
#   2. On first boot (no wp-config.php in the volume yet): write the config,
#      run the WordPress install, create the admin account (name enforced to
#      never contain admin/administrator) and a second, regular user.
#   3. exec php-fpm in the foreground (-F), so it becomes PID 1.
# ============================================================================
set -e

DB_PASSWORD=$(cat "${MYSQL_PASSWORD_FILE}")
WP_ADMIN_PASSWORD=$(cat "${WP_ADMIN_PASSWORD_FILE}")
WP_USER_PASSWORD=$(cat "${WP_USER_PASSWORD_FILE}")

# php-fpm pool: apply the configurable listen port (defense may ask to
# change it live) before starting.
sed -i "s/^listen = .*/listen = ${WP_FPM_PORT}/" /etc/php/8.2/fpm/pool.d/www.conf

echo "[wordpress] Waiting for MariaDB at ${MYSQL_HOST}:${MYSQL_PORT}..."
until mysqladmin ping -h"${MYSQL_HOST}" -P"${MYSQL_PORT}" -u"${MYSQL_USER}" -p"${DB_PASSWORD}" --silent 2>/dev/null; do
    sleep 2
done
echo "[wordpress] MariaDB is up."

cd /var/www/html

if [ ! -f wp-config.php ]; then
    echo "[wordpress] First run: installing WordPress..."

    wp config create \
        --dbname="${MYSQL_DATABASE}" \
        --dbuser="${MYSQL_USER}" \
        --dbpass="${DB_PASSWORD}" \
        --dbhost="${MYSQL_HOST}:${MYSQL_PORT}" \
        --path="/var/www/html" \
        --allow-root

    wp core install \
        --url="https://${DOMAIN_NAME}" \
        --title="${WP_TITLE}" \
        --admin_user="${WP_ADMIN_USER}" \
        --admin_password="${WP_ADMIN_PASSWORD}" \
        --admin_email="${WP_ADMIN_EMAIL}" \
        --path="/var/www/html" \
        --skip-email \
        --allow-root

    wp user create "${WP_USER}" "${WP_USER_EMAIL}" \
        --role=author \
        --user_pass="${WP_USER_PASSWORD}" \
        --path="/var/www/html" \
        --allow-root

    echo "[wordpress] Installation complete."
else
    echo "[wordpress] Existing installation found, skipping install."
fi

# Always re-apply DB host/port and site URL, in case a defense-time
# configuration change (e.g. DB_PORT or NGINX_PORT) happened after the
# initial install above.
if [ "${NGINX_PORT}" = "443" ]; then
    SITE_URL="https://${DOMAIN_NAME}"
else
    SITE_URL="https://${DOMAIN_NAME}:${NGINX_PORT}"
fi

wp config set DB_HOST "${MYSQL_HOST}:${MYSQL_PORT}" --path="/var/www/html" --allow-root
wp option update siteurl "${SITE_URL}" --path="/var/www/html" --allow-root
wp option update home "${SITE_URL}" --path="/var/www/html" --allow-root

chown -R www-data:www-data /var/www/html

echo "[wordpress] Starting php-fpm as PID 1..."
exec php-fpm8.2 -F
