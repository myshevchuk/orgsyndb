#!/usr/bin/env python3
"""Django's command-line utility for the lab application."""

import os
import sys


def main() -> None:
    """Run the Django command named by the command-line arguments."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orgsyndb_web.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
