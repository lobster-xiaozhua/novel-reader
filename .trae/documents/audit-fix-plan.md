# Novel Reader 全量修复规划

> 基于 2026-06-06 深度审计结果，覆盖代码质量、性能、UX/可访问性、SEO、安全、业务逻辑 6 大维度。
> 新增：v1 API 路由移除 + 项目目录整理。

---

## 一、策略总览

### 总体建议：分阶段迭代修复 + 目录重构

- **P0（6项）**：立即修复，阻断级安全漏洞和核心逻辑缺陷
- **P1（15项）**：1周内修复，高级功能缺陷和体验问题
- **P2（11项）**：2周内修复，一般优化和技术债务
- **重构（2项）**：v1 路由移除 + 目录整理，与 P0 同步进行

### 风险提示

1. **v1 移除影响**：需确认无外部服务调用 v1 API，移除后 Django URL 配置、中间件中的 v1 引用需同步清理
2. **Token双存储**：后端 `set_jwt_cookies` 设置 HttpOnly cookie，前端 `login/page.tsx` 又将 token 存入 localStorage。修复需统一为 cookie 方案，涉及前后端联动
3. **v2 章节读取同样存在路径遍历漏洞**：`backend/api_v2/reader/routes.py:310-312` 与 v1 相同的 `not allowed` 仅 log 不拦截
4. **目录整理影响**：前端 `shared/` 目录合并到标准 `src/` 结构，需更新 `tsconfig.json` 的 paths 和 `next.config.ts` 的配置

---

## 二、分阶段路线图

### 第零阶段（与 P0 同步）— 项目重构

#### R-1: 移除 v1 API 路由

前端已全部使用 v2 (`/api/v2/`)，v1 路由无任何调用方，属于历史遗留代码。

**删除文件**：
- `/workspace/apps/api/routes_auth.py`
- `/workspace/apps/api/routes_books.py`
- `/workspace/apps/api/routes_crawler.py`
- `/workspace/apps/api/routes_favorites.py`
- `/workspace/apps/api/routes_health.py`
- `/workspace/apps/api/routes_progress.py`
- `/workspace/apps/api/routes_stats.py`
- `/workspace/apps/api/routes_tags.py`
- `/workspace/apps/api/routes_users.py`
- `/workspace/apps/api/auth.py`
- `/workspace/apps/api/router.py`
- `/workspace/apps/api/schemas.py`
- `/workspace/apps/api/__init__.py`

**修改文件**：
- `/workspace/novel_reader/urls.py`：移除 v1 路由挂载（`path('api/v1/', include('apps.api.router'))`）
- `/workspace/novel_reader/middleware.py`：`JwtAuthMiddleware.PUBLIC_PATHS` 中移除 `/api/v1/` 前缀的路径，仅保留 `/api/v2/` 对应路径
- `/workspace/novel_reader/middleware.py`：`LoginRateLimitMiddleware.PATH_PREFIXES` 移除 v1 路径
- `/workspace/apps/api/` 目录：整个删除

**验证**：Django 启动无报错，`/api/v1/` 返回 404，`/api/v2/` 正常工作

#### R-2: 项目目录整理

**当前问题**：
- 前端源码散落在 `frontend/app/`、`frontend/shared/`、`frontend/middleware.ts` 等位置，无统一 `src/` 目录
- 后端 `apps/api/`（v1）与 `backend/api_v2/`（v2）目录命名不一致
- 根目录存在冗余文件：`dump.rdb`、`.flake8`、`conftest.py`、`build.py`

**整理方案**：

##### 前端目录重构
```
frontend/
├── src/                        # 新建统一源码目录
│   ├── app/                    # 从 frontend/app/ 迁移
│   │   ├── layout.tsx
│   │   ├── (reader)/
│   │   └── (admin)/
│   ├── components/             # 从 frontend/shared/components/ 迁移
│   ├── lib/                    # 从 frontend/shared/lib/ 迁移
│   │   ├── api.ts
│   │   └── utils.ts
│   ├── styles/                 # 从 frontend/shared/styles/ 迁移
│   │   └── globals.css
│   └── types/                  # 从 frontend/shared/types/ 迁移
│       └── index.ts
├── middleware.ts                # 保持根位置（Next.js 约定）
├── next.config.ts
├── package.json
└── tsconfig.json
```

