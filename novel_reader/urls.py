from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from apps.books.views import home
from apps.ninja_api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('accounts/', include('apps.accounts.urls')),
    path('books/', include('apps.books.urls')),
    path('chapters/', include('apps.chapters.urls')),
    path('reader/', include('apps.reader.urls')),
    path('favorites/', include('apps.favorites.urls')),
    path('crawler/', include('apps.crawler.urls')),
    path('search/', include('apps.search.urls')),
    path('api/v1/', api.urls),
]

if settings.DEBUG:
    urlpatterns += [path('__debug__/', include('debug_toolbar.urls'))]
