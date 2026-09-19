# Local development

## Backend

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt   # or requirements-shared-hosting.txt on a machine without MySQL headers
cp .env.example .env
```

Set `DB_ENGINE=sqlite` and `DJANGO_DEBUG=True` in `.env` for local work, then:

```bash
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py createsuperuser
./.venv/bin/python manage.py seed_content --photos seed_media/photos
./.venv/bin/python manage.py runserver
```

The API is at `http://127.0.0.1:8000/api/`, and Django's own admin at
`http://127.0.0.1:8000/django-admin/`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

`.env.local` already points at `http://127.0.0.1:8000/api`. The site is at
`http://localhost:3000`, the dashboard at `http://localhost:3000/admin/login/`.

Run the backend first: several pages read the API while rendering. If it is
down, they fall back to the bundled placeholder content rather than failing.

## Checks before you push

```bash
cd frontend && npm run typecheck && npm run lint && npm run build
cd ../backend && ./.venv/bin/python manage.py check && ./.venv/bin/python manage.py makemigrations --check --dry-run
```

`npm run build` writes the static export to `frontend/out/`, which is exactly
what Cloudflare publishes.

## Where things are

```
backend/
  config/            settings, urls, wsgi
  apps/accounts/     JWT login, staff-only
  apps/siteinfo/     SiteSettings, Testimonial, ContentFlag, rebuild signals
  apps/gallery/      GalleryImage
  apps/blog/         Post (slug, scheduling, read time)
  apps/contact/      ContactMessage + honeypot
  apps/analytics/    VisitEvent + dashboard summary
  apps/common/       shared mixins, pagination, cron management commands
  deploy/            deploy.sh, restart_app.sh, cron/run.sh
  passenger_wsgi.py  cPanel entry point

frontend/src/
  app/(site)/        public pages
  app/admin/         dashboard (client-rendered, noindex)
  components/        NavBar, Footer, GalleryGrid, ContactForm, admin/*
  lib/               api client, auth, types, site copy
```

## Things that will bite you

**Tailwind cascade layers.** Base resets in `globals.css` live inside
`@layer base`. Unlayered CSS outranks every layered utility, so an unlayered
`a { color: inherit }` silently defeats `text-white/80` on links. Keep new
global rules inside a layer.

**`overflow-hidden` kills `position: sticky`.** An ancestor with
`overflow: hidden` becomes a scroll container, which silently disables sticky
for everything inside it — the nav and every pinned section. `body` therefore
uses `overflow-x: clip`, and neither the site wrapper nor `StickyNarrative`
sets an overflow class. If the sticky image column or the nav ever stops
holding, look for a new `overflow-hidden` above it first.

**Percentage heights inside flex columns.** A bar with `height: 80%` in a flex
column has no definite parent to resolve against and collapses to nothing. The
dashboard chart sizes its bars in pixels for this reason.

**Static export and dynamic routes.** Adding a route like `/x/[id]` means
adding `generateStaticParams`, and it must return at least one entry or the
build fails. See how `/news/[slug]` handles the empty case.

**Images.** `next/image` optimisation is off (`unoptimized: true`) — there is
no optimiser in a static export, and the images come from the Namecheap origin.
Plain `<img>` is correct here; the eslint disable comments are deliberate.

Because nothing optimises images at request time, the backend does it at upload
time instead: `apps/common/images.py` caps every upload at 1600px on the long
edge (400px for avatars) and re-encodes it. A 5 MB phone photo lands as roughly
150 KB. Do not remove that hook without putting an optimiser somewhere else —
most visitors are on mobile data.

## The world map

`src/components/world-map-data.ts` is generated, not hand-written:

```bash
cd frontend && node scripts/generate-world-map.mjs
```

The script projects Natural Earth's 110m land outline into an SVG path and
computes the pin positions with the **same** projection, so a pin cannot drift
off its coastline. Editing one without the other is the only way to break it.

`d3-geo`, `topojson-client`, `topojson-simplify` and `world-atlas` are
devDependencies used solely by that script; nothing ships to the browser but
the generated path. The chunk is ~80 KB and code-splits to
`/services/fashion/` alone — check that with:

