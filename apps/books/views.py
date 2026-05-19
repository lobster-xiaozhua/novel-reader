import os
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Book
from .forms import BookForm

logger = logging.getLogger(__name__)


def home(request):
    try:
        from apps.reader.models import ReadingProgress
        from apps.favorites.models import Favorite

        recent_books = Book.objects.all()[:6]
        book_count = Book.objects.count()
        
        if request.user.is_authenticated:
            reading_count = ReadingProgress.objects.filter(user=request.user).count()
            favorite_count = Favorite.objects.filter(user=request.user).count()
        else:
            reading_count = 0
            favorite_count = 0
        
        context = {
            'recent_books': recent_books,
            'total_books': book_count,
            'reading_count': reading_count,
            'favorite_count': favorite_count,
            'completed_count': 0,
        }
    except Exception as e:
        logger.warning(f'[Home] 数据加载异常: {e}')
        context = {
            'recent_books': [],
            'total_books': 0,
            'reading_count': 0,
            'favorite_count': 0,
            'completed_count': 0,
        }
    
    return render(request, 'home.html', context)


def book_list(request):
    query = request.GET.get('q', '')
    books = Book.objects.all()
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))

    paginator = Paginator(books, 12)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)

    context = {
        'page_obj': page_obj,
        'books': page_obj,
        'search_query': query,
    }
    return render(request, 'books/list.html', context)


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    chapters = book.chapters.all()
    
    is_favorited = False
    if request.user.is_authenticated:
        try:
            from apps.favorites.models import Favorite
            is_favorited = Favorite.objects.filter(user=request.user, book=book).exists()
        except Exception:
            pass
    
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
