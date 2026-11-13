"""``manage.py forge_accounts``: set every Forgejo account in line with
its lab account."""

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from accounts import forge


class Command(BaseCommand):
    help = ("Set every Forgejo account of the source lab to its lab "
            "account, block those of no lab account, and print each "
            "account changed.")

    def handle(self, *args: Any, **options: Any) -> None:
        """Bring Forgejo in line, as ``accounts.forge.bring_in_line``
        does, printing each Forgejo account changed with the values set
        on it. Do nothing when Forgejo is not configured; raise
        CommandError, exiting non-zero, when Forgejo cannot be reached or
        refuses a request."""
        if not forge.configured():
            self.stderr.write("ORGSYNDB_FORGE_URL or ORGSYNDB_FORGE_PASSWORD "
                              "is not set; Forgejo is left as it is.")
            return
        try:
            for account, changes in forge.bring_in_line():
                self.stdout.write(f"{account['login']}: "
                                  + json.dumps(changes, ensure_ascii=False))
        except forge.ForgeError as exc:
            raise CommandError(f"Forgejo was not brought in line: {exc}"
                               ) from exc
