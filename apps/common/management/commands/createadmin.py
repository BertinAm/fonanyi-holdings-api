"""Create the first dashboard account where there is no interactive shell.

Namecheap's cheaper plans have no Terminal and no SSH, so createsuperuser --
which prompts for a password -- cannot be run at all. cPanel's "Execute python
script" box runs manage.py with arguments but gives no way to type a reply.

This generates the password instead of asking for one, prints it once, and
never writes it anywhere. Nothing is stored in the repository or in cPanel's
environment, so there is no copy left behind to find later.
"""
import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


def generate_password(length: int = 20) -> str:
    # Ambiguous characters are left out: this gets read off a screen and typed
    # back in by hand, and an l/1 or O/0 mix-up reads as a wrong password.
    alphabet = (
        "".join(c for c in string.ascii_letters + string.digits if c not in "lI1O0")
        + "!@#$%^&*-_=+"
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Create (or reset the password of) a dashboard superuser."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Set a new password on an account that already exists.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = generate_password()

        user = User.objects.filter(username=username).first()
        if user and not options["reset"]:
            raise CommandError(
                f"{username!r} already exists. Re-run with --reset to give it a "
                f"new password, or pass --username to create a different account."
            )

        if user:
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            action = "Password reset for"
        else:
            user = User.objects.create_superuser(
                username=username, email=options["email"], password=password
            )
            action = "Created"

        self.stdout.write("")
        self.stdout.write(f"  {action} {username}")
        self.stdout.write(f"  Password: {password}")
        self.stdout.write("")
        self.stdout.write("  Copy it now. It is not stored and cannot be shown again.")
        self.stdout.write("  Change it after signing in, at /django-admin/password_change/")
