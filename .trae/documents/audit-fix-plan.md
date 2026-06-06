# Novel Reader 全量修复规划

> 基于 2026-06-06 深度审计结果，覆盖代码质量、性能、UX/可访问性、SEO、安全、业务逻辑 6 大维度。

---

## 一、策略总览

### 总体建议：分阶段迭代修复

- **P0（6项）**：立即修复，阻断级安全漏洞和核心逻辑缺陷
- **P1（15项）**：1周内修复，高级功能缺陷和体验问题
- **P2（11项）**：2周内修复，一般优化和技术债务

### 风险提示

1. **API双版本共存**：项目同时存在 v1 (`/api/v1/`) 和 v2 (`/api/v2/`) 路由，前端 `api.ts` 的 `BASE_URL = '/api/v2'`，实际调用 v2。修复时需确认所有前端调用匹配 v2 路由。
2. **Token双存储**：后端 `set_jwt_cookies` 设置 HttpOnly cookie，前端 `login/page.tsx` 又将 token 存入 localStorage。修复需统一为 cookie 方案，涉及前后端联动。
3. **v2 章节读取同样存在路径遍历漏洞**：`backend/api_v2/reader/routes.py:310-312` 与 v1 相同的 `not allowed` 仅 log 不拦截。

---

## 二、分阶段路线图

### 第一阶段（24h）— P0 问题

#### P0-1: 章节内容路径遍历漏洞（v1 + v2）

- **文件**：
  - `/workspace/apps/api/routes_books.py` L481-482
  - `/workspace/backend/api_v2/reader/routes.py` L310-312
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
  // 验证 token 有效性
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
// ShelfCard 中 progress 传入真实数据
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
  // 不再手动设置 Authorization header，依赖 cookie 自动发送
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
    credentials: 'include', // 关键：发送 cookie
  });

  if (res.status === 401) {
    // 尝试刷新 token
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      // 重试原请求
      const retryRes = await fetch(`${BASE_URL}${path}`, {
        method, headers, body: body != null ? JSON.stringify(body) : undefined,
        credentials: 'include',
      });
      if (retryRes.ok) return retryRes.json();
    }
    // 刷新失败，跳转登录
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
// 修复示例
<input aria-label="用户名" className="glass-input" type="text" placeholder="用户名" ... />
<input aria-label="密码" className="glass-input" type="password" placeholder="密码" ... />
```

#### P0-6: 401 硬跳转改为路由跳转

- **文件**：`/workspace/frontend/shared/lib/api.ts` L56-58
- **现状**：`window.location.href = '/login'` 硬跳转丢失页面状态
- **修复**：在 P0-4 的 token 刷新机制中已包含此修复，刷新失败后使用 `window.location.href` 是最终兜底（此时页面状态已无法保留），但增加了刷新重试步骤大幅减少硬跳转频率

---

### 第二阶段（1周）— P1 问题

#### P1-1: 前端收藏 API 路径修正

- **文件**：`/workspace/frontend/app/(reader)/book/[id]/page.tsx` L27-30
- **现状**：前端调用 `/reader/books/${id}/favorite`，v2 后端路由为 `POST /reader/books/{book_id}/favorite` 和 `DELETE /reader/books/{book_id}/favorite`，路径匹配
- **修复**：确认 `api.ts` 的 `BASE_URL = '/api/v2'`，前端调用路径 `/reader/books/${id}/favorite` 实际请求 `/api/v2/reader/books/${id}/favorite`，与 v2 路由匹配。但 mutation 逻辑需优化可读性

```typescript
// 修复前
const favMut = useMutation({
  mutationFn: (favorited: boolean) =>
    favorited
      ? api.delete(`/reader/books/${id}/favorite`)
      : api.post(`/reader/books/${id}/favorite`),
});
// 修复后：语义更清晰
const favMut = useMutation({
  mutationFn: (shouldRemove: boolean) =>
    shouldRemove
      ? api.delete(`/reader/books/${id}/favorite`)
      : api.post(`/reader/books/${id}/favorite`),
});
// 调用处：favMut.mutate(book.is_favorited) 保持不变，但变量名更清晰
```

#### P1-2: 搜索防抖

- **文件**：`/workspace/frontend/app/(admin)/admin/books/page.tsx` L31
- **修复**：添加 300ms 防抖

```typescript
import { useDeferredValue } from 'react';

