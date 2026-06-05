# 全站重构设计文档

> 创建日期: 2026-06-05
> 状态: 待实现

---

## 1. 概述

将当前 `novel_reader` 项目从单体混合应用重构为**用户端 + 管理端**分离架构，采用沉浸式阅读主题设计，保留玻璃拟态视觉风格，技术栈全面升级到 Next.js 15。

### 核心目标

- 用户端专注阅读体验，管理端专注内容运维
- 跨端响应式：桌面/平板三栏布局，手机全屏+底部导航
- 后端 API 全面重构为 `/api/v2/`，JWT + RBAC 认证
- 分支隔离全量重构，完成后一次性合并

---

## 2. 当前状态分析

### 2.1 前端现状
- 技术栈：React + Vite + TypeScript + Tailwind + Zustand + React Query
- 路由：React Router v6，15+ 页面混在同一应用
- 布局：Sidebar + Navbar + TagsView，普通用户和管理员共用界面
- 问题：功能混杂、权限边界模糊、Vite 不支持 SSR/SEO

### 2.2 后端现状
- 技术栈：Django + Django Ninja，API 挂载在 `/api/v1/`
- 认证：JWT（PyJWT），无角色控制
- 问题：接口缺少角色隔离、响应格式不统一、部分接口过度耦合

### 2.3 项目结构
```
workspace/
├── apps/              # Django apps (api, books, chapters, etc.)
├── frontend/          # 当前 React 前端
├── novel_reader/      # Django settings/urls
└── utils/             # 爬虫工具等
```

---

## 3. 架构设计

### 3.1 目录结构（重构后）

```
workspace/
├── apps/                       # 保留现有 Django 模型层
├── backend/                    # Django 后端配置
│   ├── api_v2/                 # 新 API v2 模块
│   │   ├── router.py           # v2 路由入口
│   │   ├── reader/             # 读者接口
│   │   ├── admin/              # 管理接口
│   │   ├── auth/               # 认证 + RBAC
│   │   └── schemas.py          # 统一响应格式
│   └── novel_reader/           # Django settings/urls (更新)
├── frontend/                   # Next.js 15 前端
│   ├── shared/                 # 共享代码
│   │   ├── components/         # 通用组件（按钮、输入框、玻璃卡片等）
│   │   ├── lib/                # 工具函数、API 客户端
│   │   ├── types/              # TypeScript 类型定义
│   │   └── styles/             # 全局 CSS 变量、玻璃拟态主题
│   ├── reader/                 # 用户端
│   │   ├── app/                # Next.js App Router
│   │   │   ├── layout.tsx      # 根布局
│   │   │   ├── page.tsx        # 发现流首页
│   │   │   ├── shelf/          # 书架 Tab
│   │   │   ├── book/[id]/      # 书籍详情
│   │   │   ├── read/[id]/      # 阅读器
│   │   │   ├── search/         # 搜索
│   │   │   └── stats/          # 个人统计
│   │   └── middleware.ts       # 认证中间件
│   └── admin/                  # 管理端
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx        # 仪表盘
│       │   ├── books/          # 书籍管理
│       │   ├── chapters/       # 章节管理
│       │   ├── crawler/        # 爬虫控制
│       │   ├── users/          # 用户管理
│       │   └── monitor/        # 系统监控
│       └── middleware.ts
├── utils/                      # 保留现有工具
└── templates/                  # 仅保留 404/500 模板
```

### 3.2 用户端架构

**布局：**
- 桌面/平板（≥992px）：左侧图标导航栏 + 中间主内容 + 右侧辅助面板
- 手机（<992px）：全屏内容 + 底部 Tab 导航

**页面路由：**
| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 发现流首页 | 推荐、排行榜、分类浏览 |
| `/shelf` | 书架 | 收藏 + 最近阅读 + 阅读进度 |
| `/book/[id]` | 书籍详情 | 元信息、章节列表、相似推荐 |
| `/read/[id]` | 阅读器 | 虚拟滚动 + 懒加载 |
| `/search` | 搜索 | 全文搜索 + 高级筛选 |
| `/stats` | 个人统计 | 阅读时长、进度、成就 |
| `/login` | 登录 | JWT 认证 |

**阅读器交互：**
- 虚拟滚动：当前章节完整渲染，相邻章节预加载
- 滚动时自动切换章节，无缝衔接
- 自动保存阅读进度（每 30s 或离开时）
- 支持字体大小、行间距、夜间模式设置

### 3.3 管理端架构

**布局：**
- 桌面：左侧完整导航菜单 + 中间内容区
- 平板：可折叠侧边栏
- 手机：全屏 + 汉堡菜单

**页面路由：**
| 路由 | 页面 | 说明 |
|------|------|------|
| `/admin` | 仪表盘 | 核心统计、快捷操作 |
| `/admin/books` | 书籍管理 | 表格列表 → 独立编辑页 |
| `/admin/chapters` | 章节管理 | 按书籍筛选，批量操作 |
| `/admin/crawler` | 爬虫控制 | 任务创建、监控、日志 |
| `/admin/users` | 用户管理 | 用户列表、角色分配 |
| `/admin/tags` | 标签管理 | CRUD |
| `/admin/monitor` | 系统监控 | 健康检查、性能指标、缓存 |

