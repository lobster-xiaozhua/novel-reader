import logging

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate

from apps.books.models import Book
from apps.favorites.models import Favorite

from .auth import jwt_auth
from .schemas import FavoriteSchema, FavoriteToggleIn, MessageSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get('/favorites/', response=list[FavoriteSchema], auth=jwt_auth)
@paginate
def list_favorites(request):
    qs = Favorite.objects.filter(user=request.user).select_related('book')
    return [{
        'id': f.id,
        'book_id': f.book_id,
        'title': f.book.title,
        'author': f.book.author,
        'category': f.book.category,
        'total_chapters': f.book.total_chapters,
        'created_at': f.created_at.isoformat(),
    } for f in qs]


@router.post('/favorites/toggle/', response=MessageSchema, auth=jwt_auth)
def toggle_favorite(request, payload: FavoriteToggleIn) -> dict:
    book = get_object_or_404(Book, id=payload.book_id)
    fav = Favorite.objects.filter(user=request.user, book=book).first()
    if fav:
        fav.delete()
        logger.info(f'[Favorite] 取消收藏: {book.title}')
        return {'message': '已取消收藏'}
    Favorite.objects.create(user=request.user, book=book)
    logger.info(f'[Favorite] 添加收藏: {book.title}')
    return {'message': '已收藏'}
