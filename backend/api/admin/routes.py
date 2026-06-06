"""API v2 Admin Routes — 后台管理接口"""
import logging

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Query, Router

from ..auth.auth import admin_auth
from ..schemas import ApiResponse, Meta, PaginatedData
from apps.books.models import Book, Tag
from apps.chapters.models import Chapter
from apps.crawler.models import CrawlerTask
from apps.crawler.tasks import run_crawler_task

logger = logging.getLogger(__name__)
router = Router(tags=['admin'], auth=admin_auth)


# ── Books CRUD ──

@router.get('/books', response=ApiResponse[PaginatedData])
def list_books(
    request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    search: str = Query('', description='搜索标题/作者'),
    category: str = Query('', description='分类筛选'),
):
    """书籍列表（分页 + 搜索 + 分类筛选）"""
    qs = Book.objects.prefetch_related('tags').annotate(_ch_count=Count('chapters'))

    query = search.strip()
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(author__icontains=query))
    if category:
        qs = qs.filter(category=category)

    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    books = qs.order_by('-updated_at')[offset:offset + per_page]

    items = [
        {
            'id': b.id, 'title': b.title, 'author': b.author or '',
            'category': b.category or '', 'description': b.description or '',
            'total_chapters': b.total_chapters or 0,
            'chapter_count': getattr(b, '_ch_count', 0),
            'tags': [{'id': t.id, 'name': t.name, 'color': t.color} for t in b.tags.all()],
            'gradient': b.cover_gradient,
            'created_at': b.created_at.isoformat() if b.created_at else '',
            'updated_at': b.updated_at.isoformat() if b.updated_at else '',
        }
        for b in books
    ]
    logger.info(f'[AdminV2] 书籍列表: q="{query}", cat="{category}", page={page}/{total_pages}, total={total}')
    return ApiResponse.ok(
        data={'items': items, 'total': total},
        meta=Meta(page=page, total_pages=total_pages, total_items=total),
    )


@router.get('/books/{book_id}', response=ApiResponse)
def get_book(request, book_id: int):
    """获取书籍详情"""
    book = get_object_or_404(Book.objects.prefetch_related('tags'), id=book_id)
    tags = [{'id': t.id, 'name': t.name, 'color': t.color} for t in book.tags.all()]
    logger.info(f'[AdminV2] 获取书籍: {book.title} (id={book_id})')
    return ApiResponse.ok(data={
        'id': book.id, 'title': book.title, 'author': book.author or '',
        'category': book.category or '', 'description': book.description or '',
        'total_chapters': book.total_chapters or 0,
        'tags': tags, 'gradient': book.cover_gradient,
        'created_at': book.created_at.isoformat() if book.created_at else '',
        'updated_at': book.updated_at.isoformat() if book.updated_at else '',
    })


@router.put('/books/{book_id}', response=ApiResponse)
def update_book(request, book_id: int):
    """更新书籍信息"""
    book = get_object_or_404(Book, id=book_id)
    data = request.json_body if hasattr(request, 'json_body') else {}

    updatable = ['title', 'author', 'category', 'description', 'total_chapters']
    changed = []
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(book, field, data[field])
            changed.append(field)

    if 'cover_gradient' in data and data['cover_gradient'] is not None:
        book.cover_gradient = tuple(data['cover_gradient'])
        changed.append('cover_gradient')

    if changed:
        book.save(update_fields=changed + ['updated_at'])

    if 'tag_ids' in data and isinstance(data['tag_ids'], list):
        book.tags.set(data['tag_ids'])
        changed.append('tags')

    logger.info(f'[AdminV2] 更新书籍: id={book_id}, fields={changed}')
    return ApiResponse.ok(data={'message': '更新成功', 'changed': changed})


@router.delete('/books/{book_id}', response=ApiResponse)
def delete_book(request, book_id: int):
    """删除书籍"""
    book = get_object_or_404(Book, id=book_id)
    title = book.title
    book.delete()
    logger.info(f'[AdminV2] 删除书籍: {title} (id={book_id})')
    return ApiResponse.ok(data={'message': f'已删除《{title}》'})


# ── Chapters CRUD ──

