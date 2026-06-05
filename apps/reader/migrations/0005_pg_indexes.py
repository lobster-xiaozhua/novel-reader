# Add concurrent index for reader_readingprogress - PostgreSQL only
from django.db import migrations, models, connection


def add_pg_index(apps, schema_editor):
    """仅在 PostgreSQL 上添加并发索引"""
    if connection.vendor != 'postgresql':
        return

    schema_editor.add_index(
        model=apps.get_model('reader', 'ReadingProgress'),
        index=models.Index(
            fields=["user_id", "book_id", "updated_at"],
            name="idx_progress_user_book",
        ),
    )


def remove_pg_index(apps, schema_editor):
    """回滚：仅在 PostgreSQL 上移除"""
    if connection.vendor != 'postgresql':
        return

    schema_editor.remove_index(
        model=apps.get_model('reader', 'ReadingProgress'),
        index_name="idx_progress_user_book",
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("reader", "0004_alter_readingprogress_updated_at_and_more"),
    ]

    operations = [
        migrations.RunPython(add_pg_index, remove_pg_index),
    ]
