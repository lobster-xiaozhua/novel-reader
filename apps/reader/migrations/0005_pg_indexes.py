# Add concurrent index for reader_readingprogress (user_id, book_id, updated_at)
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("reader", "0004_alter_readingprogress_updated_at_and_more"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="readingprogress",
            index=models.Index(
                fields=["user_id", "book_id", "updated_at"],
                name="idx_progress_user_book",
            ),
        ),
    ]