const [search, setSearch] = useState('');
const deferredSearch = useDeferredValue(search);
// useQuery 中使用 deferredSearch 替代 search
```

#### P1-3: 替换 alert() 为 Toast

- **文件**：
  - `/workspace/frontend/app/(admin)/admin/books/[id]/page.tsx` L41, L43, L56
  - `/workspace/frontend/app/(admin)/admin/crawler/page.tsx` L57, L65
  - `/workspace/frontend/app/(admin)/admin/tags/page.tsx` L27, L35
  - `/workspace/frontend/app/(admin)/admin/users/page.tsx` L23
- **修复**：创建轻量 Toast 组件（基于 React state），替换所有 `alert()` 调用

#### P1-4: 用户角色切换二次确认

- **文件**：`/workspace/frontend/app/(admin)/admin/users/page.tsx` L68-70
- **修复**：添加 `window.confirm()` 对话框

```typescript
onClick={() => {
  const action = user.is_staff ? '降级为普通读者' : '升级为管理员';
  if (window.confirm(`确定要将 ${user.username} ${action}吗？`)) {
    roleMutation.mutate({ id: user.id, is_staff: !user.is_staff });
  }
}}
```

#### P1-5: 阅读进度离开前保存

- **文件**：`/workspace/frontend/app/(reader)/read/[id]/page.tsx`
- **修复**：添加 `beforeunload` 事件监听

```typescript
useEffect(() => {
  const handleBeforeUnload = () => {
    if (id && currentChapterId) {
      // 使用 sendBeacon 确保离开前发送
      const payload = JSON.stringify({ chapter_id: currentChapterId, position: 0 });
      navigator.sendBeacon(`/api/v2/reader/books/${id}/progress`, payload);
    }
  };
  window.addEventListener('beforeunload', handleBeforeUnload);
  return () => window.removeEventListener('beforeunload', handleBeforeUnload);
}, [id, currentChapterId]);
```

#### P1-6: 阅读进度 setInterval 闭包过期

- **文件**：`/workspace/frontend/app/(reader)/read/[id]/page.tsx` L55-61
- **修复**：使用 `useRef` 保存最新 `currentChapterId`

```typescript
const currentChapterIdRef = useRef(currentChapterId);
useEffect(() => { currentChapterIdRef.current = currentChapterId; }, [currentChapterId]);

useEffect(() => {
  if (!id) return;
  const interval = setInterval(() => {
    const chId = currentChapterIdRef.current;
    if (chId) {
      api.post(`/reader/books/${id}/progress`, { chapter_id: chId, position: 0 }).catch(() => {});
    }
  }, 30000);
  return () => clearInterval(interval);
}, [id]);
```

#### P1-7: 爬虫轮询后台优化

- **文件**：`/workspace/frontend/app/(admin)/admin/crawler/page.tsx` L47
- **修复**：添加 `refetchIntervalInBackground: false`

```typescript
const { data, isLoading } = useQuery({
  queryKey: ['admin-crawler'],
  queryFn: () => api.get('/admin/crawler'),
  refetchInterval: 5000,
  refetchIntervalInBackground: false,
});
```

#### P1-8: Admin Dashboard 和 Monitor 共享 queryKey 冲突

- **文件**：
  - `/workspace/frontend/app/(admin)/admin/page.tsx` L34, L40
  - `/workspace/frontend/app/(admin)/admin/monitor/page.tsx` L19, L25
- **修复**：使用不同的 queryKey，或提取共享 hook

```typescript
// admin/page.tsx 使用 'admin-dashboard-perf' / 'admin-dashboard-health'
// admin/monitor/page.tsx 使用 'admin-monitor-perf' / 'admin-monitor-health'
```

#### P1-9: SEO 元数据独立化

- **文件**：各 page.tsx 的 `metadata` export
- **修复**：为每个页面添加独立 title 和 description

```typescript
// 示例：book/[id]/page.tsx
export async function generateMetadata({ params }) {
  return { title: `书籍详情 | Novel Reader`, description: '查看书籍详情和章节目录' };
}
// search/page.tsx
export const metadata = { title: '搜索 | Novel Reader', description: '搜索你喜欢的小说' };
```

#### P1-10: 注册接口速率限制

- **文件**：`/workspace/novel_reader/middleware.py` L222-242
- **修复**：扩展 `LoginRateLimitMiddleware` 覆盖注册接口

```python
PATH_PREFIXES = ['/api/v1/auth/login/', '/api/v2/auth/login/', '/api/v1/auth/register/', '/api/v2/auth/register']
# 修改 __call__ 中的路径匹配逻辑
if any(request.path == prefix for prefix in self.PATH_PREFIXES) and request.method == 'POST':
```

#### P1-11: 外挂目录路径白名单

- **文件**：`/workspace/apps/api/routes_books.py` L312
- **现状**：黑名单策略不完整
- **修复**：改为白名单策略

```python
ALLOWED_PREFIXES = ['/mnt', '/data', '/media', '/home/books', '/opt/books']
real_path = os.path.realpath(path)
if not any(real_path.startswith(p) for p in ALLOWED_PREFIXES):
    return {'success': False, 'error': '仅允许在 /mnt, /data, /media 等数据目录下操作'}
