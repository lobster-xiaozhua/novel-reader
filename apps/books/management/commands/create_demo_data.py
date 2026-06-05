"""创建演示数据的 Django 管理命令"""
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from apps.books.models import Book, Tag
from apps.chapters.models import Chapter

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '创建演示数据（用户、标签、书籍、章节）'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始创建演示数据...'))

        # 1. 创建演示账号
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True},
        )
        if not admin_user.has_usable_password():
            admin_user.set_password('admin123')
            admin_user.save()

        demo_user, _ = User.objects.get_or_create(
            username='demo',
            defaults={'email': 'demo@example.com', 'is_staff': False},
        )
        if not demo_user.has_usable_password():
            demo_user.set_password('demo123')
            demo_user.save()
        self.stdout.write(f'  - 用户账号: demo / demo123 | admin / admin123')

        # 2. 创建标签
        tag_names_colors = [
            ('玄幻', '#f59e0b'),
            ('武侠', '#ef4444'),
            ('言情', '#ec4899'),
            ('科幻', '#3b82f6'),
            ('历史', '#10b981'),
            ('悬疑', '#8b5cf6'),
        ]
        tags = []
        for name, color in tag_names_colors:
            tag, _ = Tag.objects.get_or_create(name=name, defaults={'color': color})
            tags.append(tag)
        self.stdout.write(f'  - 标签: {len(tags)}个')

        # 3. 创建示例书籍
        demo_books = [
            {
                'title': '完美世界',
                'author': '辰东',
                'category': '玄幻',
                'description': '一粒尘可填海，一根草斩落星空，弹指间诸天万界灰飞烟灭。',
                'cover_gradient': ('#f59e0b', '#ef4444'),
                'tags': ['玄幻', '武侠'],
                'chapters': 300,
            },
            {
                'title': '遮天',
                'author': '辰东',
                'category': '玄幻',
                'description': '冰冷与黑暗并存的宇宙深处，九龙拉棺，引动天地风云，开启一个不可知的玄幻世界。',
                'cover_gradient': ('#8b5cf6', '#3b82f6'),
                'tags': ['玄幻', '科幻'],
                'chapters': 1825,
            },
            {
                'title': '斗破苍穹',
                'author': '天蚕土豆',
                'category': '玄幻',
                'description': '三十年河东，三十年河西，莫欺少年穷！',
                'cover_gradient': ('#ef4444', '#f59e0b'),
                'tags': ['玄幻', '历史'],
                'chapters': 1648,
            },
            {
                'title': '斗罗大陆',
                'author': '唐家三少',
                'category': '玄幻',
                'description': '这里没有魔法，没有斗气，没有武术，却有神奇的武魂。',
                'cover_gradient': ('#10b981', '#3b82f6'),
                'tags': ['玄幻', '武侠'],
                'chapters': 336,
            },
            {
                'title': '凡人修仙传',
                'author': '忘语',
                'category': '玄幻',
                'description': '凡人流开山之作，讲述一个普通山村少年的修仙之路。',
                'cover_gradient': ('#ec4899', '#8b5cf6'),
                'tags': ['玄幻', '悬疑'],
                'chapters': 2447,
            },
        ]

        created_books = 0
        created_chapters = 0
        for book_data in demo_books:
            book_tags = [t for t in tags if t.name in book_data.pop('tags')]
            chapter_count = book_data.pop('chapters')
            book, created = Book.objects.get_or_create(
                title=book_data['title'],
                author=book_data['author'],
                defaults={**book_data, 'total_chapters': chapter_count},
            )
            if created:
                created_books += 1
            book.tags.add(*book_tags)

            # 创建章节
            existing = Chapter.objects.filter(book=book).count()
            if existing == 0:
                for i in range(1, min(10, chapter_count) + 1):
                    Chapter.objects.create(
                        book=book,
                        chapter_number=i,
                        title=f'第{i}章 初始章节',
                        content=f'这是《{book.title}》第{i}章的内容。\n\n'
                                f'精彩故事由此展开...\n\n'
                                f'（本章节为演示数据，后续内容可通过爬虫获取）',
                        word_count=120 + i * 30,
                    )
                    created_chapters += 1

        self.stdout.write(f'  - 书籍: {created_books}本（共{Book.objects.count()}本）')
        self.stdout.write(f'  - 章节: {created_chapters}章（共{Chapter.objects.count()}章）')
        self.stdout.write(self.style.SUCCESS('演示数据创建完毕！'))
