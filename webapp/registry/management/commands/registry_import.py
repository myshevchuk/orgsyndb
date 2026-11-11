"""``manage.py registry_import COLLECTION``: fill an empty registry from a
collection's compounds and vocabularies."""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from registry import snapshot
from registry.collection import read
from registry.management.commands.registry_load import loaded


class Command(BaseCommand):
    help = ("Fill an empty registry from the compounds/ and vocabularies/ "
            "of a collection directory.")

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("collection",
                            help="The directory of the collection.")

    def handle(self, *args: Any, **options: Any) -> None:
        """Read the registry of COLLECTION and load it; raise
        CommandError, writing nothing, when a file cannot be read, a
        compound lacks a group or a chemical class, or the load is
        refused. The keys left out of the compounds are named on
        stderr."""
        try:
            table, left = read(Path(options["collection"]))
        except snapshot.Broken as error:
            raise CommandError(f"The registry was not imported: {error}") \
                from error
        if left:
            counts = ", ".join(
                f"{key} ({count} {'compound' if count == 1 else 'compounds'})"
                for key, count in sorted(left.items()))
            self.stderr.write(f"Warning: these keys of the compound files "
                              f"are left out: {counts}.")
        self.stdout.write(loaded(table))

