from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from apps.books.models import Book
from .models import Favorite


@login_required
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('book')
    return JsonResponse({
        'items': [{
            'id': f.id,
            'book_id': f.book_id,
            'title': f.book.title,
            'author': f.book.author,
            'category': f.book.category,
            'total_chapters': f.book.total_chapters,
            'created_at': f.created_at.isoformat(),
        } for f in favorites],
        'total': favorites.count(),
    })


@login_required
@require_POST
def favorite_toggle(request):
    import json
    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
    book_id = data.get('book_id')
    book = Book.objects.get(pk=book_id)

    favorite = Favorite.objects.filter(user=request.user, book=book).first()
    if favorite:
        favorite.delete()
        return JsonResponse({'success': True, 'message': f'已取消收藏《{book.title}》'})
    Favorite.objects.create(user=request.user, book=book)
    return JsonResponse({'success': True, 'message': f'已收藏《{book.title}》'})
