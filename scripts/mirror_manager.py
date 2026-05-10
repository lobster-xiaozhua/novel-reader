#!/usr/bin/env python3
"""
智能镜像源管理器
自动检测可用镜像源并切换，加快部署速度

支持:
- Python (pip/conda)
- Node.js (npm/yarn/pnpm)
- Docker (镜像加速)
"""

import os
import sys
import json
import asyncio
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import urllib.request
import urllib.error


class MirrorStatus(str, Enum):
    AVAILABLE = "available"
    SLOW = "slow"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class Mirror:
    name: str
    url: str
    country: str
    priority: int = 100


@dataclass
class MirrorTestResult:
    mirror: Mirror
    status: MirrorStatus
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class MirrorManager:
    def __init__(self):
        self.system = platform.system().lower()
        self.is_china = self._detect_china()

    def _detect_china(self) -> bool:
        try:
            result = subprocess.run(
                ["curl", "-s", "ipinfo.io", "--max-time", "3"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("country") == "CN"
        except Exception:
            pass

        locale = os.environ.get("LANG", "").lower()
        lang = os.environ.get("LANGUAGE", "").lower()
        return "cn" in locale or "cn" in lang

    def _test_url(self, url: str, timeout: int = 5) -> Tuple[MirrorStatus, Optional[float]]:
        try:
            import time
            start = time.time()
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            urllib.request.urlopen(req, timeout=timeout)
            latency = (time.time() - start) * 1000
            return MirrorStatus.AVAILABLE, latency
        except urllib.error.HTTPError:
            return MirrorStatus.AVAILABLE, None
        except Exception as e:
            return MirrorStatus.UNAVAILABLE, None


class PythonMirrorManager(MirrorManager):
    PYPI_ORIGIN = "https://pypi.org/simple"
    PIP_CONFIG_FILE = Path.home() / ".pip" / "pip.conf"
    PIP_CONFIG_FILE_OLD = Path.home() / ".pip" / "pip.ini"

    MIRRORS = {
        "china": [
            Mirror("阿里云", "https://mirrors.aliyun.com/pypi/simple/", "CN", 1),
            Mirror("清华", "https://pypi.tuna.tsinghua.edu.cn/simple", "CN", 2),
            Mirror("腾讯云", "https://mirrors.cloud.tencent.com/pypi/simple", "CN", 3),
            Mirror("华为云", "https://repo.huaweicloud.com/repository/pypi/simple", "CN", 4),
            Mirror("中科大", "https://pypi.mirrors.ustc.edu.cn/simple", "CN", 5),
        ],
        "global": [
            Mirror("PyPI官方", "https://pypi.org/simple", "US", 1),
            Mirror("PyPI镜像", "https://files.pythonhosted.org", "US", 2),
        ]
    }

    def get_current_mirror(self) -> Optional[str]:
        config_file = self.PIP_CONFIG_FILE if self.PIP_CONFIG_FILE.exists() else self.PIP_CONFIG_FILE_OLD
        if not config_file.exists():
            return None

        try:
            content = config_file.read_text()
            for line in content.split("\n"):
                if line.startswith("index-url"):
                    return line.split("=", 1)[1].strip()
        except Exception:
            pass
        return None

    def test_mirrors(self, mirrors: List[Mirror] = None) -> List[MirrorTestResult]:
        if mirrors is None:
            mirrors = self.MIRRORS["china"] if self.is_china else self.MIRRORS["global"]

        results = []
        for mirror in mirrors:
            status, latency = self._test_url(mirror.url, timeout=3)
            results.append(MirrorTestResult(mirror, status, latency))
        return sorted(results, key=lambda x: (x.status != MirrorStatus.AVAILABLE, x.latency_ms or 9999))

    def set_mirror(self, mirror: Mirror) -> bool:
        try:
            self.PIP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            config_content = f"""[global]
index-url = {mirror.url}
timeout = 60

[install]
trusted-host = {mirror.url.replace("https://", "").replace("http://", "").rstrip("/")}
"""
            self.PIP_CONFIG_FILE.write_text(config_content)
            return True
        except Exception as e:
            print(f"设置 pip 镜像失败: {e}")
            return False

    def auto_configure(self) -> Optional[Mirror]:
        mirrors = self.MIRRORS["china"] if self.is_china else self.MIRRORS["global"]
        print(f"[{'✓' if self.is_china else '✗'}] 检测到地区: {'中国' if self.is_china else '海外'}")

        print("正在测试镜像源...")
        results = self.test_mirrors(mirrors)

        for result in results[:3]:
            if result.status == MirrorStatus.AVAILABLE:
                print(f"  {result.mirror.name}: {result.latency_ms:.0f}ms")
            else:
                print(f"  {result.mirror.name}: 不可用")

        best = next((r for r in results if r.status == MirrorStatus.AVAILABLE), None)
        if best:
            print(f"\n选择最佳镜像: {best.mirror.name}")
            if self.set_mirror(best.mirror):
                return best.mirror

        return None


class NodeMirrorManager(MirrorManager):
    NPM_CONFIG_FILE = Path.home() / ".npmrc"
    YARN_CONFIG_FILE = Path.home() / ".yarnrc"
    PNPM_CONFIG_FILE = Path.home() / ".npmrc"

    NPM_MIRRORS = {
        "china": [
            Mirror("淘宝npm", "https://registry.npmmirror.com", "CN", 1),
            Mirror("腾讯npm", "https://mirrors.cloud.tencent.com/npm", "CN", 2),
            Mirror("华为npm", "https://repo.huaweicloud.com/repository/npm", "CN", 3),
        ],
        "global": [
            Mirror("npm官方", "https://registry.npmjs.org", "US", 1),
        ]
    }

    YARN_MIRRORS = {
        "china": [
            Mirror("淘宝Yarn", "https://registry.npmmirror.com", "CN", 1),
        ],
        "global": [
            Mirror("Yarn官方", "https://registry.yarnpkg.com", "US", 1),
        ]
    }

    PNPM_MIRRORS = NPM_MIRRORS

    def test_npm_mirrors(self) -> List[MirrorTestResult]:
        mirrors = self.NPM_MIRRORS["china"] if self.is_china else self.NPM_MIRRORS["global"]
        results = []
        for mirror in mirrors:
            test_url = mirror.url + "/express"
            status, latency = self._test_url(test_url, timeout=3)
            results.append(MirrorTestResult(mirror, status, latency))
        return sorted(results, key=lambda x: (x.status != MirrorStatus.AVAILABLE, x.latency_ms or 9999))

    def set_npm_mirror(self, mirror: Mirror) -> bool:
        try:
            self.NPM_CONFIG_FILE.write_text(f"registry={mirror.url}\n")
            return True
        except Exception as e:
            print(f"设置 npm 镜像失败: {e}")
            return False

    def set_yarn_mirror(self, mirror: Mirror) -> bool:
        try:
            self.YARN_CONFIG_FILE.write_text(f'registry "{mirror.url}"\n')
            return True
        except Exception as e:
            print(f"设置 yarn 镜像失败: {e}")
            return False

    def set_pnpm_mirror(self, mirror: Mirror) -> bool:
        try:
            self.PNPM_CONFIG_FILE.write_text(f"registry={mirror.url}\n")
            subprocess.run(["pnpm", "config", "set", "registry", mirror.url], capture_output=True)
            return True
        except Exception as e:
            print(f"设置 pnpm 镜像失败: {e}")
            return False

    def auto_configure_npm(self) -> Optional[Mirror]:
        print(f"[{'✓' if self.is_china else '✗'}] 检测到地区: {'中国' if self.is_china else '海外'}")

        print("正在测试 npm 镜像源...")
        results = self.test_npm_mirrors()

        for result in results[:3]:
            if result.status == MirrorStatus.AVAILABLE:
                print(f"  {result.mirror.name}: {result.latency_ms:.0f}ms")
            else:
                print(f"  {result.mirror.name}: 不可用")

        best = next((r for r in results if r.status == MirrorStatus.AVAILABLE), None)
        if best:
            print(f"\n选择最佳 npm 镜像: {best.mirror.name}")
            self.set_npm_mirror(best.mirror)
            return best.mirror
        return None


class DockerMirrorManager(MirrorManager):
    DOCKER_CONFIG_FILE = Path.home() / ".docker" / "daemon.json"

    MIRRORS = {
        "china": [
            "https://docker.1ms.run",
            "https://docker.xuanyuan.me",
            "https://docker.m.daocloud.io",
        ],
        "global": []
    }

    def get_current_config(self) -> Dict:
        if not self.DOCKER_CONFIG_FILE.exists():
            return {}
        try:
            return json.loads(self.DOCKER_CONFIG_FILE.read_text())
        except Exception:
            return {}

    def set_docker_mirrors(self, mirrors: List[str]) -> bool:
        try:
            self.DOCKER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            config = self.get_current_config()
            config["registry-mirrors"] = mirrors

            self.DOCKER_CONFIG_FILE.write_text(json.dumps(config, indent=2))
            return True
        except Exception as e:
            print(f"设置 Docker 镜像加速失败: {e}")
            return False

    def test_docker_mirrors(self) -> List[MirrorTestResult]:
        results = []
        for url in self.MIRRORS["china"]:
            status, latency = self._test_url(url, timeout=3)
            results.append(MirrorTestResult(
                Mirror(url, url, "CN"),
                status,
                latency
            ))
        return sorted(results, key=lambda x: (x.status != MirrorStatus.AVAILABLE, x.latency_ms or 9999))

    def auto_configure(self) -> Optional[List[str]]:
        if not self.is_china:
            print("海外用户无需配置 Docker 镜像加速")
            return None

        print("正在测试 Docker 镜像加速器...")
        results = self.test_docker_mirrors()

        available = [r for r in results if r.status == MirrorStatus.AVAILABLE]
        if not available:
            print("所有 Docker 镜像加速器均不可用")
            return None

        for result in available[:3]:
            print(f"  {result.mirror.name}: {result.latency_ms:.0f}ms")

        working_mirrors = [r.mirror.url for r in available]
        print(f"\n配置 Docker 镜像加速器: {working_mirrors[0]}")

        if self.set_docker_mirrors(working_mirrors[:3]):
            print("✓ Docker 镜像加速配置成功")
            print("  请运行: sudo systemctl restart docker")
            return working_mirrors

        return None


class DepInstaller:
    def __init__(self):
        self.python_mgr = PythonMirrorManager()
        self.node_mgr = NodeMirrorManager()
        self.docker_mgr = DockerMirrorManager()

    def configure_all(self):
        print("=" * 50)
        print("  智能镜像源配置")
        print("=" * 50)
        print()

        print("━━━ Python (pip) ━━━")
        self.python_mgr.auto_configure()
        print()

        print("━━━ Node.js (npm) ━━━")
        self.node_mgr.auto_configure_npm()
        print()

        print("━━━ Docker ━━━")
        self.docker_mgr.auto_configure()
        print()

        print("=" * 50)
        print("  镜像源配置完成!")
        print("=" * 50)

    def install_python_deps(self, requirements_file: str = "backend/requirements.txt"):
        req_path = Path(requirements_file)
        if not req_path.exists():
            print(f"requirements.txt 不存在: {requirements_file}")
            return False

        print(f"安装 Python 依赖: {requirements_file}")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_path)],
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"pip 安装失败: {e}")
            return False

    def install_node_deps(self, package_json: str = "frontend/package.json"):
        pkg_path = Path(package_json)
        if not pkg_path.exists():
            print(f"package.json 不存在: {package_json}")
            return False

        print(f"安装 Node.js 依赖: {package_json}")
        try:
            if self._command_exists("pnpm"):
                cmd = ["pnpm", "install"]
            elif self._command_exists("yarn"):
                cmd = ["yarn", "install"]
            else:
                cmd = ["npm", "install"]

            subprocess.run(cmd, check=True, cwd=pkg_path.parent)
            return True
        except subprocess.CalledProcessError as e:
            print(f"npm 安装失败: {e}")
            return False

    def _command_exists(self, cmd: str) -> bool:
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            return True
        except Exception:
            return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="智能镜像源管理器")
    parser.add_argument("--configure", "-c", action="store_true", help="配置所有镜像源")
    parser.add_argument("--python", action="store_true", help="仅配置 Python 镜像")
    parser.add_argument("--node", action="store_true", help="仅配置 Node.js 镜像")
    parser.add_argument("--docker", action="store_true", help="仅配置 Docker 镜像")
    parser.add_argument("--install-py", metavar="FILE", help="安装 Python 依赖")
    parser.add_argument("--install-node", metavar="FILE", help="安装 Node 依赖")
    parser.add_argument("--status", "-s", action="store_true", help="显示当前镜像配置")

    args = parser.parse_args()

    installer = DepInstaller()

    if args.status:
        print("━━━ Python (pip) ━━━")
        current = installer.python_mgr.get_current_mirror()
        print(f"  当前镜像: {current or '官方 (pypi.org)'}")
        print()
        print("━━━ Docker ━━━")
        config = installer.docker_mgr.get_current_config()
        mirrors = config.get("registry-mirrors", [])
        if mirrors:
            print(f"  已配置镜像加速: {mirrors}")
        else:
            print("  未配置镜像加速")
        return

    if args.configure or (not args.python and not args.node and not args.docker):
        installer.configure_all()
        return

    if args.python:
        installer.python_mgr.auto_configure()

    if args.node:
        installer.node_mgr.auto_configure_npm()

    if args.docker:
        installer.docker_mgr.auto_configure()

    if args.install_py:
        installer.install_python_deps(args.install_py)

    if args.install_node:
        installer.install_node_deps(args.install_node)


if __name__ == "__main__":
    main()
