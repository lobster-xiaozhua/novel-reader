from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import TemplateView
from apps.ninja_api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('api/v1/', api.urls),
]

# React SPA fallback - serve index.html for all non-API routes
if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^(?!static/|admin/|api/|accounts/).*$', 
                TemplateView.as_view(template_name='index.html')),
    ]
else:
    # In debug mode, keep Django views alongside React dev server
    urlpatterns += [
        path('books/', include('apps.books.urls')),
        path('chapters/', include('apps.chapters.urls')),
        path('reader/', include('apps.reader.urls')),
        path('favorites/', include('apps.favorites.urls')),
        path('crawler/', include('apps.crawler.urls')),
        path('search/', include('apps.search.urls')),
    ]

if settings.DEBUG:
    urlpatterns += [path('__debug__/', include('debug_toolbar.urls'))]
