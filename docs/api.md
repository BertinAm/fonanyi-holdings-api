# API reference

Base URL: `https://api.fonanyiholdingsltd.com/api`

Authentication is JWT (`Authorization: Bearer <access>`). Public reads need no
token. Anything that changes data needs a **staff** account.

## Auth

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/auth/login/` | `{username, password}` → `{access, refresh, user}`. Rejects non-staff accounts. Throttled to 10/hour. |
| POST | `/auth/refresh/` | `{refresh}` → `{access, refresh}` |
| GET | `/auth/me/` | The signed-in staff user |

Access tokens last 60 minutes, refresh tokens 7 days and rotate on use.

## Public content

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/site-settings/` | Contact details and homepage counters |
| GET | `/gallery/` | `?category=events\|energy\|logistics\|fashion`, `?page_size=` up to 200 |
| GET | `/testimonials/` | Featured entries only, unless staff |
| GET | `/posts/` | Published posts only, unless staff. `?division=` |
| GET | `/posts/<slug>/` | One post, including `body` |

Unauthenticated callers never see unpublished gallery images or draft posts —
the queryset is filtered, not just the serializer.

## Public writes

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/contact/` | Contact form. Throttled to 8/hour per IP. |
| POST | `/track/` | Analytics beacon. Throttled to 240/hour. Returns 204. |

`/contact/` carries a honeypot field, `company_website`. It must be empty; a
filled one is rejected. The response never reveals which check failed.

`/track/` stores no cookie and no raw IP. The visitor is identified by
`sha256(ip + user-agent + date + salt)`, which counts unique visitors per day
and is useless for anything else.

## Staff only

| Method | Path | Notes |
| --- | --- | --- |
| PATCH | `/site-settings/` | Update settings |
| POST / PATCH / DELETE | `/gallery/`, `/gallery/<id>/` | `multipart/form-data` for uploads |
| POST / PATCH / DELETE | `/testimonials/`, `/testimonials/<id>/` | |
| POST / PATCH / DELETE | `/posts/`, `/posts/<slug>/` | Looked up by slug |
| GET / PATCH / DELETE | `/admin/messages/`, `/admin/messages/<id>/` | Enquiries |
| GET | `/admin/visits/` | Raw visit events |
| GET | `/admin/summary/` | Everything the dashboard header needs, in one request |

## Pagination

List endpoints return `{count, next, previous, results}`. Default page size 24,
`?page_size=` up to 200.

## Conventions

* Image fields are write-only. Reads return an absolute `image_url` /
  `cover_image_url` / `avatar_url`, because the frontend lives on a different
  origin and relative paths would break.
* `POST /posts/` derives `slug` from the title, uniquifying on collision, and
  computes `read_minutes` from the body.
* Setting `is_published` on a post with no `published_at` stamps it with the
  current time.
* Any write to gallery, testimonials, posts or settings sets the rebuild flag
  the `rebuild_if_dirty` cron job watches.

## Errors

Standard DRF shapes: `400` with per-field errors, `401` for a missing or
expired token, `403` for a valid token without staff rights, `404`, and `429`
with a `Retry-After` header when throttled.

## Image sizes

`GET /gallery/` returns two URLs per photo:

* `thumb_url` — a 600px JPEG, generated on upload. Grids and strips use this.
* `image_url` — the stored image, capped at 1600px. Only the lightbox uses it.

Serving the full image into a 250px grid slot costs a visitor on mobile data
roughly three times what it needs to, so prefer `thumb_url` anywhere the photo
is not displayed large. Rows created before thumbnails existed fall back to
`image_url`, so the field is always populated.