**修改文件**：
- `frontend/tsconfig.json`：更新 paths 别名 `@/` 指向 `./src/`
- `frontend/next.config.ts`：确认 `srcDir` 配置
- 所有页面中的 import 路径：`@/components/`、`@/lib/`、`@/styles/`、`@/types/`
- 删除 `frontend/shared/` 目录

##### 后端目录重构
```
# v1 移除后，将 v2 目录重命名为标准结构
backend/
├── api/                        # 从 backend/api_v2/ 重命名
│   ├── __init__.py
│   ├── router.py
│   ├── auth/
│   ├── reader/
│   └── admin/
```

**修改文件**：
- `/workspace/novel_reader/urls.py`：路由挂载从 `backend.api_v2.router` 改为 `backend.api.router`
- `/workspace/novel_reader/settings.py`：`INSTALLED_APPS` 中相关引用
- 所有 v2 内部的 import 路径

##### 根目录清理
- 删除 `/workspace/dump.rdb`（Redis dump，不应入库）
- 删除 `/workspace/.flake8`（已无 v1 代码，lint 配置统一到 pyproject.toml）
- 删除 `/workspace/conftest.py`（空文件或仅含 v1 测试配置）
- 删除 `/workspace/build.py`（构建脚本功能已由 Dockerfile 覆盖）
- 删除 `/workspace/.superpowers/` 目录（IDE 配置，不应入库）
- 更新 `.gitignore`：添加 `dump.rdb`、`.superpowers/`、`__pycache__/`

**验证**：Django 启动正常，Next.js dev server 启动正常，所有页面可访问

---

### 第一阶段（24h）— P0 问题

#### P0-1: 章节内容路径遍历漏洞（v2）

- **文件**：`/workspace/backend/api_v2/reader/routes.py` L310-312
- **现状**：`not allowed` 时仅 `logger.error()`，不拦截请求，攻击者可读取任意文件
- **修复**：`not allowed` 时直接 `raise HttpError(403, '文件路径越界')` 并 return
- **验证**：构造 `chapter.file_path = '/etc/passwd'` 的请求，确认返回 403

```python
# 修复前
if not allowed:
    logger.error(f'[Chapter] 文件路径越界: real_path={real_file_path}')
# 修复后
if not allowed:
    logger.error(f'[Chapter] 文件路径越界: real_path={real_file_path}')
    raise HttpError(403, '文件路径越界，访问被拒绝')
```

#### P0-2: Middleware Admin 路由保护失效

- **文件**：`/workspace/frontend/middleware.ts`
- **现状**：仅检查 `request.cookies.get('access_token')?.value` 存在性，不验证有效性；且前端登录后 token 存 localStorage 不存 cookie
- **修复**：调用后端 `/api/v2/auth/me` 验证 token 有效性；登录时后端已通过 `set_jwt_cookies` 设置 HttpOnly cookie，前端移除 localStorage 存储逻辑

```typescript
// middleware.ts 修复方案
if (pathname.startsWith('/admin')) {
  const token = request.cookies.get('access_token')?.value;
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  try {
    const verifyRes = await fetch(new URL('/api/v2/auth/me', request.url), {
      headers: { Cookie: `access_token=${token}` },
    });
    if (!verifyRes.ok) {
      return NextResponse.redirect(new URL('/login', request.url));
    }
    const data = await verifyRes.json();
    if (!data?.data?.is_staff) {
      return NextResponse.redirect(new URL('/', request.url));
    }
  } catch {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}
```

#### P0-3: Shelf 页 Math.random() 假进度

- **文件**：`/workspace/frontend/app/(reader)/shelf/page.tsx` L38-41
- **现状**：`progress: Math.floor(Math.random() * 80) + 10` 每次渲染随机生成
- **修复**：v2 `/reader/shelf` API 已返回 `progress` 字段（含 `chapter_id` 和 `position`），前端直接使用

```typescript
// 修复前
const recents: (ShelfItem & { progress: number })[] = (shelf?.items || []).map((item) => ({
  ...item,
  progress: Math.floor(Math.random() * 80) + 10,
}));
// 修复后：使用后端返回的 progress 数据计算百分比
const recents = shelf?.recent_reads || [];
```

同时更新 `ShelfItem` 类型，添加 `progress` 和 `gradient` 字段匹配 v2 API 响应。

