# 全栈优化：前端渲染布局 + 后端安全架构 + 功能测试 Spec

## Why
项目当前存在三类问题：(1) 前端渲染布局在移动端适配、组件复用和加载性能上有优化空间；(2) 后端存在多项安全最佳实践偏差（缺少安全头、JWT 配置不完整、日志泄露风险等）；(3) 缺乏端到端功能测试，API 健康路由需要全面验证。

## What Changes

### 前端渲染布局优化
- 优化 ReaderLayout 响应式布局，修复移动端导航闪烁问题
- 优化首页 Hero 区域搜索引导的移动端适配
- 统一 CSS 变量管理，消除重复样式定义
- 优化书籍详情页章节列表的网格布局和虚拟滚动
- 优化阅读页面字体加载和主题切换性能
- 添加骨架屏（Skeleton）加载状态

### 后端安全架构优化
- 添加安全响应头（X-Content-Type-Options、X-Frame-Options、Referrer-Policy）
- 配置 CSP（Content-Security-Policy）基础策略
- 完善 JWT 认证配置（token 过期时间、refresh token 安全 cookie）
- 添加 API 限流（auth 端点登录/注册频率限制）
- 修复日志泄露风险（脱敏 sensitive headers/body）
- 验证 ALLOWED_HOSTS 配置
- 确保 MEDIA_ROOT 和 STATIC_ROOT 分离
- 添加密码强度验证器

### 功能测试
- 验证所有 API 健康路由（/api/health/、/api/v2/admin/monitor/health）
- 检测无异常路由（404 handler、异常路由注册）
- 测试核心用户流程：首页加载 → 搜索 → 书籍详情 → 阅读章节
- 测试认证流程：注册 → 登录 → 访问受保护接口
- 验证搜索功能：模糊搜索、拼音搜索、作者搜索

## Impact
- Affected specs: 前端渲染布局、后端安全、API 测试
- Affected code:
  - 前端：`frontend/shared/components/ReaderLayout.tsx`、`frontend/app/(reader)/page.tsx`、`frontend/app/(reader)/search/page.tsx`、`frontend/app/(reader)/book/[id]/page.tsx`、`frontend/app/(reader)/read/[id]/page.tsx`、`frontend/app/(reader)/layout.tsx`
  - 后端：`novel_reader/settings.py`、`novel_reader/middleware.py`、`apps/api/auth.py`、`backend/api_v2/auth/auth.py`、`novel_reader/urls.py`

## ADDED Requirements

### Requirement: 响应式布局优化
前端 SHALL 在所有页面提供一致的移动端/桌面端响应式体验，无布局闪烁或内容溢出。

#### Scenario: 移动端导航栏正常显示
- **WHEN** 用户在移动端（宽度 < 768px）访问任意页面
- **THEN** 底部导航栏正常显示，无闪烁，无内容被遮挡

#### Scenario: 桌面端侧边栏固定
- **WHEN** 用户在桌面端（宽度 >= 1024px）访问任意页面
- **THEN** 左侧导航栏和右侧最近阅读栏固定显示，主内容区域居中

### Requirement: 骨架屏加载状态
前端 SHALL 在数据加载时显示骨架屏（Skeleton）而非空白页面或简单 spinner。

#### Scenario: 首页加载中
- **WHEN** 用户首次访问首页，数据正在加载
- **THEN** 显示与最终布局一致的骨架屏占位

#### Scenario: 书籍详情加载中
- **WHEN** 用户进入书籍详情页，数据正在加载
- **THEN** 显示骨架屏而非仅文字"加载中..."

### Requirement: 安全响应头
后端 SHALL 在所有 HTTP 响应中添加基础安全头。

#### Scenario: API 响应包含安全头
- **WHEN** 客户端请求任意 API 端点
- **THEN** 响应头包含 `X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Referrer-Policy: same-origin`

#### Scenario: CSP 基础策略
- **WHEN** 客户端请求任意页面
- **THEN** 响应头包含 `Content-Security-Policy` 指令，限制 script-src

### Requirement: API 限流
后端 SHALL 对认证端点实施速率限制，防止暴力破解。

#### Scenario: 登录限流
- **WHEN** 同一 IP 在 1 分钟内发送超过 10 次登录请求
- **THEN** 返回 429 Too Many Requests

#### Scenario: 注册限流
- **WHEN** 同一 IP 在 10 分钟内发送超过 5 次注册请求
- **THEN** 返回 429 Too Many Requests

### Requirement: JWT 安全配置
后端 SHALL 为 JWT token 配置合理的过期时间和安全 cookie 属性。

#### Scenario: Access Token 短期有效
- **WHEN** 用户登录成功
- **THEN** 返回的 access_token 过期时间不超过 30 分钟

#### Scenario: Refresh Token 存储安全
- **WHEN** 用户登录成功
- **THEN** refresh_token 存储为 HttpOnly cookie（生产环境）

### Requirement: 日志脱敏
后端 SHALL 不在日志中输出敏感信息（Authorization header、cookie、password）。

#### Scenario: 认证请求日志
- **WHEN** 用户发送包含 Authorization header 的请求
- **THEN** 日志中不包含 token 明文

### Requirement: 健康路由验证
后端 SHALL 提供可用的健康检查端点，返回数据库和缓存状态。

#### Scenario: 健康检查正常
- **WHEN** 请求 `/api/v2/admin/monitor/health`
- **THEN** 返回 `{"status": "healthy", "database": true, "cache": true}`

#### Scenario: API v1 健康检查
- **WHEN** 请求 `/api/health/`
- **THEN** 返回 200 状态码

### Requirement: 端到端功能测试
系统 SHALL 通过自动化测试验证核心用户流程可用。

#### Scenario: 搜索流程
- **WHEN** 用户在搜索框输入关键词并提交
- **THEN** 返回匹配的书籍列表

#### Scenario: 拼音搜索
- **WHEN** 用户输入拼音关键词（如"doupo"）
- **THEN** 返回拼音匹配的书籍（如"斗破苍穹"）

#### Scenario: 阅读流程
- **WHEN** 用户点击书籍开始阅读
- **THEN** 章节内容正确加载并显示

### Requirement: 密码强度验证
后端 SHALL 在用户注册时验证密码强度。

#### Scenario: 弱密码拒绝
- **WHEN** 用户使用短于 8 位的密码注册
- **THEN** 返回验证错误提示密码要求

## MODIFIED Requirements

### Requirement: 中间件安全增强
现有的 `SecurityMiddleware` 中间件 SHALL 扩展以包含安全响应头设置。

#### Scenario: 安全头自动添加
- **WHEN** 任何 HTTP 请求经过中间件
- **THEN** 响应自动包含安全头

## REMOVED Requirements
无