**数据操作模式：**
- 列表页展示数据表格，支持筛选、排序、分页
- 点击行跳转到独立编辑页（完整表单）
- 批量操作（删除、状态变更）通过顶部工具栏

### 3.4 后端 API v2 设计

**认证与 RBAC：**
- JWT 保留，增加 `role` 字段（`reader`/`user`/`admin`）
- Token 中包含角色信息，API 按角色鉴权
- 管理端接口需要 `admin` 角色
- Token 刷新机制保留

**接口分组：**
| 前缀 | 模块 | 权限 |
|------|------|------|
| `/api/v2/auth/` | 认证 | 公开 |
| `/api/v2/reader/` | 读者接口 | JWT（reader+） |
| `/api/v2/admin/` | 管理接口 | JWT（admin） |

**统一响应格式：**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "total_pages": 10,
    "total_items": 200
  },
  "error": null
}
```

**关键接口设计：**

*读者接口：*
- `GET /reader/discover/` — 发现流（推荐 + 排行 + 分类）
- `GET /reader/shelf/` — 书架数据（收藏 + 进度）
- `GET /reader/book/{id}/` — 书籍详情
- `GET /reader/book/{id}/chapters/` — 章节列表（分页，预加载相邻章节内容）
- `GET /reader/read/{book_id}/{chapter_id}/` — 单章内容（含缓存优化）
- `POST /reader/progress/` — 保存阅读进度
- `GET /reader/search/` — 全文搜索
- `GET /reader/stats/` — 个人统计

*管理接口：*
- `GET /admin/books/` — 书籍列表（完整字段）
- `POST/PUT/DELETE /admin/books/{id}/` — 书籍 CRUD
- `GET /admin/chapters/` — 章节列表
- `POST/PUT/DELETE /admin/chapters/{id}/` — 章节 CRUD
- `POST /admin/crawler/tasks/` — 创建爬虫任务
- `GET /admin/crawler/tasks/` — 任务列表
- `POST /admin/crawler/tasks/{id}/stop/` — 停止任务
- `GET /admin/users/` — 用户列表
- `PUT /admin/users/{id}/role/` — 角色分配
- `GET /admin/monitor/health/` — 健康检查
- `GET /admin/monitor/perf/` — 性能指标

---

## 4. 技术栈

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 15 (App Router) | 全栈框架 + SSR |
| React | 19 | UI 库 |
| TypeScript | 5.x | 类型系统 |
| Tailwind CSS | 3.x/4.x | 样式 |
| Zustand | 5.x | 状态管理 |
| TanStack Query | 5.x | 数据获取 |
| Shadcn/ui | latest | 基础组件库 |
| Recharts | 2.x | 图表 |
| Lucide React | latest | 图标 |

### 后端
| 技术 | 用途 |
|------|------|
| Django + Django Ninja | API 框架 |
| PyJWT | JWT 认证（扩展 RBAC） |
| PostgreSQL | 主数据库 |
| Redis + DiskCache | 缓存层 |
| Celery | 异步任务 |

---

## 5. 视觉设计原则

- 沉浸式阅读主题：减少非内容区域的视觉干扰
- 保留玻璃拟态：`backdrop-filter: blur()` + 半透明背景
- 阅读模式：深色/浅色/护眼三种模式
- 动画克制：只在必要交互处使用微动效
- 响应式断点：`<992px` 移动端布局，`≥992px` 桌面端布局

---

## 6. 错误处理

### 前端
- Next.js Error Boundary 捕获组件级错误
- 全局错误处理器（`onUnhandledError`）
- Toast 通知系统（成功/警告/错误/信息）
- 网络错误重试策略（指数退避）

### 后端
- 统一异常中间件，所有异常转为标准响应格式
- 422 验证错误 + 403 权限错误 + 500 服务器错误
- 结构化日志（app/error/request/auth/crawler）
- 性能监控中间件

---

## 7. 实施策略

采用**分支隔离全量重构**：

1. 创建 `refactor/v2-full` 分支
2. 在该分支上同时重构后端 API 和前端应用
3. 后端 API v2 开发完成并测试
4. 前端 Reader 和 Admin 应用开发完成
5. 集成测试通过后合并到主分支

---

## 8. 移除内容

- 当前 `frontend/` React 应用（整体替换为 Next.js）
- Django Admin Unfold 主题模板（替换为管理前端）
- 混合权限逻辑（分离为 RBAC）
- TagsView 标签页管理（用户端不需要，管理端用浏览器标签）

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Next.js 学习曲线 | 开发速度 | 使用 App Router 最佳实践 |
| 分支合并冲突 | 主分支功能继续开发 | 定期 rebase，小批量提交 |
| 虚拟滚动内存泄漏 | 阅读器崩溃 | 严格清理策略，虚拟窗口大小限制 |
| API v2 兼容性 | 旧客户端失效 | 保留 `/api/v1/` 一段时间作为过渡 |