from django.urls import path
from . import views

urlpatterns = [
    path('<int:book_id>/<int:chapter_id>/', views.chapter_read, name='chapter_read'),
    path('<int:book_id>/save-progress/', views.save_progress, name='save_progress'),
    path('track-stats/', views.track_stats, name='track_stats'),
]
