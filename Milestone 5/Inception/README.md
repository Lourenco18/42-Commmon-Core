*This project has been created as part of the 42 curriculum by yourlogin.*

# Inception

## Description

Inception is a system administration project whose goal is to build a small,
production-style web infrastructure entirely out of Docker containers,
orchestrated with **Docker Compose**, each service built from a
**Dockerfile written from scratch** (no ready-made images from Docker Hub,
besides the Alpine/Debian base image itself).

The stack reproduces a classic three-tier web architecture:

- **NGINX** — the single entrypoint of the infrastructure, terminating
  TLS (TLSv1.2/TLSv1.3 only) on port 443 and forwarding PHP requests to
  WordPress over FastCGI.
- **WordPress + php-fpm** — the application layer, installed and configured
  automatically at container start (no manual setup wizard).
- **MariaDB** — the persistence layer, storing WordPress's data.

Two Docker **named volumes** persist state across restarts (the database
files and the WordPress website files), a dedicated **Docker network**
connects the three containers, and all credentials are injected through
**Docker secrets** — never hard-coded, never committed to git.

```
                                   WWW
                                    │
                                   443 (TLS 1.2/1.3)
                                    │
                              ┌───────────┐
                              │   nginx   │
                              └─────┬─────┘
                                 9000 (fastcgi)
                              ┌─────┴─────┐
                              │ wordpress │
                              │ (php-fpm) │
                              └─────┬─────┘
                                 3306
                              ┌─────┴─────┐
                              │  mariadb  │
                              └───────────┘
              (all three containers share the `inception` network)
```

## Project structure

```
.
├── Makefile
├── secrets/                     # never committed — see .gitignore
│   ├── credentials.txt          # WordPress admin password
│   ├── db_password.txt          # MariaDB app-user password
│   ├── db_root_password.txt     # MariaDB root password
│   └── wp_user_password.txt     # WordPress second user's password
└── srcs/
    ├── .env                     # non-secret configuration (domain, usernames…)
    ├── docker-compose.yml
    └── requirements/
        ├── mariadb/
        │   ├── Dockerfile
        │   ├── conf/my.cnf
        │   └── tools/setup.sh
        ├── nginx/
        │   ├── Dockerfile
        │   ├── conf/nginx.conf.template
        │   └── tools/entrypoint.sh
        └── wordpress/
            ├── Dockerfile
            └── tools/setup.sh
```

## Instructions

See **DEV_DOC.md** for full build/run instructions and **USER_DOC.md** for
day-to-day usage. Quick start:

```bash
# 1. Edit LOGIN in the Makefile and srcs/.env to match your 42 login
# 2. Replace the placeholder files in secrets/ with real passwords
# 3. Add "127.0.0.1  yourlogin.42.fr" to /etc/hosts on the VM
make
```

Then browse to `https://yourlogin.42.fr` (the self-signed certificate will
trigger a browser warning — that's expected, accept it to continue).

## Design choices

**Virtual Machines vs Docker** — A VM virtualizes an entire machine,
including its own kernel, which is heavy on CPU/RAM/disk and slow to boot.
A Docker container shares the host kernel and only isolates the process,
filesystem and network namespace, so it starts in milliseconds and uses a
fraction of the resources. For running three cooperating, disposable
services (web server, app, database) whose whole point is to be rebuilt and
redeployed often, Docker's speed and reproducibility (images are built once
from a Dockerfile and behave identically everywhere) make far more sense
than provisioning a separate VM per service. The project still runs inside
one VM to isolate it from the host, but each *service* is a container, not
a VM.

**Secrets vs Environment Variables** — Plain environment variables set in a
Compose file or `.env` are visible to anyone who can run `docker inspect` or
read process environment on the host, and they tend to leak into logs, crash
dumps, or `docker-compose.yml` itself if someone is not careful — a serious
problem for passwords. Docker **secrets** are mounted as read-only files
under `/run/secrets/` inside the container only at runtime, are never baked
into an image layer, and never show up in `docker inspect`. This project
uses `.env` only for non-sensitive configuration (domain name, database
name, usernames) and file-based secrets for every password, referenced from
the containers through `*_FILE` environment variables that are read once at
startup.

**Docker Network vs Host Network** — `network: host` makes a container share
the host's network namespace directly: no isolation, port collisions are
easy, and any container can talk to any host port. A user-defined **bridge
network** (as used here) gives the containers their own private subnet, DNS
based on service name (`wordpress`, `mariadb`), and only the ports we
explicitly publish (443 on nginx) are reachable from outside — MariaDB and
php-fpm are never exposed to the outside world, only to sibling containers
on the `inception` network. This is both more secure and closer to how a
real production deployment would be isolated.

**Docker Volumes vs Bind Mounts** — A bind mount ties a container path
directly to an arbitrary host path chosen by whoever runs `docker run`,
outside of Docker's management (no `docker volume ls`, no built-in backup
tooling, permission/ownership handling is entirely manual, and the path is
implicit rather than declared). A **named volume** is created and tracked by
the Docker engine, portable across `docker-compose` invocations, and safer
by default. This project uses named volumes for both the database and the
WordPress files, configured with the `local` driver's `bind` option so that
their actual storage still lands in `/home/<login>/data` as required by the
subject — they remain genuine Docker-managed volumes (visible to
`docker volume inspect`), not manual bind mounts declared in the `volumes:`
section of a service.

## Resources

- [Docker documentation](https://docs.docker.com/)
- [Docker Compose file reference](https://docs.docker.com/compose/compose-file/)
- [Docker secrets](https://docs.docker.com/engine/swarm/secrets/)
- [NGINX documentation](https://nginx.org/en/docs/)
- [WP-CLI documentation](https://wp-cli.org/)
- [MariaDB documentation](https://mariadb.com/kb/en/documentation/)
- [42 Inception subject (this repository's `en_subject.pdf`)]

### AI usage disclosure

An AI assistant (Claude, Anthropic) was used to draft the initial project
scaffolding based directly on the subject PDF: the Dockerfiles, entrypoint
scripts, `docker-compose.yml`, `Makefile`, and this documentation set. It
was used to accelerate boilerplate (apt package lists, `wp-cli`/WordPress
install commands, TLS certificate generation, Compose secret wiring) rather
than to design the architecture, which follows the mandatory structure
given in the subject. As instructed by the subject's own AI guidelines,
every generated file should still be read, tested end-to-end on a real VM,
and understood in full — in particular the PID 1 / entrypoint behaviour of
each container, the secrets flow, and the volume `driver_opts` bind trick —
before being submitted, since the evaluator can ask about any part of it.
