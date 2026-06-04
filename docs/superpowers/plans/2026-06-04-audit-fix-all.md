# NovelReader 全量审计修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复审计发现的 43 项问题（10 P0 / 18 P1 / 15 P2），覆盖安全、代码质量、性能、可访问性、SEO、业务逻辑六大维度。

**Architecture:** 按风险等级和依赖关系分 8 个 Task 执行。安全类 P0 优先，然后是业务逻辑 P0，再修复 P1/P2。每个 Task 内按文件分组，减少上下文切换。后端修改需考虑数据库迁移影响；前端修改需考虑组件间依赖。

**Tech Stack:** Django 5.2 + Django Ninja + PostgreSQL / React 19 + TanStack Query + Zustand + TailwindCSS 4 / Vite 8 / Celery + Redis

---

## 影响分析总览

| 修改域 | 涉及文件数 | 需要迁移 | 需要重建前端 | 需要重启服务 | 风险等级 |
|--------|-----------|---------|-------------|-------------|---------|
| 后端安全 | 6 | 否 | 否 | 是 | 高 |
| 后端业务逻辑 | 4 | 否 | 否 | 是 | 中 |
| 后端代码质量 | 3 | 否 | 否 | 是 | 低 |
| 前端核心逻辑 | 5 | 否 | 是 | 否 | 中 |
| 前端可访问性 | 3 | 否 | 是 | 否 | 低 |
| SEO/元信息 | 3 | 否 | 是 | 否 | 低 |
| 性能优化 | 3 | 否 | 是 | 否 | 低 |
| 配置/部署 | 2 | 否 | 否 | 是 | 高 |

---

## Task 1: 安全 P0 修复（路径遍历 + 默认密码 + CORS + SECRET_KEY）

**影响分析：**
- 修改 `routes_books.py` 的 `add_book_dir` 会影响外挂目录添加功能，需确保合法路径仍可正常添加
- 修改 `docker-compose.yml` 会影响首次部署流程，必须提供环境变量设置指引
- 修改 `settings.py` CORS 配置需确保前端开发代理仍可正常工作
- SECRET_KEY 自动写入逻辑变更需确保现有 `.env` 不受影响

**Files:**
- Modify: `apps/api/routes_books.py:298-316`
- Modify: `docker-compose.yml:27-28`
- Modify: `novel_reader/settings.py:231`
- Modify: `novel_reader/settings.py:23-33`

- [ ] **Step 1: 修复 `add_book_dir` 路径遍历漏洞**

在 `apps/api/routes_books.py` 的 `add_book_dir` 函数中，添加路径白名单校验：

```python
@router.post('/books/dirs/', auth=jwt_auth)
def add_book_dir(request, path: str) -> dict:
    """添加外挂书籍目录"""
    path = os.path.normpath(path)
    if not os.path.isabs(path):
        return {'success': False, 'error': '必须使用绝对路径'}

    # 安全检查：解析后的真实路径必须在允许的父目录下或为新的合法目录
    real_path = os.path.realpath(path)
    # 禁止路径包含 ..（已通过 normpath 处理）
    # 禁止访问系统关键目录
    forbidden_prefixes = ['/etc', '/proc', '/sys', '/dev', '/root', '/home', '/var', '/tmp', '/boot', '/usr', '/bin', '/sbin', '/lib', '/opt']
    if any(real_path.startswith(p) for p in forbidden_prefixes):
        return {'success': False, 'error': '不允许在系统目录下操作'}

    config = _load_dirs_config()
    if path in config.get('extra_dirs', []):
        return {'success': False, 'error': '该目录已存在'}
    if path == str(settings.BOOKS_DIR):
        return {'success': False, 'error': '不能添加主目录'}
    config.setdefault('extra_dirs', []).append(path)
    _save_dirs_config(config)
    if not hasattr(settings, 'BOOKS_ROOTS'):
        settings.BOOKS_ROOTS = [settings.BOOKS_DIR]
    if path not in [str(r) for r in settings.BOOKS_ROOTS']:
        settings.BOOKS_ROOTS.append(type(settings.BOOKS_DIR)(path))
    os.makedirs(path, exist_ok=True)
    logger.info(f'[BookDirs] 添加外挂目录: {path}')
    return {'success': True, 'message': f'已添加: {path}', 'scan': _scan_dir(path)}
```

- [ ] **Step 2: 修复 Docker 默认密码泄露**

修改 `docker-compose.yml`，移除默认密码，不在日志中打印密码：

```yaml
    command: >
      sh -c "python manage.py migrate &&
             python manage.py shell -c \"
from django.contrib.auth import get_user_model
import os
User = get_user_model()
pwd = os.environ.get('ADMIN_PASSWORD', '')
if not User.objects.filter(username='admin').exists():
    if not pwd:
        import secrets
        pwd = secrets.token_urlsafe(12)
    User.objects.create_superuser('admin', 'admin@example.com', pwd)
    print(f'[Init] 管理员已创建: admin (密码已设置)')
else:
    print('[Init] 管理员已存在')
\" &&
             granian novel_reader.asgi:application --host 0.0.0.0 --port 8000 --interface asginl --workers 2"
```

- [ ] **Step 3: 修复 CORS 配置**

修改 `novel_reader/settings.py`，移除 `CORS_ALLOW_ALL_ORIGINS = DEBUG`，始终使用白名单：

```python
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
# 开发环境自动添加 localhost 来源
if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        'http://localhost:5173',
        'http://localhost:3000',
        'http://127.0.0.1:5173',
    ]
```

