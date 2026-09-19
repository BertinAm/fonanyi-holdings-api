# Backend deployment — Namecheap shared hosting

The Django API runs under cPanel's **Setup Python App**, which uses Phusion
Passenger. Code arrives through **Git Version Control**; you pull and restart
by hand, which is deliberate — nothing deploys itself.

Two things are worth knowing before you start:

* Passenger recycles worker processes when the app is idle. Anything that must
  survive a restart lives in MySQL, never in memory. There is no Celery, no
  Redis and no long-running worker.
* `mysqlclient` needs MySQL C headers that shared hosting does not have. The
  app uses **PyMySQL** instead (`requirements-shared-hosting.txt`), and
  `passenger_wsgi.py` registers it as `MySQLdb` before Django loads.

---

## 1. Create the MySQL database

cPanel → **MySQL Databases**

1. Create a database, e.g. `fonanyi`. cPanel prefixes it with your account
   name, so the real name is something like `cpuser_fonanyi`.
2. Create a user, e.g. `cpuser_fonanyi`, with a strong password.
3. Add the user to the database with **ALL PRIVILEGES**.

Write down the full prefixed names — you need them in `.env`.

## 2. Create the Python application

cPanel → **Setup Python App** → **Create Application**

| Field | Value |
| --- | --- |
| Python version | 3.11 or 3.12 (highest available) |
| Application root | `fonanyi-api` |
| Application URL | `api.fonanyiholdings.com` (a subdomain, not a subfolder) |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

Click **Create**. cPanel makes a virtualenv at
`~/virtualenv/fonanyi-api/3.11/` and shows you the command to activate it.
Copy that command — you will use it in the terminal.

> Use a **subdomain** for the API. A subfolder under `public_html` fights with
> the static frontend over routing and cookie paths.

## 3. Set up Git Version Control

cPanel → **Git™ Version Control** → **Create**

| Field | Value |
| --- | --- |
| Clone a Repository | on |
| Clone URL | your repository's SSH or HTTPS URL |
| Repository Path | `/home/<cpuser>/repositories/fonanyi-holdings` |
| Repository Name | `fonanyi-holdings` |

For a private repo over SSH, add cPanel's key (**Terminal** →
`cat ~/.ssh/id_rsa.pub`, or SSH Access → Manage SSH Keys) as a deploy key on
GitHub first.

`.cpanel.yml` at the repository root tells cPanel what to do on deploy: it
rsyncs `backend/` into `~/fonanyi-api` (leaving `.env`, `media/`, `logs/` and
`backups/` untouched) and then runs `deploy/deploy.sh`.

## 4. Configure the environment

SSH in (cPanel → **Terminal**) and create the environment file. It lives
outside Git on purpose, so a deploy never overwrites it.

```bash
cd ~/fonanyi-api
cp .env.example .env
nano .env
```

Fill in at least:

```
DJANGO_SECRET_KEY=<50+ random characters>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.fonanyiholdings.com
DB_ENGINE=mysql
DB_NAME=cpuser_fonanyi
DB_USER=cpuser_fonanyi
DB_PASSWORD=<the password from step 1>
DB_HOST=localhost
SITE_URL=https://api.fonanyiholdings.com
FRONTEND_URL=https://fonanyiholdings.com
CORS_ALLOWED_ORIGINS=https://fonanyiholdings.com,https://www.fonanyiholdings.com
CSRF_TRUSTED_ORIGINS=https://fonanyiholdings.com,https://www.fonanyiholdings.com
DJANGO_MEDIA_ROOT=/home/<cpuser>/fonanyi-api/media
CLOUDFLARE_DEPLOY_HOOK=<from the Cloudflare docs, step 5 there>
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

## 5. First deploy

In cPanel → Git Version Control, click **Manage** on the repository, then
**Deploy HEAD Commit**. Or from the terminal:

```bash
cd ~/repositories/fonanyi-holdings && git pull && /usr/local/cpanel/bin/cpanel_yaml_deploy
```

Then create the first staff account:

```bash
cd ~/fonanyi-api
source ~/virtualenv/fonanyi-api/3.11/bin/activate
python manage.py createsuperuser
```

Optionally load the starter content (site settings, testimonials, a first
article, and the gallery photos bundled with the repo):

```bash
python manage.py seed_content --photos seed_media/photos
```

## 6. Serving media files

Uploaded photos are written to `~/fonanyi-api/media/`. Passenger will serve
them, but Apache does it faster. Point the subdomain's document root at a
directory containing a symlink:

```bash
ln -s ~/fonanyi-api/media ~/public_html/api/media
ln -s ~/fonanyi-api/staticfiles ~/public_html/api/static
```

If symlinks are disabled on your plan, leave it — WhiteNoise and Passenger
handle both, just with a little more CPU per request.

## 7. The routine after that

Every change follows the same three steps:

```bash
# 1. In cPanel → Git Version Control → Manage → "Update from Remote"
# 2. Click "Deploy HEAD Commit"   (this runs .cpanel.yml → deploy/deploy.sh)
# 3. Confirm it came back up:
curl -si https://api.fonanyiholdings.com/api/site-settings/ | head -1
```

`deploy/deploy.sh` installs dependencies, migrates, collects static files and
restarts Passenger. To restart on its own, without a deploy:

```bash
bash ~/fonanyi-api/deploy/restart_app.sh
```

---

## Troubleshooting

**500 error after a deploy.** Read the Passenger log:
`tail -50 ~/fonanyi-api/stderr.log`, or check cPanel → Errors. The usual cause
is a missing `.env` value or a migration that did not run.

**`ModuleNotFoundError: MySQLdb`.** PyMySQL is not installed in the
virtualenv. Activate it and run
`pip install -r requirements-shared-hosting.txt`.

**`DisallowedHost`.** Add the domain to `DJANGO_ALLOWED_HOSTS` and restart.

**CORS errors in the browser.** `CORS_ALLOWED_ORIGINS` must list the exact
frontend origin, with scheme and no trailing slash.

**The app does not pick up new code.** Passenger caches aggressively. Run
`touch ~/fonanyi-api/tmp/restart.txt`, or use the Restart button in Setup
Python App.

**Changes vanish after a deploy.** Anything inside `backend/` in Git is
replaced on deploy. `.env`, `media/`, `logs/`, `tmp/` and `backups/` are
excluded in `.cpanel.yml` — keep it that way.
