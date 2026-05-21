import logging
from django.utils import timezone
from rest_framework import serializers, viewsets, generics, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from apps.books.models import Book, Tag
from apps.chapters.models import Chapter
from apps.reader.models import ReadingProgress, ReadingStats
from apps.favorites.models import Favorite
from apps.crawler.models import CrawlerTask

logger = logging.getLogger(__name__)


class TagSerializer(serializers.ModelSerializer):
    book_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'book_count']


class BookListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    gradient = serializers.SerializerMethodField()
    chapter_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'category', 'description', 'total_chapters',
                  'chapter_count', 'tags', 'gradient', 'created_at', 'updated_at']

    def get_gradient(self, obj):
        return obj.cover_gradient


class BookDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    gradient = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    reading_progress = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = ['id', 'title', 'author', 'category', 'description', 'total_chapters',
                  'tags', 'gradient', 'is_favorited', 'reading_progress',
                  'created_at', 'updated_at']

    def get_gradient(self, obj):
        return obj.cover_gradient

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Favorite.objects.filter(user=user, book=obj).exists()
        return False

    def get_reading_progress(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            progress = ReadingProgress.objects.filter(user=user, book=obj).first()
            if progress:
                return {'chapter_id': progress.chapter_id, 'position': progress.position}
        return None


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['id', 'chapter_number', 'title', 'word_count']


class ChapterContentSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'chapter_number', 'title', 'word_count', 'content']

    def get_content(self, obj):
        import os
        from django.core.cache import cache
        cache_key = f'chapter_content:{obj.id}'
        content = cache.get(cache_key)
        if content is not None:
            return content
        if not os.path.exists(obj.file_path):
            return ''
        for enc in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
            try:
                with open(obj.file_path, 'r', encoding=enc) as f:
                    content = f.read()
                cache.set(cache_key, content, 300)
                return content
            except (UnicodeDecodeError, Exception):
                continue
        return ''


class ReadingProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingProgress
        fields = ['id', 'book', 'chapter', 'position', 'updated_at']


class ReadingStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingStats
        fields = ['date', 'read_seconds', 'chapters_read', 'words_read']


class CrawlerTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrawlerTask
        fields = ['id', 'url', 'status', 'total_chapters', 'downloaded_chapters',
                  'error_message', 'created_at', 'updated_at']
        read_only_fields = ['status', 'total_chapters', 'downloaded_chapters', 'error_message']


class BookViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Book.objects.prefetch_related('chapters', 'tags').all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    search_fields = ['title', 'author']
    ordering_fields = ['title', 'author', 'created_at', 'total_chapters']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BookDetailSerializer
        return BookListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        tag = self.request.query_params.get('tag')
        cat = self.request.query_params.get('category')
        if tag:
            qs = qs.filter(tags__name=tag)
        if cat:
            qs = qs.filter(category=cat)
        return qs

    @action(detail=True, methods=['get'])
    def chapters(self, request, pk=None):
        book = self.get_object()
        chapters = book.chapters.all()
        serializer = ChapterSerializer(chapters, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='chapters/(?P<ch_pk>[^/.]+)')
    def chapter_detail(self, request, pk=None, ch_pk=None):
        book = self.get_object()
        try:
            chapter = book.chapters.get(pk=ch_pk)
        except Chapter.DoesNotExist:
            return Response({'detail': '章节不存在'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ChapterContentSerializer(chapter)
        return Response(serializer.data)


class ReadingProgressViewSet(viewsets.ModelViewSet):
    serializer_class = ReadingProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReadingProgress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CrawlerTaskViewSet(viewsets.ModelViewSet):
    serializer_class = CrawlerTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CrawlerTask.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        task = serializer.save(user=self.request.user)
        from apps.crawler.tasks import run_crawler_task
        run_crawler_task.delay(task.id)
        logger.info(f'[API] 创建爬虫任务: {task.id}')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_stats(request):
    user = request.user
    today = timezone.now().date()
    from datetime import timedelta

    total_books = Book.objects.count()
    reading_count = ReadingProgress.objects.filter(user=user).count()
    favorite_count = Favorite.objects.filter(user=user).count()

    today_stats = ReadingStats.objects.filter(user=user, date=today).first()
    week_start = today - timedelta(days=today.weekday())
    week_stats = ReadingStats.objects.filter(user=user, date__gte=week_start)
    week_chapters = sum(s.chapters_read for s in week_stats)
    total_words = sum(s.words_read for s in ReadingStats.objects.filter(user=user))

    days = int(request.query_params.get('days', 7))
    start = today - timedelta(days=days - 1)
    daily_stats = ReadingStats.objects.filter(user=user, date__gte=start)
    stats_map = {s.date: s for s in daily_stats}

    chart = []
    current = start
    while current <= today:
        s = stats_map.get(current)
        chart.append({
            'date': current.isoformat(),
            'minutes': round(s.read_seconds / 60, 1) if s else 0,
            'chapters': s.chapters_read if s else 0,
            'words': s.words_read if s else 0,
        })
        current += timedelta(days=1)

    return Response({
        'total_books': total_books,
        'reading_count': reading_count,
        'favorite_count': favorite_count,
        'today_chapters': today_stats.chapters_read if today_stats else 0,
        'today_minutes': round(today_stats.read_seconds / 60, 1) if today_stats else 0,
        'week_chapters': week_chapters,
        'total_words': total_words,
        'chart': chart,
    })