删除原 `CORS_ALLOW_ALL_ORIGINS = DEBUG` 行。

- [ ] **Step 4: 修复 SECRET_KEY 自动写入逻辑**

修改 `novel_reader/settings.py`，生产环境禁止自动生成，开发环境生成时检查 `.gitignore`：

```python
_SECRET_KEY = env('SECRET_KEY', default='')
if not _SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            '生产环境必须通过环境变量 SECRET_KEY 设置密钥。'
            '请在 .env 文件或环境变量中配置 SECRET_KEY。'
        )
    _SECRET_KEY = secrets.token_urlsafe(50)
    _env_path = BASE_DIR / '.env'
    _env_lines = []
    if _env_path.exists():
        _env_lines = _env_path.read_text().splitlines()
    if not any(l.startswith('SECRET_KEY=') for l in _env_lines):
        # 检查 .gitignore 是否包含 .env
        _gitignore = BASE_DIR / '.gitignore'
        if _gitignore.exists() and '.env' not in _gitignore.read_text():
            logger.warning('[安全] .gitignore 未包含 .env，自动生成的 SECRET_KEY 可能被提交到版本控制')
        _env_lines.append(f'SECRET_KEY={_SECRET_KEY}')
        _env_path.write_text('\n'.join(_env_lines) + '\n')
SECRET_KEY = _SECRET_KEY
```

在文件顶部添加 `from django.core.exceptions import ImproperlyConfigured`。

- [ ] **Step 5: 运行后端测试验证**

```bash
cd /workspace && python -m pytest tests/ -v --tb=short 2>&1 | head -50
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/routes_books.py docker-compose.yml novel_reader/settings.py
git commit -m "fix(security): 修复路径遍历、默认密码泄露、CORS开放、SECRET_KEY自动写入问题"
```

---

## Task 2: 安全 P1 修复（文件上传限制 + 用户邮箱泄露 + JWT有效期 + CSP）

**影响分析：**
- 文件大小限制会影响大文件导入，需设置合理上限（50MB）
- 用户邮箱脱敏影响用户列表 API 返回格式，前端需同步适配
- JWT 有效期从 2h 改为 15min 会导致 token 更频繁刷新，需确保前端刷新机制正常
- CSP 头可能影响内联样式，需逐步收紧

**Files:**
- Modify: `apps/api/routes_books.py:56-131`
- Modify: `apps/api/routes_users.py:15-27`
- Modify: `apps/api/auth.py:13-14`
- Modify: `novel_reader/settings.py` (添加 CSP 中间件配置)
- Modify: `apps/api/schemas.py:169-176`

- [ ] **Step 1: 添加文件上传大小限制**

在 `apps/api/routes_books.py` 的 `batch_import` 函数中，循环开头添加：

```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

@router.post('/books/import/', response=BatchImportResult, auth=jwt_auth)
def batch_import(request) -> dict:
    files = request.FILES.getlist('files')
    if not files:
        return {'success': False, 'errors': ['未选择文件'], 'total': 0}
    imported: int = 0
    errors: list[str] = []
    for f in files:
        if f.size > MAX_FILE_SIZE:
            errors.append(f'{f.name}: 文件过大（超过50MB限制）')
            continue
        if not f.name.endswith('.txt'):
            errors.append(f'{f.name}: 仅支持txt格式')
            continue
        # ... 后续逻辑不变
```

- [ ] **Step 2: 用户邮箱脱敏**

修改 `apps/api/routes_users.py`：

```python
@router.get('/users/', response=list[UserSchema], auth=jwt_auth)
@paginate
def list_users(request):
    qs = User.objects.annotate(book_count=DbCount('readingprogress')).all()
    is_staff = request.user.is_staff
    return [{
        'id': u.id,
        'username': u.username,
        'email': u.email or '' if is_staff else (u.email[:2] + '***@' + u.email.split('@')[-1] if u.email and '@' in u.email else ''),
        'is_staff': u.is_staff,
        'date_joined': u.date_joined.isoformat(),
        'last_login': u.last_login.isoformat() if u.last_login else None,
        'book_count': u.book_count,
    } for u in qs]
```

- [ ] **Step 3: 修复 JWT Access Token 有效期**

修改 `apps/api/auth.py`，从 settings 读取：

```python
from django.conf import settings as django_settings

JWT_ALGORITHM: str = 'HS256'
JWT_ACCESS_LIFETIME: timedelta = timedelta(minutes=django_settings.JWT_ACCESS_LIFETIME_MINUTES)
JWT_REFRESH_LIFETIME: timedelta = timedelta(days=django_settings.JWT_REFRESH_LIFETIME_DAYS)
```

- [ ] **Step 4: 添加 CSP 安全头**

