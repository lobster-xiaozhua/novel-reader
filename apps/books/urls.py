from django.urls import path
from . import views
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda r: redirect('book_list'), name='books_index'),
    path('list/', views.book_list, name='book_list'),
    path('add/', views.book_add, name='book_add'),
    path('batch-import/', views.batch_import, name='batch_import'),
    path('reading-stats/', views.reading_stats_api, name='reading_stats_api'),
    path('<int:pk>/', views.book_detail, name='book_detail'),
    path('<int:pk>/delete/', views.book_delete, name='book_delete'),
]
