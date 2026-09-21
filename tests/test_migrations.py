"""The migration graph must match the models.

This has drifted twice, both times a help_text change with no schema behind
it, and both times it was found by reading a deploy log rather than by a
failing test. An unrecorded change is harmless until the next real one lands
on top of a graph that does not match the models.
"""
import pytest
from django.core.management import call_command

# makemigrations opens a connection to read the applied-migration table, even
# with --dry-run, so the test needs the database like any other.
pytestmark = pytest.mark.django_db


def test_no_model_changes_are_missing_a_migration():
    try:
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)
    except SystemExit as exit_signal:
        pytest.fail(
            "A model has changed with no migration recorded. Run:\n"
            "    python manage.py makemigrations\n"
            f"and commit the result. (makemigrations --check exited {exit_signal.code})"
        )