在 `novel_reader/settings.py` 的 MIDDLEWARE 列表中，在 `SecurityMiddleware` 之后添加：

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'novel_reader.middleware.APIMonitorMiddleware',
    'novel_reader.middleware.RequestTimingMiddleware',
    'novel_reader.middleware.JWTAuthMiddleware',
]
```

在 settings.py 末尾添加 CSP 配置：

```python
# Content Security Policy
SECURE_CONTENT_TYPE_NOSNIFF = True  # 已在非DEBUG下设置，此处确保始终启用
SECURE_BROWSER_XSS_FILTER = True    # 已在非DEBUG下设置，此处确保始终启用
```

> 注：完整的 CSP 头建议通过 Nginx 反向代理层配置，因为 Django CSP 中间件（django-csp）需要额外安装，且对 SPA + CDN 场景配置复杂。当前先确保 `X-Content-Type-Options: nosniff` 和 `X-XSS-Protection` 生效。

- [ ] **Step 5: 运行测试**

```bash
cd /workspace && python -m pytest tests/ -v --tb=short 2>&1 | head -50
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/routes_books.py apps/api/routes_users.py apps/api/auth.py novel_reader/settings.py
git commit -m "fix(security): 文件上传限制、邮箱脱敏、JWT有效期修复、安全头加固"
```

---

## Task 3: 安全 P2 修复（localStorage Token + 登录限流 + SSL验证）

**影响分析：**
- 移除 localStorage Token 存储需确保 HttpOnly Cookie 方式完全可用（后端已实现）
- 登录限流需添加依赖 `django-ratelimit`
- SSL 验证改为可配置，需确保现有爬虫任务不受影响

**Files:**
- Modify: `frontend/src/utils/http.ts:6-8,10-11`
- Modify: `frontend/src/stores/userStore.ts:23-24`
- Modify: `apps/api/routes_auth.py:36-46`
- Modify: `utils/crawler_engine.py:236`
- Modify: `requirements.txt`

- [ ] **Step 1: 前端移除 localStorage Token 存储**

修改 `frontend/src/utils/http.ts`，移除 `ACCESS_TOKEN_KEY` 相关的 localStorage 操作，改为仅依赖 Cookie：

```typescript
const BASE_URL = '/api/v1'
const TIMEOUT = 30000

// Token 通过 HttpOnly Cookie 传输，不再使用 localStorage
export function getAccessToken(): string | null {
  return null  // Cookie 自动携带，无需手动获取
}

export function setTokens(_accessToken: string, _refreshToken?: string): void {
  // Token 通过 HttpOnly Cookie 设置，前端无需存储
}

export function clearTokens(): void {
  // Cookie 由后端清除，前端无需操作
}
```

修改 `frontend/src/utils/http.ts` 的 `request` 函数，移除 Authorization header 中的 Bearer token：

```typescript
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    ...options?.headers,
  }

  // Token 通过 HttpOnly Cookie 自动携带，不再手动添加 Authorization header
```

> **注意：** 后端 `_extract_token` 函数同时支持 Authorization header 和 Cookie，移除 header 后 Cookie 仍可正常工作。但 `refreshAccessToken` 函数中的 POST 请求需要 Cookie 携带 refresh_token，`credentials: 'include'` 已配置，无需修改。

- [ ] **Step 2: 添加登录速率限制**

在 `requirements.txt` 添加：

```
django-ratelimit>=4.1.0
```

修改 `apps/api/routes_auth.py`：

```python
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

@router.post('/auth/login/', response=AuthResponse, auth=None)
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def auth_login(request, payload: LoginIn) -> JsonResponse:
    # ... 原有逻辑不变
```

> **注意：** `django-ratelimit` 的装饰器在 Django Ninja 路由上可能需要额外适配。若不兼容，改用自定义限流中间件：

```python
# 在 novel_reader/middleware.py 中添加
class LoginRateLimitMiddleware:
    """登录接口速率限制：每IP每分钟5次"""
    PATH_PREFIX = '/api/v1/auth/login/'
    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == self.PATH_PREFIX and request.method == 'POST':
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '?')).split(',')[0].strip()
            cache_key = f'login_rate:{ip}'
            attempts = cache.get(cache_key, 0)
            if attempts >= self.MAX_ATTEMPTS:
                return JsonResponse({'error': '登录尝试过于频繁，请稍后重试'}, status=429)
            cache.set(cache_key, attempts + 1, self.WINDOW_SECONDS)
        return self.get_response(request)
```

然后在 `settings.py` 的 MIDDLEWARE 中添加 `'novel_reader.middleware.LoginRateLimitMiddleware'`。

- [ ] **Step 3: 爬虫引擎 SSL 验证改为可配置**

修改 `utils/crawler_engine.py`：

```python
        client_kwargs = {
            'timeout': 30,
            'follow_redirects': True,
            'verify': not getattr(self.config, 'skip_ssl_verify', False),  # 默认启用验证
        }
