# Scheduled tasks (cPanel cron)

Namecheap gives you cron under cPanel → **Cron Jobs**. Every entry below calls
the same wrapper, `deploy/cron/run.sh`, which resolves the virtualenv, changes
to the app directory and appends output to `logs/cron-<command>.log`.

Set the notification email at the top of the Cron Jobs page to a real inbox,
then add the entries.

## The entries

Replace `<cpuser>` with your cPanel username.

### Publish scheduled articles — every 15 minutes

```
*/15 * * * * /bin/bash /home/<cpuser>/fonanyi-api/deploy/cron/run.sh publish_scheduled
```

Staff can write an article, set **Schedule for** in the dashboard and leave it
unpublished. This job publishes anything whose time has passed, then asks
Cloudflare to rebuild.

### Rebuild the site when content changes — every 10 minutes

```
*/10 * * * * /bin/bash /home/<cpuser>/fonanyi-api/deploy/cron/run.sh rebuild_if_dirty
```

Saving a photo, testimonial, article or setting flags the site as changed. This
job checks that flag and triggers the Cloudflare Pages deploy hook only when
there is something to rebuild, so most runs do nothing.

The work is done from cron rather than inside the request because an outbound
HTTPS call from a Passenger worker on shared hosting is slow enough to time out
the staff member's save.

### Daily enquiry digest — 7am

```
0 7 * * * /bin/bash /home/<cpuser>/fonanyi-api/deploy/cron/run.sh daily_digest
```

Emails `CONTACT_NOTIFY_EMAIL` a summary of the last 24 hours of contact-form
messages. Skips silently when there is nothing to report.

### Database backup — 2am

```
0 2 * * * /bin/bash /home/<cpuser>/fonanyi-api/deploy/cron/run.sh db_backup
```

Writes a gzipped `mysqldump` into `~/fonanyi-api/backups/` and keeps the most
recent 14. Download them periodically — a backup on the same disk as the
database is only half a backup.

### Prune old analytics — Sunday 3am

```
0 3 * * 0 /bin/bash /home/<cpuser>/fonanyi-api/deploy/cron/run.sh prune_analytics
```

Deletes visit events older than `ANALYTICS_RETENTION_DAYS` (180 by default) in
batches of 2000, so it never holds a long transaction open. Shared-hosting
MySQL quotas are small; without this the visits table grows without limit.

---

## Running one by hand

```bash
cd ~/fonanyi-api
source ~/virtualenv/fonanyi-api/3.11/bin/activate
python manage.py publish_scheduled
python manage.py rebuild_site        # force a rebuild regardless of the flag
python manage.py prune_analytics --days 90
```

## Reading the logs

```bash
tail -40 ~/fonanyi-api/logs/cron-rebuild_if_dirty.log
```

The logs grow slowly but forever. If you want them capped, add a monthly
entry:

```
0 4 1 * * /usr/bin/find /home/<cpuser>/fonanyi-api/logs -name '*.log' -size +5M -delete
```

## A note on frequency

Namecheap discourages cron entries more often than every 5 minutes on shared
plans, and will throttle accounts that abuse it. The schedule above stays well
inside that. Do not lower `rebuild_if_dirty` below 5 minutes; if content needs
to go live immediately, run `rebuild_site` by hand instead.
