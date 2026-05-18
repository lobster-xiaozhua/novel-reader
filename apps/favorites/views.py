from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.books.models import Book
from .models import Favorite


@login_required
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('book')
    return render(request, 'favorites/list.html', {'favorites': favorites})


@login_required
@require_POST
def favorite_toggle(request):
    book_id = request.POST.get('book_id')
    book = get_object_or_404(Book, pk=book_id)

    favorite = Favorite.objects.filter(user=request.user, book=book).first()
    if favorite:
        favorite.delete()
        messages.success(request, f'已取消收藏《{book.title}》')
    else:
        Favorite.objects.create(user=request.user, book=book)
        messages.success(request, f'已收藏《{book.title}》')

    next_url = request.POST.get('next', 'book_list')
    if next_url.startswith('/'):
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(next_url)
    try:
        return redirect(next_url)
    except Exception:
        return redirect('book_detail', pk=book_id)