@router.get('/chapters', response=ApiResponse[PaginatedData])
def list_chapters(
    request,
    book_id: int = Query(..., description='书籍ID'),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """章节列表（分页，按书籍筛选）"""
    qs = Chapter.objects.filter(book_id=book_id).order_by('chapter_number')
    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    chapters = qs[offset:offset + per_page]

    items = [
        {
            'id': ch.id, 'chapter_number': ch.chapter_number,
            'title': ch.title, 'word_count': ch.word_count or 0,
            'created_at': ch.created_at.isoformat() if ch.created_at else '',
        }
        for ch in chapters
    ]
    logger.info(f'[AdminV2] 章节列表: book_id={book_id}, page={page}/{total_pages}, total={total}')
    return ApiResponse.ok(
        data={'items': items, 'total': total},
        meta=Meta(page=page, total_pages=total_pages, total_items=total),
    )


@router.get('/chapters/{chapter_id}', response=ApiResponse)
def get_chapter(request, chapter_id: int):
    """获取章节详情（含内容）"""
    chapter = get_object_or_404(Chapter.objects.select_related('book'), id=chapter_id)
    content = chapter.content if hasattr(chapter, 'content') else ''
    logger.info(f'[AdminV2] 获取章节: id={chapter_id}, title={chapter.title}')
    return ApiResponse.ok(data={
        'id': chapter.id, 'chapter_number': chapter.chapter_number,
        'title': chapter.title, 'word_count': chapter.word_count or 0,
        'content': content,
        'book_id': chapter.book_id, 'book_title': chapter.book.title,
        'created_at': chapter.created_at.isoformat() if chapter.created_at else '',
        'updated_at': chapter.updated_at.isoformat() if chapter.updated_at else '',
    })


@router.put('/chapters/{chapter_id}', response=ApiResponse)
def update_chapter(request, chapter_id: int):
    """更新章节标题/内容"""
    chapter = get_object_or_404(Chapter, id=chapter_id)
    data = request.json_body if hasattr(request, 'json_body') else {}

    changed = []
    if 'title' in data and data['title'] is not None:
        chapter.title = data['title']
        changed.append('title')
    if 'content' in data and data['content'] is not None:
        if hasattr(chapter, 'content'):
            chapter.content = data['content']
        changed.append('content')

    if changed:
        chapter.save(update_fields=changed + ['updated_at'])

    logger.info(f'[AdminV2] 更新章节: id={chapter_id}, fields={changed}')
    return ApiResponse.ok(data={'message': '更新成功', 'changed': changed})


@router.delete('/chapters/{chapter_id}', response=ApiResponse)
def delete_chapter(request, chapter_id: int):
    """删除章节"""
    chapter = get_object_or_404(Chapter, id=chapter_id)
    title = chapter.title
    chapter.delete()
    logger.info(f'[AdminV2] 删除章节: {title} (id={chapter_id})')
    return ApiResponse.ok(data={'message': f'已删除章节《{title}》'})


# ── Crawler Tasks ──

@router.get('/crawler', response=ApiResponse)
def list_crawler_tasks(
    request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """爬虫任务列表（分页）"""
    qs = CrawlerTask.objects.order_by('-created_at')
    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    tasks = qs[offset:offset + per_page]

    items = [
        {
            'id': t.id, 'url': t.url or '', 'name': t.name or '',
            'status': t.status, 'progress': getattr(t, 'progress', 0),
            'error': getattr(t, 'error', ''),
            'created_at': t.created_at.isoformat() if t.created_at else '',
            'updated_at': t.updated_at.isoformat() if t.updated_at else '',
        }
        for t in tasks
    ]
    logger.info(f'[AdminV2] 爬虫任务列表: page={page}/{total_pages}, total={total}')
    return ApiResponse.ok(
        data={'items': items, 'total': total},
        meta=Meta(page=page, total_pages=total_pages, total_items=total),
    )


@router.post('/crawler', response=ApiResponse)
def create_crawler_task(
    request,
    url: str = Query(..., description='爬取目标URL'),
):
    """创建爬虫任务并异步调度"""
    task = CrawlerTask.objects.create(url=url, status='pending')
    run_crawler_task.delay(task.id)
    logger.info(f'[AdminV2] 创建爬虫任务: id={task.id}, url={url}')
    return ApiResponse.ok(data={
        'id': task.id, 'url': task.url, 'status': task.status,
        'message': '任务已创建并加入队列',
    })


@router.post('/crawler/{task_id}/stop', response=ApiResponse)
def stop_crawler_task(request, task_id: int):
    """停止爬虫任务"""
    task = get_object_or_404(CrawlerTask, id=task_id)
    task.status = 'stopped'
    task.save(update_fields=['status', 'updated_at'])
    logger.info(f'[AdminV2] 停止爬虫任务: id={task_id}')
    return ApiResponse.ok(data={'message': '任务已停止', 'status': task.status})


# ── Users ──

@router.get('/users', response=ApiResponse[PaginatedData])
def list_users(
    request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    q: str = Query('', description='搜索用户名'),
):
    """用户列表（分页 + 搜索）"""
    qs = User.objects.annotate(_fav_count=Count('favorite'), _progress_count=Count('reading_progress'))

    query = q.strip()
    if query:
        qs = qs.filter(username__icontains=query)

    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    users = qs.order_by('-date_joined')[offset:offset + per_page]

    items = [
        {
            'id': u.id, 'username': u.username, 'email': u.email or '',
            'is_staff': u.is_staff, 'is_superuser': u.is_superuser,
            'favorites': getattr(u, '_fav_count', 0),
            'reading_count': getattr(u, '_progress_count', 0),
            'date_joined': u.date_joined.isoformat() if u.date_joined else '',
            'last_login': u.last_login.isoformat() if u.last_login else '',
        }
        for u in users
    ]
    logger.info(f'[AdminV2] 用户列表: q="{query}", page={page}/{total_pages}, total={total}')
    return ApiResponse.ok(
        data={'items': items, 'total': total},
        meta=Meta(page=page, total_pages=total_pages, total_items=total),
    )


@router.put('/users/{user_id}/role', response=ApiResponse)
def update_user_role(request, user_id: int, is_staff: bool = Query(..., description='是否设为管理员')):
    """更新用户角色"""
    user = get_object_or_404(User, id=user_id)
    user.is_staff = is_staff
    user.save(update_fields=['is_staff'])
    logger.info(f'[AdminV2] 更新用户角色: {user.username} is_staff={is_staff}')
    return ApiResponse.ok(data={
        'id': user.id, 'username': user.username, 'is_staff': user.is_staff,
        'message': f'已{"设为" if is_staff else "取消"}管理员',
    })


# ── Tags ──

@router.get('/tags', response=ApiResponse)
def list_tags(request):
    """标签列表（含书籍计数）"""
    tags = Tag.objects.annotate(book_count=Count('books')).order_by('-book_count', 'name')
    items = [
        {'id': t.id, 'name': t.name, 'color': t.color or '#f59e0b', 'book_count': t.book_count}
        for t in tags
    ]
    logger.info(f'[AdminV2] 标签列表: {len(items)}个标签')
    return ApiResponse.ok(data={'items': items, 'total': len(items)})


@router.post('/tags', response=ApiResponse)
def create_tag(
    request,
    name: str = Query(..., description='标签名称'),
    color: str = Query('#f59e0b', description='标签颜色'),
):
    """创建标签"""
    tag, created = Tag.objects.get_or_create(name=name, defaults={'color': color})
    if not created and tag.color != color:
        tag.color = color
        tag.save(update_fields=['color'])
    logger.info(f'[AdminV2] 创建标签: {name}, color={color}, created={created}')
    return ApiResponse.ok(data={
        'id': tag.id, 'name': tag.name, 'color': tag.color,
        'message': '创建成功' if created else '标签已存在，颜色已更新',
    })


@router.put('/tags/{tag_id}', response=ApiResponse)
def update_tag(request, tag_id: int):
    """更新标签"""
    tag = get_object_or_404(Tag, id=tag_id)
    data = request.json_body if hasattr(request, 'json_body') else {}
    changed = []
    if 'name' in data and data['name'] is not None:
        tag.name = data['name']
        changed.append('name')
    if 'color' in data and data['color'] is not None:
        tag.color = data['color']
        changed.append('color')
    if changed:
        tag.save(update_fields=changed)
    logger.info(f'[AdminV2] 更新标签: id={tag_id}, fields={changed}')
    return ApiResponse.ok(data={'id': tag.id, 'name': tag.name, 'color': tag.color, 'message': '更新成功'})


@router.delete('/tags/{tag_id}', response=ApiResponse)
def delete_tag(request, tag_id: int):
    """删除标签"""
    tag = get_object_or_404(Tag, id=tag_id)
    name = tag.name
    tag.delete()
    logger.info(f'[AdminV2] 删除标签: {name} (id={tag_id})')
    return ApiResponse.ok(data={'message': f'已删除标签「{name}」'})


# ── Monitor ──

@router.get('/monitor/health', response=ApiResponse)
def monitor_health(request):
    """健康检查：数据库 + 缓存"""
    db_ok = False
    cache_ok = False
    try:
        Book.objects.exists()
        db_ok = True
    except Exception as exc:
        logger.error(f'[AdminV2] 数据库健康检查失败: {exc}')

    try:
        cache.set('v2:admin:health_check', 'ok', 10)
        cache_ok = cache.get('v2:admin:health_check') == 'ok'
    except Exception as exc:
        logger.error(f'[AdminV2] 缓存健康检查失败: {exc}')

    healthy = db_ok and cache_ok
    logger.info(f'[AdminV2] 健康检查: db={db_ok}, cache={cache_ok}, healthy={healthy}')
    return ApiResponse.ok(data={
        'status': 'healthy' if healthy else 'unhealthy',
        'database': db_ok, 'cache': cache_ok,
        'timestamp': timezone.now().isoformat(),
    })


@router.get('/monitor/perf', response=ApiResponse)
def monitor_perf(request):
    """性能概览：各实体计数 + 时间戳"""
    now = timezone.now()
    try:
        book_count = Book.objects.count()
        chapter_count = Chapter.objects.count()
        user_count = User.objects.count()
        tag_count = Tag.objects.count()
    except Exception as exc:
        logger.error(f'[AdminV2] 性能统计查询失败: {exc}')
        return ApiResponse.fail(error=f'查询失败: {exc}')

    logger.info(f'[AdminV2] 性能概览: books={book_count}, chapters={chapter_count}, users={user_count}, tags={tag_count}')
    return ApiResponse.ok(data={
        'books': book_count,
        'chapters': chapter_count,
        'users': user_count,
        'tags': tag_count,
        'timestamp': now.isoformat(),
    })