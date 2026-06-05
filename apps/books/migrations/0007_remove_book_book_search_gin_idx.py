# Generated migration - remove PG-only index for SQLite compatibility
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("books", "0006_postgres_extensions"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="book",
            name="book_search_gin_idx",
        ),
    ]