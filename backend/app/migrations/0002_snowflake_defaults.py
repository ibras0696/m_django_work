from django.db import migrations


def noop(apps, schema_editor):
    # This migration only sets default callable; no data migration needed.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(noop, reverse_code=noop),
    ]