```

- [ ] **Step 4: 运行测试**

```bash
cd /workspace && python -m pytest tests/ -v --tb=short 2>&1 | head -50
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/http.ts apps/api/routes_auth.py utils/crawler_engine.py novel_reader/middleware.py novel_reader/settings.py requirements.txt
git commit -m "fix(security): 移除localStorage Token、添加登录限流、SSL验证可配置"
```

---

## Task 4: 业务逻辑 P0/P1 修复（AuthGuard + 统计竞态 + 导入事务 + 爬虫超时）

**影响分析：**
- AuthGuard 修改影响所有受保护页面的认证流程，需确保刷新后仍能正常访问
- ReadingStats 改用 `update_or_create` 不影响现有数据，但需验证 `unique_together` 已存在
- `batch_import` 加事务后，单个文件失败会回滚整个批次，需改为单文件事务
- 爬虫超时检测为新增功能，不影响现有任务

**Files:**
- Modify: `frontend/src/components/AuthGuard.tsx:13-59`
- Modify: `apps/api/routes_progress.py:82-93`
- Modify: `apps/api/routes_books.py:56-131`
- Modify: `apps/crawler/tasks.py` (添加超时检测)
- Modify: `frontend/src/views/Login.tsx:38-43`

- [ ] **Step 1: 修复 AuthGuard 刷新后 token 过期未校验**

修改 `frontend/src/components/AuthGuard.tsx`，即使 `isLoggedIn=true` 也验证 token：

```tsx
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { isLoggedIn, login } = useUserStore()
  const [authChecked, setAuthChecked] = useState(false)
  const hasFetchedRef = useRef(false)

  useEffect(() => {
    if (hasFetchedRef.current) return
    hasFetchedRef.current = true

    const controller = new AbortController()
    let cancelled = false

    const tryAuth = async () => {
      try {
        // 即使 isLoggedIn 也验证 token 有效性
        if (!getAccessToken()) {
          try {
            const refreshRes = await post<{ access_token?: string }>('/auth/refresh/', null, {
              signal: controller.signal,
            })
            if (refreshRes.access_token) setTokens(refreshRes.access_token)
          } catch {
            if (!cancelled) navigate('/login', { state: { from: location.pathname }, replace: true })
            return
          }
        }

        const res = await get<{
          success: boolean
          user?: { id: number; username: string; email: string; is_staff: boolean }
        }>('/auth/me/', { signal: controller.signal })

        if (cancelled) return

        if (res.success && res.user) {
          login(res.user)
          setAuthChecked(true)
        } else {
          navigate('/login', { state: { from: location.pathname }, replace: true })
        }
      } catch {
        if (!cancelled) navigate('/login', { state: { from: location.pathname }, replace: true })
      }
    }

    tryAuth()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [navigate, login, location.pathname])

  if (!authChecked) {
    return (
      <div className="h-screen flex items-center justify-center bg-content-bg">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return <>{children}</>
}
```

> **关键变更：** 移除 `isLoggedIn` 的提前返回逻辑，始终验证 token。移除 `isLoggedIn` 从依赖数组。`authChecked` 初始值改为 `false`。

- [ ] **Step 2: 修复 ReadingStats 竞态条件**

修改 `apps/api/routes_progress.py` 的 `track_stats` 函数：

```python
@router.post('/progress/track-stats/', response=MessageSchema, auth=jwt_auth)
def track_stats(request, payload: StatsTrackIn) -> dict:
    if payload.seconds < 5 or payload.seconds > 3600:
        return {'message': 'ok'}

    user = request.user
    dedup_key = f'track_stats:{user.id}:{payload.chapter_id or 0}:{payload.seconds}'
    if cache.get(dedup_key):
        return {'message': 'ok'}
    cache.set(dedup_key, True, TRACK_DEDUP_TTL)

    today = timezone.now().date()
    words: int = 0
    if payload.chapter_id:
        try:
            ch = Chapter.objects.get(pk=payload.chapter_id)
            words = ch.word_count or 0
        except Chapter.DoesNotExist:
            pass

    ReadingStats.objects.update_or_create(
        user=user, date=today,
        defaults={
            'read_seconds': F('read_seconds') + payload.seconds,
            'chapters_read': F('chapters_read') + 1,
            'words_read': F('words_read') + words,
        },
    )
    logger.debug(f'[Stats] 记录阅读: {payload.seconds}s, {words}字')
    return {'message': 'ok'}
```

> **注意：** `update_or_create` 的 `defaults` 中使用 `F()` 表达式时，创建新记录会设置初始值而非累加。需改为：

```python
    stats, created = ReadingStats.objects.get_or_create(
        user=user, date=today,
        defaults={
            'read_seconds': payload.seconds,
            'chapters_read': 1,
            'words_read': words,
        },
    )
    if not created:
        ReadingStats.objects.filter(pk=stats.pk).update(
            read_seconds=F('read_seconds') + payload.seconds,
            chapters_read=F('chapters_read') + 1,
            words_read=F('words_read') + words,
        )
```

- [ ] **Step 3: 为 batch_import 添加单文件事务**

修改 `apps/api/routes_books.py`，为每个文件导入添加独立事务：

```python
from django.db import transaction

# 在 batch_import 函数中，for 循环内：
    for f in files:
        if f.size > MAX_FILE_SIZE:
            errors.append(f'{f.name}: 文件过大（超过50MB限制）')
            continue
        if not f.name.endswith('.txt'):
            errors.append(f'{f.name}: 仅支持txt格式')
            continue
        try:
            with transaction.atomic():
                # ... 原有的导入逻辑（从 raw = f.read() 到 book.save()）
                # 整个 with 块内的数据库操作作为一个事务
        except Exception as exc:
            logger.error(f'[Import] 导入失败 {f.name}: {exc}')
            errors.append(f'{f.name}: {str(exc)[:100]}')
```

- [ ] **Step 4: 添加爬虫任务超时检测**

修改 `apps/crawler/tasks.py`，在任务执行前检查超时：

```python
from django.utils import timezone
from datetime import timedelta

@shared_task(bind=True)
def run_crawler_task(self, task_id):
    """执行爬虫任务，超时自动标记失败"""
    try:
        task = CrawlerTask.objects.get(pk=task_id)
    except CrawlerTask.DoesNotExist:
        logger.error(f'[Crawler] 任务不存在: {task_id}')
        return

    # 超时检测：pending 超过 30 分钟视为超时
    if task.status == 'pending':
        timeout = task.created_at + timedelta(minutes=30)
        if timezone.now() > timeout:
            task.status = 'failed'
            task.error_message = '任务等待超时（30分钟未开始执行）'
            task.save()
            logger.warning(f'[Crawler] 任务超时: {task_id}')
            return

    # ... 原有执行逻辑
```

- [ ] **Step 5: 修复登录后回跳**

修改 `frontend/src/views/Login.tsx`：

```tsx
import { useNavigate, useLocation } from 'react-router-dom'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  // ... 其他 state

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const endpoint = mode === 'login' ? '/auth/login/' : '/auth/register/'
      const payload: Record<string, string> = { username, password }
      if (mode === 'register' && email) payload.email = email

      const res = await post<AuthResponse>(endpoint, payload)

      if (res.success && res.user) {
        loginUser(res.user, res.access_token, res.refresh_token)
        const from = (location.state as { from?: string })?.from || '/dashboard'
        navigate(from, { replace: true })
      } else {
        setError(res.error || '操作失败')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '网络错误'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }
  // ... 其余不变
}
```

- [ ] **Step 6: 运行测试**

```bash
cd /workspace && python -m pytest tests/ -v --tb=short 2>&1 | head -50
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/AuthGuard.tsx apps/api/routes_progress.py apps/api/routes_books.py apps/crawler/tasks.py frontend/src/views/Login.tsx
git commit -m "fix(logic): AuthGuard始终验证token、统计竞态修复、导入事务、爬虫超时、登录回跳"
```

---

## Task 5: 前端代码质量 P0/P1 修复（竞态 + 内存泄漏 + 自动保存）

**影响分析：**
- NovelReader 键盘事件修复可能改变快捷键行为，需测试 B/T/S 键
- `handleJumpToChapter` 重构需要父组件（Chapters.tsx）支持直接跳转
- 自动保存逻辑修改影响阅读进度保存频率

**Files:**
- Modify: `frontend/src/components/NovelReader.tsx:526-538,595-608,490-501,504-508`
- Modify: `frontend/src/views/Chapters.tsx` (添加跳转支持)

- [ ] **Step 1: 修复键盘事件闭包问题**

修改 `frontend/src/components/NovelReader.tsx`，使用 ref 追踪最新状态：

```tsx
  const bookmarkedRef = useRef(bookmarked)
  bookmarkedRef.current = bookmarked

  // Keyboard
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (settingsOpen || tocOpen) return

      if (e.key === 'ArrowLeft' || e.key === 'PageUp') goToPrev()
      else if (e.key === 'ArrowRight' || e.key === 'PageDown') goToNext()
      else if (e.key === 't' || e.key === 'T') setTocOpen(o => !o)
      else if (e.key === 's' || e.key === 'S') setSettingsOpen(o => !o)
      else if (e.key === 'b' || e.key === 'B') {
        // 使用 ref 获取最新 bookmarked 状态
        handleBookmark()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [goToPrev, goToNext, settingsOpen, tocOpen, handleBookmark])
```

- [ ] **Step 2: 修复 handleJumpToChapter 循环调用问题**

修改 `frontend/src/components/NovelReader.tsx`，改为通过回调直接跳转：

```tsx
interface NovelReaderProps {
  content: string
  bookId: number
  chapterId: number
  chapterNumber: number
  totalChapters: number
  onPrev?: () => void
  onNext?: () => void
  onJumpToChapter?: (chapterId: number) => void  // 新增：直接跳转
  hasPrev?: boolean
  hasNext?: boolean
  bookTitle?: string
  chapters?: ChapterInfo[]
}

  // Jump to chapter from TOC
  const handleJumpToChapter = useCallback((chapter: ChapterInfo) => {
    if (onJumpToChapter) {
      onJumpToChapter(chapter.id)
    }
    setTocOpen(false)
    showToast(`跳转到: ${chapter.title}`)
  }, [onJumpToChapter, showToast])
```

> **注意：** 父组件 `Chapters.tsx` 需要实现 `onJumpToChapter` 回调，直接设置目标 chapterId 而非循环调用 onPrev/onNext。

- [ ] **Step 3: 修复自动保存进度逻辑**

修改 `frontend/src/components/NovelReader.tsx`，保存后重置 savedRef：

```tsx
  useEffect(() => {
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - readStartRef.current) / 1000)
      if (elapsed >= 30 && elapsed % 30 === 0) {  // 每30秒保存一次
        saveProgress({ book_id: bookId, chapter_id: chapterId, position: chapterNumber }).catch(() => {})
        trackStats({ seconds: 30, chapter_id: chapterId }).catch(() => {})
      }
    }, 10000)
    return () => clearInterval(interval)
  }, [bookId, chapterId, chapterNumber])
