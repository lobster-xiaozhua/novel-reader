# Novel Reader 跨平台部署指南

## 概述

本项目已进行**降级优化**，确保在 Windows、Linux、Android (Termux) 三端无障碍部署。所有 Python 依赖已替换为**纯 Python 版本**，无需编译工具链。

## 依赖降级说明

### 原始依赖问题

| 原包 | 问题 | 降级方案 |
|------|------|----------|
| `python-jose[cryptography]` | cryptography 需要编译 Rust | → `pyjwt==2.8.0` (纯 Python) |
| `passlib[bcrypt]` | bcrypt 需要编译 | → `passlib==1.7.4` + `bcrypt==3.2.2` |
| `redis>=5.0.0` | 可选 hiredis 需编译 | 使用纯 Python redis-py |
| 其他 | - | 固定兼容版本 |

### 当前 requirements.txt

```txt
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
aiosqlite==0.19.0
redis==5.0.1
pydantic==2.5.2
pydantic-settings==2.1.0
pyjwt==2.8.0          # 替代 python-jose
passlib==1.7.4
bcrypt==3.2.2         # 固定版本
python-multipart==0.0.6
aiohttp==3.9.1
beautifulsoup4==4.12.2
tenacity==8.2.3
python-magic==0.4.27
rich==13.7.0
pyyaml==6.0.1
```

## 快速开始

### Windows

```powershell
# 方式1: 使用 PowerShell
.\scripts\deploy-windows.ps1 install
.\scripts\deploy-windows.ps1 start

# 方式2: 使用统一入口 (WSL2/Linux 子系统)
.\scripts\deploy.sh install
.\scripts\deploy.sh start
```

### Linux

```bash
# 方式1: 直接使用 Linux 脚本
chmod +x ./scripts/deploy-linux.sh
./scripts/deploy-linux.sh install
./scripts/deploy-linux.sh start

# 方式2: 使用统一入口
chmod +x ./scripts/deploy.sh
./scripts/deploy.sh install
./scripts/deploy.sh start
```

### Android/Termux

```bash
# 安装 Termux 后
chmod +x ./scripts/deploy-termux.sh
./scripts/deploy-termux.sh install
./scripts/deploy-termux.sh start
```

## 部署脚本说明

### 目录结构

```
scripts/
├── deploy.sh              # 统一入口，自动检测平台
├── deploy-windows.ps1     # Windows PowerShell 脚本
├── deploy-linux.sh       # Linux Bash 脚本
└── deploy-termux.sh       # Android/Termux 脚本
```

### 脚本命令

#### 统一入口 (deploy.sh)

```bash
./deploy.sh install      # 完整安装
./deploy.sh start        # 启动服务
./deploy.sh stop         # 停止服务
./deploy.sh status       # 查看状态
./deploy.sh docker       # Docker 模式
./deploy.sh python       # 仅安装 Python
./deploy.sh node         # 仅安装 Node.js
./deploy.sh mirror       # 配置镜像源
```

#### Windows PowerShell (deploy-windows.ps1)

```powershell
.\scripts\deploy-windows.ps1 install   # 完整安装
.\scripts\deploy-windows.ps1 start      # 本地模式启动
.\scripts\deploy-windows.ps1 docker     # Docker 模式
.\scripts\deploy-windows.ps1 redis      # 安装 Redis
```

#### Linux (deploy-linux.sh)

```bash
./scripts/deploy-linux.sh install      # 完整安装
./scripts/deploy-linux.sh start        # 本地模式启动
./scripts/deploy-linux.sh docker        # Docker 模式
./scripts/deploy-linux.sh redis         # 安装 Redis
```

#### Termux (deploy-termux.sh)

```bash
./scripts/deploy-termux.sh install      # 完整安装
./scripts/deploy-termux.sh start       # 启动服务
./scripts/deploy-termux.sh redis        # 安装 Redis
./scripts\deploy-termux.sh perm        # 配置权限
```

## 自动检测功能

### 平台检测

| 检测结果 | 操作系统 | 使用的脚本 |
|----------|----------|-----------|
| `windows` | Windows (PowerShell) | deploy-windows.ps1 |
| `wsl` | WSL2 / Linux 子系统 | deploy-linux.sh |
| `termux` | Android/Termux | deploy-termux.sh |
| `macos` | macOS | deploy-linux.sh |
| `linux` | 其他 Linux | deploy-linux.sh |

### 镜像源自动配置

脚本会自动检测 IP 所属地区：

- **中国大陆**: 自动配置阿里云/清华 pip 镜像，npmmirror npm 镜像
- **海外**: 使用官方源

## 环境要求

### Windows

- Windows 10/11
- PowerShell 5.1+
- Python 3.8+ 或 Docker Desktop
- Node.js 16+ (本地模式)

### Linux

- Ubuntu 18.04+ / Debian 10+ / Fedora 30+ / Arch Linux
- Python 3.8+
- Node.js 16+
- Redis (Docker 或系统包)

### Android/Termux

- Termux (F-Droid 推荐)
- 无需 root
- 无需编译工具

## 访问地址

| 模式 | 前端 | API |
|------|------|-----|
| Docker | http://localhost | http://localhost:8000/docs |
| 本地 (Linux) | http://localhost | http://localhost:8000/docs |
| Termux | http://localhost:5173 | http://localhost:8080/docs |

## 故障排查

### Python 依赖安装失败

```bash
# 清除缓存重试
pip cache purge
pip install -r requirements.txt --no-cache-dir

# 手动指定镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### Docker 容器无法启动

```bash
# 检查 Docker 状态
docker info

# 查看容器日志
docker-compose logs -f
```

### Termux 权限问题

```bash
# 重新配置权限
termux-setup-storage

# 检查目录权限
ls -la ~/storage
```

## 代码修改

### JWT 替换

将 `python-jose` 替换为 `pyjwt`：

**修改前 (security.py)**:
```python
from jose import JWTError, jwt
jwt.encode(...)
jwt.decode(...)
```

**修改后**:
```python
from jwt import PyJWTError as JWTError, encode, decode
encode(...)
decode(...)
```

### 启动检查更新

**startup_check.py**:
```python
# 修改前
("jose", "python-jose"),

# 修改后
("jwt", "pyjwt"),
```

## 技术支持

- 项目主页: https://github.com/lobster-xiaozhua/novel-reader
- 问题反馈: https://github.com/lobster-xiaozhua/novel-reader/issues
