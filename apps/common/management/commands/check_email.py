"""Prove that outgoing mail works, loudly.

The contact and careers forms deliberately never fail because mail failed --
an enquiry that reached the database is not worth losing over a flaky SMTP
server. The cost of that is you cannot tell from the forms whether mail is
working at all. This is the counterpart: it reports every problem instead of
swallowing it.

    python manage.py check_email                  # report the configuration
    python manage.py check_email --probe          # find a combination that works
    python manage.py check_email --send you@…     # actually send one
"""

from __future__ import annotations

import smtplib
import socket
import ssl

from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.core.management.base import BaseCommand

REQUIRED = ["EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"]


class Command(BaseCommand):
    help = "Report the mail configuration and optionally send a test message."

    def add_arguments(self, parser):
        parser.add_argument(
            "--send",
            metavar="ADDRESS",
            help="Send a test message to this address. Without it, nothing is sent.",
        )
        parser.add_argument(
            "--probe",
            action="store_true",
            help=(
                "Try the plausible host/port/encryption combinations and report "
                "which ones connect and authenticate. Sends nothing."
            ),
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=20,
            help="Seconds to wait for the SMTP server (default: 20).",
        )

    def handle(self, *args, **options):
        self.stdout.write("Configuration")
        self.stdout.write(f"  EMAIL_BACKEND        {settings.EMAIL_BACKEND}")
        self.stdout.write(f"  EMAIL_HOST           {settings.EMAIL_HOST or '(unset)'}")
        self.stdout.write(f"  EMAIL_PORT           {settings.EMAIL_PORT}")
        self.stdout.write(f"  EMAIL_USE_SSL        {settings.EMAIL_USE_SSL}")
        self.stdout.write(f"  EMAIL_USE_TLS        {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"  EMAIL_HOST_USER      {settings.EMAIL_HOST_USER or '(unset)'}")
        # Never print the password. Its length is enough to tell an empty
        # value from one that failed to parse out of .env.
        password = settings.EMAIL_HOST_PASSWORD or ""
        self.stdout.write(
            f"  EMAIL_HOST_PASSWORD  {'set, ' + str(len(password)) + ' characters' if password else '(unset)'}"
        )
        self.stdout.write(f"  DEFAULT_FROM_EMAIL   {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(
            f"  CONTACT_NOTIFY_EMAIL {getattr(settings, 'CONTACT_NOTIFY_EMAIL', '') or '(unset)'}"
        )

        problems = self._configuration_problems()
        if problems:
            self.stdout.write("\nProblems")
            for problem in problems:
                self.stderr.write(f"  - {problem}")

        if "console" in settings.EMAIL_BACKEND:
            self.stdout.write(
                "\nThe console backend is active, so nothing leaves this machine. "
                "That is expected with DEBUG on."
            )

        if options["probe"]:
            self._probe(options["timeout"])

        if not options["send"]:
            self.stdout.write("\nNo --send address given, so nothing was sent.")
            return

        self._connect(options["timeout"])
        self._send(options["send"], options["timeout"])

    def _configuration_problems(self) -> list[str]:
        problems = []
        local = settings.EMAIL_HOST in {"localhost", "127.0.0.1", "::1"}

        for name in REQUIRED:
            if getattr(settings, name, ""):
                continue
            # The local relay accepts mail from its own machine without
            # authenticating, so a blank password there is correct.
            if name == "EMAIL_HOST_PASSWORD" and local:
                continue
            problems.append(f"{name} is not set")

        # A password with a local host used to be reported here as a problem,
        # on the reasoning that Django calls login() whenever one is set and a
        # local relay offers no AUTH. This host's relay does offer it, and the
        # warning sent someone to blank a password that was working. Whether
        # AUTH is available is a fact about the server, so it is established by
        # connecting to it -- see _connect -- rather than assumed from here.
        if settings.EMAIL_USE_SSL and settings.EMAIL_USE_TLS:
            problems.append("EMAIL_USE_SSL and EMAIL_USE_TLS cannot both be on")
        if settings.EMAIL_PORT == 465 and not settings.EMAIL_USE_SSL:
            problems.append("port 465 is implicit SSL, so EMAIL_USE_SSL should be on")
        if settings.EMAIL_PORT == 587 and not settings.EMAIL_USE_TLS:
            problems.append("port 587 is STARTTLS, so EMAIL_USE_TLS should be on")
        if not getattr(settings, "CONTACT_NOTIFY_EMAIL", ""):
            problems.append(
                "CONTACT_NOTIFY_EMAIL is not set, so the forms will not alert anyone"
            )
        return problems

    def _candidates(self) -> list[tuple[str, int, str, bool]]:
        """(host, port, encryption, verify_certificate).

        localhost first: the mail server is on this machine, so that path needs
        no DNS and no certificate that matches. The public name is tried too,
        but only the mail.* one -- the bare domain is behind Cloudflare, which
        does not carry SMTP, so it would hang rather than fail quickly.
        """
        user = settings.EMAIL_HOST_USER or ""
        domain = user.partition("@")[2]
        hosts = ["localhost"]
        if domain:
            hosts.append(f"mail.{domain}")
        if settings.EMAIL_HOST and settings.EMAIL_HOST not in hosts:
            hosts.append(settings.EMAIL_HOST)

        candidates = []
        # Whatever is configured right now goes first. Leaving it out made the
        # probe unable to confirm a working setting that was already in .env.
        if settings.EMAIL_HOST:
            if settings.EMAIL_USE_SSL:
                configured = "ssl"
            elif settings.EMAIL_USE_TLS:
                configured = "starttls"
            else:
                configured = "none"
            candidates.append((settings.EMAIL_HOST, settings.EMAIL_PORT, configured, True))

        for host in hosts:
            candidates.append((host, 25, "none", False))
            candidates.append((host, 587, "starttls", True))
            candidates.append((host, 465, "ssl", True))
            # The origin presents a shared *.web-hosting.com certificate, so
            # the name will not match. Worth knowing whether that is the only
            # thing in the way.
            candidates.append((host, 465, "ssl (no cert check)", False))
        return candidates

    def _probe(self, timeout: int) -> None:
        self.stdout.write("\nProbing (nothing is sent)")
        user = settings.EMAIL_HOST_USER or ""
        password = settings.EMAIL_HOST_PASSWORD or ""
        working = []

        seen = set()
        for host, port, encryption, verify in self._candidates():
            if (host, port, encryption, verify) in seen:
                continue
            seen.add((host, port, encryption, verify))
            label = f"  {host}:{port} {encryption}"
            try:
                result = self._try(host, port, encryption, verify, user, password, timeout)
            except Exception as error:  # noqa: BLE001 - the whole point is to report it
                self.stdout.write(f"{label:<52} {type(error).__name__}: {error}")
                continue
            self.stdout.write(f"{label:<52} {result}")
            if result.startswith("OK"):
                working.append((host, port, encryption, result))

        if not working:
            self.stderr.write(
                "\n  Nothing worked. If every attempt timed out, outbound SMTP is "
                "blocked; if they were refused, the server is not listening there."
            )
            return

        host, port, encryption, _ = working[0]
        self.stdout.write("\n  Use this in .env:")
        self.stdout.write(f"    EMAIL_HOST={host}")
        self.stdout.write(f"    EMAIL_PORT={port}")
        self.stdout.write(f"    EMAIL_USE_SSL={'True' if encryption.startswith('ssl') else 'False'}")
        self.stdout.write(f"    EMAIL_USE_TLS={'True' if encryption == 'starttls' else 'False'}")

    @staticmethod
    def _try(host, port, encryption, verify, user, password, timeout) -> str:
        context = ssl.create_default_context()
        if not verify:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        if encryption.startswith("ssl"):
            server = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context)
        else:
            server = smtplib.SMTP(host, port, timeout=timeout)
        try:
            server.ehlo()
            if encryption == "starttls":
                server.starttls(context=context)
                server.ehlo()
            if not (user and password):
                return "OK, connected (no credentials to test)"
            if "auth" not in server.esmtp_features:
                return "connected, but the server offers no AUTH"
            server.login(user, password)
            return "OK, connected and authenticated"
        finally:
            try:
                server.quit()
            except Exception:
                server.close()

    def _connect(self, timeout: int) -> None:
        """Open the connection on its own, so a failure names its own cause."""
        self.stdout.write("\nOpening the connection")
        connection = get_connection(timeout=timeout)
        try:
            connection.open()
        except smtplib.SMTPNotSupportedError:
            self.stderr.write(
                "  the server offers no AUTH, but a username and password are set, "
                "so Django tried to authenticate anyway. Blank EMAIL_HOST_PASSWORD "
                "for this host."
            )
            return
        except smtplib.SMTPAuthenticationError as error:
            self.stderr.write(f"  rejected the username or password: {error}")
            return
        except (socket.timeout, TimeoutError):
            self.stderr.write(
                f"  timed out after {timeout}s. Shared hosting often blocks outbound "
                "SMTP to other providers, but its own server on localhost is allowed."
            )
            return
        except (ssl.SSLError, smtplib.SMTPException, OSError) as error:
            self.stderr.write(f"  failed: {type(error).__name__}: {error}")
            return
        self.stdout.write("  connected and authenticated")
        connection.close()

    def _send(self, address: str, timeout: int) -> None:
        self.stdout.write(f"\nSending a test message to {address}")
        try:
            sent = send_mail(
                subject="[Fonanyi] Mail configuration test",
                message=(
                    "If you are reading this, the API can send mail.\n\n"
                    "The contact and careers forms use the same connection, so "
                    "their alerts will arrive too.\n"
                ),
                from_email=None,
                recipient_list=[address],
                fail_silently=False,
                connection=get_connection(timeout=timeout),
            )
        except Exception as error:
            self.stderr.write(f"  failed: {type(error).__name__}: {error}")
            return
        if sent:
            self.stdout.write("  accepted by the server. Check the inbox, and spam.")
        else:
            self.stderr.write("  the server accepted nothing, without raising an error.")