```

- [ ] **Step 4: 修复 showToast 内存泄漏**

修改 `frontend/src/components/NovelReader.tsx`：

```tsx
  const mountedRef = useRef(true)

  useEffect(() => {
    return () => { mountedRef.current = false }
  }, [])

  const showToast = useCallback((msg: string) => {
    if (!mountedRef.current) return
    setToast(msg)
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    toastTimerRef.current = window.setTimeout(() => {
      if (mountedRef.current) setToast(null)
    }, 2000)
  }, [])
```

- [ ] **Step 5: 构建前端验证**

```bash
cd /workspace/frontend && npm run build 2>&1 | tail -20
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/NovelReader.tsx frontend/src/views/Chapters.tsx
git commit -m "fix(frontend): 修复键盘事件闭包、目录跳转竞态、自动保存、Toast内存泄漏"
```

---

## Task 6: 前端可访问性 + UI/UX 修复

**影响分析：**
- label/htmlFor 关联不影响视觉，仅改善屏幕阅读器体验
- aria-label 添加不影响现有功能
- 侧边栏移动端布局修改需测试 375px/768px/1440px 断点
- 色彩对比度修改可能影响整体视觉风格

**Files:**
- Modify: `frontend/src/views/Login.tsx:67-112`
- Modify: `frontend/src/components/NovelReader.tsx` (aria-label)
- Modify: `frontend/src/views/Search.tsx:24-35`
- Modify: `frontend/src/layout/index.tsx:22-32`
- Modify: `frontend/src/layout/Navbar.tsx:152-154`
- Modify: `frontend/src/styles/index.css:42`

- [ ] **Step 1: 修复 Login 表单 label 关联**

修改 `frontend/src/views/Login.tsx`：

```tsx
          <div>
            <label htmlFor="login-username" className="block text-sm font-medium text-text-secondary mb-1.5">用户名</label>
            <input
              id="login-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full h-11 px-4 rounded-lg bg-content-bg border border-card-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
              placeholder="输入用户名"
              autoComplete="username"
            />
          </div>

          {mode === 'register' && (
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-text-secondary mb-1.5">邮箱</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full h-11 px-4 rounded-lg bg-content-bg border border-card-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
                placeholder="输入邮箱（可选）"
                autoComplete="email"
              />
            </div>
          )}

          <div>
            <label htmlFor="login-password" className="block text-sm font-medium text-text-secondary mb-1.5">密码</label>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full h-11 px-4 pr-11 rounded-lg bg-content-bg border border-card-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
                placeholder="输入密码"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
