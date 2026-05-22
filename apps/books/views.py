import os
import re
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Book, Tag
from apps.reader.models import ReadingProgress, ReadingStats
from apps.favorites.models import Favorite

logger = logging.getLogger(__name__)


@login_required
@require_POST
def batch_import(request):
    files = request.FILES.getlist('files')
    if not files:
        return JsonResponse({'success': False, 'error': '未选择文件'}, status=400)

    imported = 0
    errors = []
    for f in files:
        if not f.name.endswith('.txt'):
            errors.append(f'{f.name}: 仅支持txt格式')
            continue
        try:
            raw = f.read()
            for enc in ('utf-8', 'gbk', 'gb2312'):
                try:
                    text = raw.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                errors.append(f'{f.name}: 编码无法识别')
                continue

            title = os.path.splitext(f.name)[0].strip()
            if not title:
                errors.append(f'{f.name}: 无法提取书名')
                continue

            book, created = Book.objects.get_or_create(
                title=title,
                defaults={
                    'author': '',
                    'folder_path': os.path.join('data/books', re.sub(r'[\\/:*?"<>|]', '_', title)[:100]),
                }
            )
            if not created and book.chapters.exists():
                errors.append(f'{title}: 已存在')
                continue

            book_dir = os.path.join('data/books', re.sub(r'[\\/:*?"<>|]', '_', title)[:100])
            os.makedirs(book_dir, exist_ok=True)
            if not book.folder_path:
                book.folder_path = book_dir
                book.save()

            chapter_pattern = re.compile(
                r'^(第[零一二三四五六七八九十百千万\d]+章|chapter\s*\d+|第\d+章|卷[零一二三四五六七八九十百千万\d]+)',
                re.IGNORECASE | re.MULTILINE
            )
            parts = chapter_pattern.split(text)

            chapters_data = []
            if len(parts) > 1:
                i = 1
                while i < len(parts):
                    ch_title = parts[i].strip()
                    ch_content = parts[i + 1].strip() if i + 1 < len(parts) else ''
                    if ch_title:
                        chapters_data.append((ch_title, ch_content))
                    i += 2
            else:
                paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                chunk_size = max(1, len(paragraphs) // max(1, len(paragraphs) // 50))
                for idx in range(0, len(paragraphs), chunk_size):
                    chunk = paragraphs[idx:idx + chunk_size]
                    ch_num = idx // chunk_size + 1
                    chapters_data.append((f'第{ch_num}章', '\n'.join(chunk)))

            for idx, (ch_title, ch_content) in enumerate(chapters_data, 1):
                ch_filename = f'第{idx}章.txt'
                ch_path = os.path.join(book_dir, ch_filename)
                with open(ch_path, 'w', encoding='utf-8') as wf:
                    wf.write(f'{ch_title}\n\n{ch_content}')
                from apps.chapters.models import Chapter
                Chapter.objects.update_or_create(
                    book=book, chapter_number=idx,
                    defaults={'title': ch_title, 'file_path': ch_path, 'word_count': len(ch_content)}
                )

            book.total_chapters = len(chapters_data)
            book.save()
            imported += 1
            logger.info(f'[BatchImport] 导入成功: {title} ({len(chapters_data)}章)')

        except Exception as e:
            logger.error(f'[BatchImport] 导入失败 {f.name}: {e}')
            errors.append(f'{f.name}: {str(e)[:100]}')

    return JsonResponse({
        'success': True,
        'imported': imported,
        'errors': errors,
        'total': len(files),
    })


@login_required
def reading_stats_api(request):
    today = timezone.now().date()
    user = request.user
    days = int(request.GET.get('days', 7))
    from datetime import timedelta
    start = today - timedelta(days=days - 1)

    stats = ReadingStats.objects.filter(user=user, date__gte=start).values('date', 'read_seconds', 'chapters_read', 'words_read')
    stats_map = {s['date']: s for s in stats}

    result = []
    current = start
    while current <= today:
        s = stats_map.get(current, {'date': current, 'read_seconds': 0, 'chapters_read': 0, 'words_read': 0})
        result.append({
            'date': current.isoformat(),
            'minutes': round(s.get('read_seconds', 0) / 60, 1),
            'chapters': s.get('chapters_read', 0),
            'words': s.get('words_read', 0),
        })
        current += timedelta(days=1)

    return JsonResponse({'stats': result})
