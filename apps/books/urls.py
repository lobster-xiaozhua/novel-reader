from django.urls import path
from . import views

urlpatterns = [
    path('batch-import/', views.batch_import, name='batch_import'),
    path('reading-stats/', views.reading_stats_api, name='reading_stats_api'),
]
