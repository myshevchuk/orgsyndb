from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def record_creations(apps: Apps,
                     schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Write one creation record for each entered value stored that has
    no history yet, so that applying this again adds none."""
    entered = apps.get_model("inventory", "EnteredConsumption")
    history = apps.get_model("inventory", "HistoricalEnteredConsumption")
    recorded = set(history.objects.values_list("id", flat=True))
    history.objects.bulk_create([
        history(id=row.pk, item_id=row.item_id, year=row.year,
                quarter=row.quarter, count=row.count,
                entered_by_id=row.entered_by_id, entered_at=row.entered_at,
                history_date=row.entered_at, history_type="+",
                history_user_id=row.entered_by_id)
        for row in entered.objects.order_by("pk")
        if row.pk not in recorded])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0008_entered_consumption_history"),
    ]

    operations = [
        migrations.RunPython(record_creations,
                             reverse_code=migrations.RunPython.noop),
    ]
