"""``manage.py demo_data``: write the demo data set as of today."""

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from demo import data, seed
from orgsyndb_web import index


class Command(BaseCommand):
    help = ("Write the demo data set as of today into an empty database, "
            "or with --replace into a demo database. Needs "
            "ORGSYNDB_DEMO=true.")

    def add_arguments(self, parser: Any) -> None:
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--replace", action="store_true",
            help="Delete every lab record of a demo database, or of a "
                 "database without lab records, and write the data set.")
        group.add_argument(
            "--if-empty", action="store_true",
            help="Write the data set only when ORGSYNDB_DEMO is true and "
                 "the database holds no lab records; otherwise change "
                 "nothing and succeed.")

    def handle(self, *args: Any, replace: bool = False,
               if_empty: bool = False, **options: Any) -> None:
        """Write the data set, refusing as the options say.

        Raise CommandError, changing nothing, outside demo mode (unless
        IF_EMPTY), when the database holds lab records (unless REPLACE
        on a demo database, or IF_EMPTY), and when a change of the data
        set is refused.
        """
        demo = settings.ORGSYNDB_DEMO
        if if_empty:
            if not demo:
                self.stdout.write("ORGSYNDB_DEMO is not true; nothing "
                                  "written.")
                return
            if seed.holds_records():
                self.stdout.write("The database holds lab records; "
                                  "nothing written.")
                return
        if not demo:
            raise CommandError(
                "ORGSYNDB_DEMO is not true; the demo data is written only "
                "with ORGSYNDB_DEMO=true, into a test database.")
        missing = seed.missing_compounds()
        if missing:
            self.stderr.write(
                f"Warning: the collection index lacks {missing} of the "
                f"{len(data.compounds())} compounds of examples/demo the "
                "demo data names; their names will not link and their "
                "units will not convert.")
        today = timezone.localdate()
        try:
            with transaction.atomic():
                if seed.holds_records():
                    if not replace:
                        raise CommandError(
                            "The database holds lab records; use --replace "
                            "to replace a demo database.")
                    if not seed.is_demo():
                        raise CommandError(
                            "The database holds lab records the demo data "
                            "did not write; --replace replaces only a demo "
                            "database.")
                if replace:
                    seed.clear()
                summary = seed.write(today, index.current().language)
        except ValidationError as error:
            raise CommandError(
                f"The demo data could not be written: {error}") from error
        self.stdout.write(
            f"Demo data as of {today.isoformat()} written: "
            f"{summary.accounts} accounts, {summary.items} items, "
            f"{summary.notes} delivery notes and {summary.tasks} tasks.")
