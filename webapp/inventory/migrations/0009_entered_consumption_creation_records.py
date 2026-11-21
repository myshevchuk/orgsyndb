from django.db import migrations


def record_creations(apps, schema_editor):
    """Write one creation record for each entered value stored."""
    entered = apps.get_model("inventory", "EnteredConsumption")
    history = apps.get_model("inventory", "HistoricalEnteredConsumption")
    history.objects.bulk_create([
        history(id=row.pk, item_id=row.item_id, year=row.year,
                quarter=row.quarter, count=row.count,
                entered_by_id=row.entered_by_id, entered_at=row.entered_at,
                history_date=row.entered_at, history_type="+",
                history_user_id=row.entered_by_id)
        for row in entered.objects.order_by("pk")])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0008_entered_consumption_history"),
    ]

    operations = [
        migrations.RunPython(record_creations,
                             reverse_code=migrations.RunPython.noop),
    ]
