"""Settings for the test suite.

pytest-django configures Django in pytest_load_initial_conftests, which runs
before any conftest.py, so environment defaults have to be in place by the
time the settings module is imported. Setting them here -- then importing the
real settings -- is the earliest hook there is, and it means a fresh clone can
run the suite without first writing a .env.

These values never leave the test run. settings.py refuses to start with a
placeholder key whenever DEBUG is off, which one of the tests asserts by
setting those variables itself.
"""
import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-key-not-used-outside-the-test-suite")
os.environ.setdefault("DJANGO_DEBUG", "True")
os.environ.setdefault("DB_ENGINE", "sqlite")

from .settings import *  # noqa: F401,F403,E402
