#!/usr/bin/env python3
"""
Novel Reader 一键启动脚本（Python版本）
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path
import venv
import logging
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 颜色输出（ANSI）
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'
    BOLD = '\033[1m'


def print_banner():
    """打印启动横幅"""
    print(f"""{Colors.MAGENTA}
╔═══════════════════════════════════════════════════╗
║{Colors.NC}  {Colors.CYAN}Novel Reader v2.0 - 沉浸式小说阅读器{Colors.NC}        {Colors.MAGENTA}║
║{Colors.NC}  {Colors.BLUE}一键启动，无需配置{Colors.NC}                          {Colors.MAGENTA}║
╚═══════════════════════════════════════════════════╝{Colors.NC}
""")


def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        logger.error(f"Python 3.8+ required, current: {sys.version}")
        sys.exit(1)
    logger.info(f"{Colors.GREEN}✓{Colors.NC} Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def create_virtual_environment():
    """创建虚拟环境"""
    venv_dir = Path("venv")
    if not venv_dir.exists():
        logger.info("正在创建虚拟环境...")
        venv.create(venv_dir, with_pip=True)
        logger.info(f"{Colors.GREEN}✓{Colors.NC} 虚拟环境已创建")
    else:
        logger.info(f"{Colors.GREEN}✓{Colors.NC} 虚拟环境已存在")
    return venv_dir


def get_venv_python(venv_dir: Path) -> Path:
    """获取虚拟环境中的Python解释器路径"""
    if sys.platform == 'win32':
        return venv_dir / 'Scripts' / 'python.exe'
    return venv_dir / 'bin' / 'python'


def install_dependencies(venv_python: Path):
    """安装依赖"""
    requirements = Path("requirements.txt")
    if not requirements.exists():
        logger.error(f"{Colors.RED}✗{Colors.NC} requirements.txt not found")
        sys.exit(1)

    logger.info("正在安装依赖...")
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt",
             "-i", "https://mirrors.aliyun.com/pypi/simple/", "--trusted-host", "mirrors.aliyun.com"],
            check=True,
            capture_output=False
        )
        logger.info(f"{Colors.GREEN}✓{Colors.NC} 依赖安装完成")
    except subprocess.CalledProcessError:
        logger.warning("使用官方镜像重试...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )


def ensure_env_file():
    """确保.env文件存在，使用SQLite作为默认数据库"""
    env_file = Path(".env")
    if not env_file.exists():
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        logger.info("正在创建 .env 配置文件...")
        env_content = """DEBUG=true
DATABASE_URL=sqlite:///data/novel_reader.db
"""
        env_file.write_text(env_content)
        logger.info(f"{Colors.GREEN}✓{Colors.NC} .env 配置文件已创建")


def run_migrations(venv_python: Path):
    """运行数据库迁移"""
    logger.info("正在运行数据库迁移...")
    try:
        subprocess.run(
            [str(venv_python), "manage.py", "migrate", "--no-input"],
            check=True
        )
        logger.info(f"{Colors.GREEN}✓{Colors.NC} 数据库迁移完成")
    except subprocess.CalledProcessError as e:
        logger.error(f"{Colors.RED}✗{Colors.NC} 数据库迁移失败: {e}")
        sys.exit(1)


def initialize_configs(venv_python: Path):
    """初始化系统配置"""
    logger.info("正在初始化系统配置...")
    init_script = """
try:
    from apps.config.models import ConfigManager
    count = ConfigManager.initialize_defaults()
    print(f'OK:{count}')
except Exception as e:
    print(f'ERROR:{e}')
"""
    result = subprocess.run(
        [str(venv_python), "manage.py", "shell", "-c", init_script],
        capture_output=True,
        text=True
    )
    if "OK:" in result.stdout:
        count = result.stdout.split("OK:")[-1].strip()
        if count != "0":
            logger.info(f"{Colors.GREEN}✓{Colors.NC} 已初始化 {count} 个配置")
        else:
            logger.info(f"{Colors.GREEN}✓{Colors.NC} 配置已存在")
    else:
        logger.warning("配置初始化跳过")


def create_superuser(venv_python: Path):
    """创建默认管理员账号"""
    logger.info("正在创建管理员账号...")
    admin_script = """
