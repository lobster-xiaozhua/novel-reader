#!/bin/bash
# Novel Reader - Linux/macOS Deployment Script
# Supported package managers: apt/yum/dnf/zypper/pacman

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USE_DOCKER=false
SKIP_INSTALL=false
USE_VENV=true

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -d, --docker      Use Docker deployment"
    echo "  -n, --native      Native Python deployment (default)"
    echo "  -s, --skip        Skip dependency installation"
    echo "  -h, --help        Show this help"
    echo ""
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--docker)
            USE_DOCKER=true
            shift
            ;;
        -n|--native)
            USE_DOCKER=false
            shift
            ;;
        -s|--skip)
            SKIP_INSTALL=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo -e "${MAGENTA}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║         Novel Reader - Linux Deployment Script v1.0        ║
║  Support: apt/yum/dnf/zypper/pacman + Docker               ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

log_step() {
    echo -e "\n${CYAN}=== $1 ===${NC}"
}

log_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

log_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

detect_os() {
    if check_command apt-get; then
        echo "debian"
    elif check_command yum; then
        echo "rhel"
    elif check_command dnf; then
        echo "fedora"
    elif check_command zypper; then
        echo "suse"
    elif check_command pacman; then
        echo "arch"
    elif check_command apk; then
        echo "alpine"
    else
        echo "unknown"
    fi
}

install_system_deps() {
    local os_type="$1"
    log_step "Installing system dependencies"

    case "$os_type" in
        debian)
            log_step "Detected Debian/Ubuntu"
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv \
                libmagic1 libxml2 libxslt1.1 zlib1g \
                build-essential pkg-config \
                curl redis-server
            ;;
        rhel|centos)
            log_step "Detected RHEL/CentOS"
            sudo yum install -y python3 python3-pip \
                file-devel libxml2-devel libxslt-devel zlib-devel \
                gcc gcc-c++ \
                curl redis
            sudo systemctl enable redis
            ;;
        fedora)
            log_step "Detected Fedora"
            sudo dnf install -y python3 python3-pip \
                file-devel libxml2-devel libxslt-devel zlib-devel \
                gcc gcc-c++ \
                curl redis
            sudo systemctl enable redis
            ;;
        suse)
            log_step "Detected openSUSE"
            sudo zypper install -y python3 python3-pip \
                file-devel libxml2-devel libxslt-devel zlib-devel \
                gcc gcc-c++ \
                curl redis
            ;;
        arch)
            log_step "Detected Arch Linux"
            sudo pacman -Sy --noconfirm python python-pip \
                libmagic libxml2 libxslt zlib \
                base-devel \
                curl redis
            sudo systemctl enable redis
            ;;
        alpine)
            log_step "Detected Alpine"
            apk add --no-cache python3 py3-pip \
                file libxml2-dev libxslt-dev zlib-dev \
                gcc musl-dev python3-dev \
                curl redis
            ;;
        *)
            log_warning "Cannot detect OS type, please install manually:"
            log_warning "  Python 3.10+, pip, build-essential"
            log_warning "  libmagic, libxml2, libxslt, zlib"
            ;;
    esac

    if check_command python3; then
        local py_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        log_success "Python version: $py_version"
    fi
}

install_python_deps() {
    log_step "Installing Python dependencies"

    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        log_step "Creating virtual environment"
        python3 -m venv "$PROJECT_ROOT/venv"
        log_success "Virtual environment created"
    else
        log_warning "Virtual environment exists, skipping"
    fi

    source "$PROJECT_ROOT/venv/bin/activate"

    log_step "Upgrading pip and installing wheel"
    pip install --upgrade pip wheel setuptools

    log_step "Installing project dependencies"
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/requirements.txt"
    elif [ -f "$PROJECT_ROOT/backend/requirements-crossplatform.txt" ]; then
        pip install -r "$PROJECT_ROOT/backend/requirements-crossplatform.txt"
    elif [ -f "$PROJECT_ROOT/backend/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/backend/requirements.txt"
    fi

    log_success "Python dependencies installed"
    deactivate
}

init_data_dirs() {
    log_step "Initializing data directories"
    mkdir -p "$PROJECT_ROOT/data"/{books,index,static,logs,cache}
    log_success "Data directories initialized"
}

setup_env_file() {
    log_step "Configuring environment variables"
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            log_success ".env file created, please set SECRET_KEY"
        else
            cat > "$PROJECT_ROOT/.env" << 'ENVEOF'
SECRET_KEY=change-me-in-production
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///data/novel.db
REDIS_URL=redis://localhost:6379
ENVEOF
            log_success ".env file created"
        fi
    else
        log_warning ".env file exists"
    fi
}

start_redis() {
    if check_command redis-server; then
        log_step "Starting Redis service"
        if check_command systemctl; then
            sudo systemctl start redis 2>/dev/null || sudo systemctl start redis-server 2>/dev/null || true
        fi
        if ! pgrep -x redis-server > /dev/null; then
            redis-server --daemonize yes --maxmemory 64mb --maxmemory-policy allkeys-lru 2>/dev/null || true
        fi
        log_success "Redis service started"
    fi
}

start_backend() {
    log_step "Starting backend service"
    source "$PROJECT_ROOT/venv/bin/activate"

    export PYTHONPATH="$PROJECT_ROOT/backend:$PROJECT_ROOT"
    export DATA_DIR="$PROJECT_ROOT/data"
    export BOOKS_DIR="$PROJECT_ROOT/data/books"
    export LOG_LEVEL="INFO"

    cd "$PROJECT_ROOT/backend"

    echo ""
    log_success "Start command: python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""

    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

deploy_docker() {
    log_step "Using Docker deployment"

    if ! check_command docker; then
        log_error "Docker not installed"
        exit 1
    fi

    if ! check_command docker-compose && ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose not installed"
        exit 1
    fi

    log_step "Building Docker image"
    docker-compose build

    log_step "Starting services"
    docker-compose up -d

    log_step "Waiting for services"
    sleep 10

    log_step "Service status"
    docker-compose ps

    log_success "Deployment complete!"
    echo ""
    echo -e "Access URLs:"
    echo -e "  ${CYAN}Frontend: http://localhost:80${NC}"
    echo -e "  ${CYAN}Backend: http://localhost:8000${NC}"
    echo -e "  ${CYAN}API Docs: http://localhost:8000/docs${NC}"
}

main() {
    local os_type=$(detect_os)
    echo -e "${GREEN}Detected OS: $os_type${NC}"

    if [ "$USE_DOCKER" = true ]; then
        deploy_docker
    else
        if [ "$SKIP_INSTALL" = false ]; then
            install_system_deps "$os_type"
            install_python_deps
        fi

        init_data_dirs
        setup_env_file
        start_redis
        start_backend
    fi
}

main
