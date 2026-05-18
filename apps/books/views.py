import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Book
from .forms import BookForm


@login_required
def home(request):
    recent_books = Book.objects.all()[:6]
    book_count = Book.objects.count()
    context = {
        'recent_books': recent_books,
        'stats': {
            'book_count': book_count,
            'reading_count': 0,
            'favorite_count': 0,
            'completed_count': 0,
        }
    }
    return render(request, 'home.html', context)


@login_required
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
        'query': query,
    }
    return render(request, 'books/list.html', context)


@login_required
def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    chapters = book.chapters.all()
    context = {
        'book': book,
        'chapters': chapters,
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
            os.makedirs(book.folder_path, exist_ok=True)
            book.save()
            messages.success(request, f'书籍《{book.title}》已添加')
            return redirect('book_list')
    else:
        form = BookForm()

    return render(request, 'books/list.html', {'form': form})


@login_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'书籍《{title}》已删除')
        return redirect('book_list')
    return redirect('book_detail', pk=pk)
