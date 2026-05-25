from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import TemplateView
from apps.api.router import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', api.urls),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
        re_path(r'^(?!static/|admin/|api/|__debug__/).*$', TemplateView.as_view(template_name='index.html')),
    ]
else:
    urlpatterns += [
        re_path(r'^(?!static/|admin/|api/).*$', TemplateView.as_view(template_name='index.html')),
    ]
