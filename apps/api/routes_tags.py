import logging

from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate

from apps.books.models import Tag

from .auth import jwt_auth, optional_jwt_auth
from .schemas import MessageSchema, TagIn, TagListSchema

logger = logging.getLogger(__name__)
router = Router()


@router.get('/tags/', response=list[TagListSchema], auth=optional_jwt_auth)
@paginate
def list_tags(request):
    qs = Tag.objects.all()
    return [{
        'id': t.id,
        'name': t.name,
        'color': t.color,
        'book_count': t.books.count(),
    } for t in qs]


@router.post('/tags/', response=TagListSchema, auth=jwt_auth)
def create_tag(request, payload: TagIn) -> dict:
    tag = Tag.objects.create(name=payload.name, color=payload.color)
    logger.info(f'[Tag] 创建标签: {tag.name}')
    return {'id': tag.id, 'name': tag.name, 'color': tag.color, 'book_count': 0}


@router.delete('/tags/{tag_id}/', response=MessageSchema, auth=jwt_auth)
def delete_tag(request, tag_id: int) -> dict:
    tag = get_object_or_404(Tag, id=tag_id)
    tag_name = tag.name
    tag.delete()
    logger.info(f'[Tag] 删除标签: {tag_name}')
    return {'message': '删除成功'}
