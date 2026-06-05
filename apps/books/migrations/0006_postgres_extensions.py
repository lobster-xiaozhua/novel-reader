# Add PostgreSQL extensions (Trigram, BtreeGin) - PostgreSQL only
from django.db import migrations, connection
from django.db import models as django_models


def add_postgres_extensions(apps, schema_editor):
    """仅在 PostgreSQL 上添加扩展和索引"""
    if connection.vendor != 'postgresql':
        return

    # 添加扩展
    from django.contrib.postgres.operations import TrigramExtension, BtreeGinExtension
    TrigramExtension().database_forwards(
        'books', schema_editor, state=None, project_state=None
    )
    BtreeGinExtension().database_forwards(
        'books', schema_editor, state=None, project_state=None
    )

    # 添加 GIN 索引
    from django.contrib.postgres.indexes import GinIndex
    schema_editor.add_index(
        model=apps.get_model('books', 'Book'),
        index=GinIndex(
            fields=["title", "author", "description"],
            name="book_search_gin_idx",
        ),
    )


def remove_postgres_extensions(apps, schema_editor):
    """回滚：仅在 PostgreSQL 上移除"""
    if connection.vendor != 'postgresql':
        return
    # 回滚逻辑（如有需要）


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("books", "0005_alter_book_updated_at_alter_tag_name"),
    ]

    operations = [
        migrations.RunPython(add_postgres_extensions, remove_postgres_extensions),
    ]
