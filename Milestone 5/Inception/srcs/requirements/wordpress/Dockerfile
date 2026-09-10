FROM debian:bookworm-slim

# php8.2 is Debian bookworm's default PHP version.
RUN apt-get update && apt-get install -y --no-install-recommends \
        php8.2-fpm php8.2-cli php8.2-mysqli php8.2-gd php8.2-curl \
        php8.2-xml php8.2-mbstring php8.2-zip php8.2-intl \
        mariadb-client curl ca-certificates less \
    && rm -rf /var/lib/apt/lists/*

# --- wp-cli, to install & configure WordPress without a web install wizard --
RUN curl -sS -o /usr/local/bin/wp \
        https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    && chmod +x /usr/local/bin/wp

# --- WordPress core, baked into the image; Docker will seed the empty ------
# --- named volume with this content on the container's first start.  ------
RUN curl -sS https://wordpress.org/latest.tar.gz -o /tmp/wordpress.tar.gz \
    && mkdir -p /var/www/html \
    && tar -xzf /tmp/wordpress.tar.gz -C /var/www/html --strip-components=1 \
    && rm -f /tmp/wordpress.tar.gz \
    && chown -R www-data:www-data /var/www/html

# --- php-fpm pool: listen on TCP 9000 for nginx, not on a unix socket ------
RUN sed -i "s/^listen = .*/listen = 9000/" /etc/php/8.2/fpm/pool.d/www.conf \
    && sed -i "s/;listen.owner = www-data/listen.owner = www-data/" /etc/php/8.2/fpm/pool.d/www.conf \
    && sed -i "s/;listen.group = www-data/listen.group = www-data/" /etc/php/8.2/fpm/pool.d/www.conf \
    && sed -i "s/^;clear_env = no/clear_env = no/" /etc/php/8.2/fpm/pool.d/www.conf

COPY tools/setup.sh /usr/local/bin/setup.sh
RUN chmod +x /usr/local/bin/setup.sh

WORKDIR /var/www/html
EXPOSE 9000

ENTRYPOINT ["/usr/local/bin/setup.sh"]
