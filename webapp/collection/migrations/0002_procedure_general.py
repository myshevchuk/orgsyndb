from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("collection", "0001_imported_rows"),
    ]

    operations = [
        migrations.AddField(
            model_name="procedure",
            name="general",
            field=models.BooleanField(default=False, verbose_name="General"),
            preserve_default=False,
        ),
    ]
