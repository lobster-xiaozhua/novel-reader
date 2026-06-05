# Generated migration - remove PG-only index for SQLite compatibility
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("chapters", "0004_pg_indexes"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="chapter",
            name="idx_chapter_book_order",
        ),
    ]