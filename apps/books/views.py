import os
import re
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils import timezone
from .models import Book, Tag
from .forms import BookForm, BatchImportForm
from apps.reader.models import ReadingProgress, ReadingStats
from apps.favorites.models import Favorite

logger = logging.getLogger(__name__)


@cache_page(60)
def home(request):
    try:
        recent_books = Book.objects.prefetch_related('chapters', 'tags').order_by('-created_at')[:6]
        stats = Book.objects.aggregate(book_count=Count('id'))

        if request.user.is_authenticated:
            reading_count = ReadingProgress.objects.filter(user=request.user).count()
            favorite_count = Favorite.objects.filter(user=request.user).count()
            today = timezone.now().date()
            today_stats = ReadingStats.objects.filter(user=request.user, date=today).first()
            today_chapters = today_stats.chapters_read if today_stats else 0
            week_start = today - timezone.timedelta(days=today.weekday())
            week_stats = ReadingStats.objects.filter(user=request.user, date__gte=week_start)
            week_chapters = sum(s.chapters_read for s in week_stats)
            total_words = sum(s.words_read for s in ReadingStats.objects.filter(user=request.user))
            streak = _calc_streak(request.user)
        else:
            reading_count = 0
            favorite_count = 0
            today_chapters = 0
            week_chapters = 0
            total_words = 0
            streak = 0

        context = {
            'recent_books': recent_books,
            'total_books': stats['book_count'],
            'reading_count': reading_count,
            'favorite_count': favorite_count,
            'completed_count': 0,
            'today_read': today_chapters,
            'week_read': week_chapters,
            'total_words': f'{total_words // 10000}万' if total_words >= 10000 else str(total_words),
            'read_days': streak,
        }
    except Exception as e:
        logger.warning(f'[Home] 数据加载异常: {e}')
        context = {
            'recent_books': [], 'total_books': 0, 'reading_count': 0,
            'favorite_count': 0, 'completed_count': 0,
            'today_read': 0, 'week_read': 0, 'total_words': '0', 'read_days': 0,
        }

    return render(request, 'home.html', context)


def _calc_streak(user):
    from datetime import timedelta
    today = timezone.now().date()
    streak = 0
    check_date = today
    for _ in range(365):
        if ReadingStats.objects.filter(user=user, date=check_date, read_seconds__gt=0).exists():
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak


@cache_page(30)
def book_list(request):
    query = request.GET.get('q', '')
    tag = request.GET.get('tag', '')
    cat = request.GET.get('cat', '')
    sort = request.GET.get('sort', 'created_at')
    order = request.GET.get('order', 'desc')

    books = Book.objects.prefetch_related('chapters', 'tags').all()
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))
    if tag:
        books = books.filter(tags__name=tag)
    if cat:
        books = books.filter(category=cat)

    sort_field = sort if sort in ('title', 'author', 'created_at', 'total_chapters') else 'created_at'
    if order == 'asc':
        books = books.order_by(sort_field)
    else:
        books = books.order_by(f'-{sort_field}')

    paginator = Paginator(books, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    all_tags = Tag.objects.annotate(book_count=Count('books')).filter(book_count__gt=0)

    context = {
        'page_obj': page_obj,
        'books': page_obj,
        'search_query': query,
        'current_tag': tag,
        'current_cat': cat,
        'all_tags': all_tags,
    }
    return render(request, 'books/list.html', context)


def book_detail(request, pk):
    book = get_object_or_404(Book.objects.select_related().prefetch_related('chapters', 'tags'), pk=pk)
    chapters = book.chapters.all()

    is_favorited = False
    if request.user.is_authenticated:
        cache_key = f'fav:{request.user.id}:{book.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            is_favorited = cached
        else:
            is_favorited = Favorite.objects.filter(user=request.user, book=book).exists()
            cache.set(cache_key, is_favorited, 60)

    context = {
        'book': book,
        'chapters': chapters,
        'is_favorited': is_favorited,
        'user': request.user,
    }
    return render(request, 'books/detail.html', context)


@login_required
def book_add(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save(commit=False)
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in book.title)
            book.folder_path = os.path.join('data/books', safe_name.strip())
            try:
                os.makedirs(book.folder_path, exist_ok=True)
            except OSError as e:
                logger.error(f'创建书籍目录失败: {e}')
                messages.error(request, '创建书籍目录失败，请检查书名')
                return redirect('book_list')
            book.save()
            form.save_m2m()
            messages.success(request, f'书籍《{book.title}》已添加')
            return redirect('book_list')
        else:
            messages.error(request, '请填写正确的书名')
            return redirect('book_list')
    return redirect('book_list')


@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'书籍《{title}》已删除')
        return redirect('book_list')
    return redirect('book_detail', pk=pk)


@login_required
@require_POST
def batch_import(request):
    form = BatchImportForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'success': False, 'error': '请选择有效的txt文件'}, status=400)

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
