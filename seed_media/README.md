# Seed media

Photographs supplied by the client, committed so a fresh install has real
gallery content rather than placeholders:

```bash
python manage.py seed_content --photos seed_media/photos
```

The images are copied into `media/gallery/` on import, so this directory is
read-only as far as the app is concerned — deleting a photo in the dashboard
does not touch it.

The client also supplied three short videos. They are not in Git: at ~5.5 MB
they would be pulled on every deploy and every Cloudflare build for no benefit,
since nothing on the site plays them yet. They live in `_client_media_videos/`
in the working copy. If the site ever needs video, put them behind a CDN rather
than in the repository.
