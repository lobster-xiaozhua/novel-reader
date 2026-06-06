# 项目全面修复计划

## 问题汇总

从用户日志和代码分析中发现以下问题：

### P0 - 服务不可用
1. **前端 API 请求无法到达后端** — 前端 `api.ts` 使用相对路径 `/api/v2`，但前端运行在 `:3000`，后端在 `:8000`，跨端口请求被浏览器拦截（CORS + 无代理）
2. **后端根路由 404** — `GET /` 返回 404，Django 没有配置根路由视图或前端静态文件服务
3. **ALLOWED_HOSTS 不包含局域网 IP** — 从 `192.168.0.107:8000` 访问时触发 `DisallowedHost` 错误

### P1 - 启动流程问题
4. **`../logs/frontend.log: No such file or directory`** — `start.sh` 第 860 行，`logs/` 目录不存在时 nohup 重定向失败
5. **"数据库: 未知 | 缓存: 未知"** — `detect_db_backend()` 在 `start_infra` 中调用但结果未传递；`start_server` 中用 `python -c` 检测但 venv 未激活导致失败
6. **middleware.ts 使用已废弃的 convention** — Next.js 16 提示 `"middleware" file convention is deprecated. Please use "proxy" instead`

### P2 - 前端问题
7. **前端 middleware 检查 cookie 而非 localStorage** — `api.ts` 用 `localStorage` 存 token，但 `middleware.ts` 检查 `request.cookies.get('access_token')`，两者不一致
8. **前端无 favicon** — `GET /favicon.ico` 返回 404

## 修复方案

### 1. 前后端连通（核心修复）

**方案：Next.js rewrites 代理 API 请求到后端**

修改 `frontend/next.config.ts`，添加 API 代理：
```ts
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' },
      { source: '/static/:path*', destination: 'http://localhost:8000/static/:path*' },
    ];
  },
};
```
这样前端 `:3000/api/v2/*` 请求会被代理到 `:8000/api/v2/*`，无需 CORS。

### 2. 后端根路由

在 `novel_reader/urls.py` 添加根路由，返回 API 状态信息：
```python
path('', lambda r: JsonResponse({'status': 'ok', 'version': '2.0', 'api_docs': '/api/v2/docs/'})),
```

### 3. ALLOWED_HOSTS

修改 `settings.py`，在 DEBUG 模式下自动添加局域网 IP：
```python
if DEBUG:
    ALLOWED_HOSTS += ['*']  # 开发环境允许所有 host
```
或更安全地：在 `.env` 中添加 `ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,192.168.0.107`

### 4. start.sh 修复

- 第 860 行：创建 `logs/` 目录（`mkdir -p data/logs`）
- 修复数据库/缓存检测：在 `python -c` 前激活 venv
- 将 `../logs/frontend.log` 改为 `../data/logs/frontend.log`

### 5. middleware.ts → proxy.ts

Next.js 16 废弃了 `middleware.ts`，改用 `proxy.ts`。但考虑到兼容性和当前功能简单性，暂时保留 middleware.ts 并抑制警告（在 next.config.ts 中配置）。

### 6. Token 存储一致性

将 `api.ts` 的 token 存储改为同时写入 cookie，使 middleware.ts 能读取：
```ts
function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  document.cookie = `access_token=${token}; path=/; max-age=86400; SameSite=Lax`;
}
```

### 7. favicon

复制 `frontend/app/favicon.ico` 到根目录（已存在则跳过）。

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `frontend/next.config.ts` | 添加 rewrites 代理 API 请求 |
| `novel_reader/urls.py` | 添加根路由返回 API 状态 |
| `novel_reader/settings.py` | DEBUG 模式下 ALLOWED_HOSTS 放宽 |
| `frontend/shared/lib/api.ts` | setToken/clearToken 同时操作 cookie |
| `start.sh` | 修复 logs 目录创建、数据库检测激活 venv |
| `frontend/.next/` | 重新构建前端（next.config.ts 变更后） |

## 验证步骤

1. `python manage.py check` — 0 issues
2. `npm run build` — 14 routes
3. 启动后 `curl http://localhost:8000/` — 返回 JSON 状态
4. 启动后 `curl http://localhost:3000/api/v2/reader/discover` — 通过代理返回数据
5. 从局域网 IP 访问 `http://192.168.0.107:8000/api/v2/docs/` — 不再 DisallowedHost
