#!/bin/bash
# ============================================================================
# MariaDB entrypoint.
#   1. On first boot (empty data volume): initialise the system tables,
#      create the application database + user, set the root password.
#   2. Always finish by `exec mysqld`, so mysqld itself becomes PID 1 and
#      correctly receives signals from Docker (no infinite-loop wrapper,
#      no `tail -f`, no daemon mode).
# ============================================================================
set -e

DB_PASSWORD=$(cat "${MYSQL_PASSWORD_FILE}")
DB_ROOT_PASSWORD=$(cat "${MYSQL_ROOT_PASSWORD_FILE}")

if [ ! -d "/var/lib/mysql/mysql" ]; then
    echo "[mariadb] First run: initialising data directory..."
    mysql_install_db --user=mysql --datadir=/var/lib/mysql > /dev/null

    # Temporary local-only instance to run the bootstrap SQL against
    mysqld_safe --skip-networking --datadir=/var/lib/mysql &
    tmp_pid="$!"

    for i in $(seq 1 30); do
        mysqladmin --silent ping && break
        sleep 1
    done

    mysql -u root <<-EOSQL
        CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\`;
        CREATE USER IF NOT EXISTS '${MYSQL_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
        GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';
        ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_ROOT_PASSWORD}';
        FLUSH PRIVILEGES;
EOSQL

    mysqladmin -u root -p"${DB_ROOT_PASSWORD}" shutdown
    wait "${tmp_pid}" 2>/dev/null || true
    echo "[mariadb] Initialisation complete."
fi

echo "[mariadb] Starting mysqld as PID 1..."
exec mysqld --user=mysql