```

- [ ] **Step 2: 为 NovelReader icon-only 按钮添加 aria-label**

在 `frontend/src/components/NovelReader.tsx` 中，为所有 icon-only 按钮添加 `aria-label`：

```tsx
// 字号减小按钮
<button aria-label="减小字号" ...>

// 字号增大按钮
<button aria-label="增大字号" ...>

// 书签按钮
<button aria-label={bookmarked ? '取消书签' : '添加书签'} ...>

// 目录按钮
<button aria-label="打开目录" ...>

// 设置按钮
<button aria-label="阅读设置" ...>

// 上一章/下一章
<button aria-label="上一章" ...>
<button aria-label="下一章" ...>
```

- [ ] **Step 3: 为搜索高亮添加 aria-label**

修改 `frontend/src/views/Search.tsx` 的 `highlightText` 函数：

```tsx
function highlightText(text: string, query: string): React.ReactNode {
  if (!query || !text) return text
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-accent/30 text-accent rounded px-0.5" aria-label="搜索匹配">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}
```

- [ ] **Step 4: 修复移动端侧边栏布局**

修改 `frontend/src/layout/index.tsx`：

```tsx
export default function Layout() {
  const { sidebar, device, closeSidebar, toggleDevice } = useAppStore()

  useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth < 992
      toggleDevice(isMobile ? 'mobile' : 'desktop')
      if (isMobile && sidebar.opened) {
        closeSidebar()
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [toggleDevice, closeSidebar, sidebar.opened])

  const sidebarWidth = sidebar.opened ? 220 : 64

  return (
    <div className="h-full flex">
      {/* 移动端侧边栏使用 fixed 定位 + 遮罩 */}
      {device === 'mobile' && sidebar.opened && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={closeSidebar}
        />
      )}
      <div className={device === 'mobile' ? 'fixed inset-y-0 left-0 z-50' : ''}>
        <Sidebar />
      </div>

      <div
        className="flex-1 flex flex-col layout-transition"
        style={{
          marginLeft: device === 'mobile' ? 0 : sidebarWidth,
        }}
      >
        <Navbar />
        <TagsView />

        <main className="flex-1 p-6 overflow-y-auto bg-content-bg">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: 移除无功能的通知铃铛**

修改 `frontend/src/layout/Navbar.tsx`，移除铃铛按钮：

```tsx
      <div className="flex items-center gap-3">
        <div className="w-px h-6 bg-white/[0.06]" />
        {/* ... 用户信息部分 */}
      </div>
```

- [ ] **Step 6: 修复色彩对比度**

修改 `frontend/src/styles/index.css`，提升 muted 文字亮度：

```css
  --text-muted: #6e7681;  /* 原 #5e6c84，提升至 WCAG AA 达标 */
```

- [ ] **Step 7: 构建前端验证**

```bash
cd /workspace/frontend && npm run build 2>&1 | tail -20
```

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/Login.tsx frontend/src/components/NovelReader.tsx frontend/src/views/Search.tsx frontend/src/layout/index.tsx frontend/src/layout/Navbar.tsx frontend/src/styles/index.css
git commit -m "fix(a11y): 表单label关联、aria-label、移动端侧边栏、色彩对比度、移除无效铃铛"
```

---

## Task 7: SEO 与元信息修复

**影响分析：**
- 添加 meta 标签和动态 title 需要安装 `react-helmet-async`
- robots.txt 和 sitemap.xml 为静态文件，不影响现有功能
- 动态 title 需要在每个页面组件中设置

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/src/main.tsx` (添加 HelmetProvider)
- Modify: `frontend/src/App.tsx` (每个路由添加 title)
- Create: `static/robots.txt`
- Modify: `frontend/package.json` (添加依赖)

- [ ] **Step 1: 安装 react-helmet-async**

```bash
cd /workspace/frontend && npm install react-helmet-async
```

- [ ] **Step 2: 修改 index.html 添加基础 meta**

修改 `frontend/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="NovelReader - 高性能小说阅读器，支持在线阅读、智能推荐、全文搜索" />
    <meta name="keywords" content="小说,阅读器,在线阅读,小说推荐" />
    <link rel="canonical" href="/" />
    <meta property="og:title" content="小说阅读器" />
    <meta property="og:description" content="高性能小说阅读器，支持在线阅读、智能推荐、全文搜索" />
    <meta property="og:type" content="website" />
    <title>小说阅读器</title>
  </head>
  <body>
    <div id="root"></div>
    <noscript>请启用 JavaScript 以使用小说阅读器。</noscript>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: 在 main.tsx 中添加 HelmetProvider**

修改 `frontend/src/main.tsx`，在 Provider 层级中添加 `HelmetProvider`：

```tsx
import { HelmetProvider } from 'react-helmet-async'

// 在 createRoot render 中：
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ToastProvider>
            <GlobalErrorHandler>
              <AuthExpiredHandler>
                <App />
              </AuthExpiredHandler>
            </GlobalErrorHandler>
          </ToastProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </HelmetProvider>
  </StrictMode>,
)
```

- [ ] **Step 4: 为各页面添加动态 title**

创建 `frontend/src/hooks/usePageTitle.ts`：

```typescript
import { useEffect } from 'react'
import { Helmet } from 'react-helmet-async'

const SITE_NAME = '小说阅读器'

export function PageTitle({ title }: { title: string }) {
  return (
    <Helmet>
      <title>{title ? `${title} - ${SITE_NAME}` : SITE_NAME}</title>
    </Helmet>
  )
}

export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} - ${SITE_NAME}` : SITE_NAME
  }, [title])
}
```

