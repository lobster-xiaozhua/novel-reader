# Checklist

## 后端安全

- [ ] 安全响应头已配置：响应头包含 `X-Content-Type-Options: nosniff`
- [ ] 安全响应头已配置：响应头包含 `X-Frame-Options: DENY`
- [ ] 安全响应头已配置：响应头包含 `Referrer-Policy: same-origin`
- [ ] CSP 基础策略已配置：`Content-Security-Policy` 头存在，script-src 受限
- [ ] JWT access_token 过期时间不超过 30 分钟
- [ ] JWT refresh_token 通过 HttpOnly cookie 传输（生产环境 Secure）
- [ ] 登录端点限流：1 分钟内最多 10 次请求
- [ ] 注册端点限流：10 分钟内最多 5 次请求
- [ ] 日志中不包含 Authorization header 明文
- [ ] 日志中不包含 cookie 值
- [ ] `AUTH_PASSWORD_VALIDATORS` 已启用，至少包含最小长度和通用密码检查
- [ ] `ALLOWED_HOSTS` 不为 `['*']`（生产环境）
- [ ] `MEDIA_ROOT` 与 `STATIC_ROOT` 分离
- [ ] `DEBUG=False` 在生产环境（已通过 docker-compose 环境变量配置）

## 前端渲染布局

- [ ] 移动端底部导航栏无闪烁
- [ ] 移动端内容不被底部导航栏遮挡（有 safe-area 适配）
- [ ] 桌面端左侧导航栏和右侧最近阅读栏 sticky 定位正常
- [ ] 首页 Hero 区域在移动端完整显示
- [ ] 首页加载时显示骨架屏，非空白页面
- [ ] 书籍详情页加载时显示骨架屏
- [ ] 搜索页加载时显示骨架屏
- [ ] CSS 变量完整覆盖所有主题颜色
- [ ] 阅读页面主题切换无闪烁
- [ ] 各页面内联样式已统一为 CSS 变量或 Tailwind 类

## 功能测试

- [ ] `/api/health/` 返回 200 状态码
- [ ] `/api/v2/admin/monitor/health` 返回 `{"status": "healthy", "database": true, "cache": true}`
- [ ] 所有注册路由无重复、无异常
- [ ] 首页加载测试通过：热门书籍和推荐内容正常显示
- [ ] 搜索功能测试通过：关键词搜索返回匹配结果
- [ ] 拼音搜索测试通过：输入拼音返回匹配书籍
- [ ] 书籍详情测试通过：点击书籍跳转详情页
- [ ] 阅读章节测试通过：进入阅读页显示章节内容
- [ ] 注册流程测试通过：新用户注册成功
- [ ] 登录流程测试通过：登录后获取有效 token
- [ ] 404 路由返回正确的错误响应格式