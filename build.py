#!/usr/bin/env python3
"""Universal App Builder - 通用应用构建系统

支持自动检测项目结构，构建前端/后端，打包发布。
集成 Gitee MCP 实现仓库管理与 Release 创建。

用法:
  python build.py              # 完整构建 + 打包
  python build.py --frontend   # 仅构建前端
  python build.py --backend    # 仅构建后端
  python build.py --package    # 仅打包
  python build.py --version x.y.z  # 指定版本号
  python build.py --dry-run    # 模拟运行，不执行实际操作
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

R = "\033[0;31m"
G = "\033[0;32m"
Y = "\033[1;33m"
B = "\033[0;34m"
C = "\033[0;36m"
M = "\033[0;35m"
D = "\033[2m"
BD = "\033[1m"
NC = "\033[0m"

_step = 0
_total = 0
_timer = 0


def _elapsed():
    return int(time.time() - _timer)


def _fmt_dur(s):
    return f"{s // 60}m{s % 60}s" if s >= 60 else f"{s}s"


def log_info(msg):
    print(f"  {B}ℹ{NC} {msg}")


def log_ok(msg):
    print(f"  {G}✓{NC} {msg}")


def log_warn(msg):
    print(f"  {Y}⚠{NC} {msg}")


def log_err(msg):
    print(f"  {R}✗{NC} {msg}")


def log_detail(msg):
    print(f"  {D}→ {msg}{NC}")


def step(title):
    global _step, _timer
    _step += 1
    print(f"\n{BD}{C}[{_step}/{_total}]{NC} {BD}{title}{NC}")
    _timer = time.time()


def step_done():
    print(f"  {G}✓{NC} {D}完成 ({_fmt_dur(_elapsed())}){NC}")


def run(cmd, cwd=None, capture=False, check=True):
    if capture:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if check and r.returncode != 0:
            raise BuildError(f"命令失败: {cmd}\n{r.stderr.strip()}")
        return r.stdout.strip()
    r = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and r.returncode != 0:
        raise BuildError(f"命令失败: {cmd} (exit={r.returncode})")
    return None


class BuildError(Exception):
    pass


class ProjectDetector:
    def __init__(self, root):
        self.root = Path(root)
        self.has_frontend = (self.root / "frontend" / "package.json").exists()
        self.has_django = (self.root / "manage.py").exists()
        self.has_docker = (self.root / "Dockerfile").exists()
        self.has_requirements = (self.root / "requirements.txt").exists()
        self.project_name = self._detect_name()

    def _detect_name(self):
        if self.has_django:
            for p in self.root.iterdir():
                if p.is_dir() and (p / "settings.py").exists() and p.name != "apps":
                    return p.name
        if (self.root / "setup.py").exists() or (self.root / "pyproject.toml").exists():
            return self.root.name
        return self.root.name

    @property
    def summary(self):
        parts = []
        if self.has_django:
            parts.append("Django")
        if self.has_frontend:
            parts.append("Frontend")
        if self.has_docker:
            parts.append("Docker")
        return " + ".join(parts) if parts else "Unknown"


class Builder:
    def __init__(self, root, version=None, dry_run=False, frontend_only=False, backend_only=False, package_only=False):
        self.root = Path(root)
        self.detector = ProjectDetector(root)
        self.version = version or self._auto_version()
        self.dry_run = dry_run
        self.frontend_only = frontend_only
        self.backend_only = backend_only
        self.package_only = package_only
        self.build_dir = self.root / "dist"
        self.artifact = None
        self.build_info = {
            "version": self.version,
            "project": self.detector.project_name,
            "type": self.detector.summary,
            "timestamp": datetime.now().isoformat(),
            "steps": [],
        }

    def _auto_version(self):
        try:
            v = run("git describe --tags --abbrev=0 2>/dev/null", capture=True, check=False)
            if v:
                return v.lstrip("v")
            h = run("git rev-parse --short HEAD 2>/dev/null", capture=True, check=False)
            if h:
                return f"0.1.0-dev.{h}"
        except Exception:
            pass
        return datetime.now().strftime("0.1.0-dev.%Y%m%d%H%M")

    def _record(self, name, status, detail=""):
        self.build_info["steps"].append({"name": name, "status": status, "detail": detail, "time": _elapsed()})

    def build(self):
        global _total
        tasks = []
        if not self.package_only:
            if not self.backend_only and self.detector.has_frontend:
                tasks.append("frontend")
            if not self.frontend_only and self.detector.has_django:
                tasks.append("backend")
        tasks.append("package")
        _total = len(tasks)

        self._print_banner()
        self._step_env()

        for t in tasks:
            try:
                if t == "frontend":
                    self._step_frontend()
                elif t == "backend":
                    self._step_backend()
                elif t == "package":
                    self._step_package()
            except BuildError as e:
                self._record(t, "failed", str(e))
                log_err(str(e))
                self._save_build_info()
                sys.exit(1)

        self._save_build_info()
        self._print_summary()
        return self.build_info

    def _print_banner(self):
        print(f"""
{M}╔═══════════════════════════════════════════════════════╗{NC}
{M}║{NC}  {C}Universal App Builder v1.0{NC}                      {M}║{NC}
{M}║{NC}  {D}项目: {BD}{self.detector.project_name}{NC} {D}类型: {BD}{self.detector.summary}{NC}    {M}║{NC}
{M}║{NC}  {D}版本: {BD}{self.version}{NC}                              {M}║{NC}
{M}╚═════════════════════════════════════════════════════╝{NC}""")

    def _step_env(self):
        step("环境检查")
        errors = 0
        if self.detector.has_frontend or self.frontend_only:
            try:
                v = run("node --version", capture=True)
                log_ok(f"Node {v}")
            except Exception:
                log_err("Node.js 未安装")
                errors += 1
            try:
                v = run("npm --version", capture=True)
                log_ok(f"npm {v}")
            except Exception:
                log_err("npm 未安装")
                errors += 1
        if self.detector.has_django or self.backend_only:
            try:
                v = run("python3 --version", capture=True)
                log_ok(v)
            except Exception:
                log_err("Python3 未安装")
                errors += 1
        if errors:
            raise BuildError(f"环境检查失败: {errors} 项缺失")
        step_done()

    def _step_frontend(self):
        step("构建前端")
        fe_dir = self.root / "frontend"
        if not (fe_dir / "node_modules").exists():
            log_info("安装 Node 依赖...")
            if self.dry_run:
                log_warn("[DRY-RUN] 跳过 npm install")
            else:
                out = run("npm install --registry https://registry.npmmirror.com", cwd=str(fe_dir), capture=True)
                added = [l for l in out.splitlines() if "added" in l]
                if added:
                    log_ok(added[0].strip())
                else:
                    log_ok("依赖安装完成")

        log_info("执行前端构建...")
        if self.dry_run:
            log_warn("[DRY-RUN] 跳过 npm run build")
        else:
            out = run("npm run build", cwd=str(fe_dir), capture=True)
            built = [l for l in out.splitlines() if "built in" in l]
            if built:
                log_ok(built[0].strip())
            else:
                log_ok("前端构建完成")

        dist = fe_dir / "dist"
        if dist.exists():
            files = list(dist.rglob("*"))
            log_detail(f"输出 {len([f for f in files if f.is_file()])} 个文件到 {dist.relative_to(self.root)}")
        self._record("frontend", "success")
        step_done()

    def _step_backend(self):
        step("构建后端")
        venv = self.root / "venv"
        python = str(venv / "bin" / "python") if venv.exists() else "python3"

        if self.detector.has_requirements:
            if venv.exists():
                log_info("检查 Python 依赖...")
                if self.dry_run:
                    log_warn("[DRY-RUN] 跳过依赖检查")
                else:
                    try:
                        run(f"{python} -c 'import django'", capture=True)
                        log_ok("Python 依赖已就绪")
                    except BuildError:
                        log_info("安装 Python 依赖...")
                        run(f"{python} -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --quiet", cwd=str(self.root))

        if self.detector.has_django:
            log_info("收集静态文件...")
            if self.dry_run:
                log_warn("[DRY-RUN] 跳过 collectstatic")
            else:
                out = run(f"{python} manage.py collectstatic --noinput", cwd=str(self.root), capture=True)
                count = [l for l in out.splitlines() if "static file" in l.lower()]
                if count:
                    log_ok(count[0].strip())
                else:
                    log_ok("静态文件收集完成")

        self._record("backend", "success")
        step_done()

    def _step_package(self):
        step("打包发布")
        self.build_dir.mkdir(exist_ok=True)
        name = f"{self.detector.project_name}-v{self.version}"
        tar_path = self.build_dir / f"{name}.tar.gz"

        excludes = {
            "venv", "node_modules", "__pycache__", ".git", "data",
            "staticfiles", "dist", ".env", "*.pyc", ".idea", ".vscode",
            "*.sqlite3", "*.log", ".DS_Store",
        }

        def _filter(ti):
            parts = Path(ti.name).parts
            if len(parts) < 2:
                ti.name = f"{name}/{ti.name}"
                return ti
            rel = "/".join(parts[1:])
            for exc in excludes:
                if exc in parts or any(rel.endswith(e.lstrip("*")) for e in excludes if e.startswith("*")):
                    return None
            ti.name = f"{name}/{rel}"
            return ti

        if self.dry_run:
            log_warn(f"[DRY-RUN] 跳过打包 {tar_path.name}")
        else:
            log_info(f"打包到 {tar_path.name}...")
            with tarfile.open(str(tar_path), "w:gz") as tar:
                for item in self.root.iterdir():
                    if item.name in excludes or item.name.startswith("."):
                        continue
                    tar.add(str(item), filter=_filter)
            size_mb = tar_path.stat().st_size / 1024 / 1024
            log_ok(f"打包完成: {tar_path.name} ({size_mb:.1f}MB)")

        self.artifact = str(tar_path)
        info_path = self.build_dir / f"{name}-build-info.json"
        if not self.dry_run:
            with open(str(info_path), "w") as f:
                json.dump(self.build_info, f, indent=2, ensure_ascii=False)
            log_detail(f"构建信息: {info_path.name}")

        self._record("package", "success", str(tar_path))
        step_done()

    def _save_build_info(self):
        self.build_info["success"] = all(s["status"] == "success" for s in self.build_info["steps"])
        if not self.dry_run:
            self.build_dir.mkdir(exist_ok=True)
            info_path = self.build_dir / "latest-build-info.json"
            with open(str(info_path), "w") as f:
                json.dump(self.build_info, f, indent=2, ensure_ascii=False)

    def _print_summary(self):
        ok = all(s["status"] == "success" for s in self.build_info["steps"])
        icon = f"{G}✓{NC}" if ok else f"{R}✗{NC}"
        print(f"""
{G if ok else R}═══════════════════════════════════════════════════════{NC}
  {icon} 构建{'成功' if ok else '失败'}: {BD}{self.detector.project_name}{NC} v{BD}{self.version}{NC}
{G if ok else R}═══════════════════════════════════════════════════════{NC}
  {D}项目类型:{NC}  {self.detector.summary}
  {D}构建步骤:{NC}  {len(self.build_info['steps'])} 步
  {D}总耗时:{NC}    {_fmt_dur(sum(s['time'] for s in self.build_info['steps']))}
  {D}产物:{NC}      {self.artifact or 'N/A'}
""")


def main():
    parser = argparse.ArgumentParser(description="Universal App Builder", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", "-v", help="指定版本号 (默认自动检测)")
    parser.add_argument("--frontend", action="store_true", help="仅构建前端")
    parser.add_argument("--backend", action="store_true", help="仅构建后端")
    parser.add_argument("--package", action="store_true", help="仅打包")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    builder = Builder(
        root=root,
        version=args.version,
        dry_run=args.dry_run,
        frontend_only=args.frontend,
        backend_only=args.backend,
        package_only=args.package,
    )
    info = builder.build()
    if not info["success"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
