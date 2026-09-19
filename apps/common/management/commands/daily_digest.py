from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.contact.models import ContactMessage


class Command(BaseCommand):
    help = "Email staff a summary of the last 24 hours of enquiries. Run daily from cron."

    def handle(self, *args, **options):
        recipient = getattr(settings, "CONTACT_NOTIFY_EMAIL", "")
        if not recipient:
            self.stdout.write("CONTACT_NOTIFY_EMAIL not set; skipping.")
            return
        since = timezone.now() - timedelta(days=1)
        messages = ContactMessage.objects.filter(created_at__gte=since)
        unread = ContactMessage.objects.filter(status="new").count()
        if not messages and not unread:
            self.stdout.write("Nothing to report.")
            return
        lines = [f"{m.created_at:%d %b %H:%M}  {m.full_name} <{m.email}>  [{m.get_division_display()}]"
                 for m in messages]
        body = (
            f"{messages.count()} new enquiry(ies) in the last 24 hours.\n"
            f"{unread} unread in total.\n\n" + "\n".join(lines)
        )
        send_mail(
            subject=f"[Fonanyi] Daily enquiry digest - {messages.count()} new",
            message=body,
            from_email=None,
            recipient_list=[recipient],
            fail_silently=True,
        )
        self.stdout.write(self.style.SUCCESS("Digest sent."))
