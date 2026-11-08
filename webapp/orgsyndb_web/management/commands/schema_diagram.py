"""The command that writes the table diagram, or checks that it is
current."""

import shlex
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from orgsyndb_web.schema_diagram import OUTPUT, generate


class Command(BaseCommand):
    help = ("Write the table diagram from the models to "
            "webapp/docs/database-schema.html, or check that it is "
            "current.")

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--check", action="store_true",
            help="Write nothing; fail when the file differs from what the "
                 "models give.")
        parser.add_argument(
            "--output", type=Path, default=OUTPUT,
            help="The file to write or check, in place of "
                 "webapp/docs/database-schema.html.")

    def handle(self, *args: Any, check: bool, output: Path,
               **options: Any) -> None:
        """Write the diagram to OUTPUT, creating its directory, and print
        the path; with CHECK, write nothing and raise CommandError, exit
        status 1, when OUTPUT is missing or differs from the diagram."""
        text = generate().encode("utf-8")
        if check:
            try:
                current = output.read_bytes()
            except FileNotFoundError:
                current = None
            if current != text:
                command = ("ORGSYNDB_DEBUG=true uv run python manage.py "
                           "schema_diagram")
                if output != OUTPUT:
                    command += f" --output {shlex.quote(str(output))}"
                raise CommandError(
                    f"{output} is not current; regenerate it with "
                    f"`{command}` in webapp/", returncode=1)
            self.stdout.write(f"{output} is current")
            return
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(text)
        self.stdout.write(str(output))
