# User Documentation

This document explains how to use the Inception stack once it has been set
up on the virtual machine — no development knowledge required.

## 1. What services are provided

| Service     | Role                                                            |
|-------------|------------------------------------------------------------------|
| `nginx`     | The website's public entrypoint (HTTPS, port 443)                |
| `wordpress` | The blog/CMS engine (WordPress) that generates the pages          |
| `mariadb`   | The database storing all articles, users, settings, etc.          |

You never talk to `wordpress` or `mariadb` directly — everything goes
through `nginx` on port 443.

## 2. Starting and stopping the project

From the project's root directory (the one containing the `Makefile`):

| Action                              | Command        |
|--------------------------------------|----------------|
| Build the images and start everything| `make` or `make up` |
| Stop the containers (keep data)      | `make stop`    |
| Start previously-stopped containers  | `make start`   |
| Stop and remove the containers       | `make down`    |
| Restart everything                   | `make restart` |
| Wipe data and rebuild from scratch   | `make re`      |

Containers are configured to restart automatically if they crash
(`restart: on-failure`), so you generally don't need to babysit them.

## 3. Accessing the website and the admin panel

1. Make sure your domain resolves to the VM. On the VM itself (or the
   client machine), add to `/etc/hosts`:
   ```
   127.0.0.1   yourlogin.42.fr
   ```
   (replace `yourlogin` with the value configured in `srcs/.env`).
2. Open **`https://yourlogin.42.fr`** in a browser.
   - The TLS certificate is self-signed (generated locally by the nginx
     container), so your browser will show a security warning the first
     time — click "Advanced" → "Proceed" to continue. This is expected and
     does not indicate a real problem.
3. The **admin dashboard** is reachable at
   `https://yourlogin.42.fr/wp-admin`.

## 4. Locating and managing credentials

All passwords live as plain files under the project's `secrets/` folder
(never inside a Dockerfile, never in git):

| File                          | What it's for                          |
|--------------------------------|-----------------------------------------|
| `secrets/credentials.txt`      | WordPress **administrator** password    |
| `secrets/wp_user_password.txt` | WordPress second (author) user's password |
| `secrets/db_password.txt`      | MariaDB application user's password     |
| `secrets/db_root_password.txt` | MariaDB root password                   |

Usernames themselves are set as plain (non-secret) variables in
`srcs/.env`: `WP_ADMIN_USER`, `WP_USER`, `MYSQL_USER`.

To change a password: edit the relevant file in `secrets/`, then run
`make down && make up` so the containers pick it up. Note that on an
**already-installed** WordPress site, changing `credentials.txt` will not
retroactively change the password stored in the database — use the
`wp-admin` "Users" screen (or `wp user update` inside the wordpress
container) for that instead.

## 5. Checking that services are running correctly

```bash
make ps
```

Expect to see `nginx`, `wordpress`, and `mariadb` all listed as `Up` /
`running`. To watch live logs from every service:

```bash
make logs
```

Or for a single service:

```bash
docker compose -f srcs/docker-compose.yml logs -f nginx
docker compose -f srcs/docker-compose.yml logs -f wordpress
docker compose -f srcs/docker-compose.yml logs -f mariadb
```

If the website doesn't load, check in order: (1) `make ps` shows all three
containers `Up`, (2) `/etc/hosts` points your domain at the VM's IP,
(3) `wordpress` logs show `"MariaDB is up."` and no install errors,
(4) `nginx` logs show it started without a certificate/config error.