```

#### P1-12: CSP 安全头

- **文件**：`/workspace/novel_reader/middleware.py`
- **修复**：在 `RequestTimingMiddleware` 的 response 中添加 CSP 头

```python
response['Content-Security-Policy'] = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Next.js 需要 unsafe-inline/eval
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none';"
)
```

#### P1-13: 搜索页添加热门推荐和搜索历史

- **文件**：`/workspace/frontend/app/(reader)/search/page.tsx`
- **修复**：未搜索时显示热门分类（从 discover API 获取），搜索历史存 localStorage

#### P1-14: 阅读器设置面板（字号/背景色）

- **文件**：`/workspace/frontend/app/(reader)/read/[id]/page.tsx`
- **修复**：添加设置按钮和面板，支持字号（14-24px）、行距（1.5-2.5）、背景色（白/米/暗）切换，存 localStorage

#### P1-15: 右侧栏"继续阅读"功能实现

- **文件**：`/workspace/frontend/shared/components/ReaderLayout.tsx` L66-72
- **修复**：调用 `/api/v2/reader/shelf` 或 `/api/v2/reader/progress` 获取最近阅读

---

### 第三阶段（2周）— P2 问题

| ID | 问题 | 修复动作 | 延后条件 |
|----|------|----------|----------|
| P2-1 | 多页面加载状态仅文字 | 添加 Skeleton 骨架屏组件 | 需设计规范 |
| P2-2 | 章节列表一次加载全部 | v2 已支持分页，前端适配分页参数 | 依赖 P1-6 |
| P2-3 | 搜索结果无分页 | v2 已支持分页，前端添加分页/无限滚动 | 依赖 P1-2 |
| P2-4 | 统计页无时间范围选择 | 添加日期选择器，v2 已支持 days 参数 | 低优先级 |
| P2-5 | Admin 侧边栏移动端不响应 | 添加汉堡菜单/抽屉 | 低频使用场景 |
| P2-6 | skip-to-content 链接 | 在 layout 顶部添加跳过导航 | 可访问性优化 |
| P2-7 | 结构化数据 JSON-LD | 在书籍详情页添加 Book Schema | SEO 优化 |
| P2-8 | robots.txt 和 sitemap | 创建静态文件 | SEO 优化 |
| P2-9 | docker-compose SECRET_KEY 检查 | 启动脚本添加校验 | 部署优化 |
| P2-10 | 发现页 SSR/SSG | 改为 Server Component | 性能优化，需重构 |
| P2-11 | 章节内容流式返回 | 后端实现分页/流式 | 大章节场景 |

---

## 三、任务清单

| ID | 优先级 | 问题 | 修复动作 | 依赖 | 验收标准 |
|----|--------|------|----------|------|----------|
| P0-1 | P0 | 章节路径遍历漏洞 | v1+v2 的 `not allowed` 改为 `raise HttpError(403)` | 无 | 构造越界路径返回 403 |
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
| P1-10 | P1 | 注册无速率限制 | 扩展 LoginRateLimitMiddleware | 无 | 注册接口也受限 |
| P1-11 | P1 | 外挂目录黑名单不完整 | 改为白名单策略 | 无 | 仅允许数据目录 |
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

### 推荐工具

| 工具 | 用途 | 目标 |
|------|------|------|
| Lighthouse | 性能 + SEO + 可访问性评分 | Performance > 70, SEO > 80, Accessibility > 90 |
| WAVE | 可访问性详细检查 | 0 error, < 3 warning |
| ESLint | 代码质量 | 0 error |
| browser DevTools | Network 面板检查 cookie/请求 | credentials: include 生效 |

### 上线前 3 条必过项

1. **路径遍历测试**：构造恶意 `file_path` 的章节请求，确认返回 403（而非 200 + 文件内容）
2. **Admin 保护测试**：未登录/普通用户访问 `/admin`，确认被 redirect 到 `/login`
3. **Token 刷新测试**：access_token 过期后，自动刷新并继续操作，无硬跳转

---

## 五、技术债务建议（最小改动方案）

1. **API v1/v2 共存**：v1 路由（`/api/v1/`）已无前端调用，可在下个版本标记为 deprecated，后续移除
2. **前端全 client component**：发现页、书籍详情等可改为 Server Component 提升 SSR 性能，但需较大重构，建议在 P2-10 阶段处理
3. **Django User 模型**：使用默认 `django.contrib.auth.models.User`，建议后续迁移到自定义 User 模型以支持更多字段
4. **TypeScript 类型安全**：前端 API 调用返回类型较松散（`unknown`），建议后续引入 zod 做运行时校验
