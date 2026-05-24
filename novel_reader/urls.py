"""
URL 路由配置模块

该模块定义了小说阅读器项目的顶层 URL 路由规则，负责将不同路径
的请求分发到对应的处理器：
- /admin/ → Django 管理后台
- /api/v1/ → Django Ninja API 接口
- 其他路径 → 前端 SPA 入口（index.html），由前端路由接管

在开发模式下（DEBUG=True），还会额外挂载静态文件服务和 Django
Debug Toolbar 的路由。
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.generic import TemplateView
from apps.ninja_api import api

# 核心路由：管理后台和 API 接口
urlpatterns = [
    path('admin/', admin.site.urls),                       # Django 管理后台入口
    path('api/v1/', api.urls),                             # Django Ninja API v1 接口
]

# 根据运行环境（开发/生产）添加不同的路由规则
if settings.DEBUG:
    # 开发环境：启用调试工具和静态文件服务
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    # 挂载开发环境静态文件 URL（/static/ 前缀）
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        # Django Debug Toolbar 路由
        path('__debug__/', include('debug_toolbar.urls')),
        # 前端 SPA 回退路由：所有不匹配特定前缀的请求都返回 index.html
        # 排除 static/、admin/、api/、__debug__/ 前缀，避免冲突
        re_path(r'^(?!static/|admin/|api/|__debug__/).*$', TemplateView.as_view(template_name='index.html')),
    ]
else:
    # 生产环境：前端 SPA 回退路由
    # 排除 static/、admin/、api/ 前缀，其余请求统一返回 index.html
    # 由前端框架（如 Vue/React Router）处理客户端路由
    urlpatterns += [
        re_path(r'^(?!static/|admin/|api/).*$', TemplateView.as_view(template_name='index.html')),
    ]
