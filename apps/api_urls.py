from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .api import BookViewSet, ReadingProgressViewSet, CrawlerTaskViewSet, user_stats

router = DefaultRouter()
router.register(r'books', BookViewSet)
router.register(r'progress', ReadingProgressViewSet, basename='progress')
router.register(r'crawler', CrawlerTaskViewSet, basename='crawler')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', user_stats, name='api_user_stats'),
    path('auth/', obtain_auth_token, name='api_auth'),
]