#### P0-4: Token 存储策略统一（HttpOnly Cookie）

- **文件**：
  - `/workspace/frontend/app/(reader)/login/page.tsx` L30-36
  - `/workspace/frontend/shared/lib/api.ts` L7-20, L43-46, L54-59
- **现状**：登录后前端将 access_token 存 localStorage，refresh_token 也存 localStorage；后端 v2 login 已通过 `set_jwt_cookies` 设置 HttpOnly cookie
- **修复**：
  1. `login/page.tsx`：移除 `api.setToken()` 和 `localStorage.setItem('refresh_token', ...)` 调用
  2. `api.ts`：移除 `getToken/setToken/clearToken` 的 localStorage 逻辑，改为从 cookie 读取（或依赖浏览器自动发送 cookie）
  3. `api.ts`：`request()` 函数添加 `credentials: 'include'` 到 fetch 选项
  4. 401 处理：尝试调用 `/api/v2/auth/refresh` 刷新 token，成功后重试原请求

```typescript
// api.ts 核心修复
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
    credentials: 'include',
  });

  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      const retryRes = await fetch(`${BASE_URL}${path}`, {
        method, headers, body: body != null ? JSON.stringify(body) : undefined,
        credentials: 'include',
      });
      if (retryRes.ok) return retryRes.json();
    }
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new ApiError('未授权，请重新登录', 401);
  }
  // ...
}

async function tryRefreshToken(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    return res.ok;
  } catch { return false; }
}
```

#### P0-5: Input 无障碍标签

- **文件**：
  - `/workspace/frontend/app/(reader)/login/page.tsx` L54-69
  - `/workspace/frontend/app/(reader)/search/page.tsx` L29-36
  - `/workspace/frontend/app/(admin)/admin/books/page.tsx` L27-33
  - `/workspace/frontend/app/(admin)/admin/crawler/page.tsx` L73-79
- **修复**：为所有 `<input>` 添加 `aria-label` 属性

```tsx
<input aria-label="用户名" className="glass-input" type="text" placeholder="用户名" ... />
<input aria-label="密码" className="glass-input" type="password" placeholder="密码" ... />
```

#### P0-6: 401 硬跳转改为路由跳转

- **文件**：`/workspace/frontend/shared/lib/api.ts` L56-58
- **修复**：在 P0-4 的 token 刷新机制中已包含此修复，刷新失败后使用 `window.location.href` 是最终兜底，但增加了刷新重试步骤大幅减少硬跳转频率

---

### 第二阶段（1周）— P1 问题

#### P1-1: 前端收藏 API 路径修正

- **文件**：`/workspace/frontend/app/(reader)/book/[id]/page.tsx` L27-30
- **修复**：确认 v2 路由匹配，mutation 逻辑优化可读性

```typescript
const favMut = useMutation({
  mutationFn: (shouldRemove: boolean) =>
    shouldRemove
      ? api.delete(`/reader/books/${id}/favorite`)
      : api.post(`/reader/books/${id}/favorite`),
});
```

#### P1-2: 搜索防抖

- **文件**：`/workspace/frontend/app/(admin)/admin/books/page.tsx` L31
- **修复**：使用 `useDeferredValue`

```typescript
const [search, setSearch] = useState('');
const deferredSearch = useDeferredValue(search);
// useQuery 中使用 deferredSearch 替代 search
```

#### P1-3: 替换 alert() 为 Toast

- **文件**：所有 admin 页面的 `alert()` 调用
- **修复**：创建轻量 Toast 组件（基于 React state），替换所有 `alert()` 调用

#### P1-4: 用户角色切换二次确认

- **文件**：`/workspace/frontend/app/(admin)/admin/users/page.tsx` L68-70
- **修复**：添加 `window.confirm()` 对话框

#### P1-5: 阅读进度离开前保存

- **文件**：`/workspace/frontend/app/(reader)/read/[id]/page.tsx`
- **修复**：添加 `beforeunload` + `sendBeacon`

#### P1-6: 阅读进度 setInterval 闭包过期

- **文件**：`/workspace/frontend/app/(reader)/read/[id]/page.tsx` L55-61
- **修复**：使用 `useRef` 保存最新 `currentChapterId`

#### P1-7: 爬虫轮询后台优化

