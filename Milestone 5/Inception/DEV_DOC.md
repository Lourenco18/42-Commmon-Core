# Developer Documentation

This document explains how to set up, build, and maintain the Inception
stack from a developer's point of view.

## 1. Prerequisites

- A Linux **virtual machine** (the subject requires the whole project to
  run inside a VM), with:
  - Docker Engine and the Docker Compose plugin installed
    (`docker compose version` should work).
  - `make`.
- Root/sudo access on the VM (needed to create `/home/<login>/data`, and
  used by `make fclean` to remove it).

## 2. Setting up the environment from scratch

1. Clone the repository onto the VM.
2. **Login placeholder**: replace `yourlogin` in two places so they match:
   - `Makefile` → `LOGIN := yourlogin`
   - `srcs/.env` → `LOGIN=yourlogin` and `DOMAIN_NAME=yourlogin.42.fr`
     (`LOGIN` is consumed by `docker-compose.yml`'s volume `driver_opts`;
     `DOMAIN_NAME` by nginx and WordPress).
3. **Secrets**: the `secrets/` folder ships with randomly generated
   placeholder passwords so the stack works out of the box, but you should
   replace them with your own before any real use:
   ```bash
   echo "your-strong-password" > secrets/db_password.txt
   echo "your-strong-password" > secrets/db_root_password.txt
   echo "your-strong-password" > secrets/credentials.txt        # WP admin
   echo "your-strong-password" > secrets/wp_user_password.txt   # WP 2nd user
   ```
   `secrets/*.txt` and `srcs/.env` are both git-ignored (see `.gitignore`) —
   never commit real credentials.
4. **Configuration**: adjust `srcs/.env` if you want a different database
   name, WordPress title, or usernames. The WordPress admin username
   (`WP_ADMIN_USER`) must **not** contain `admin`/`Admin`/`administrator`/
   `Administrator` — this is enforced by convention here (default:
   `supervisor_le`), the entrypoint script does not itself validate it, so
   double-check before first boot.
5. **Hosts file**: on the VM, `sudo` add `127.0.0.1  yourlogin.42.fr` to
   `/etc/hosts` so the domain resolves locally.

## 3. Building and launching the project

Everything goes through the root `Makefile`, which wraps
`docker compose -f srcs/docker-compose.yml --env-file srcs/.env`:

```bash
make            # build all three images and start the stack (detached)
make build      # (re)build images without starting containers
make down       # stop & remove containers (volumes/data survive)
make stop       # stop containers without removing them
make start      # restart previously stopped containers
make restart    # down + up
make re         # fclean + up : full wipe and rebuild from zero
make clean      # down + docker system prune (dangling images/build cache)
make fclean     # clean + remove the persisted data under /home/<login>/data
```

`make prepare` (run automatically by `up`/`build`) creates
`/home/<login>/data/db` and `/home/<login>/data/wordpress` on the host — the
directories that back the two named volumes.

### Build order & dependencies

`docker-compose.yml` declares `depends_on` so that:
- `wordpress` starts after `mariadb` (container start order only — the
  WordPress entrypoint still actively polls `mysqladmin ping` before doing
  anything, since `depends_on` does not wait for the DB to be *ready*, only
  for the container process to have *started*).
- `nginx` starts after `wordpress`.

## 4. Managing containers and volumes

Useful raw Compose/Docker commands (run from the project root):

```bash
docker compose -f srcs/docker-compose.yml ps
docker compose -f srcs/docker-compose.yml logs -f <service>
docker compose -f srcs/docker-compose.yml exec wordpress bash
docker compose -f srcs/docker-compose.yml exec mariadb bash

docker volume ls                    # shows db_data / wp_data (prefixed by project name)
docker volume inspect srcs_db_data  # shows Mountpoint == /home/<login>/data/db
docker network ls                   # shows the "inception" bridge network
```

To rebuild a single service after editing its Dockerfile:

```bash
docker compose -f srcs/docker-compose.yml build wordpress
docker compose -f srcs/docker-compose.yml up -d wordpress
```

## 5. Where project data lives and how it persists

- **`db_data`** volume → bind-backed at `/home/<login>/data/db` on the host
  → mounted at `/var/lib/mysql` in the `mariadb` container. Contains all
  MariaDB tables/data files.
- **`wp_data`** volume → bind-backed at `/home/<login>/data/wordpress` on
  the host → mounted at `/var/www/html` in **both** the `wordpress` and
  `nginx` containers (wordpress needs it to run PHP files and write
  uploads/plugins; nginx needs it to serve static assets directly).

Both are declared as Docker **named volumes** using the `local` driver with
`driver_opts: {type: none, o: bind, device: ...}` — this is Docker's
supported way to have a named volume (tracked, inspectable, portable
through Compose) whose backing storage is a specific host path, satisfying
the subject's constraint that data must land in `/home/<login>/data` while
still forbidding a plain bind mount declared directly under a service's
`volumes:` list.

Because both volumes are named (not anonymous) and their host directories
are not wiped by `make down`/`make stop`/`make restart`, data — the
database content and the WordPress installation/files — survives container
restarts and rebuilds. Only `make fclean` (or manually deleting
`/home/<login>/data`) destroys it.

### First-boot vs subsequent boots

Both `mariadb`'s and `wordpress`'s entrypoint scripts detect an
already-initialised volume (`/var/lib/mysql/mysql` directory present, or
`wp-config.php` present, respectively) and skip re-initialisation/reinstall
on every subsequent `docker compose up` — only the very first start (empty
volume) performs the MariaDB `mysql_install_db` + user creation, and the
WordPress `wp core install` + user creation.

## 6. Changing a service's port (defense "configuration modification" test)

Every service's port is a variable in `srcs/.env`, never hard-coded in a
Dockerfile or in `docker-compose.yml`:

| Variable      | Used by                          | Default |
|---------------|-----------------------------------|---------|
| `NGINX_PORT`  | nginx's `listen` + host port mapping | 443 |
| `WP_FPM_PORT` | php-fpm's `listen` + nginx's `fastcgi_pass` | 9000 |
| `DB_PORT`     | mysqld's `--port` + WordPress's `DB_HOST` | 3306 |

To change one live during the defense, edit the value in `srcs/.env`
(e.g. `NGINX_PORT=8443`), then simply:

```bash
make re
```

Everything downstream re-reads the new value automatically: the nginx
config template is re-rendered with `envsubst` on container start, the
php-fpm pool file is patched on container start, `mysqld` is launched with
`--port=$DB_PORT`, and the WordPress `wp-config.php`/site URL are
re-applied on every boot — no manual file editing required beyond `.env`.

## 7. PID 1 / process model notes

Per the subject's constraints, none of the three Dockerfiles use `tail -f`,
`sleep infinity`, `while true`, or a bare shell as a long-running command.
Each entrypoint script performs its one-time setup, then finishes with
`exec` so that the actual server process replaces the shell as PID 1 and
receives Docker's stop/restart signals directly:

- `mariadb` → `exec mysqld --user=mysql`
- `wordpress` → `exec php-fpm8.2 -F` (foreground mode)
- `nginx` → `exec nginx -g "daemon off;"`
