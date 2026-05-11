#!/usr/bin/env python3
"""
Novel Reader - Cross-Platform Deployment Entry
Auto-detect platform and select optimal deployment method

Supported platforms:
- Windows: PowerShell deployment script
- Linux/macOS: Bash deployment script
- Termux (Android): Dedicated Bash deployment script
- Docker: Docker Compose deployment
"""

import sys
import os
import subprocess
import platform
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()

PLATFORMS = {
    "windows": {
        "name": "Windows",
        "scripts": ["deploy.ps1"],
        "shell": "powershell",
        "args": ["-ExecutionPolicy", "Bypass", "-File"]
    },
    "linux": {
        "name": "Linux/macOS",
        "scripts": ["deploy.sh"],
        "shell": "bash",
        "args": []
    },
    "termux": {
        "name": "Termux (Android)",
        "scripts": ["deploy-termux.sh"],
        "shell": "bash",
        "args": []
    },
    "docker": {
        "name": "Docker",
        "scripts": [],
        "shell": None,
        "args": []
    }
}

REQUIREMENTS_FILES = [
    "requirements.txt",
    "backend/requirements-crossplatform.txt",
    "backend/requirements.txt"
]


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           Novel Reader - Cross-Platform Deploy Tool v1.0   ║
║  Auto-detect system and select optimal deployment method   ║
╚══════════════════════════════════════════════════════════════╝
    """)


def detect_platform():
    """Detect current platform"""
    system = platform.system().lower()

    if system == "windows":
        return "windows"
    elif system == "linux":
        if is_termux():
            return "termux"
        return "linux"
    elif system == "darwin":
        return "linux"
    else:
        return "linux"


def is_termux():
    """Check if running in Termux environment"""
    prefix = os.environ.get("PREFIX", "")
    return "com.termux" in prefix or os.path.exists("/data/data/com.termux")


def has_docker():
    """Check if Docker is available"""
    return shutil.which("docker") is not None


def has_docker_compose():
    """Check if Docker Compose is available"""
    if shutil.which("docker-compose"):
        return True
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def find_script(scripts):
    """Find available script file"""
    for script in scripts:
        script_path = SCRIPT_DIR / script
        if script_path.exists():
            return script_path
    return None


def check_requirements():
    """Check requirements files"""
    print("\nChecking project files...")

    for req_file in REQUIREMENTS_FILES:
        req_path = SCRIPT_DIR / req_file
        if req_path.exists():
            print(f"  [OK] Found requirements: {req_file}")
            return True

    print(f"  [WARN] No requirements file found")
    return False


def check_python():
    """Check Python environment"""
    print("\nChecking Python environment...")

    python_cmd = None
    python_version = None

    for cmd in ["python3", "python"]:
        python_path = shutil.which(cmd)
        if python_path:
            python_cmd = cmd
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                python_version = result.stdout.strip() or result.stderr.strip()
            except Exception:
                pass
            break

    if python_cmd:
        print(f"  [OK] Python: {python_version}")
        return python_cmd
    else:
        print(f"  [ERROR] Python not installed")
        return None


def run_powershell(script_path, args=None):
    """Run PowerShell script"""
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
    if args:
        cmd.extend(args)

    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        print("\nDeployment cancelled")
        return 1


def run_bash(script_path, args=None):
    """Run Bash script"""
    cmd = ["bash", str(script_path)]
    if args:
        cmd.extend(args)

    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        print("\nDeployment cancelled")
        return 1


def run_docker():
    """Run Docker deployment"""
    print("\nUsing Docker deployment...")

    compose_file = SCRIPT_DIR / "docker-compose.yml"
    if not compose_file.exists():
        print("  [ERROR] docker-compose.yml not found")
        return 1

    print("  Building image: docker-compose build")
    result = subprocess.run(["docker-compose", "build"], cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print("  [ERROR] Docker build failed")
        return 1

    print("  Starting services: docker-compose up -d")
    result = subprocess.run(["docker-compose", "up", "-d"], cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print("  [ERROR] Docker start failed")
        return 1

    print("\n  [OK] Docker deployment complete!")
    print("  Access URLs:")
    print("    Frontend: http://localhost:80")
    print("    Backend: http://localhost:8000")
    print("    API Docs: http://localhost:8000/docs")

    return 0


def main():
    print_banner()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode in ["-h", "--help"]:
            print("Usage: python deploy.py [options]")
            print("")
            print("Options:")
            print("  -h, --help       Show this help")
            print("  --docker         Use Docker deployment")
            print("  --native         Use native Python deployment")
            print("  --check          Check environment only")
            return 0

        if mode == "--check":
            check_requirements()
            check_python()
            return 0

        detected = detect_platform()

        if mode == "--docker":
            return run_docker()
        elif mode == "--native":
            pass
        else:
            print(f"Unknown option: {mode}")
            return 1
    else:
        detected = detect_platform()

    platform_info = PLATFORMS[detected]
    print(f"\nDetected platform: {platform_info['name']}")

    if has_docker() and has_docker_compose():
        print("\nDocker is available. Use Docker deployment?")
        print("  [1] Docker deployment (Recommended)")
        print("  [2] Native Python deployment")
        print("  [Other] Exit")

        choice = input("\nPlease select [1]: ").strip() or "1"

        if choice == "1":
            return run_docker()
        elif choice == "2":
            pass
        else:
            print("Cancelled")
            return 0

    print(f"\nUsing {platform_info['name']} native deployment...")

    script = find_script(platform_info["scripts"])
    if script:
        if detected == "windows":
            args = sys.argv[2:] if len(sys.argv) > 2 else []
            return run_powershell(script, args)
        else:
            args = sys.argv[2:] if len(sys.argv) > 2 else []
            os.chmod(script, 0o755)
            return run_bash(script, args)
    else:
        print(f"  [ERROR] Deployment script not found")
        print(f"  Please run manually:")
        if detected == "windows":
            print("    .\\deploy.ps1")
        else:
            print("    bash deploy.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())