- **文件**：`/workspace/frontend/app/(admin)/admin/crawler/page.tsx` L47
- **修复**：添加 `refetchIntervalInBackground: false`

#### P1-8: Admin Dashboard 和 Monitor queryKey 冲突

- **文件**：admin/page.tsx 和 admin/monitor/page.tsx
- **修复**：使用不同的 queryKey

#### P1-9: SEO 元数据独立化

- **文件**：各 page.tsx 的 `metadata` export
- **修复**：为每个页面添加独立 title 和 description

#### P1-10: 注册接口速率限制

- **文件**：`/workspace/novel_reader/middleware.py`
- **修复**：扩展 `LoginRateLimitMiddleware` 覆盖注册接口

#### P1-11: 外挂目录路径白名单

- **文件**：`/workspace/backend/api_v2/admin/routes.py`（v1 移除后仅修 v2）
- **修复**：改为白名单策略

```python
ALLOWED_PREFIXES = ['/mnt', '/data', '/media', '/home/books', '/opt/books']
real_path = os.path.realpath(path)
if not any(real_path.startswith(p) for p in ALLOWED_PREFIXES):
    return {'success': False, 'error': '仅允许在数据目录下操作'}
```

#### P1-12: CSP 安全头

- **文件**：`/workspace/novel_reader/middleware.py`
- **修复**：在响应中添加 CSP 头

#### P1-13: 搜索页添加热门推荐和搜索历史

- **文件**：`/workspace/frontend/app/(reader)/search/page.tsx`
- **修复**：未搜索时显示热门分类，搜索历史存 localStorage

#### P1-14: 阅读器设置面板（字号/背景色）

- **文件**：`/workspace/frontend/app/(reader)/read/[id]/page.tsx`
- **修复**：添加设置按钮和面板，支持字号、行距、背景色切换

#### P1-15: 右侧栏"继续阅读"功能实现

- **文件**：`/workspace/frontend/shared/components/ReaderLayout.tsx` L66-72
- **修复**：调用 API 获取最近阅读

---

### 第三阶段（2周）— P2 问题

| ID | 问题 | 修复动作 | 延后条件 |
|----|------|----------|----------|
| P2-1 | 多页面加载状态仅文字 | 添加 Skeleton 骨架屏组件 | 需设计规范 |
| P2-2 | 章节列表一次加载全部 | v2 已支持分页，前端适配 | 依赖 P1-6 |
| P2-3 | 搜索结果无分页 | v2 已支持分页，前端添加分页 | 依赖 P1-2 |
| P2-4 | 统计页无时间范围选择 | 添加日期选择器 | 低优先级 |
| P2-5 | Admin 侧边栏移动端不响应 | 添加汉堡菜单 | 低频场景 |
| P2-6 | skip-to-content 链接 | 在 layout 顶部添加跳过导航 | 可访问性优化 |
| P2-7 | 结构化数据 JSON-LD | 在书籍详情页添加 Book Schema | SEO 优化 |
| P2-8 | robots.txt 和 sitemap | 创建静态文件 | SEO 优化 |
| P2-9 | docker-compose SECRET_KEY 检查 | 启动脚本添加校验 | 部署优化 |
| P2-10 | 发现页 SSR/SSG | 改为 Server Component | 性能优化 |
| P2-11 | 章节内容流式返回 | 后端实现分页/流式 | 大章节场景 |

---

## 三、任务清单

