from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.books.views import home

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
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
