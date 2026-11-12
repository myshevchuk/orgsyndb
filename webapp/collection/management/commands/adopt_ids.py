"""``manage.py adopt_ids``: adopt procedure and sequence IDs by hand."""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from collection import issuing


class Command(BaseCommand):
    help = ("Adopt each named procedure or sequence ID that the lab "
            "application has not issued, with no account, as after "
            "restoring a database dump older than the collection.")

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("ids", nargs="+", metavar="ID",
                            help="a procedure ID, OSDB-NNNN, or a sequence "
                                 "ID, SEQ-NNNN")

    def handle(self, *args: Any, ids: list[str], **options: Any) -> None:
        """Adopt each of IDS that is not issued, printing ``adopted
        <ID>``, and print ``<ID> was issued`` for one that is. Raise
        CommandError, adopting nothing, naming the first of IDS that is
        not a procedure or sequence ID."""
        for key in ids:
            if not issuing.is_id(key):
                raise CommandError(
                    f'"{key}" is not a procedure or sequence ID, OSDB- or '
                    "SEQ- and four digits; nothing adopted.")
        for key, adopted in issuing.adopt(ids):
            self.stdout.write(f"adopted {key}" if adopted
                              else f"{key} was issued")
