#!/usr/bin/env python3
"""
Novel Reader 跨平台自动部署脚本
自动检测操作系统并选择合适的部署方式

支持平台:
- Windows: PowerShell 部署
- Linux: Bash 部署
- macOS: Bash 部署
- Android (Termux): Bash 部署
- WSL: Bash 部署
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR / "backend"
FRONTEND_DIR = SCRIPT_DIR / "frontend"
DATA_DIR = SCRIPT_DIR / "data"


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    MAGENTA = "\033[0;35m"
    NC = "\033[0m"


def is_wsl():
    """检测是否在 WSL 环境中"""
    if platform.system() == "Linux":
        try:
            with open("/proc/version", "r") as f:
                return "microsoft" in f.read().lower()
        except:
            pass
    return False


def detect_platform():
    """检测当前平台"""
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    elif system == "linux":
        if is_wsl():
            return "wsl"
        if os.environ.get("PREFIX"):
            return "termux"
        return "linux"
    elif system == "darwin":
        return "macos"
    return "unknown"


def has_command(cmd):
    """检查命令是否存在"""
    return shutil.which(cmd) is not None


def has_docker():
    """检查 Docker 是否可用"""
    if not has_command("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def print_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")


def print_success(msg):
    print(f"{Colors.GREEN}[✓]{Colors.NC} {msg}")


def print_warning(msg):
    print(f"{Colors.YELLOW}[⚠]{Colors.NC} {msg}")


def print_error(msg):
    print(f"{Colors.RED}[✗]{Colors.NC} {msg}")


def print_header(msg):
    print(f"\n{Colors.CYAN}{'='*50}{Colors.NC}")
    print(f"{Colors.CYAN}  {msg}{Colors.NC}")
    print(f"{Colors.CYAN}{'='*50}{Colors.NC}\n")


def create_directories():
    """创建必要的数据目录"""
    print_info("创建数据目录...")
    for subdir in ["books", "index", "static", "logs", "cache", "backups"]:
        (DATA_DIR / subdir).mkdir(parents=True, exist_ok=True)
    print_success("目录创建完成")


def check_env():
    """检查并创建 .env 文件"""
    env_file = SCRIPT_DIR / ".env"
    if not env_file.exists():
        print_info("创建 .env 配置文件...")
        import secrets
        secret_key = secrets.token_hex(32)
        env_content = f"""SECRET_KEY={secret_key}
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
DATA_DIR=./data
BOOKS_DIR=./data/books
INDEX_DIR=./data/index
STATIC_DIR=./data/static
LOGS_DIR=./data/logs
CACHE_DIR=./data/cache
"""
        env_file.write_text(env_content)
        print_success(".env 文件已创建")


def run_script(script_path, shell="bash"):
    """运行脚本"""
    script_path = SCRIPT_DIR / script_path
    if not script_path.exists():
        print_error(f"脚本不存在: {script_path}")
        return False

    os.chmod(script_path, 0o755)

    try:
        if platform.system() == "Windows" and not is_wsl():
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
                cwd=str(SCRIPT_DIR)
            )
        else:
            result = subprocess.run(
                [str(script_path)],
                cwd=str(SCRIPT_DIR),
                shell=True
            )
        return result.returncode == 0
    except Exception as e:
        print_error(f"运行脚本失败: {e}")
        return False


def deploy_windows(mode="local"):
    """Windows 部署"""
    print_header(f"Windows 部署 ({mode})")

    if mode == "local":
        if not has_docker():
            print_error("Docker Desktop 未安装或未运行")
            print_info("请访问 https://docker.com/download 下载安装")
            print_info("或使用原生模式: python deploy.py native")
            return False

        create_directories()
        check_env()

        print_info("启动 Docker 服务...")
        subprocess.run(["docker-compose", "up", "-d", "redis"], cwd=str(SCRIPT_DIR))
        import time
        time.sleep(3)
        subprocess.run(["docker-compose", "up", "-d", "backend"], cwd=str(SCRIPT_DIR))
        subprocess.run(["docker-compose", "up", "-d", "frontend"], cwd=str(SCRIPT_DIR))

        print_success("部署完成!")
        print(f"  {Colors.GREEN}📖{Colors.NC} 前端: http://localhost")
        print(f"  {Colors.GREEN}🔧{Colors.NC} API: http://localhost:8000/docs")
        return True

    elif mode == "wsl":
        print_info("使用 WSL2 部署...")
        return run_script("deploy.sh", "bash")

    elif mode == "native":
        return run_script("deploy.ps1", "powershell")

    return False


def deploy_linux(mode="docker"):
    """Linux 部署"""
    print_header(f"Linux 部署 ({mode})")

    if mode == "docker":
        if not has_docker():
            print_error("Docker 未安装")
            print_info("请运行: sudo apt install docker.io docker-compose")
            print_info("或使用原生模式: python deploy.py native")
            return False

        create_directories()
        check_env()

        print_info("启动 Docker 服务...")
        subprocess.run(["docker-compose", "up", "-d", "redis"], cwd=str(SCRIPT_DIR))
        import time
        time.sleep(3)
        subprocess.run(["docker-compose", "up", "-d", "backend"], cwd=str(SCRIPT_DIR))
        subprocess.run(["docker-compose", "-d", "frontend"], cwd=str(SCRIPT_DIR))

        print_success("部署完成!")
        return True

    elif mode == "native":
        return run_script("deploy.sh", "bash")

    return False


def deploy_termux():
    """Termux 部署"""
    print_header("Termux (Android) 部署")
    return run_script("deploy-termux.sh", "bash")


def deploy_macos(mode="docker"):
    """macOS 部署"""
    print_header(f"macOS 部署 ({mode})")
    return run_script("deploy.sh", "bash")


def show_status():
    """显示服务状态"""
    print_header("服务状态")

    docker_available = has_docker()

    if docker_available:
        print(f"{Colors.CYAN}[Docker 容器]{Colors.NC}")
        try:
            subprocess.run(["docker-compose", "ps"], cwd=str(SCRIPT_DIR))
        except:
            pass
    else:
        print(f"{Colors.CYAN}[原生模式]{Colors.NC}")

    print(f"\n{Colors.CYAN}健康检查:{Colors.NC}")

    import urllib.request
    import urllib.error

    try:
        urllib.request.urlopen("http://localhost:8000/api/health", timeout=2)
        print_success("后端 API: 运行中")
    except:
        print_error("后端 API: 未响应")

    try:
        urllib.request.urlopen("http://localhost", timeout=2)
        print_success("前端页面: 运行中")
    except:
        try:
            urllib.request.urlopen("http://localhost:8080", timeout=2)
            print_success("前端页面: 运行中 (端口 8080)")
        except:
            print_error("前端页面: 未响应")


def stop_services():
    """停止所有服务"""
    print_header("停止服务")

    if has_docker():
        print_info("停止 Docker 容器...")
        subprocess.run(["docker-compose", "down"], cwd=str(SCRIPT_DIR), capture_output=True)

    import signal
    for proc_name in ["uvicorn", "python", "node", "npm", "vite", "redis-server"]:
        try:
            if platform.system() == "Windows":
                subprocess.run(f"taskkill /F /IM {proc_name}.exe", shell=True, capture_output=True)
            else:
                subprocess.run(["pkill", "-f", proc_name], capture_output=True)
        except:
            pass

    print_success("所有服务已停止")


def show_help():
    """显示帮助信息"""
    print_header("Novel Reader 跨平台部署")

    current_platform = detect_platform()

    print(f"""
{Colors.CYAN}使用方法:{Colors.NC}
  python deploy.py [command] [mode]

