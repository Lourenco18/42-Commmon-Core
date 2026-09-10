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

echo "[wordpress] Waiting for MariaDB at ${MYSQL_HOST}..."
until mysqladmin ping -h"${MYSQL_HOST}" -u"${MYSQL_USER}" -p"${DB_PASSWORD}" --silent 2>/dev/null; do
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
        --dbhost="${MYSQL_HOST}" \
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

chown -R www-data:www-data /var/www/html

echo "[wordpress] Starting php-fpm as PID 1..."
exec php-fpm8.2 -F