| ID | 优先级 | 问题 | 修复动作 | 依赖 | 验收标准 |
|----|--------|------|----------|------|----------|
| R-1 | P0 | v1 API 路由移除 | 删除 apps/api/ 目录，清理 urls.py 和 middleware 中的 v1 引用 | 无 | /api/v1/ 返回 404，/api/v2/ 正常 |
| R-2 | P0 | 项目目录整理 | 前端迁移到 src/，后端 api_v2/ 重命名为 api/，清理冗余文件 | R-1 | Django + Next.js 启动正常 |
| P0-1 | P0 | 章节路径遍历漏洞 | `not allowed` 改为 `raise HttpError(403)` | R-1 | 构造越界路径返回 403 |
| P0-2 | P0 | Admin middleware 保护失效 | middleware 调用后端验证 token + is_staff | P0-4 | 空/无效 token 被 redirect |
| P0-3 | P0 | Shelf 假进度数据 | 使用 v2 API 返回的真实 progress | 无 | 进度条显示真实百分比 |
| P0-4 | P0 | Token 双存储不一致 | 前端改用 cookie + credentials:include + 刷新机制 | 无 | 登录后 cookie 自动发送，401 自动刷新 |
| P0-5 | P0 | Input 无障碍标签 | 所有 input 添加 aria-label | 无 | WAVE 工具 0 error |
| P0-6 | P0 | 401 硬跳转 | 增加刷新重试步骤（P0-4 已包含） | P0-4 | 401 后先尝试刷新再跳转 |
| P1-1 | P1 | 收藏 mutation 可读性 | 重命名变量 + 确认 API 路径匹配 | 无 | 收藏/取消收藏正常工作 |
| P1-2 | P1 | 搜索无防抖 | 使用 useDeferredValue | 无 | 快速输入不触发多余请求 |
| P1-3 | P1 | alert() 替换为 Toast | 创建 Toast 组件 | 无 | 所有 alert 替换完成 |
| P1-4 | P1 | 用户角色切换无确认 | 添加 confirm() | 无 | 切换前弹出确认框 |
| P1-5 | P1 | 离开页面进度丢失 | beforeunload + sendBeacon | 无 | 关闭标签页后进度已保存 |
| P1-6 | P1 | setInterval 闭包过期 | useRef 保存最新值 | 无 | 30s 自动保存使用正确 chapterId |
| P1-7 | P1 | 爬虫轮询后台持续 | refetchIntervalInBackground: false | 无 | 标签页后台时停止轮询 |
| P1-8 | P1 | queryKey 冲突 | 区分 dashboard/monitor 的 key | 无 | 两页面数据独立 |
| P1-9 | P1 | SEO 元数据 | 每页独立 title/description | 无 | Lighthouse SEO > 80 |
| P1-10 | P1 | 注册无速率限制 | 扩展 LoginRateLimitMiddleware | R-1 | 注册接口也受限 |
| P1-11 | P1 | 外挂目录黑名单不完整 | 改为白名单策略 | R-1 | 仅允许数据目录 |
| P1-12 | P1 | 无 CSP 头 | 中间件添加 CSP 响应头 | 无 | 响应头包含 CSP |
| P1-13 | P1 | 搜索页无热门/历史 | 添加热门推荐 + localStorage 历史 | 无 | 未搜索时显示推荐 |
| P1-14 | P1 | 阅读器无设置 | 添加字号/行距/背景色面板 | 无 | 设置可切换且持久化 |
| P1-15 | P1 | 右侧栏硬编码 | 调用 API 获取最近阅读 | 无 | 显示真实阅读记录 |

---

## 四、验证计划

### 回归测试范围

1. **核心用户路径**：登录 → 发现页 → 书籍详情 → 阅读 → 收藏 → 书架 → 统计
2. **Admin 路径**：登录 → 仪表盘 → 书籍管理（CRUD）→ 爬虫 → 用户 → 标签 → 监控
3. **认证流程**：登录 → token 过期 → 自动刷新 → 刷新失败跳转登录
4. **v1 移除验证**：`/api/v1/` 全部 404，`/api/v2/` 全部正常

### 推荐工具

| 工具 | 用途 | 目标 |
|------|------|------|
| Lighthouse | 性能 + SEO + 可访问性评分 | Performance > 70, SEO > 80, Accessibility > 90 |
| WAVE | 可访问性详细检查 | 0 error, < 3 warning |
| ESLint | 代码质量 | 0 error |
| browser DevTools | Network 面板检查 cookie/请求 | credentials: include 生效 |

### 上线前 3 条必过项

1. **路径遍历测试**：构造恶意 `file_path` 的章节请求，确认返回 403
2. **Admin 保护测试**：未登录/普通用户访问 `/admin`，确认被 redirect 到 `/login`
3. **Token 刷新测试**：access_token 过期后，自动刷新并继续操作，无硬跳转

---

## 五、技术债务建议（最小改动方案）

1. **前端全 client component**：发现页、书籍详情等可改为 Server Component 提升 SSR 性能，建议在 P2-10 阶段处理
2. **Django User 模型**：使用默认 `django.contrib.auth.models.User`，建议后续迁移到自定义 User 模型
3. **TypeScript 类型安全**：前端 API 调用返回类型较松散（`unknown`），建议后续引入 zod 做运行时校验
