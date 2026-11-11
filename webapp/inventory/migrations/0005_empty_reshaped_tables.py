"""Delete every item, lot, movement, delivery note and line and entered
consumption, with their histories, so that the next migration reshapes
empty tables: items become sizes of articles and lots name substances,
and no value of a new column is guessed."""

from typing import Any

from django.db import migrations


def empty(apps: Any, schema_editor: Any) -> None:
    """Delete the records the next migration reshapes, each before the
    records it protects."""
    model = apps.get_model
    movements = model("inventory", "Movement").objects
    movements.exclude(reverses=None).delete()
    movements.all().delete()
    for name in ("DeliveryLine", "DeliveryNote", "LotMovement", "Lot",
                 "EnteredConsumption", "Item", "HistoricalItem",
                 "HistoricalLot", "HistoricalDeliveryNote"):
        model("inventory", name).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_item_locations"),
    ]

    operations = [
        migrations.RunPython(empty, migrations.RunPython.noop),
    ]
