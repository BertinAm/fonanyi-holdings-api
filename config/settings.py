"""Django settings for the Fonanyi Holdings backend.

Runs in two places:
  * locally on SQLite   -> DB_ENGINE=sqlite
  * Namecheap shared hosting on MySQL -> DB_ENGINE=mysql (the default)
"""
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return str(env(key, default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(key, default=""):
    return [v.strip() for v in str(env(key, default)).split(",") if v.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "django_filters",
    "apps.common",
    "apps.accounts",
    "apps.siteinfo",
    "apps.gallery",
    "apps.blog",
    "apps.contact",
    "apps.analytics",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

if env("DB_ENGINE", "mysql") == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DB_NAME", ""),
            "USER": env("DB_USER", ""),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                # Namecheap's MySQL is 5.7/8.x; strict mode avoids silent truncation.
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
            "CONN_MAX_AGE": 0,  # Passenger recycles processes; do not hold sockets.
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Africa/Douala"
USE_I18N = True
USE_TZ = True

STATIC_URL = env("DJANGO_STATIC_URL", "/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = env("DJANGO_MEDIA_URL", "/media/")
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Public site origin, used to build absolute media URLs and to allow CORS.
SITE_URL = env("SITE_URL", "http://localhost:8000")
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:3000")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "contact": "8/hour",
        "track": "240/hour",
        "login": "10/hour",
    },
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:3000")

# Outgoing mail. Namecheap gives you SMTP on the same cPanel account.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "465"))
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", True)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@localhost")
CONTACT_NOTIFY_EMAIL = env("CONTACT_NOTIFY_EMAIL", "")

# Rebuilding the Cloudflare Pages site after content changes.
CLOUDFLARE_DEPLOY_HOOK = env("CLOUDFLARE_DEPLOY_HOOK", "")

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    # cPanel terminates TLS upstream of Passenger.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    # HSTS is opt-in: turn it on only once HTTPS is confirmed working on every
    # subdomain, because browsers cache the header and it is hard to undo.
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}
