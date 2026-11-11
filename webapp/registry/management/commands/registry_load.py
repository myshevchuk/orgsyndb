"""``manage.py registry_load FILE``: fill an empty registry from a
snapshot."""

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from registry import snapshot


def loaded(table: Any) -> str:
    """Load the snapshot TABLE into the empty registry and return the
    line that says what was written; raise CommandError, writing
    nothing, when it is refused."""
    try:
        terms, substances, articles = snapshot.load(table)
    except snapshot.Broken as error:
        raise CommandError(f"The registry was not loaded: {error}") \
            from error
    return (f"Loaded {terms} terms, {substances} substances and "
            f"{articles} articles.")


class Command(BaseCommand):
    help = ("Fill an empty registry from a snapshot of it, the JSON file "
            "/lab/registry/snapshot.json serves.")

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("file", help="The snapshot to load.")

    def handle(self, *args: Any, file: str, **options: Any) -> None:
        """Load the snapshot FILE; raise CommandError, writing nothing,
        when it cannot be read or is refused."""
        try:
            table = json.loads(Path(file).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as error:
            raise CommandError(f"Cannot read the snapshot {file}: {error}") \
                from error
        self.stdout.write(loaded(table))
