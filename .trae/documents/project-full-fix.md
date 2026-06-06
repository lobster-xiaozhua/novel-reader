# 项目全面修复计划 — 前后端连通 + 启动脚本修复

## 摘要

修复前后端无法连通、Django 根路由 404、ALLOWED_HOSTS 拒绝局域网 IP、start.sh 日志目录缺失和数据库检测失败等 5 个核心问题。

## 当前问题分析

| # | 问题 | 根因 | 影响 |
|---|------|------|------|
| 1 | 前端 API 请求到不了后端 | 前端 :3000 发 `/api/v2/*` 请求到自身，无代理到 :8000 | 前端完全无法使用 |
| 2 | `GET /` 返回 404 | Django urls.py 无根路由 | 直接访问后端 IP 也无响应 |
| 3 | `DisallowedHost: 192.168.0.107` | ALLOWED_HOSTS 仅 `['localhost','127.0.0.1','0.0.0.0']` | 局域网设备无法访问 |
| 4 | `../logs/frontend.log: No such file or directory` | start.sh 第 860 行写入 `../logs/` 但该目录不存在 | 前端启动失败 |
| 5 | 数据库/缓存显示"未知" | start.sh 第 843-854 行 `python -c` 未激活 venv | 信息展示错误 |

## 修改计划

### 1. `frontend/next.config.ts` — 添加 API 代理 rewrites

**为什么**: 前端在 :3000 运行，API 请求 `/api/v2/*` 需要代理到后端 :8000

**改什么**: 添加 `rewrites` 配置，将 `/api/:path*` 代理到 `http://localhost:8000/api/:path*`

```ts
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
};
```

**注意**: 后端端口从环境变量 `BACKEND_PORT` 读取，默认 8000。rewrites 在 Next.js 生产模式 (`next start`) 和开发模式 (`next dev`) 下均生效。

### 2. `novel_reader/urls.py` — 添加根路由

**为什么**: 直接访问 `http://host:8000/` 返回 404，需要返回 API 状态信息

**改什么**: 添加 `path('', ...)` 返回 JSON 格式的 API 状态

```python
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({
        'name': 'Novel Reader API',
        'version': '2.0.0',
        'docs': '/api/v2/docs/',
        'health': '/api/v1/health/',
    })

urlpatterns = [
    path('', api_root),
    path('sys-admin/', admin.site.urls),
    path('api/v1/', api.urls),
    path('api/v2/', api_v2.urls),
]
```

### 3. `novel_reader/settings.py` — 放宽 ALLOWED_HOSTS

**为什么**: DEBUG 模式下局域网 IP（如 192.168.0.107）被 Django 拒绝

**改什么**: DEBUG 模式下允许所有 host（开发环境安全风险可控）

```python
if DEBUG:
    ALLOWED_HOSTS = ['*']
```

同时更新 CORS_ALLOWED_ORIGINS，在 DEBUG 模式下添加通配支持：

```python
if DEBUG:
    CORS_ALLOWED_ORIGINS += [
        'http://localhost:5173',
        'http://localhost:3000',
        'http://localhost:3001',
        'http://127.0.0.1:5173',
        'http://127.0.0.1:3000',
    ]
    # 允许局域网 IP 访问（通过正则匹配）
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r'^https?://192\.168\.\d+\.\d+:\d+$',
        r'^https?://10\.\d+\.\d+\.\d+:\d+$',
        r'^https?://172\.(1[6-9]|2\d|3[01])\.\d+\.\d+:\d+$',
    ]
```

### 4. `frontend/shared/lib/api.ts` — token 同时写入 cookie

**为什么**: Next.js middleware.ts 从 `request.cookies` 读取 token，但 api.ts 只写 localStorage，导致 middleware 无法检测登录状态

**改什么**: `setToken` 同时写入 cookie，`clearToken` 同时清除 cookie

```ts
function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  document.cookie = `access_token=${token}; path=/; max-age=${15 * 60}; SameSite=Lax`;
}

function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  document.cookie = 'access_token=; path=/; max-age=0';
}
```

### 5. `start.sh` — 修复 logs 目录和数据库检测

**为什么**:
- 第 860 行 `nohup ... > ../logs/frontend.log` — `logs/` 目录不存在
- 第 843-854 行 `python -c` 未激活 venv，导致 Django settings 无法导入

**改什么**:

5a. 在 `start_server()` 函数开头创建 `logs/` 目录：
```bash
mkdir -p logs
```

5b. 将 `python -c` 的 Django settings 检测改为在已激活 venv 的上下文中执行（当前已在 `source venv/bin/activate` 之后，但 `python -c` 缺少 `DJANGO_SETTINGS_MODULE` 环境变量）：
```bash
db_engine=$(DJANGO_SETTINGS_MODULE=novel_reader.settings python -c "..." 2>/dev/null || echo "未知")
```

或者更简单：改用 `python manage.py shell -c` 来检测（manage.py 自动配置 settings）。

### 6. 重新构建前端

**为什么**: `next.config.ts` 变更后需要重新构建前端产物，否则 rewrites 配置不生效

**改什么**: 在服务器环境执行 `cd frontend && npm run build`，将构建产物提交到 git

## 假设与决策

1. **Next.js rewrites 在生产模式生效**: Next.js 16 的 `rewrites()` 在 `next start` 模式下正常工作
2. **DEBUG 模式下 ALLOWED_HOSTS=['*'] 可接受**: 仅开发环境，生产环境仍需严格配置
3. **cookie max-age 与 JWT access token 生命周期对齐**: 15 分钟
4. **前端构建在服务器完成**: Termux 无法构建，预构建产物提交到 git

## 验证步骤

1. `curl http://localhost:8000/` → 返回 JSON API 状态
2. `curl http://localhost:8000/api/v1/health/` → 返回健康检查
3. 从局域网 IP 访问 `http://192.168.x.x:8000/` → 不再 DisallowedHost
4. 前端 :3000 页面发起 API 请求 → 通过 rewrites 代理到 :8000
5. 登录后 cookie 中包含 `access_token` → middleware 可检测登录状态
6. `./start.sh start` → logs/frontend.log 正常写入，数据库/缓存显示正确
