from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.book_list, name='book_list'),
    path('add/', views.book_add, name='book_add'),
    path('<int:pk>/', views.book_detail, name='book_detail'),
    path('<int:pk>/delete/', views.book_delete, name='book_delete'),
]
