"""Prove whether the dashboard summary works on this server, and why not.

The summary endpoint returned a 500 in production while every test passed,
because the tests run on SQLite and production runs on MySQL. This reports
the difference rather than requiring anyone to reason about it.

    python manage.py check_analytics
"""

from __future__ import annotations

import traceback

from django.db import connection
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.utils import timezone

from apps.analytics.models import VisitEvent


class Command(BaseCommand):
    help = "Report whether the dashboard summary can be built on this database."

    def handle(self, *args, **options):
        self.stdout.write(f"Database vendor : {connection.vendor}")
        self.stdout.write(f"TIME_ZONE       : {timezone.get_current_timezone_name()}")
        self.stdout.write(f"Events stored   : {VisitEvent.objects.count()}")
        for kind, label in VisitEvent.KIND_CHOICES:
            self.stdout.write(
                f"  {label:<18} {VisitEvent.objects.filter(kind=kind).count()}"
            )

        self._check_convert_tz()
        self._check_summary()

    def _check_convert_tz(self):
        """The specific thing that broke: MySQL's timezone tables.

        Django's TruncDate asks MySQL to CONVERT_TZ from UTC to the local
        zone. Without the tables that mysql_tzinfo_to_sql loads, that returns
        NULL rather than failing, so the breakage surfaces far from its cause.
        """
        self.stdout.write("\nCan this database convert timezones?")
        if connection.vendor != "mysql":
            self.stdout.write("  not MySQL, so the question does not arise")
            return
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT CONVERT_TZ('2026-01-01 12:00:00', 'UTC', %s)",
                    [timezone.get_current_timezone_name()],
                )
                result = cursor.fetchone()[0]
        except Exception as error:
            self.stderr.write(f"  the query itself failed: {error}")
            return

        if result is None:
            self.stdout.write(
                "  NO -- CONVERT_TZ returned NULL. The timezone tables are not\n"
                "  loaded, which is normal on shared hosting. Anything built on\n"
                "  TruncDate or TruncMonth will silently produce None here, so\n"
                "  group dates in Python instead."
            )
        else:
            self.stdout.write(f"  yes, it returned {result}")

    def _check_summary(self):
        self.stdout.write("\nBuilding the dashboard summary")
        from apps.analytics.views import DashboardSummaryView

        request = RequestFactory().get("/api/admin/summary/")
        try:
            response = DashboardSummaryView().get(request)
        except Exception:
            self.stderr.write("  it raised. This is what the dashboard sees as a 500:\n")
            self.stderr.write(traceback.format_exc())
            return

        data = response.data
        self.stdout.write("  built successfully. Some of what it returned:")
        for key in (
            "views_this_week",
            "visitors_this_week",
            "form_submissions_this_week",
            "logins_this_week",
            "failed_logins_this_week",
            "conversion_rate",
        ):
            self.stdout.write(f"    {key:<28} {data.get(key)}")
        self.stdout.write(f"    views_by_day                 {data.get('views_by_day')}")
