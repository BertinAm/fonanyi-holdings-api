"""Entry point for Namecheap cPanel -> Setup Python App (Phusion Passenger).

cPanel points the application at this file. Passenger imports it and looks for
a module-level `application` callable.

Notes for whoever maintains this:
  * Passenger re-executes this file with the virtualenv's interpreter, so no
    manual sys.path juggling into site-packages is needed.
  * After a `git pull` you must restart the app, either from the cPanel
    "Setup Python App" screen or by running `touch tmp/restart.txt` here.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Namecheap shared hosting has no MySQL C headers, so mysqlclient cannot be
# built there. PyMySQL speaks the same protocol and registers itself as the
# `MySQLdb` module that Django's mysql backend imports.
try:
    import MySQLdb  # noqa: F401
except ImportError:  # pragma: no cover - only on shared hosting
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