```bash
grep -l "Buea, Cameroon" out/_next/static/chunks/*.js
```

It writes two files, deliberately separate:

* `world-map-data.ts` (~79 KB) — the world outline. `WorldMap` imports it
  dynamically when the section nears the viewport, so the homepage does not
  pay for it up front. Confirm that with:
  `grep -c "$(basename $(grep -l 'Buea, Cameroon' out/_next/static/chunks/*.js))" out/index.html` — it should be 0.
* `cameroon-map-data.ts` (~4 KB) — the country outline and the ten regional
  pins. Small enough to load eagerly.

world-atlas has no sub-national boundaries, so the ten regions are pins at
their capitals rather than filled shapes. Label positions (`anchor`, `dx`,
`dy`) are set per region in the script: the four southern regions sit within
about 90px of each other at this scale, and any generic rule stacks Buea,
Douala and Yaounde on top of one another.

To add a country, add it to `PLACES` in the script and to `SHIPS_TO` in
`src/lib/site.ts`, then re-run the generator.

## Opening hours

Two sets, because the businesses keep different hours:

* `hours_*` — solar, electrical and rentals. Long days; setups start early.
* `boutique_hours_*` — the shop.

Both are editable from the dashboard. If you add a third business, add fields
rather than compressing them into one line: someone turning up to a shut shop
is a worse outcome than a slightly longer settings form.


## Motion

Everything is CSS transitions and transforms driven by IntersectionObserver;
there is no animation library. The pieces:

| Component | Where | Notes |
| --- | --- | --- |
| `TextReveal` | Big headings | Masked line-by-line slide. Lines are strings, not JSX, so a call site cannot forget a key. |
| `ClipReveal` | Photography | Wipes in behind a moving edge. A fade reads as "still loading"; a wipe reads as deliberate. |
| `Parallax` | Hero and section images | Writes transform inside rAF, never through state. |
| `Magnetic` | Primary buttons | Pointer devices only. |
| `Tilt` | Division cards | Pointer devices only. |
| `Spotlight` | Every `DarkPanel` | Pointer-following light, written to a CSS variable. |
| `Counter` | Statistics | Coerces a missing value to 0 rather than rendering `NaN`. |
| `WordBand` | Section dividers | Infinite scrolling word strip. |
| `PhotoMarquee` | Work strips | Speeds up and leans with scroll velocity. |

Two rules that are easy to break:

**Never change `animation-duration` on a running CSS animation.** It re-maps
the animation's current time into the new duration rather than retiming
smoothly: 23s into a 46s loop you are halfway through, and shortening the loop
to 23s puts you at the end instantly. Driving it from a scroll handler makes
the element jump on every event. `PhotoMarquee` therefore advances its own
offset in rAF, where speed can change freely and position only ever moves
forward.

**Never put an inline `transform` on an element that also runs a keyframe
animation** — the inline style replaces the animation outright.

**A looping strip does not wrap at `scrollWidth / 2`.** A flex `gap` sits
between items, so a doubled list of n photos measures `2n*size + (2n-1)*gap`,
one gap short of two repeats. The period is `(scrollWidth + gap) / 2`; using
half the scroll width leaves an 8px hitch on every cycle.

**`prefers-reduced-motion` and pointer capability are respected everywhere.**
`useSkipAnimation` reads both through `useSyncExternalStore`, so reading them
never breaks hydration and never needs a synchronous `setState` in an effect.


## Hash links

`HashScroll` in the site layout handles `#anchor` navigation. The browser does
this natively for a plain document load, but the App Router restores scroll
after hydration and lands you back at the top, and a client-side navigation
carrying a hash never scrolls at all — `/contact/#send-message` would quietly
do nothing.

It uses `window.scrollTo` with an explicit header offset rather than
`scrollIntoView`, so the sticky nav is accounted for in one place instead of a
`scroll-margin` class on every target, and it retries briefly while images
above the anchor are still settling.

Note that `scroll-behavior: smooth` means no scroll executes at all in a hidden
document, which is worth knowing when a scroll appears to do nothing under
automation.
