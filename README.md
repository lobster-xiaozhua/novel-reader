# Novel Reader

一个跨平台的小说阅读器应用，使用 FastAPI 后端和 Vue 3 前端。

## 功能特性

- FastAPI 异步后端
- Vue 3 现代化 UI
- 多平台部署支持（Windows、Linux、Android Termux）
- Docker 部署支持
- 完整的测试覆盖
- 自适应代码更新系统 - 通过自然语言指令更新项目代码
- 国内镜像源支持

## 快速开始

### 使用 Docker 部署（推荐）

```bash
docker-compose up
```

### 一键部署脚本

此项目提供统一跨平台部署支持：

#### 统一部署入口（自动检测平台）：
```bash
./deploy.sh
```

#### 各平台专用脚本：

- **Linux (Debian/Ubuntu/CentOS/Arch)**
```bash
./deploy_linux.sh
```

- **Android Termux**
```bash
./deploy_termux.sh
```

- **Windows**
```powershell
# 使用 PowerShell
.\start.ps1
```

### 传统一键启动脚本：

```bash
# Linux / macOS / WSL
./start.sh

# Windows PowerShell
.\start.ps1
```

## 跨平台兼容性

为了确保在所有平台上无障碍部署，我们做了以下优化：

- **依赖降级**：移除了需要编译的依赖（cryptography、bcrypt、python-magic）
- **纯 Python 加密**：使用 `hashlib.pbkdf2_hmac` 替代 bcrypt 进行密码加密
- **轻量级依赖**：使用纯 Python 实现的功能替代方案
- **镜像源支持**：自动检测地区并配置国内镜像（阿里云、npmmirror）

## 支持的部署方式

1. Docker Compose（推荐，适用于所有支持 Docker 的平台）
2. 本地部署（适用于 Linux/macOS/WSL2）
3. Android Termux（移动设备部署）
4. Windows 本地或 WSL2

## 全局命令

配置全局命令后，可以在任意位置使用：

```bash
readweb start    # 启动项目
readweb stop     # 停止服务
readweb status   # 查看状态
readweb update  # 更新项目
```

## 文档

- [用户指南](docs/USER_GUIDE.md)
- [部署指南](docs/DEPLOYMENT.md)


