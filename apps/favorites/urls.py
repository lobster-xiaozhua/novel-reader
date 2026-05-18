from django.urls import path
from . import views

urlpatterns = [
    path('', views.favorite_list, name='favorite_list'),
    path('toggle/', views.favorite_toggle, name='favorite_toggle'),
]
