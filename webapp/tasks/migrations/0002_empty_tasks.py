"""Delete every task, with its history, so that the next migration
replaces the product of an empty table by a substance and guesses no
substance for a task."""

from typing import Any

from django.db import migrations


def empty(apps: Any, schema_editor: Any) -> None:
    """Delete every task and its history."""
    apps.get_model("tasks", "Task").objects.all().delete()
    apps.get_model("tasks", "HistoricalTask").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(empty, migrations.RunPython.noop),
    ]
