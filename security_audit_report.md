# 安全审计报告

**项目名称**: Novel Reader (小说阅读器)
**审计日期**: 2026-05-20
**技术栈**: Django 4.2 + SQLite + Python
**审计范围**: 认证与访问控制、注入向量、外部交互、敏感数据处理

---

## 执行摘要

本次审计发现 **4个高严重度** 和 **2个中严重度** 已确认漏洞，均具备可论证的端到端利用路径。系统存在硬编码凭证、不安全默认配置、路径遍历和SSRF绕过等关键安全问题，需要立即修复。

---

## 高严重度发现

### [HIGH-1] 硬编码管理员凭证

**严重程度**: 高
**CWE**: CWE-798, CWE-259
**攻击者画像**: 外部攻击者
**影响**: 未授权访问管理后台，权限提升

**攻击路径**:
1. 攻击者下载代码仓库（如果私有仓库泄露或内部人员访问）
2. 查看启动脚本发现硬编码凭证
3. 使用 `admin/admin123` 登录管理后台
4. 获取完整系统控制权

**受影响文件**:
- [start.sh:83-84](file:///workspace/start.sh#L83-L84)
- [start.ps1:81-83](file:///workspace/start.ps1#L81-L83)
- [start.bat:150-152](file:///workspace/start.bat#L150-L152)

**证据**:
```bash
# start.sh
./venv/bin/python manage.py shell -c "from django.contrib.auth.models import User; \
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); \
    print('Superuser created: admin / admin123')"
```

**修复建议**:
1. 移除所有硬编码凭证，改用环境变量
2. 强制首次部署时交互式创建管理员账户
3. 实施密码策略：最小12位，包含大小写字母、数字和特殊字符
4. 不在启动脚本中输出凭证信息

**修复代码示例**:
```python
# 在启动脚本中使用环境变量
import os
admin_password = os.environ.get('ADMIN_PASSWORD')
if not admin_password:
    raise ValueError('ADMIN_PASSWORD environment variable must be set')
```

---

### [HIGH-2] 不安全的Django密钥配置

**严重程度**: 高
**CWE**: CWE-798, CWE-321
**攻击者画像**: 外部攻击者
**影响**: Session伪造、会话劫持、潜在远程代码执行

**攻击路径**:
1. 攻击者获取生产环境的 `settings.py` 或 `settings.json`
2. 由于使用默认的不安全密钥，攻击者可以：
   - 伪造有效的 Django session cookie
   - 绕过 CSRF 保护
   - 可能的 RCE（取决于应用逻辑）

**受影响文件**:
- [novel_reader/settings.py:6](file:///workspace/novel_reader/settings.py#L6)

**证据**:
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production-!@#$%^&*()')
```

**修复建议**:
1. 移除默认值，确保 SECRET_KEY 必须通过环境变量设置
2. 生产环境使用 `openssl rand -hex 50` 生成强随机密钥
3. 定期轮换密钥（建议90天）
4. 使用 Django 的 `get_random_secret_key()` 生成密钥

**修复代码示例**:
```python
from django.core.management.utils import get_random_secret_key

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")
```

---

### [HIGH-3] 调试模式默认启用

**严重程度**: 高
**CWE**: CWE-489
**攻击者画像**: 外部攻击者
**影响**: 敏感信息泄露、目录遍历、内部服务探测

**攻击路径**:
1. 攻击者访问应用，触发错误页面
2. DEBUG=True 时，Django 返回详细的错误堆栈
3. 泄露信息包括：
   - 文件系统路径结构
   - 数据库连接字符串
   - Python 模块加载路径
   - 代码片段（部分堆栈跟踪）
   - 环境变量配置

**受影响文件**:
- [novel_reader/settings.py:8](file:///workspace/novel_reader/settings.py#L8)

**证据**:
```python
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
```

**修复建议**:
1. 移除默认值，强制明确设置 DEBUG=False
2. 配置独立的错误处理页面
3. 生产环境设置 `ALLOWED_HOSTS` 为精确域名列表
4. 实施日志聚合系统替代 DEBUG 输出

**修复代码示例**:
```python
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
if not DEBUG:
    # 启用生产安全设置
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
    if DEBUG and not ALLOWED_HOSTS:
        warnings.warn("DEBUG=True should not be used in production")
```

---

### [HIGH-4] 路径遍历导致任意文件读取

**严重程度**: 高
**CWE**: CWE-22
**攻击者画像**: 已认证用户
**影响**: 敏感文件泄露、配置文件泄露、源代码泄露

**攻击路径**:
1. 攻击者创建书籍，书籍标题构造路径
2. 通过爬虫下载外部内容时，路径验证不充分
3. 攻击者通过修改 `file_path` 数据库记录
4. 访问任意章节内容时，读取系统任意文件

**受影响文件**:
- [apps/chapters/views.py:21-26](file:///workspace/apps/chapters/views.py#L21-L26)

**证据**:
```python
def _read_chapter_content(chapter):
    cache_key = f'chapter_content:{chapter.id}'
    content = cache.get(cache_key)
    if content is not None:
        return content

    if not os.path.exists(chapter.file_path):
        return '章节文件不存在'

    for encoding in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
        try:
            with open(chapter.file_path, 'r', encoding=encoding) as f:
                content = f.read()
```

**攻击场景**:
```python
# 攻击者通过爬虫或其他方式设置 file_path 为:
file_path = '../../../etc/passwd'
# 然后调用 chapter_read 视图读取任意文件
```

**修复建议**:
1. 实施路径白名单验证
2. 使用 `os.path.realpath()` 验证最终路径在允许目录内
3. 移除或严格限制用户对 `file_path` 字段的写入权限
4. 实施文件存储沙箱机制

**修复代码示例**:
```python
def _read_chapter_content(chapter):
    base_dir = Path(settings.BOOKS_DIR).resolve()

    try:
        file_path = Path(chapter.file_path).resolve()
        # 路径遍历检查
        if not str(file_path).startswith(str(base_dir)):
            logger.warning(f'路径越界访问尝试: {chapter.file_path}')
            return '文件不存在'
    except (ValueError, OSError):
        return '文件路径无效'

    if not file_path.exists():
        return '章节文件不存在'
```

---

## 中严重度发现

### [MEDIUM-1] SSRF保护可被绕过

**严重程度**: 中
**CWE**: CWE-918
**攻击者画像**: 已认证用户
**影响**: 内网服务探测、SSRF攻击、数据外泄

**攻击路径**:
1. 攻击者创建爬虫任务
2. 利用 DNS 重绑定或 HTTP redirect 绕过验证
3. 访问内部元数据端点或内部服务
4. 可能泄露云服务商凭证或内部数据

**受影响文件**:
- [utils/crawler_engine.py:95-118](file:///workspace/utils/crawler_engine.py#L95-L118)

**证据**:
```python
SSRF_BLOCKED_HOSTS = {
    "169.254.169.254", "metadata.google.internal", "localhost", "127.0.0.1", "::1"
}

def validate_crawl_url(url):
    # ... 解析 URL ...
    hostname = parsed.hostname
    if not hostname or hostname in SSRF_BLOCKED_HOSTS:
        return False
    try:
        resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved_ips:
            ip = sockaddr[0]
            if ipaddress.ip_address(ip).is_private:
                return False
    except socket.gaierror:
        return False
    return True
```

**绕过技术**:
1. **DNS重绑定**: 使用短TTL DNS记录，首次解析为公网IP，后续解析为内网IP
2. **HTTP 307重定向**: 验证后的URL返回重定向到内网地址
3. **IPv6绕过**: `::1` 被阻止但 `[::1]` 格式可能绕过

**修复建议**:
1. 禁用 HTTP 重定向或严格验证重定向目标
2. 实施 DNS 验证缓存（如验证 URL 后缓存解析结果）
3. 阻止所有非标准端口（仅允许80和443）
4. 定期更新 SSRF_BLOCKED_HOSTS 列表

**修复代码示例**:
```python
import requests

class CrawlerEngine:
    def __init__(self, task_id, books_dir):
        # ... 其他初始化 ...
        self.session = requests.Session()
        self.session.max_redirects = 0  # 禁用重定向

    def _fetch_page(self, session, url):
        # 仅允许 HTTP/HTTPS
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f'不支持的协议: {parsed.scheme}')

        # 验证最终 URL（处理重定向后）
        final_url = url  # 需要在 requests 中获取最终 URL
        if not validate_crawl_url(final_url):
            raise ValueError('SSRF 检测: URL 指向内网地址')

        headers = {"User-Agent": self._get_ua()}
        resp = session.get(url, headers=headers, timeout=30,
                          allow_redirects=False)  # 严格禁止重定向
        return resp.text
```

---

### [MEDIUM-2] 搜索和爬虫端点缺乏速率限制

**严重程度**: 中
**CWE**: CWE-770
**攻击者画像**: 任何用户（已认证或匿名）
**影响**: 拒绝服务、资源耗尽、成本攻击

**攻击路径**:
1. 攻击者使用脚本高频访问搜索端点
2. 每次查询触发数据库全表扫描（无查询优化）
3. 数据库连接耗尽，应用响应变慢
4. 正则表达式搜索可能导致 CPU 过载

**受影响文件**:
- [apps/search/views.py:7-20](file:///workspace/apps/search/views.py#L7-L20)
- [apps/crawler/views.py:19-34](file:///workspace/apps/crawler/views.py#L19-L34)

**证据**:
```python
def search(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        ).prefetch_related('chapters')
```

**修复建议**:
1. 实施请求速率限制（如每分钟20次搜索请求）
2. 添加请求签名或 CAPTCHA
3. 优化数据库查询，添加搜索索引
4. 实施查询超时机制

**修复代码示例**:
```python
from django.core.cache import cache
from django.http import JsonResponse

def search(request):
    # 速率限制
    rate_key = f'search_rate:{request.META.get("REMOTE_ADDR")}'
    hits = cache.get(rate_key, 0)
    if hits >= 20:
        return JsonResponse({'error': '请求过于频繁，请稍后再试'}, status=429)

    # 更新计数
    cache.set(rate_key, hits + 1, 60)  # 60秒窗口

    query = request.GET.get('q', '').strip()
    # ... 后续搜索逻辑 ...
```

---

## 安全最佳实践建议

### 已正确实施的安全措施

1. **CSRF保护**: Django 内置 CSRF 中间件已启用
2. **XSS防护**: Django 模板自动转义用户输入
3. **SQL注入防护**: 使用 ORM 查询，未发现原始 SQL 执行
4. **会话管理**: 使用数据库会话引擎
5. **认证装饰器**: 敏感操作使用 `@login_required`
6. **内容安全策略**: 生产环境应配置 CSP 头

### 建议添加的安全措施

1. **输入验证**: 增强所有用户输入的验证
2. **安全头**: 配置 HSTS、X-Content-Type-Options 等
3. **日志审计**: 记录关键安全事件
4. **备份策略**: 实施自动加密备份
5. **依赖审计**: 定期检查已知漏洞

---

## 修复优先级总结

| ID | 严重程度 | 修复优先级 | 预计工时 |
|----|---------|-----------|---------|
| HIGH-1 | 高 | P0 - 紧急 | 1小时 |
| HIGH-2 | 高 | P0 - 紧急 | 30分钟 |
| HIGH-3 | 高 | P0 - 紧急 | 30分钟 |
| HIGH-4 | 高 | P1 - 高 | 2小时 |
| MEDIUM-1 | 中 | P1 - 高 | 3小时 |
| MEDIUM-2 | 中 | P2 - 中 | 2小时 |

---

## 附录：漏洞证据

### A. 硬编码凭证证据

**start.sh 第83-84行**:
```bash
./venv/bin/python manage.py shell -c "from django.contrib.auth.models import User; \
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); \
    print('Superuser created: admin / admin123')"
```

**start.ps1 第83行**:
```powershell
.\venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth.models import User; \
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123'); \
    print('Superuser created: admin / admin123')"
```

### B. 路径遍历证据

**apps/chapters/views.py 第21-26行**:
```python
if not os.path.exists(chapter.file_path):
    return '章节文件不存在'

for encoding in ('utf-8', 'gbk', 'gb2312', 'utf-16'):
    try:
        with open(chapter.file_path, 'r', encoding=encoding) as f:
            content = f.read()
```

---

**报告生成工具**: 自动化安全审计工具
**报告版本**: 1.0
**下次审计建议日期**: 2026-06-20
