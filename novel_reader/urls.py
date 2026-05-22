from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.views.generic import TemplateView
from apps.ninja_api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
]

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
        re_path(r'^(?!static/|admin/|api/|__debug__/).*$', TemplateView.as_view(template_name='index.html')),
    ]
else:
    urlpatterns += [
        re_path(r'^(?!static/|admin/|api/).*$', TemplateView.as_view(template_name='index.html')),
    ]
