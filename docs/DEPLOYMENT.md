# Novel Reader 部署指南

## 目录
- [系统要求](#系统要求)
- [Docker 部署（推荐）](#docker-部署推荐)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [环境变量](#环境变量)
- [数据备份](#数据备份)
- [升级维护](#升级维护)
- [故障排查](#故障排查)

---

## 系统要求

### 最低配置
- **CPU**: 2 核心
- **内存**: 512MB（推荐 1GB）
- **磁盘**: 10GB 可用空间
- **操作系统**: Linux / macOS / Windows (WSL2)

### 推荐配置
- **CPU**: 4 核心
- **内存**: 2GB
- **磁盘**: 50GB+ SSD
- **网络**: 稳定互联网连接（用于爬虫功能）

### 依赖软件
- Docker 20.10+ & Docker Compose 2.0+
- 或 Python 3.11+ & Node.js 20+

---

## Docker 部署（推荐）

### 一键启动

```bash
# 1. 克隆项目
git clone <repository-url>
cd novel-reader

# 2. 创建环境变量文件
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false
EOF

# 3. 启动服务
docker-compose up -d

# 4. 查看状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f
```

### 服务说明

启动后包含三个服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| frontend | 80 | Nginx 前端服务 |
| backend | 8000 | FastAPI 后端服务 |
| redis | 6379 | Redis 缓存服务 |

### 访问应用
- 前端: http://localhost
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎操作）
docker-compose down -v
```

---

## 手动部署

### 后端部署

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建数据目录
mkdir -p data/books data/index data/static data/logs data/cache

# 5. 配置环境变量
export SECRET_KEY="your-secret-key"
export DATABASE_URL="sqlite+aiosqlite:///data/novel.db"
export REDIS_URL="redis://localhost:6379"

# 6. 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 前端部署

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 构建生产版本
npm run build

# 4. 使用 Nginx 部署
cp -r dist /usr/share/nginx/html/
cp nginx.conf /etc/nginx/conf.d/default.conf
nginx -s reload
```

### Redis 安装

```bash
# Docker 方式
docker run -d --name redis \
  -p 6379:6379 \
  -v redis_data:/data \
  redis:7-alpine \
  redis-server --appendonly yes --maxmemory 64mb --maxmemory-policy allkeys-lru

# 或系统包管理器
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis
brew services start redis
```

---

## 配置说明

### 配置文件位置
- **后端配置**: `backend/.env` 或环境变量
- **前端配置**: `frontend/.env.production`

### 关键配置项

#### 数据库
```env
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
```

#### Redis
```env
REDIS_URL=redis://localhost:6379
```

#### 安全
```env
SECRET_KEY=your-32-char-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

#### 路径
```env
DATA_DIR=./data
BOOKS_DIR=./data/books
INDEX_DIR=./data/index
STATIC_DIR=./data/static
LOGS_DIR=./data/logs
CACHE_DIR=./data/cache
```

---

## 环境变量

### 必需变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SECRET_KEY` | - | JWT 密钥，生产环境必须修改 |
| `DATABASE_URL` | sqlite:///data/novel.db | 数据库连接地址 |

### 可选变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DEBUG` | false | 调试模式 |
| `REDIS_URL` | redis://localhost:6379 | Redis 连接地址 |
| `APP_NAME` | Novel Reader | 应用名称 |
| `APP_VERSION` | 1.0.0 | 应用版本 |
| `PASSWORD_MIN_LENGTH` | 8 | 最小密码长度 |
| `BCRYPT_ROUNDS` | 12 | 密码哈希强度 |
| `MAX_LOGIN_ATTEMPTS` | 5 | 最大登录尝试次数 |
| `LOGIN_LOCKOUT_MINUTES` | 15 | 登录锁定时间 |
| `CRAWLER_MAX_CONCURRENT` | 5 | 爬虫最大并发数 |
| `CRAWLER_REQUEST_DELAY` | 1.0 | 爬虫请求间隔(秒) |
| `CACHE_EXPIRE_MINUTES` | 10 | 缓存过期时间 |
| `SEARCH_RESULTS_LIMIT` | 50 | 搜索结果限制 |
| `PAGE_SIZE` | 20 | 分页大小 |

---

## 数据备份

### 备份脚本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/novel-reader/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 备份数据库
cp data/novel.db "$BACKUP_DIR/"

# 备份书籍文件
tar czf "$BACKUP_DIR/books.tar.gz" data/books/

# 备份索引
tar czf "$BACKUP_DIR/index.tar.gz" data/index/

# 备份配置
cp .env "$BACKUP_DIR/"

echo "备份完成: $BACKUP_DIR"
```

### 定时备份（crontab）

```bash
# 每天凌晨 3 点备份
0 3 * * * /path/to/backup.sh >> /var/log/novel-reader-backup.log 2>&1

# 保留最近 7 天备份
0 4 * * * find /backup/novel-reader -type d -mtime +7 -exec rm -rf {} +
```

### 恢复备份

```bash
# 停止服务
docker-compose down

# 恢复数据
cp /backup/novel-reader/20240115_030000/novel.db data/
tar xzf /backup/novel-reader/20240115_030000/books.tar.gz
tar xzf /backup/novel-reader/20240115_030000/index.tar.gz

# 启动服务
docker-compose up -d
```

---

## 升级维护

### Docker 升级

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker-compose build --no-cache

# 3. 重启服务
docker-compose up -d

# 4. 清理旧镜像
docker image prune -f
```

### 数据库迁移

```bash
# 进入后端容器
docker-compose exec backend bash

# 执行迁移（如有）
alembic upgrade head

# 退出
exit
```

### 日志轮转

```bash
# 安装 logrotate
sudo apt-get install logrotate

# 创建配置
cat > /etc/logrotate.d/novel-reader << EOF
/data/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF
```

---

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
sudo lsof -i :80
sudo lsof -i :8000
sudo lsof -i :6379

# 查看详细日志
docker-compose logs --tail=100 backend
docker-compose logs --tail=100 frontend
docker-compose logs --tail=100 redis
```

### 数据库连接失败

```bash
# 检查数据库文件权限
ls -la data/novel.db

# 修复权限
chmod 644 data/novel.db

# 检查磁盘空间
df -h
```

### Redis 连接失败

```bash
# 检查 Redis 状态
docker-compose exec redis redis-cli ping

# 重启 Redis
docker-compose restart redis
```

### 性能问题

```bash
# 查看资源使用
docker stats

# 查看后端响应时间
docker-compose logs backend | grep "X-Response-Time"

# 数据库查询优化
# 检查慢查询日志
docker-compose exec backend python -c "
from app.database import engine
# 启用查询日志
"
```

### 内存不足

```bash
# 查看内存使用
free -h

# 限制容器内存
docker-compose up -d --no-deps --memory=512m backend

# 清理缓存
docker-compose exec backend python -c "
from app.services.cache_service import cache_service
import asyncio
asyncio.run(cache_service.connect())
asyncio.run(cache_service._client.flushall())
"
```

---

## 安全建议

1. **修改默认密钥**: 生产环境必须修改 `SECRET_KEY`
2. **使用 HTTPS**: 配置反向代理（Nginx/Traefik）启用 SSL
3. **防火墙**: 仅开放必要端口（80, 443）
4. **定期更新**: 及时更新依赖包修复安全漏洞
5. **访问控制**: 限制管理后台访问 IP

---

## 监控告警

### 健康检查端点

- `GET /api/health` - 基础健康检查
- `GET /api/health/startup` - 启动自检报告
- `GET /api/health/detailed` - 详细系统信息

### Prometheus 监控（可选）

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'novel-reader'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics
```

---

## 性能优化

### 已实现的优化

- **数据库连接池**: 限制最大连接数
- **Redis 连接池**: 复用连接减少开销
- **查询缓存**: 缓存频繁查询结果
- **批量处理**: FTS 索引批量更新
- **内存限制**: 章节内容读取上限 50KB
- **静态文件缓存**: Nginx 缓存前端资源

### 调优建议

```env
# 高并发场景
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
REDIS_POOL_SIZE=20
CRAWLER_MAX_CONCURRENT=3

# 低内存场景
DB_POOL_SIZE=3
CACHE_EXPIRE_MINUTES=5
MAX_CHAPTER_CONTENT_SIZE=30000
```
