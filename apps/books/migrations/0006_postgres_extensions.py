# Add PostgreSQL extensions (Trigram, BtreeGin)
from django.contrib.postgres.operations import (
    BtreeGinExtension,
    TrigramExtension,
    AddIndexConcurrently,
)
from django.db import migrations
from django.contrib.postgres.indexes import GinIndex


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("books", "0005_alter_book_updated_at_alter_tag_name"),
    ]

    operations = [
        # PostgreSQL extensions
        TrigramExtension(),
        BtreeGinExtension(),

        # books_book: GIN index for full-text search
        AddIndexConcurrently(
            model_name="book",
            index=GinIndex(
                fields=["title", "author", "description"],
                name="book_search_gin_idx",
            ),
        ),
    ]
