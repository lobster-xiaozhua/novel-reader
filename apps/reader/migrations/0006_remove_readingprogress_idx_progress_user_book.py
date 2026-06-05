# Generated migration - remove PG-only index for SQLite compatibility
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("reader", "0005_pg_indexes"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="readingprogress",
            name="idx_progress_user_book",
        ),
    ]