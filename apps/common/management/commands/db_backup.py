import gzip
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Dump the MySQL database to backups/ and keep the last N copies. Run nightly from cron."

    def add_arguments(self, parser):
        parser.add_argument("--keep", type=int, default=14)

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        if "mysql" not in db["ENGINE"]:
            self.stdout.write("Not a MySQL database; skipping.")
            return
        out_dir = Path(settings.BASE_DIR) / "backups"
        out_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        raw = out_dir / f"{db['NAME']}-{stamp}.sql"
        cmd = [
            "mysqldump",
            f"--host={db['HOST']}",
            f"--user={db['USER']}",
            f"--password={db['PASSWORD']}",
            "--single-transaction",
            "--quick",
            db["NAME"],
        ]
        with raw.open("wb") as fh:
            subprocess.run(cmd, stdout=fh, check=True)
        with raw.open("rb") as src, gzip.open(f"{raw}.gz", "wb") as dst:
            shutil.copyfileobj(src, dst)
        raw.unlink()

        dumps = sorted(out_dir.glob("*.sql.gz"))
        for old in dumps[: max(0, len(dumps) - options["keep"])]:
            old.unlink()
        self.stdout.write(self.style.SUCCESS(f"Backed up to {raw}.gz"))
