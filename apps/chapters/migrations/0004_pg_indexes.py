# Add concurrent index for chapters_chapter - PostgreSQL only
from django.db import migrations, models, connection


def add_pg_index(apps, schema_editor):
    """仅在 PostgreSQL 上添加并发索引"""
    if connection.vendor != 'postgresql':
        return

    schema_editor.add_index(
        model=apps.get_model('chapters', 'Chapter'),
        index=models.Index(
            fields=["book_id", "chapter_number"],
            name="idx_chapter_book_order",
        ),
    )


def remove_pg_index(apps, schema_editor):
    """回滚：仅在 PostgreSQL 上移除"""
    if connection.vendor != 'postgresql':
        return

    schema_editor.remove_index(
        model=apps.get_model('chapters', 'Chapter'),
        index_name="idx_chapter_book_order",
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("chapters", "0003_alter_chapter_created_at_alter_chapter_title_and_more"),
    ]

    operations = [
        migrations.RunPython(add_pg_index, remove_pg_index),
    ]
