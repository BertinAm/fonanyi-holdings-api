# Fonanyi Holdings — API

Django REST API behind the [Fonanyi Holdings Ltd](https://fonanyiholdings.com)
website: site settings, gallery, articles, testimonials, enquiries and job
applications, plus the data layer for the staff dashboard.

Runs on shared hosting under Passenger. The public site is a separate
statically-exported Next.js app that reads this API at build time.

> **This repository is public.** It contains no credentials, no database and
> no customer data. Every secret is supplied through environment variables at
> deploy time — see [Configuration](#configuration).

## Stack

| | |
| --- | --- |
| Django | 5.2 |
| Django REST Framework | 3.16, with SimpleJWT for staff auth |
| Database | MySQL in production, SQLite for local work |
| Images | Pillow, compressed and thumbnailed on upload |
| Python | 3.10-3.13 supported by Django 5.2; developed on 3.14 |

## Apps

| App | Responsibility |
| --- | --- |
| `siteinfo` | Site settings singleton, testimonials, the rebuild flag |
| `gallery` | Photographs, categorised and published per division |
| `blog` | Articles, drafts and scheduled posts |
| `contact` | Enquiries from the public contact form |
| `careers` | Job applications |
| `analytics` | Page-visit events and the dashboard summary |
| `accounts` | Staff sign-in |
| `common` | Shared helpers: image handling, sanitising, idempotency, cron commands |

## Quick start

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env          # set DB_ENGINE=sqlite for local work
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py createsuperuser
./.venv/bin/python manage.py seed_content        # optional demo content
./.venv/bin/python manage.py runserver
```

The API is then on `http://127.0.0.1:8000/api/`.

`seed_content` only fills an empty installation: it will not overwrite
testimonials or settings that already exist, so it is safe to re-run.

## Tests

```bash
./.venv/bin/python -m pytest
```

63 tests covering permissions, submission handling, image processing,
sanitising, login idempotency and the model layer.

## Configuration

Every setting is read from the environment. `.env.example` lists all of them
with placeholder values; copy it to `.env` and fill it in. `.env` is ignored
by git and must never be committed.

These have no default and the app will not start in production without them:

| Variable | Notes |
| --- | --- |
| `DJANGO_SECRET_KEY` | Generate a fresh one per environment (see below) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | From the hosting control panel |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames |
| `CORS_ALLOWED_ORIGINS` | The front end's origin |

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

The settings module refuses to boot with `DEBUG=False` and no secret key,
rather than falling back to the development placeholder. That placeholder is
a literal in this repository, and Django signs session cookies and
password-reset tokens with the key.

## Scheduled tasks

Run from cron on the host; `cron-jobs.md` in the deployment docs has the
schedule and the wrapper scripts.

| Command | Purpose |
| --- | --- |
| `publish_scheduled` | Publishes articles whose scheduled time has passed |
| `rebuild_if_dirty` | Triggers a front-end rebuild when published content changed |
| `rebuild_site` | Forces a rebuild |
| `daily_digest` | Emails a summary of new enquiries |
| `db_backup` | Dumps the database to the backups directory |
| `prune_analytics` | Drops visit events past the retention window |

Because the front end is statically exported, a content change is only visible
once a rebuild runs. `rebuild_if_dirty` is what connects the two.

## Security

- Staff endpoints require a JWT from `POST /api/auth/login/` and reject
  non-staff accounts.
- Querysets are filtered by permission, so drafts and unpublished records are
  never served to anonymous callers.
- Both public forms are rate limited and carry a honeypot field.
- Submitted text is normalised and stripped of control characters, zero-width
  characters and bidi overrides before storage, and single-line fields cannot
  carry a line break.
- `X-Forwarded-For` is only trusted when `TRUST_PROXY_HEADER` is set.
- The login endpoint accepts an `Idempotency-Key` header so a retried sign-in
  replays the first response instead of issuing a second token pair. Replay is
  bound to the exact credentials that produced it.

Uploaded media and the database live outside this repository.

## Deployment

`deployment-namecheap.md` in the deployment docs covers the full sequence.
In outline: push, pull on the host through the control panel's
git integration, install requirements, migrate, collect static files, run
`createcachetable`, then restart the Python application.

`requirements-shared-hosting.txt` pins the versions that build on the host,
where some wheels are unavailable.

## Reporting a problem

Open an issue. Please do not include customer data, request logs or
environment values in the report.
