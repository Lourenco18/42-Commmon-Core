# Penultimate stable Debian release, pinned (never "latest")
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        mariadb-server \
        mariadb-client \
    && rm -rf /var/lib/apt/lists/*

# Custom server configuration (bind address, data dir, ...)
COPY conf/my.cnf /etc/mysql/mariadb.conf.d/50-server.cnf

# Entrypoint that initialises the DB on first boot then execs mysqld (PID 1)
COPY tools/setup.sh /usr/local/bin/setup.sh
RUN chmod +x /usr/local/bin/setup.sh \
    && mkdir -p /var/run/mysqld \
    && chown -R mysql:mysql /var/run/mysqld /var/lib/mysql

EXPOSE 3306

ENTRYPOINT ["/usr/local/bin/setup.sh"]
