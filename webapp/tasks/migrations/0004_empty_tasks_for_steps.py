"""Delete every task, with its history, so that the next migration
replaces the steps a task counts and copies by step rows and its
sequence ID by an imported sequence, and guesses neither."""

from typing import Any

from django.db import migrations


def empty(apps: Any, schema_editor: Any) -> None:
    """Delete every task and its history."""
    apps.get_model("tasks", "Task").objects.all().delete()
    apps.get_model("tasks", "HistoricalTask").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tasks", "0003_substance"),
    ]

    operations = [
        migrations.RunPython(empty, migrations.RunPython.noop),
    ]
