import logging

from django.contrib.auth.models import User
from django.db.models import Count as DbCount
from ninja import Router
from ninja.pagination import paginate

from .auth import jwt_auth
from .schemas import UserSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get('/users/', response=list[UserSchema], auth=jwt_auth)
@paginate
def list_users(request):
    qs = User.objects.annotate(book_count=DbCount('readingprogress')).all()
    return [{
        'id': u.id,
        'username': u.username,
        'email': u.email or '',
        'is_staff': u.is_staff,
        'date_joined': u.date_joined.isoformat(),
        'last_login': u.last_login.isoformat() if u.last_login else None,
        'book_count': u.book_count,
    } for u in qs]
