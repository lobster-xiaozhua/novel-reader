#!/usr/bin/env python3
"""Novel Reader - 统一跨平台部署入口"""

import sys
import os
import subprocess
import platform
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = SCRIPT_DIR / "backend"

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[OK]{Colors.NC} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}", file=sys.stderr)

def get_platform():
    system = platform.system().lower()
    if system == "windows": return "windows"
    elif system == "linux":
        if os.path.exists("/data/data/com.termux/files/usr"): return "termux"
        return "linux"
    elif system == "darwin": return "macos"
    return system

def check_command(cmd):
    return shutil.which(cmd) is not None

def main():
    plat = get_platform()
    print(f"{Colors.CYAN}  ╔═══════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.CYAN}  ║   Novel Reader 统一部署工具         ║{Colors.NC}")
    print(f"{Colors.CYAN}  ╚═══════════════════════════════════════╝{Colors.NC}")
    print("")
    log_info(f"检测到平台: {plat.upper()}")
    mode = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["--docker", "-d"]: mode = "docker"
        elif arg in ["--native", "-n"]: mode = "native"
        elif arg in ["--termux", "-t"]: mode = "termux"
        elif arg in ["--help", "-h"]:
            print("用法: python deploy.py [--docker|--native|--termux]")
            return 0
    if mode is None:
        if plat == "termux": mode = "termux"
        elif check_command("docker"): mode = "docker"
        else: mode = "native"
    log_info(f"部署模式: {mode.upper()}")
    print("")
    if mode == "docker":
        log_info("Docker 部署需要运行对应的 deploy.sh 或 deploy.ps1")
    elif mode == "native":
        python_cmd = "python3" if check_command("python3") else "python"
        if not check_command(python_cmd):
            log_error("Python 未安装")
            return 1
        log_success(f"Python: {subprocess.run([python_cmd, '--version'], capture_output=True, text=True).stdout.strip()}")
        venv_path = SCRIPT_DIR / "venv"
        if not venv_path.exists():
            log_info("创建虚拟环境...")
            subprocess.run([python_cmd, "-m", "venv", str(venv_path)], check=True)
            log_success("虚拟环境已创建")
        pip_cmd = venv_path / "bin" / "pip"
        if plat == "windows": pip_cmd = venv_path / "Scripts" / "pip"
        subprocess.run([str(pip_cmd), "install", "--upgrade", "pip", "setuptools", "wheel"], check=True)
        log_info("安装 Python 依赖...")
        result = subprocess.run([str(pip_cmd), "install", "-r", str(BACKEND_DIR / "requirements.txt")])
        if result.returncode != 0:
            log_error("依赖安装失败")
            return 1
        for d in ["books", "index", "static", "logs", "cache"]:
            (SCRIPT_DIR / "data" / d).mkdir(parents=True, exist_ok=True)
        log_success("原生部署完成!")
    elif mode == "termux":
        log_info("请在 Termux 中运行: bash deploy-termux.sh")
    log_success("部署完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