from django.contrib.auth.models import User
import secrets
import string
if not User.objects.filter(username='admin').exists():
    pwd = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    User.objects.create_superuser('admin', 'admin@example.com', pwd)
    print(f'CREATED:{pwd}')
else:
    print('EXISTS')
"""
    result = subprocess.run(
        [str(venv_python), "manage.py", "shell", "-c", admin_script],
        capture_output=True,
        text=True
    )
    if "CREATED:" in result.stdout:
        pwd = result.stdout.split("CREATED:")[-1].strip()
        logger.info(f"{Colors.GREEN}✓{Colors.NC} 管理员账号: admin / {pwd}")
        logger.warning("请妥善保存此密码！")
    else:
        logger.info(f"{Colors.GREEN}✓{Colors.NC} 管理员账号已存在: admin")


def collect_static(venv_python: Path):
    """收集静态文件"""
    logger.info("正在收集静态文件...")
    subprocess.run(
        [str(venv_python), "manage.py", "collectstatic", "--noinput", "--clear"],
        capture_output=True
    )
    logger.info(f"{Colors.GREEN}✓{Colors.NC} 静态文件已收集")


def start_server(venv_python: Path, port: int = 8000):
    """启动服务器"""
    logger.info(f"{Colors.BOLD}🚀 服务已启动!{Colors.NC}")
    print(f"""
{Colors.GREEN}═══════════════════════════════════════════════════
  📖 API 服务:   http://localhost:{port}
  📋 API 文档:   http://localhost:{port}/api/docs/
  🔧 系统后台:  http://localhost:{port}/sys-admin
  ⚙️  配置管理:  登录后台后在'系统配置'中修改
═══════════════════════════════════════════════════{Colors.NC}
""")
    print(f"{Colors.BLUE}按 Ctrl+C 停止服务{Colors.NC}\n")

    try:
        subprocess.run(
            [str(venv_python), "-m", "granian", "novel_reader.asgi:application",
             "--host", "0.0.0.0", "--port", str(port), "--interface", "asginl", "--workers", "1"]
        )
    except KeyboardInterrupt:
        logger.info(f"{Colors.YELLOW}服务已停止{Colors.NC}")


def main():
    parser = argparse.ArgumentParser(description="Novel Reader 一键启动脚本")
    parser.add_argument("--port", type=int, default=8000, help="服务端口 (default: 8000)")
    args = parser.parse_args()

    print_banner()

    # 步骤1：检查Python版本
    print(f"{Colors.CYAN}[1/8]{Colors.NC} {Colors.BOLD}环境检查{Colors.NC}")
    check_python_version()

    # 步骤2：创建虚拟环境
    print(f"\n{Colors.CYAN}[2/8]{Colors.NC} {Colors.BOLD}虚拟环境{Colors.NC}")
    venv_dir = create_virtual_environment()
    venv_python = get_venv_python(venv_dir)

    # 步骤3：安装依赖
    print(f"\n{Colors.CYAN}[3/8]{Colors.NC} {Colors.BOLD}安装依赖{Colors.NC}")
    install_dependencies(venv_python)

    # 步骤4：确保.env存在
    print(f"\n{Colors.CYAN}[4/8]{Colors.NC} {Colors.BOLD}配置初始化{Colors.NC}")
    ensure_env_file()

    # 步骤5：运行数据库迁移
    print(f"\n{Colors.CYAN}[5/8]{Colors.NC} {Colors.BOLD}数据库迁移{Colors.NC}")
    run_migrations(venv_python)

    # 步骤6：初始化系统配置
    print(f"\n{Colors.CYAN}[6/8]{Colors.NC} {Colors.BOLD}系统配置{Colors.NC}")
    initialize_configs(venv_python)

    # 步骤7：创建默认管理员
    print(f"\n{Colors.CYAN}[7/8]{Colors.NC} {Colors.BOLD}创建管理员{Colors.NC}")
    create_superuser(venv_python)

    # 步骤8：收集静态文件并启动服务
    print(f"\n{Colors.CYAN}[8/8]{Colors.NC} {Colors.BOLD}启动服务{Colors.NC}")
    collect_static(venv_python)
    start_server(venv_python, args.port)


if __name__ == "__main__":
    main()