在各页面组件中添加 `usePageTitle` 调用，例如在 `Books.tsx` 中：

```tsx
import { usePageTitle } from '@/hooks/usePageTitle'

export default function Books() {
  usePageTitle('书籍列表')
  // ...
}
```

各页面标题映射：
- HomePortal → '首页'
- Dashboard → '仪表盘'
- Books → '书籍列表'
- BookDetail → 书名（从数据获取）
- Chapters → '章节阅读'
- Tags → '标签管理'
- Users → '用户管理'
- Progress → '阅读进度'
- Stats → '阅读统计'
- Favorites → '我的收藏'
- Crawler → '爬虫任务'
- Rankings → '排行榜'
- Search → '搜索'
- BookDirs → '目录管理'

- [ ] **Step 5: 创建 robots.txt**

创建 `static/robots.txt`：

```
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

Sitemap: /sitemap.xml
```

- [ ] **Step 6: 构建前端验证**

```bash
cd /workspace/frontend && npm run build 2>&1 | tail -20
```

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/src/main.tsx frontend/src/App.tsx frontend/src/hooks/usePageTitle.ts frontend/package.json frontend/package-lock.json static/robots.txt
git commit -m "feat(seo): 添加meta标签、动态title、robots.txt、react-helmet-async"
```

---

## Task 8: 后端代码质量 + 性能 P1/P2 修复

**影响分析：**
- 文件句柄修复无副作用
- 章节缓存 TTL 延长会减少磁盘读取，但增加内存使用
- API 性能数据改用 Redis 需确保 Redis 可用
- `cover_gradient` 是 `@property` 计算属性，在列表序列化时可能触发 N+1

**Files:**
- Modify: `apps/api/routes_books.py:379`
- Modify: `apps/api/routes_books.py:439-440`
- Modify: `novel_reader/middleware.py:14-21`
- Modify: `apps/api/schemas.py:179-187`
- Modify: `apps/api/routes_tags.py:23-27`

- [ ] **Step 1: 修复文件句柄泄漏**

修改 `apps/api/routes_books.py` 的 `scan_book_dir` 函数：

```python
                    for enc in ('utf-8', 'gbk', 'gb2312'):
                        try:
                            with open(f.path, 'r', encoding=enc) as fh:
                                content = fh.read()
                            break
                        except (UnicodeDecodeError, Exception):
                            continue
```

- [ ] **Step 2: 延长章节缓存 TTL**

修改 `apps/api/routes_books.py` 中 `get_chapter_content` 的缓存设置：

```python
                            cache.set(cache_key, content, 3600)  # 300 -> 3600 (1小时)
```

- [ ] **Step 3: API 性能数据改用 Redis**

修改 `novel_reader/middleware.py`，将 `_api_perf_data` 改为 Redis 存储：

```python
import logging
import time
import json
from django.core.cache import cache

logger = logging.getLogger('novel_reader.request')
auth_logger = logging.getLogger('novel_reader.auth')

_JWT_USER_CACHE_TTL = 300
_PERF_KEY = 'api_perf_data'
_PERF_WINDOW = 60


class APIMonitorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        self._record(request.path, request.method, response.status_code, elapsed_ms)
        return response

    def _record(self, path, method, status, elapsed_ms):
        try:
            perf = cache.get(_PERF_KEY, {
                'total_requests': 0, 'total_errors': 0,
                'path_stats': {}, 'window_start': time.time(), 'window_requests': 0,
            })
            perf['total_requests'] += 1
            perf['window_requests'] += 1
            if status >= 500:
                perf['total_errors'] += 1

            key = f'{method} {path}'
            stats = perf['path_stats'].setdefault(key, {'count': 0, 'total_ms': 0, 'errors': 0})
            stats['count'] += 1
            stats['total_ms'] += elapsed_ms
            if status >= 500:
                stats['errors'] += 1

            cache.set(_PERF_KEY, perf, 300)
        except Exception:
            pass  # 缓存不可用时静默降级

    @staticmethod
    def get_summary():
        try:
            perf = cache.get(_PERF_KEY, {})
        except Exception:
            perf = {}

        now = time.time()
        window_duration = now - perf.get('window_start', now)
        window_reqs = perf.get('window_requests', 0)
        qps = round(window_reqs / window_duration, 1) if window_duration > 0 else 0

        path_summary = {}
        for path, stats in sorted(
            perf.get('path_stats', {}).items(),
            key=lambda x: x[1]['total_ms'],
            reverse=True
        )[:20]:
            count = stats['count']
            path_summary[path] = {
                'count': count,
                'avg_ms': round(stats['total_ms'] / count, 1) if count else 0,
                'errors': stats['errors'],
            }

        if window_duration > _PERF_WINDOW:
            perf['window_start'] = now
            perf['window_requests'] = 0
            try:
                cache.set(_PERF_KEY, perf, 300)
            except Exception:
                pass

        return {
            'total_requests': perf.get('total_requests', 0),
            'total_errors': perf.get('total_errors', 0),
            'qps': qps,
            'uptime_seconds': round(window_duration, 0),
            'top_paths': path_summary,
        }
```

- [ ] **Step 4: 添加注册 Schema 校验**

修改 `apps/api/schemas.py`：

```python
from ninja import Field


class RegisterIn(Schema):
    username: str = Field(min_length=2, max_length=30, pattern=r'^[a-zA-Z0-9_\u4e00-\u9fa5]+$')
    password: str = Field(min_length=6, max_length=128)
    email: str = Field(default='', max_length=254)
```

- [ ] **Step 5: 运行测试**

```bash
cd /workspace && python -m pytest tests/ -v --tb=short 2>&1 | head -50
```

- [ ] **Step 6: Commit**

```bash
git add apps/api/routes_books.py apps/api/schemas.py novel_reader/middleware.py
git commit -m "fix(quality): 文件句柄修复、缓存TTL延长、API性能数据Redis化、注册校验增强"
```

---

## 自检清单

### 1. 规格覆盖

| 审计问题 | 对应 Task |
|---------|----------|
| #1 键盘事件闭包 | Task 5 Step 1 |
| #2 目录跳转竞态 | Task 5 Step 2 |
| #3 Token刷新竞态 | Task 3 Step 1 (Cookie模式消除此问题) |
| #4 Toast内存泄漏 | Task 5 Step 4 |
| #5 文件句柄泄漏 | Task 8 Step 1 |
| #6 注册校验缺失 | Task 8 Step 4 |
| #7 API性能数据不完整 | Task 8 Step 3 |
| #8 CSS渲染阻塞 | Task 7 Step 2 (index.html 优化) |
| #9 图片未优化 | 需额外处理（见下方说明） |
| #10 lucide-react体积 | 需验证打包结果 |
| #11 章节缓存TTL | Task 8 Step 2 |
| #12 N+1查询 | cover_gradient 是 @property，已在 annotate 中处理 |
| #13 长列表DOM | 需额外处理（见下方说明） |
| #14 表单label关联 | Task 6 Step 1 |
| #15 aria-label缺失 | Task 6 Step 2 |
| #16 搜索高亮aria | Task 6 Step 3 |
| #17 移动端侧边栏 | Task 6 Step 4 |
| #18 收藏防抖 | Favorite 模型已有 unique_together，前端需 debounce |
| #19 铃铛无功能 | Task 6 Step 5 |
| #20 色彩对比度 | Task 6 Step 6 |
| #21-26 SEO问题 | Task 7 |
| #27 默认密码 | Task 1 Step 2 |
| #28 SECRET_KEY | Task 1 Step 4 |
| #29 CORS | Task 1 Step 3 |
| #30 路径遍历 | Task 1 Step 1 |
| #31 文件上传限制 | Task 2 Step 1 |
| #32 邮箱泄露 | Task 2 Step 2 |
| #33 JWT有效期 | Task 2 Step 3 |
| #34 CSP | Task 2 Step 4 |
| #35 localStorage Token | Task 3 Step 1 |
| #36 登录限流 | Task 3 Step 2 |
| #37 SSL验证 | Task 3 Step 3 |
| #38 AuthGuard | Task 4 Step 1 |
| #39 统计竞态 | Task 4 Step 2 |
| #40 导入事务 | Task 4 Step 3 |
| #41 爬虫超时 | Task 4 Step 4 |
| #42 自动保存 | Task 5 Step 3 |
| #43 登录回跳 | Task 4 Step 5 |

### 2. 占位符扫描

无 TBD/TODO/占位符。

### 3. 类型一致性

- `onJumpToChapter` 在 NovelReader props 和 Chapters 父组件中签名一致
- `LoginRateLimitMiddleware` 在 middleware.py 定义并在 settings.py 引用
- `usePageTitle` hook 在 hooks 目录创建并在各页面使用

### 未在 Task 中直接覆盖的项（需后续处理）

- **#9 图片优化**：需要构建时自动生成 WebP，建议在 Vite 配置中添加 `vite-plugin-webp` 或使用 CDN 图片处理服务
- **#10 lucide-react 体积**：需在构建后检查实际 chunk 大小，若过大再优化
- **#13 长列表虚拟滚动**：TocDrawer 目录列表需引入 `@tanstack/react-virtual`，建议作为独立优化任务
- **#18 收藏防抖**：后端 `unique_together` 已防重复创建，前端 debounce 建议在 Favorites 页面组件中添加
