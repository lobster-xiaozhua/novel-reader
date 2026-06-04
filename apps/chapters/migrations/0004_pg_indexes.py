# Add concurrent index for chapters_chapter (book_id, chapter_number)
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("chapters", "0003_alter_chapter_created_at_alter_chapter_title_and_more"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="chapter",
            index=models.Index(
                fields=["book_id", "chapter_number"],
                name="idx_chapter_book_order",
            ),
        ),
    ]
