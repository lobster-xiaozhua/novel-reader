# Tasks

## Phase 1: 后端安全架构优化

- [ ] Task 1: 添加安全响应头和 CSP 配置
  - [ ] 1.1 在 `settings.py` 中启用 `SecurityMiddleware` 并配置安全头（X-Content-Type-Options、X-Frame-Options、Referrer-Policy）
  - [ ] 1.2 在 `settings.py` 中添加基础 CSP 配置（`SECURE_CSP` 或通过中间件手动设置 `Content-Security-Policy` 响应头）
  - [ ] 1.3 验证：启动后端，检查响应头是否包含安全头

- [ ] Task 2: 完善 JWT 认证安全配置
  - [ ] 2.1 在 `backend/api_v2/auth/auth.py` 中缩短 access_token 过期时间至 30 分钟
  - [ ] 2.2 在 `backend/api_v2/auth/auth.py` 中实现 refresh_token 的 HttpOnly cookie 设置（生产环境 Secure）
  - [ ] 2.3 在 `apps/api/auth.py` 中同步 JWT 过期时间配置
  - [ ] 2.4 验证：测试登录返回的 token 过期时间

- [ ] Task 3: 添加 API 限流
  - [ ] 3.1 在 `settings.py` 中配置 Redis 缓存后端（已有 django-redis）
  - [ ] 3.2 创建限流工具模块 `utils/throttle.py`，基于 Redis 实现 IP 级别的滑动窗口限流
  - [ ] 3.3 在 auth 路由的 login/register 端点上应用限流装饰器
  - [ ] 3.4 验证：快速连续发送登录请求，确认 429 响应

- [ ] Task 4: 修复日志泄露风险
  - [ ] 4.1 在 `settings.py` 中配置 `LOGGING` 过滤敏感字段
  - [ ] 4.2 在 `novel_reader/middleware.py` 中添加请求日志脱敏（过滤 Authorization、Cookie header）
  - [ ] 4.3 验证：发送带 token 的请求，确认日志中不包含 token 明文

- [ ] Task 5: 添加密码强度验证器
  - [ ] 5.1 在 `settings.py` 中启用 `AUTH_PASSWORD_VALIDATORS`（最小长度、通用密码检查）
  - [ ] 5.2 在注册端点返回明确的密码要求错误信息
  - [ ] 5.3 验证：使用弱密码注册，确认返回验证错误

## Phase 2: 前端渲染布局优化

- [ ] Task 6: 优化 ReaderLayout 响应式布局
  - [ ] 6.1 修复移动端底部导航栏的 `useState` 闪烁问题（使用 `useEffect` + `useMediaQuery` 替代客户端判断）
  - [ ] 6.2 优化桌面端侧边栏（左侧导航 + 右侧最近阅读）的 sticky 定位
  - [ ] 6.3 添加移动端安全区域适配（`env(safe-area-inset-bottom)`）
  - [ ] 6.4 验证：在不同视口宽度下检查布局无溢出、无闪烁

- [ ] Task 7: 添加骨架屏加载组件
  - [ ] 7.1 创建 `frontend/shared/components/Skeleton.tsx` 通用骨架屏组件
  - [ ] 7.2 在首页 `page.tsx` 中替换加载状态为骨架屏
  - [ ] 7.3 在书籍详情页 `book/[id]/page.tsx` 中替换加载状态为骨架屏
  - [ ] 7.4 在搜索页 `search/page.tsx` 中替换加载状态为骨架屏
  - [ ] 7.5 验证：各页面加载时显示骨架屏，加载完成后平滑过渡

- [ ] Task 8: 优化 CSS 变量和样式一致性
  - [ ] 8.1 审查 `global.css`，确保 CSS 变量完整覆盖所有颜色和间距
  - [ ] 8.2 移除各页面中重复的内联样式，统一使用 CSS 变量或 Tailwind 类
  - [ ] 8.3 优化阅读页面的主题切换性能（使用 CSS 变量批量切换，避免逐元素更新）
  - [ ] 8.4 验证：视觉检查各页面颜色一致性，切换主题无闪烁

## Phase 3: 功能测试

- [ ] Task 9: API 健康路由验证
  - [ ] 9.1 编写 Playwright 测试脚本检查 `/api/health/` 返回 200
  - [ ] 9.2 编写 Playwright 测试脚本检查 `/api/v2/admin/monitor/health` 返回 healthy 状态
  - [ ] 9.3 扫描所有路由注册，确保无异常路由（无重复、无挂载错误）
  - [ ] 9.4 验证：所有测试通过

- [ ] Task 10: 端到端功能测试
  - [ ] 10.1 编写测试：首页加载 → 验证热门书籍和推荐内容显示
  - [ ] 10.2 编写测试：搜索功能 → 输入关键词搜索 → 验证搜索结果
  - [ ] 10.3 编写测试：拼音搜索 → 输入拼音 → 验证拼音匹配结果
  - [ ] 10.4 编写测试：书籍详情 → 点击书籍 → 验证详情页加载
  - [ ] 10.5 编写测试：阅读章节 → 从详情页进入阅读 → 验证内容加载
  - [ ] 10.6 编写测试：认证流程 → 注册 → 登录 → 验证 token 获取
  - [ ] 10.7 验证：所有测试通过

# Task Dependencies
- Task 2 依赖 Task 1（确保安全头配置后再优化 JWT）
- Task 3 依赖 Task 1（需要 Redis 配置和中间件基础）
- Task 6 不依赖后端任务，可并行
- Task 7 不依赖后端任务，可并行
- Task 8 依赖 Task 6（布局优化后再统一样式）
- Phase 3（Task 9-10）依赖 Phase 1-2 完成（需部署后才能测试）
- Task 9 和 Task 10 可并行执行