{Colors.CYAN}命令:{Colors.NC}
  start       启动服务 (默认)
  status      查看服务状态
  stop        停止所有服务
  help        显示帮助

{Colors.CYAN}部署模式:{Colors.NC}
  docker      Docker 部署 (默认)
  native      原生部署 (不使用 Docker)

{Colors.CYAN}当前平台:{Colors.NC}
  {current_platform}

{Colors.CYAN}快速开始:{Colors.NC}
  python deploy.py          # 使用默认方式启动
  python deploy.py status    # 查看状态
  python deploy.py stop      # 停止服务

{Colors.CYAN}平台特定脚本:{Colors.NC}
  Windows:  ./deploy.ps1
  Linux:    ./deploy.sh
  Termux:   ./deploy-termux.sh

{Colors.CYAN}访问地址:{Colors.NC}
  前端: http://localhost
  API:  http://localhost:8000/docs
""")


def main():
    if len(sys.argv) < 2:
        cmd = "start"
        mode = "auto"
    else:
        cmd = sys.argv[1]
        mode = sys.argv[2] if len(sys.argv) > 2 else "auto"

    current_platform = detect_platform()

    if cmd == "help":
        show_help()
        return

    if cmd == "status":
        show_status()
        return

    if cmd == "stop":
        stop_services()
        return

    if cmd == "start":
        if mode == "auto":
            if current_platform == "windows":
                mode = "local"
            elif current_platform == "termux":
                mode = "termux"
            else:
                mode = "docker"

        print_info(f"检测到平台: {current_platform}")
        print_info(f"部署模式: {mode}")

        if current_platform == "windows":
            deploy_windows(mode)
        elif current_platform == "termux":
            deploy_termux()
        elif current_platform == "linux":
            deploy_linux(mode)
        elif current_platform == "wsl":
            deploy_linux(mode)
        elif current_platform == "macos":
            deploy_macos(mode)
        else:
            print_error(f"不支持的平台: {current_platform}")
            show_help()
        return

    print_error(f"未知命令: {cmd}")
    show_help()


if __name__ == "__main__":
    main()
